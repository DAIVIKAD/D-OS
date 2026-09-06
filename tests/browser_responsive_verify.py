import asyncio
import base64
import json
import os
import subprocess
import sys
import time
import urllib.request
import websockets
from decimal import Decimal
from unittest.mock import patch

# Mock data for rendering realistic pages
MOCK_USER = {
    "uid": "test_user_123",
    "email": "commander@dos.local",
    "username": "TERMINAL_COMMANDER",
    "currency": "₹",
    "monthly_budget": Decimal("20000"),
    "has_seen_onboarding": True,
    "categories": [
        {"id": "c1", "name": "Food & Dining", "kind": "expense", "color": "#39ff88", "icon": "🍕", "monthly_budget": Decimal("6000")},
        {"id": "c2", "name": "Salary / Tech", "kind": "income", "color": "#66FF99", "icon": "💰", "monthly_budget": Decimal("0")},
        {"id": "c3", "name": "Housing / Rent", "kind": "expense", "color": "#2ed573", "icon": "🏠", "monthly_budget": Decimal("10000")},
        {"id": "c4", "name": "Investments", "kind": "expense", "color": "#1e90ff", "icon": "📈", "monthly_budget": Decimal("4000")},
    ],
}

MOCK_TXS = [
    {"id": "t1", "type": "income", "amount": Decimal("65000"), "date": "2026-09-01", "category": {"name": "Salary / Tech", "icon": "💰"}, "category_id": "c2", "note": "Primary Engineering Payout"},
    {"id": "t2", "type": "expense", "amount": Decimal("10000"), "date": "2026-09-02", "category": {"name": "Housing / Rent", "icon": "🏠"}, "category_id": "c3", "note": "Terminal Flat Rent"},
    {"id": "t3", "type": "expense", "amount": Decimal("3850"), "date": "2026-09-03", "category": {"name": "Food & Dining", "icon": "🍕"}, "category_id": "c1", "note": "Command Center Groceries"},
    {"id": "t4", "type": "expense", "amount": Decimal("4000"), "date": "2026-09-04", "category": {"name": "Investments", "icon": "📈"}, "category_id": "c4", "note": "Index SIP Allocation"},
]

MOCK_GOALS = [
    {"id": "g1", "title": "Emergency Reserve", "target_amount": Decimal("100000"), "current_amount": Decimal("45000"), "deadline": "2026-12-31", "color": "#39ff88"}
]

MOCK_DEBTS = [
    {"id": "d1", "person": "Alex M.", "type": "lend", "amount": Decimal("5000"), "remaining": Decimal("5000"), "due_date": "2026-09-20", "note": "Hardware module"}
]

MOCK_RECURRING = [
    {"id": "r1", "name": "Fiber Uplink", "amount": Decimal("1299"), "frequency": "monthly", "category_id": "c3", "next_due": "2026-09-15", "active": True}
]

MOCK_INVESTMENTS = [
    {"id": "i1", "name": "Nifty Index", "type": "sip", "amount": Decimal("5000"), "expected_return": Decimal("12.5"), "tenure_years": 10}
]

MOCK_CUSTOM_BUDGETS = [
    {
        "id": "cb1",
        "name": "Tokyo Tech Summit",
        "total_budget": Decimal("50000"),
        "expenses": [
            {"id": "e1", "title": "Flights", "amount": Decimal("32000")},
            {"id": "e2", "title": "Conference Pass", "amount": Decimal("12000")}
        ]
    }
]

PAGES = [
    ("Dashboard", "/"),
    ("Ledger", "/money"),
    ("Analytics", "/visualize"),
    ("Budget", "/budget"),
    ("More", "/more"),
    ("Goals", "/goals"),
    ("Lend & Borrow", "/lend-borrow"),
    ("Recurring Payments", "/recurring"),
    ("Investment", "/investment"),
    ("Reports", "/reports"),
    ("Help", "/help"),
    ("About", "/about"),
    ("Settings", "/settings"),
    ("Login", "/login"),
]

VIEWPORTS = [
    ("360x800", 360, 800),
    ("375x812", 375, 812),
    ("390x844", 390, 844),
    ("414x896", 414, 896),
    ("430x932", 430, 932),
    ("768x1024", 768, 1024),
    ("900x768", 900, 768),
    ("1024x768", 1024, 768),
    ("1366x768", 1366, 768),
    ("1440x900", 1440, 900),
    ("1920x1080", 1920, 1080),
]

