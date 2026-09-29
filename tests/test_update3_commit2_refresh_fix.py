import importlib.util
import tempfile
import unittest
from pathlib import Path

APP_PATH = Path(__file__).resolve().parents[1] / "app.py"
spec = importlib.util.spec_from_file_location("finance_tracker_app_commit2_fix", APP_PATH)
app = importlib.util.module_from_spec(spec)
spec.loader.exec_module(app)


class Update3Commit2RefreshFixTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        app.DB_PATH = str(Path(self.tmp.name) / "finance_data_test.db")
        app.init_db()
        self.checking = app.add_account("Test Bank", "Checking", "Checking", current_balance=1000)

    def tearDown(self):
        self.tmp.cleanup()

    def _category(self, name):
        return next(row for row in app.get_budget_categories(active_only=False) if row[1] == name)

    def test_categorized_food_transaction_updates_budget_report(self):
        food = self._category("Food")
        app.set_monthly_budget(food[0], "2026-09", 300)
        tx_id = app.add_transaction(self.checking, "2026-09-29", "Lunch", -25)
        app.assign_transaction_category([tx_id], food[0])

        report = app.get_budget_report("2026-09")
        row = next(r for r in report["rows"] if r["category_name"] == "Food")
        self.assertEqual(row["actual_spend"], 25.0)
        self.assertEqual(row["remaining"], 275.0)

    def test_transaction_tab_change_notifies_app_level_refresh_callback(self):
        calls = []
        tab = app.TransactionsTab.__new__(app.TransactionsTab)
        tab.on_change = lambda: calls.append("app_refresh")
        tab.refresh = lambda: calls.append("local_refresh")

        tab._changed()

        self.assertEqual(calls, ["app_refresh"])

    def test_transaction_tab_change_falls_back_to_local_refresh(self):
        calls = []
        tab = app.TransactionsTab.__new__(app.TransactionsTab)
        tab.on_change = None
        tab.refresh = lambda: calls.append("local_refresh")

        tab._changed()

        self.assertEqual(calls, ["local_refresh"])


if __name__ == "__main__":
    unittest.main()
