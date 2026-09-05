import unittest
from datetime import date
from decimal import Decimal

from app.services.finance import dashboard_data, chart_data
from app.core.view import NAV_ITEMS


class TestDOSMoneyModel(unittest.TestCase):
    def setUp(self):
        self.user = {
            "uid": "test_user_42",
            "username": "Test User",
            "currency": "₹",
            "monthly_budget": Decimal("300"),
            "categories": [
                {"id": "cat_food", "name": "Food", "kind": "expense", "monthly_budget": Decimal("200")},
                {"id": "cat_salary", "name": "Pocket Money", "kind": "income"},
            ],
        }

    def test_core_money_model_calculations(self):
        today = date.today()

        # Step 1: Income ₹500, Expense ₹113
        tx_step1 = [
            {"id": "tx1", "type": "income", "amount": Decimal("500"), "date": today.isoformat(), "category_id": "cat_salary"},
            {"id": "tx2", "type": "expense", "amount": Decimal("113"), "date": today.isoformat(), "category_id": "cat_food"},
        ]
        data1 = {
            "transactions": tx_step1,
            "goals": [],
            "debts": [],
            "recurring": [],
            "investments": [],
        }
        res1 = dashboard_data(self.user, data1)
        self.assertEqual(res1["total_income"], Decimal("500"))
        self.assertEqual(res1["total_expense"], Decimal("113"))
        self.assertEqual(res1["available_balance"], Decimal("387"))
        self.assertEqual(res1["remaining_budget"], Decimal("187"))

        # Step 2: Add Income ₹1,000
        tx_step2 = list(tx_step1) + [
            {"id": "tx3", "type": "income", "amount": Decimal("1000"), "date": today.isoformat(), "category_id": "cat_salary"},
        ]
        data2 = {
            "transactions": tx_step2,
            "goals": [],
            "debts": [],
            "recurring": [],
            "investments": [],
        }
        res2 = dashboard_data(self.user, data2)
        self.assertEqual(res2["total_income"], Decimal("1500"))
        self.assertEqual(res2["total_expense"], Decimal("113"))
        self.assertEqual(res2["available_balance"], Decimal("1387"))
        self.assertEqual(res2["remaining_budget"], Decimal("187"))

        # Step 3: Add Expense ₹200
        tx_step3 = list(tx_step2) + [
            {"id": "tx4", "type": "expense", "amount": Decimal("200"), "date": today.isoformat(), "category_id": "cat_food"},
        ]
        data3 = {
            "transactions": tx_step3,
            "goals": [],
            "debts": [],
            "recurring": [],
            "investments": [],
        }
        res3 = dashboard_data(self.user, data3)
        self.assertEqual(res3["total_income"], Decimal("1500"))
        self.assertEqual(res3["total_expense"], Decimal("313"))
        self.assertEqual(res3["available_balance"], Decimal("1187"))
        self.assertEqual(res3["remaining_budget"], Decimal("0"))

    def test_analytics_income_sources_and_spending_over_time(self):
        today = date.today()
        transactions = [
            {"id": "tx1", "type": "income", "amount": Decimal("500"), "date": today.isoformat(), "category": {"name": "Pocket Money"}},
            {"id": "tx2", "type": "income", "amount": Decimal("1000"), "date": today.isoformat(), "category": {"name": "Salary"}},
            {"id": "tx3", "type": "expense", "amount": Decimal("113"), "date": today.isoformat(), "category": {"name": "Food"}},
        ]
        data = {
            "transactions": transactions,
            "goals": [],
            "debts": [],
            "recurring": [],
            "investments": [],
        }
        charts = chart_data(self.user, data)
        self.assertIn("income_sources", charts)
        self.assertTrue(charts["income_sources"]["has_data"])
        self.assertEqual(charts["income_sources"]["total"], 1500.0)
        self.assertIn("spending_over_time", charts)
        self.assertTrue(charts["spending_over_time"]["has_data"])


class TestNavigationFeatureParity(unittest.TestCase):
    def test_desktop_nav_includes_more(self):
        nav_routes = [item[1] for item in NAV_ITEMS]
        self.assertIn("/more", nav_routes, "Desktop NAV_ITEMS must include /more for feature parity")
        self.assertIn("/money", nav_routes)
        self.assertIn("/visualize", nav_routes)
        self.assertIn("/budget", nav_routes)
        self.assertIn("/goals", nav_routes)
        self.assertIn("/lend-borrow", nav_routes)
        self.assertIn("/reports", nav_routes)


class TestCSSResponsiveConstraints(unittest.TestCase):
    def test_app_css_contains_mobile_table_representation(self):
        with open("static/css/app.css", "r", encoding="utf-8") as f:
            css = f.read()

        self.assertIn("data-label", css)
        self.assertIn(".terminal-table thead", css)
        self.assertIn(".investment-layout", css)
        self.assertIn(".report-layout", css)
        self.assertIn(".debt-grid", css)
        self.assertIn(".goal-grid", css)
        self.assertIn("min(380px, calc(100vw - 2rem))", css)
        self.assertIn("metric-primary", css)


if __name__ == "__main__":
    unittest.main()