SCREENSHOT_TARGETS = [
    ("Dashboard", "375x812", "dashboard_mobile_375"),
    ("Dashboard", "1440x900", "dashboard_desktop_1440"),
    ("Ledger", "375x812", "ledger_mobile_375"),
    ("Ledger", "1440x900", "ledger_desktop_1440"),
    ("Analytics", "375x812", "analytics_mobile_375"),
    ("Analytics", "1440x900", "analytics_desktop_1440"),
    ("Budget", "375x812", "budget_mobile_375"),
    ("Budget", "1440x900", "budget_desktop_1440"),
    ("More", "375x812", "more_mobile_375"),
    ("More", "1440x900", "more_desktop_1440"),
    ("Settings", "375x812", "settings_mobile_375"),
    ("Settings", "1440x900", "settings_desktop_1440"),
    ("Login", "375x812", "login_mobile_375"),
    ("Login", "1440x900", "login_desktop_1440"),
]

ARTIFACT_DIR = "/Users/daivik/.gemini/antigravity/brain/6ee7624c-b439-4f50-8582-897c6d8e8c6d"
SCREENSHOT_DIR = os.path.join(ARTIFACT_DIR, "screenshots")
os.makedirs(SCREENSHOT_DIR, exist_ok=True)


class CDPClient:
    def __init__(self, ws_url):
        self.ws_url = ws_url
        self.ws = None
        self._msg_id = 0

    async def connect(self):
        self.ws = await websockets.connect(self.ws_url, max_size=25*1024*1024)

    async def close(self):
        if self.ws:
            await self.ws.close()

    async def send(self, method, params=None):
        self._msg_id += 1
        msg_id = self._msg_id
        payload = {"id": msg_id, "method": method}
        if params:
            payload["params"] = params
        await self.ws.send(json.dumps(payload))
        while True:
            resp_raw = await self.ws.recv()
            resp = json.loads(resp_raw)
            if resp.get("id") == msg_id:
                if "error" in resp:
                    raise RuntimeError(f"CDP Error for {method}: {resp['error']}")
                return resp.get("result", {})

    async def evaluate(self, expression):
        res = await self.send("Runtime.evaluate", {
            "expression": expression,
            "returnByValue": True,
            "awaitPromise": True
        })
        val = res.get("result", {}).get("value")
        return val

    async def set_viewport(self, width, height):
        is_mobile = width <= 840
        await self.send("Emulation.setDeviceMetricsOverride", {
            "width": width,
            "height": height,
            "deviceScaleFactor": 1,
            "mobile": is_mobile,
        })
        await self.send("Emulation.setTouchEmulationEnabled", {
            "enabled": is_mobile,
            "configuration": "mobile" if is_mobile else "desktop"
        })

    async def navigate(self, url):
        await self.send("Page.navigate", {"url": url})
        # Wait for page layout and fonts to settle
        await asyncio.sleep(0.35)

    async def capture_screenshot(self, filepath):
        res = await self.send("Page.captureScreenshot", {"format": "png"})
        img_bytes = base64.b64decode(res["data"])
        with open(filepath, "wb") as f:
            f.write(img_bytes)


def start_test_server(port=8765):
    """Start local test server using uvicorn and patched dependencies."""
    import uvicorn
    import threading
    from main import app

    # Apply patches
    p1 = patch("app.firebase.auth.optional_user", return_value=MOCK_USER)
    p2 = patch("app.services.firestore_service.list_transactions", return_value=MOCK_TXS)
    p3 = patch("app.services.firestore_service.list_goals", return_value=MOCK_GOALS)
    p4 = patch("app.services.firestore_service.list_debts", return_value=MOCK_DEBTS)
    p5 = patch("app.services.firestore_service.list_recurring", return_value=MOCK_RECURRING)
    p6 = patch("app.services.firestore_service.list_investments", return_value=MOCK_INVESTMENTS)
    p7 = patch("app.services.firestore_service.list_custom_budgets", return_value=MOCK_CUSTOM_BUDGETS)
    p8 = patch("app.services.firestore_service.log_report")

    p1.start()
    p2.start()
    p3.start()
    p4.start()
    p5.start()
    p6.start()
    p7.start()
    p8.start()

    config = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning")
    server = uvicorn.Server(config)
    t = threading.Thread(target=server.run, daemon=True)
    t.start()
    time.sleep(1.0)
    return server


