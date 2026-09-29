import importlib.util
import tempfile
import unittest
from pathlib import Path

APP_PATH = Path(__file__).resolve().parents[1] / "app.py"
spec = importlib.util.spec_from_file_location("finance_tracker_app_commit2", APP_PATH)
app = importlib.util.module_from_spec(spec)
spec.loader.exec_module(app)


class Update3Commit2Tests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        app.DB_PATH = str(Path(self.tmp.name) / "finance_data_test.db")
        app.init_db()
        self.checking = app.add_account("Test Bank", "Checking", "Checking", current_balance=1000)
        self.savings = app.add_account("Test Bank", "Savings", "Savings", current_balance=500)

    def tearDown(self):
        self.tmp.cleanup()

    def _category(self, name):
        return next(row for row in app.get_budget_categories(active_only=False) if row[1] == name)

    def _assign(self, tx_id, category_name):
        category = self._category(category_name)
        app.assign_transaction_category([tx_id], category[0])
        return category

    def test_budget_report_uses_normalized_transactions_only(self):
        food = self._category("Food")
        app.set_monthly_budget(food[0], "2026-09", 400)
        tx = app.add_transaction(self.checking, "2026-09-05", "Groceries", -125)
        self._assign(tx, "Food")

        # Legacy manual expense must not be merged into normalized budget actuals.
        conn = app.get_conn()
        conn.execute(
            "INSERT INTO expenses(amount,category,description,date,active) VALUES(?,?,?,?,1)",
            (999, "Food", "Legacy row", "2026-09-06"),
        )
        conn.commit()
        conn.close()

        report = app.get_budget_report("2026-09")
        food_row = next(r for r in report["rows"] if r["category_name"] == "Food")
        self.assertEqual(food_row["budget_amount"], 400.0)
        self.assertEqual(food_row["actual_spend"], 125.0)
        self.assertEqual(report["actual_total"], 125.0)

    def test_confirmed_transfers_do_not_count_as_spending(self):
        out_id = app.add_transaction(self.checking, "2026-09-07", "Transfer Out", -200)
        in_id = app.add_transaction(self.savings, "2026-09-07", "Transfer In", 200)
        app.confirm_transfer_pair(out_id, in_id)

        report = app.get_budget_report("2026-09")
        self.assertEqual(report["actual_total"], 0.0)
        self.assertEqual(report["uncategorized_outflow"], 0.0)
        self.assertEqual(report["uncategorized_count"], 0)

    def test_refund_reduces_net_category_spend(self):
        food = self._category("Food")
        app.set_monthly_budget(food[0], "2026-09", 300)
        purchase = app.add_transaction(self.checking, "2026-09-02", "Grocery", -100)
        refund = app.add_transaction(self.checking, "2026-09-03", "Grocery Refund", 25)
        app.assign_transaction_category([purchase, refund], food[0])

        report = app.get_budget_report("2026-09")
        food_row = next(r for r in report["rows"] if r["category_name"] == "Food")
        self.assertEqual(food_row["actual_spend"], 75.0)
        self.assertEqual(food_row["remaining"], 225.0)
        self.assertAlmostEqual(food_row["percent_used"], 25.0)

    def test_uncategorized_outflow_is_reported_separately(self):
        app.add_transaction(self.checking, "2026-09-08", "Unknown Merchant", -60)
        app.add_transaction(self.checking, "2026-09-09", "Deposit", 500)

        report = app.get_budget_report("2026-09")
        self.assertEqual(report["actual_total"], 0.0)
        self.assertEqual(report["uncategorized_outflow"], 60.0)
        self.assertEqual(report["uncategorized_count"], 1)

    def test_category_with_actual_and_no_budget_appears(self):
        tx = app.add_transaction(self.checking, "2026-09-10", "Movie", -40)
        self._assign(tx, "Entertainment")

        report = app.get_budget_report("2026-09")
        row = next(r for r in report["rows"] if r["category_name"] == "Entertainment")
        self.assertIsNone(row["budget_id"])
        self.assertEqual(row["actual_spend"], 40.0)
        self.assertIsNone(row["remaining"])
        self.assertEqual(row["status"], "No budget")

    def test_inactive_category_with_budget_or_activity_is_preserved_in_report(self):
        gifts = app.add_budget_category("Gifts", "expense")
        app.set_monthly_budget(gifts, "2026-09", 100)
        tx = app.add_transaction(self.checking, "2026-09-11", "Gift", -20)
        app.assign_transaction_category([tx], gifts)
        app.set_budget_category_active(gifts, False)

        report = app.get_budget_report("2026-09")
        row = next(r for r in report["rows"] if r["category_name"] == "Gifts")
        self.assertFalse(row["is_active"])
        self.assertEqual(row["budget_amount"], 100.0)
        self.assertEqual(row["actual_spend"], 20.0)

    def test_months_are_isolated(self):
        food = self._category("Food")
        app.set_monthly_budget(food[0], "2026-09", 300)
        september_tx = app.add_transaction(self.checking, "2026-09-30", "Sep Grocery", -50)
        october_tx = app.add_transaction(self.checking, "2026-10-01", "Oct Grocery", -80)
        app.assign_transaction_category([september_tx, october_tx], food[0])

        september = app.get_budget_report("2026-09")
        october = app.get_budget_report("2026-10")
        sep_food = next(r for r in september["rows"] if r["category_name"] == "Food")
        oct_food = next(r for r in october["rows"] if r["category_name"] == "Food")
        self.assertEqual(sep_food["actual_spend"], 50.0)
        self.assertEqual(oct_food["actual_spend"], 80.0)
        self.assertIsNone(oct_food["budget_id"])

    def test_summary_totals_and_over_budget_status(self):
        food = self._category("Food")
        transport = self._category("Transport")
        app.set_monthly_budget(food[0], "2026-09", 100)
        app.set_monthly_budget(transport[0], "2026-09", 50)
        food_tx = app.add_transaction(self.checking, "2026-09-12", "Groceries", -120)
        transport_tx = app.add_transaction(self.checking, "2026-09-13", "Fuel", -20)
        app.assign_transaction_category([food_tx], food[0])
        app.assign_transaction_category([transport_tx], transport[0])

        report = app.get_budget_report("2026-09")
        self.assertEqual(report["planned_total"], 150.0)
        self.assertEqual(report["actual_total"], 140.0)
        self.assertEqual(report["remaining_total"], 10.0)
        food_row = next(r for r in report["rows"] if r["category_name"] == "Food")
        self.assertEqual(food_row["status"], "Over budget")
        self.assertEqual(food_row["remaining"], -20.0)

    def test_remove_budget_does_not_remove_transaction_history(self):
        food = self._category("Food")
        app.set_monthly_budget(food[0], "2026-09", 250)
        tx = app.add_transaction(self.checking, "2026-09-14", "Groceries", -35)
        app.assign_transaction_category([tx], food[0])
        before = app.get_budget_report("2026-09")
        row = next(r for r in before["rows"] if r["category_name"] == "Food")

        app.delete_monthly_budget(row["budget_id"])
        after = app.get_budget_report("2026-09")
        row_after = next(r for r in after["rows"] if r["category_name"] == "Food")
        self.assertIsNone(row_after["budget_id"])
        self.assertEqual(row_after["actual_spend"], 35.0)


if __name__ == "__main__":
    unittest.main()
