import importlib.util
import sqlite3
import tempfile
import unittest
from pathlib import Path

APP_PATH = Path(__file__).resolve().parents[1] / "app.py"
spec = importlib.util.spec_from_file_location("finance_tracker_app", APP_PATH)
app = importlib.util.module_from_spec(spec)
spec.loader.exec_module(app)


class Update3Commit1Tests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        app.DB_PATH = str(Path(self.tmp.name) / "finance_data_test.db")
        app.init_db()
        self.account_id = app.add_account("Test Bank", "Checking", "Checking", current_balance=1000)

    def tearDown(self):
        self.tmp.cleanup()

    def _category(self, name):
        rows = app.get_budget_categories(active_only=False)
        return next(row for row in rows if row[1] == name)

    def test_default_categories_and_budget_tables_are_seeded(self):
        categories = app.get_budget_categories(active_only=False)
        names = {row[1] for row in categories}
        self.assertIn("Food", names)
        self.assertIn("Salary", names)

        conn = sqlite3.connect(app.DB_PATH)
        try:
            tables = {r[0] for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()}
        finally:
            conn.close()
        self.assertIn("budget_categories", tables)
        self.assertIn("monthly_budgets", tables)

    def test_category_names_are_globally_unique_case_insensitive(self):
        app.add_budget_category("Pets", "expense")
        with self.assertRaises(ValueError):
            app.add_budget_category("pets", "income")

    def test_assign_and_clear_transaction_category(self):
        expense_tx = app.add_transaction(
            self.account_id, "2026-09-01", "Grocery Store", -45.25, source="manual"
        )
        income_tx = app.add_transaction(
            self.account_id, "2026-09-02", "Employer", 1500.00, source="manual"
        )
        food = self._category("Food")
        salary = self._category("Salary")

        app.assign_transaction_category([expense_tx], food[0])
        app.assign_transaction_category([income_tx], salary[0])

        conn = sqlite3.connect(app.DB_PATH)
        try:
            expense_row = conn.execute(
                "SELECT category, transaction_type FROM transactions WHERE id=?", (expense_tx,)
            ).fetchone()
            income_row = conn.execute(
                "SELECT category, transaction_type FROM transactions WHERE id=?", (income_tx,)
            ).fetchone()
        finally:
            conn.close()
        self.assertEqual(expense_row, ("Food", "expense"))
        self.assertEqual(income_row, ("Salary", "income"))

        app.assign_transaction_category([expense_tx], None)
        conn = sqlite3.connect(app.DB_PATH)
        try:
            cleared = conn.execute(
                "SELECT category, transaction_type FROM transactions WHERE id=?", (expense_tx,)
            ).fetchone()
        finally:
            conn.close()
        self.assertEqual(cleared, (None, "uncategorized"))

    def test_confirmed_transfer_cannot_be_reclassified(self):
        other_account = app.add_account("Test Bank", "Savings", "Savings", current_balance=500)
        out_id = app.add_transaction(self.account_id, "2026-09-03", "Transfer Out", -100)
        in_id = app.add_transaction(other_account, "2026-09-03", "Transfer In", 100)
        app.confirm_transfer_pair(out_id, in_id)
        food = self._category("Food")

        with self.assertRaises(ValueError):
            app.assign_transaction_category([out_id], food[0])

    def test_category_rename_updates_normalized_transaction_assignments(self):
        tx_id = app.add_transaction(self.account_id, "2026-09-04", "Vet", -80)
        category_id = app.add_budget_category("Pets", "expense")
        app.assign_transaction_category([tx_id], category_id)
        app.update_budget_category(category_id, "Pet Care", "expense")

        conn = sqlite3.connect(app.DB_PATH)
        try:
            row = conn.execute(
                "SELECT category, transaction_type FROM transactions WHERE id=?", (tx_id,)
            ).fetchone()
        finally:
            conn.close()
        self.assertEqual(row, ("Pet Care", "expense"))

    def test_monthly_budget_upsert_and_month_normalization(self):
        food = self._category("Food")
        app.set_monthly_budget(food[0], "2026-10", 400, "Initial")
        app.set_monthly_budget(food[0], "2026-10-19", 425, "Updated")

        rows = app.get_monthly_budgets("2026-10")
        food_rows = [r for r in rows if r[1] == food[0]]
        self.assertEqual(len(food_rows), 1)
        self.assertEqual(food_rows[0][3], "2026-10-01")
        self.assertEqual(food_rows[0][4], 425.0)
        self.assertEqual(food_rows[0][5], "Updated")

    def test_monthly_budget_rejects_income_category_and_negative_amount(self):
        salary = self._category("Salary")
        food = self._category("Food")
        with self.assertRaises(ValueError):
            app.set_monthly_budget(salary[0], "2026-10", 1000)
        with self.assertRaises(ValueError):
            app.set_monthly_budget(food[0], "2026-10", -1)

    def test_deactivation_preserves_category_and_history(self):
        category_id = app.add_budget_category("Gifts", "expense")
        tx_id = app.add_transaction(self.account_id, "2026-09-05", "Gift Shop", -25)
        app.assign_transaction_category([tx_id], category_id)
        app.set_budget_category_active(category_id, False)

        active_names = {r[1] for r in app.get_budget_categories(active_only=True)}
        all_names = {r[1] for r in app.get_budget_categories(active_only=False)}
        self.assertNotIn("Gifts", active_names)
        self.assertIn("Gifts", all_names)

        conn = sqlite3.connect(app.DB_PATH)
        try:
            row = conn.execute("SELECT category FROM transactions WHERE id=?", (tx_id,)).fetchone()
        finally:
            conn.close()
        self.assertEqual(row[0], "Gifts")


if __name__ == "__main__":
    unittest.main()
