from __future__ import annotations

"""
Mini line-art SVG illustrations for D-OS goal categories.
Rendered inline without PNG file dependencies or uploads.
"""

GOAL_SVG_MAP: dict[str, str] = {
    "bike": """<svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#66FF99" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="5.5" cy="17.5" r="3.5"/><circle cx="18.5" cy="17.5" r="3.5"/><path d="M15 6h-5l-3 7.5h11.5L15 6z"/><path d="M12 17.5V10"/><path d="M7 6h3"/></svg>""",
    "car": """<svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#66FF99" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M19 17h2c.6 0 1-.4 1-1v-3c0-.9-.7-1.7-1.5-1.9C18.7 10.6 16 10 16 10s-1.3-3-2-3H10c-.7 0-2 3-2 3s-2.7.6-4.5 1.1C2.7 11.3 2 12.1 2 13v3c0 .6.4 1 1 1h2"/><circle cx="7" cy="17" r="2"/><circle cx="17" cy="17" r="2"/></svg>""",
    "house": """<svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#66FF99" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="m3 9 9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/></svg>""",
    "phone": """<svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#66FF99" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><rect width="14" height="20" x="5" y="2" rx="2" ry="2"/><path d="M12 18h.01"/></svg>""",
    "laptop": """<svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#66FF99" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M20 16V5a2 2 0 0 0-2-2H6a2 2 0 0 0-2 2v11m16 0H4m16 0 1.5 3A1 1 0 0 1 20.6 21H3.4a1 1 0 0 1-.9-1.4L4 16"/></svg>""",
    "clothes": """<svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#66FF99" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M20.38 3.46 16 2a4 4 0 0 1-8 0L3.62 3.46a2 2 0 0 0-1.34 2.23l.58 3.47a1 1 0 0 0 .99.84H6v10a2 2 0 0 0 2 2h8a2 2 0 0 0 2-2V10h2.15a1 1 0 0 0 .99-.84l.58-3.47a2 2 0 0 0-1.34-2.23z"/></svg>""",
    "shoes": """<svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#66FF99" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M3 14h18v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4z"/><path d="M3 14 7 7h5l4 7"/></svg>""",
    "watch": """<svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#66FF99" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="6"/><polyline points="12 10 12 12 13.5 13.5"/><path d="M12 2v4m0 12v4"/></svg>""",
    "vacation": """<svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#66FF99" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M12 22s8-4 8-10A8 8 0 0 0 4 12c0 6 8 10 8 10z"/><circle cx="12" cy="10" r="3"/></svg>""",
    "gift": """<svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#66FF99" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="8" width="18" height="4" rx="1"/><path d="M12 8v13"/><path d="M19 12v7a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2v-7"/><path d="M7.5 8a2.5 2.5 0 0 1 0-5C11 3 12 8 12 8s1-5 4.5-5a2.5 2.5 0 0 1 0 5"/></svg>""",
    "education": """<svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#66FF99" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M22 10v6M2 10l10-5 10 5-10 5z"/><path d="M6 12v5c3 3 9 3 12 0v-5"/></svg>""",
    "camera": """<svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#66FF99" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M14.5 4h-5L7 7H4a2 2 0 0 0-2 2v9a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2V9a2 2 0 0 0-2-2h-3l-2.5-3z"/><circle cx="12" cy="13" r="3"/></svg>""",
    "gaming": """<svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#66FF99" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="6" width="20" height="12" rx="6"/><path d="M6 12h4m-2-2v4"/><circle cx="15" cy="11" r="1"/><circle cx="18" cy="13" r="1"/></svg>""",
    "travel": """<svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#66FF99" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><rect x="6" y="6" width="12" height="15" rx="2"/><path d="M9 6V4a2 2 0 0 1 2-2h2a2 2 0 0 1 2 2v2"/><path d="M6 12h12"/><circle cx="9" cy="21" r="1"/><circle cx="15" cy="21" r="1"/></svg>""",
    "custom": """<svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#66FF99" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="6"/><circle cx="12" cy="12" r="2"/></svg>"""
}


def get_goal_svg(goal_name: str) -> str:
    name_lower = (goal_name or "").lower()
    for key, svg in GOAL_SVG_MAP.items():
        if key in name_lower:
            return svg
    return GOAL_SVG_MAP["custom"]