async def run_verification():
    server_port = 8765
    server = start_test_server(server_port)
    print(f"[TEST SERVER] Running on http://127.0.0.1:{server_port}")

    # Start Chrome headless
    chrome_port = 9222
    profile_dir = os.path.join(ARTIFACT_DIR, "scratch", "chrome_verify_profile")
    os.makedirs(profile_dir, exist_ok=True)
    subprocess.run(["pkill", "-f", "chrome_verify_profile"], capture_output=True)
    time.sleep(0.5)

    chrome_cmd = [
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "--headless=new",
        f"--remote-debugging-port={chrome_port}",
        f"--user-data-dir={profile_dir}",
        "--disable-gpu",
        "--no-first-run",
        "--no-default-browser-check",
        "--disable-extensions",
        "--hide-scrollbars=false",
    ]

    print("[CHROME] Launching:", " ".join(chrome_cmd))
    chrome_proc = subprocess.Popen(chrome_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    # Wait for Chrome DevTools port to become accessible and find page target
    ws_url = None
    for attempt in range(25):
        time.sleep(0.4)
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{chrome_port}/json") as resp:
                data = json.loads(resp.read().decode("utf-8"))
                pages = [it for it in data if it.get("type") == "page"]
                if pages:
                    ws_url = pages[0].get("webSocketDebuggerUrl")
                    if ws_url:
                        break
        except Exception:
            continue

    if not ws_url:
        print("FAIL: Could not connect to Chrome DevTools page endpoint.")
        chrome_proc.terminate()
        return

    print(f"[CHROME] Connected via CDP: {ws_url}")
    cdp = CDPClient(ws_url)
    await cdp.connect()
    await cdp.send("Page.enable")
    await cdp.send("DOM.enable")

    # Set mock session cookie in browser
    await cdp.send("Network.enable")
    await cdp.send("Network.setCookie", {
        "name": "dos_session",
        "value": "mock_browser_verify_session",
        "domain": "127.0.0.1",
        "path": "/"
    })

    CHECK_SCRIPT = """
    (() => {
        const docEl = document.documentElement;
        const winWidth = window.innerWidth;
        const winHeight = window.innerHeight;
        const scrollWidth = docEl.scrollWidth;
        const bodyScrollWidth = document.body ? document.body.scrollWidth : 0;
        const maxScroll = Math.max(scrollWidth, bodyScrollWidth);
        
        // Find overflowing elements
        const overflowing = [];
        const allElements = document.querySelectorAll('*');
        allElements.forEach(el => {
            if (['SCRIPT', 'STYLE', 'HEAD', 'META', 'TITLE', 'LINK'].includes(el.tagName)) return;
            const rect = el.getBoundingClientRect();
            if (rect.width === 0 && rect.height === 0) return;
            const style = window.getComputedStyle(el);
            if (style.display === 'none' || style.visibility === 'hidden') return;
            if (el.closest('details:not([open])')) return;
            if (typeof el.checkVisibility === 'function' && !el.checkVisibility({ checkOpacity: true, checkVisibilityCSS: true })) return;
            
            // Allow 1.0px margin for rounding/antialiasing
            if (rect.right > winWidth + 1.0) {
                overflowing.push({
                    tag: el.tagName.toLowerCase(),
                    id: el.id ? '#' + el.id : '',
                    class: el.className && typeof el.className === 'string' ? '.' + el.className.trim().split(/\\s+/).join('.') : '',
                    right: Math.round(rect.right),
                    width: Math.round(rect.width)
                });
            }
        });

        // Check mobile bottom nav vs desktop top nav
        const bottomNav = document.querySelector('.mobile-bottom-nav');
        const topNavLinks = document.querySelector('.top-nav-links');
        const isMobile = winWidth <= 840;

        let navStateOk = true;
        let navNote = '';
        if (isMobile) {
            if (topNavLinks && window.getComputedStyle(topNavLinks).display !== 'none') {
                navStateOk = false;
                navNote = 'Desktop links leaked on mobile';
            }
            if (!bottomNav || window.getComputedStyle(bottomNav).display === 'none') {
                // login page has no bottom nav
                const isLoginPage = window.location.pathname.includes('/login');
                if (!isLoginPage) {
                    navStateOk = false;
                    navNote = 'Mobile bottom nav hidden on mobile';
                }
            }
        } else {
            if (bottomNav && window.getComputedStyle(bottomNav).display !== 'none') {
                navStateOk = false;
                navNote = 'Mobile bottom nav appeared on desktop';
            }
        }

        // Check bottom nav clearance (no content covered)
        let bottomNavOverlap = false;
        if (isMobile && bottomNav && window.getComputedStyle(bottomNav).display !== 'none') {
            const workspace = document.querySelector('.workspace');
            if (workspace) {
                const padBottom = parseFloat(window.getComputedStyle(workspace).paddingBottom) || 0;
                const navHeight = bottomNav.offsetHeight;
                if (padBottom < navHeight - 5) {
                    bottomNavOverlap = true;
                }
            }
        }

        // Check for text/card clipping
        let clippedCount = 0;
        document.querySelectorAll('.metric, .terminal-panel, .quick-tile, .more-nav-item').forEach(card => {
            const r = card.getBoundingClientRect();
            if (r.right > winWidth + 1.0 || r.left < -1.0) {
                clippedCount++;
            }
        });

        return {
            innerWidth: winWidth,
            innerHeight: winHeight,
            scrollWidth: maxScroll,
            isScrollOk: maxScroll <= winWidth + 1.0,
            overflowCount: overflowing.length,
            overflowing: overflowing.slice(0, 5),
            navStateOk: navStateOk,
            navNote: navNote,
            bottomNavOverlap: bottomNavOverlap,
            clippedCount: clippedCount
        };
    })()
    """

    results = []
    total_passed = 0
    total_failed = 0

    print("\n" + "="*105)
    print(f"{'PAGE':<18} | {'VIEWPORT':<10} | {'INNER W':<8} | {'SCROLL W':<8} | {'FIT?':<6} | {'OVERFLOW':<8} | {'NAV':<6} | {'STATUS'}")
    print("="*105)

    for page_name, path in PAGES:
        target_url = f"http://127.0.0.1:{server_port}{path}"
        for vp_name, width, height in VIEWPORTS:
            await cdp.set_viewport(width, height)
            await cdp.navigate(target_url)

            data = await cdp.evaluate(CHECK_SCRIPT)
            if not data:
                print(f"FAIL: No data returned for {page_name} @ {vp_name}")
                total_failed += 1
                continue

            inner_w = data["innerWidth"]
            scroll_w = data["scrollWidth"]
            is_fit = data["isScrollOk"]
            ovf_cnt = data["overflowCount"]
            nav_ok = data["navStateOk"]
            b_overlap = data["bottomNavOverlap"]
            clipped = data.get("clippedCount", 0)

            test_passed = is_fit and (ovf_cnt == 0) and nav_ok and (not b_overlap) and (clipped == 0)
            status = "PASS" if test_passed else "FAIL"

            if test_passed:
                total_passed += 1
            else:
                total_failed += 1

            res_record = {
                "page": page_name,
                "path": path,
                "viewport": vp_name,
                "width": width,
                "height": height,
                "innerWidth": inner_w,
                "scrollWidth": scroll_w,
                "is_fit": is_fit,
                "overflow_count": ovf_cnt,
                "overflow_sample": data.get("overflowing", []),
                "nav_ok": nav_ok,
                "nav_note": data.get("navNote", ""),
                "bottomNavOverlap": b_overlap,
                "clippedCount": clipped,
                "status": status
            }
            results.append(res_record)

            fit_str = "YES" if is_fit else "NO"
            nav_str = "OK" if nav_ok else "ERR"
            print(f"{page_name:<18} | {vp_name:<10} | {inner_w:<8} | {scroll_w:<8} | {fit_str:<6} | {ovf_cnt:<8} | {nav_str:<6} | {status}")

            # Check if screenshot requested for this target
            for s_page, s_vp, s_name in SCREENSHOT_TARGETS:
                if s_page == page_name and s_vp == vp_name:
                    shot_path = os.path.join(SCREENSHOT_DIR, f"{s_name}.png")
                    await cdp.capture_screenshot(shot_path)
                    print(f"  --> [SCREENSHOT] Saved {s_name}.png ({width}x{height})")

    print("="*105)
    print(f"\n[SUMMARY] Total Tests Run: {len(results)}")
    print(f"          Passed:          {total_passed}")
    print(f"          Failed:          {total_failed}")

    report_json_path = os.path.join(ARTIFACT_DIR, "scratch", "browser_verification_results.json")
    with open(report_json_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"[REPORT] Saved JSON matrix to {report_json_path}")

    await cdp.close()
    chrome_proc.terminate()


if __name__ == "__main__":
    asyncio.run(run_verification())
