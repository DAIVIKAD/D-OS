import unittest
from decimal import Decimal
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
from main import app
from app.core.config import settings

client = TestClient(app, follow_redirects=False)

MOCK_USER = {
    "uid": "user_abc123",
    "email": "tester@dos.local",
    "username": "Terminal Commander",
    "currency": "₹",
    "monthly_budget": Decimal("15000"),
    "has_seen_onboarding": True,
    "categories": [
        {"id": "cat1", "name": "Food", "kind": "expense", "color": "#39ff88", "icon": "🍕", "monthly_budget": Decimal("5000")},
        {"id": "cat2", "name": "Salary", "kind": "income", "color": "#66FF99", "icon": "💰", "monthly_budget": Decimal("0")},
    ],
}

MOCK_TXS = [
    {"id": "tx1", "type": "income", "amount": Decimal("25000"), "date": "2026-09-01", "category": {"name": "Salary", "icon": "💰"}, "category_id": "cat2", "note": "Monthly payout"},
    {"id": "tx2", "type": "expense", "amount": Decimal("3200"), "date": "2026-09-02", "category": {"name": "Food", "icon": "🍕"}, "category_id": "cat1", "note": "Groceries"},
]


class TestFeatureRoutesAndAuth(unittest.TestCase):
    @patch("app.firebase.auth.optional_user", return_value=MOCK_USER)
    @patch("app.services.firestore_service.list_transactions", return_value=MOCK_TXS)
    @patch("app.services.firestore_service.list_goals", return_value=[])
    @patch("app.services.firestore_service.list_debts", return_value=[])
    @patch("app.services.firestore_service.list_recurring", return_value=[])
    @patch("app.services.firestore_service.list_investments", return_value=[])
    @patch("app.services.firestore_service.list_custom_budgets", return_value=[])
    @patch("app.services.firestore_service.log_report")
    def test_all_matrix_routes_render_ok(self, *mocks):
        routes_to_test = [
            ("/", "Dashboard"),
            ("/money", "Ledger"),
            ("/visualize", "Analytics"),
            ("/budget", "Budget"),
            ("/budget?view=custom", "Budget"),
            ("/goals", "Goals"),
            ("/lend-borrow", "Lend & Borrow"),
            ("/reports", "Reports"),
            ("/more", "More"),
            ("/recurring", "Recurring"),
            ("/investment", "Investment"),
            ("/help", "Help"),
            ("/about", "About"),
            ("/settings", "Settings"),
        ]
        for url, desc in routes_to_test:
            response = client.get(url, cookies={"dos_session": "mock_valid_session"})
            self.assertEqual(
                response.status_code, 200,
                f"Route {url} ({desc}) failed to render with status {response.status_code}"
            )
            # Ensure no horizontal scroll or desktop minimum overflow triggers
            html = response.text
            self.assertIn("D-OS", html)

        # Test Filtered Reports exports with mock session
        csv_resp = client.get("/reports/export.csv", cookies={"dos_session": "mock_valid_session"})
        self.assertEqual(csv_resp.status_code, 200)
        self.assertIn("Date,Type,Category,Amount", csv_resp.text)

        pdf_resp = client.get("/reports/export.pdf", cookies={"dos_session": "mock_valid_session"})
        self.assertEqual(pdf_resp.status_code, 200)
        self.assertEqual(pdf_resp.headers.get("content-type"), "application/pdf")
        self.assertGreater(len(pdf_resp.content), 500)

    def test_public_login_page(self):
        response = client.get("/login")
        self.assertEqual(response.status_code, 200)
        self.assertIn("remember_me", response.text, "Login page must include Remember Me checkbox")
        self.assertIn("Remember this device", response.text)

    @patch("app.routes.auth.create_session_cookie")
    @patch("app.routes.auth.ensure_user_profile")
    @patch("app.routes.auth.require_csrf")
    def test_session_login_remember_me_true(self, mock_csrf, mock_profile, mock_create_cookie):
        mock_create_cookie.return_value = ("session_cookie_token_abc", {"uid": "u123", "email": "a@b.com"})
        response = client.post(
            "/session-login",
            json={"idToken": "fake_firebase_token", "rememberMe": True},
            headers={"X-CSRF-Token": "token123"},
            cookies={"dos_csrf": "token123"}
        )
        self.assertEqual(response.status_code, 200)
        mock_create_cookie.assert_called_with("fake_firebase_token", remember_me=True)
        cookie_header = response.headers.get("set-cookie", "")
        self.assertIn(settings.session_cookie_name, cookie_header)
        self.assertIn("Max-Age=", cookie_header)
        self.assertIn("HttpOnly", cookie_header)

    @patch("app.routes.auth.create_session_cookie")
    @patch("app.routes.auth.ensure_user_profile")
    @patch("app.routes.auth.require_csrf")
    def test_session_login_remember_me_false(self, mock_csrf, mock_profile, mock_create_cookie):
        mock_create_cookie.return_value = ("session_cookie_token_xyz", {"uid": "u123", "email": "a@b.com"})
        response = client.post(
            "/session-login",
            json={"idToken": "fake_firebase_token", "rememberMe": False},
            headers={"X-CSRF-Token": "token123"},
            cookies={"dos_csrf": "token123"}
        )
        self.assertEqual(response.status_code, 200)
        mock_create_cookie.assert_called_with("fake_firebase_token", remember_me=False)
        cookie_header = response.headers.get("set-cookie", "")
        self.assertIn(settings.session_cookie_name, cookie_header)
        # Session cookie must NOT have Max-Age so it expires with browser session
        self.assertNotIn("Max-Age=", cookie_header)
        self.assertIn("HttpOnly", cookie_header)

    @patch("firebase_admin.auth.revoke_refresh_tokens")
    @patch("app.firebase.auth.verify_session_cookie", return_value={"uid": "user_abc123"})
    def test_logout_clears_session_and_revokes(self, mock_verify, mock_revoke):
        response = client.post(
            "/logout",
            cookies={settings.session_cookie_name: "session_to_kill", "dos_csrf": "csrf_to_kill"}
        )
        self.assertEqual(response.status_code, 303)
        self.assertEqual(response.headers.get("location"), "/login")
        mock_revoke.assert_called_once()
        cookie_header = response.headers.get("set-cookie", "")
        self.assertIn(f"{settings.session_cookie_name}=""", cookie_header)


if __name__ == "__main__":
    unittest.main()
