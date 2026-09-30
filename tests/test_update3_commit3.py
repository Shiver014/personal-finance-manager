import importlib.util
import tempfile
import unittest
from pathlib import Path

APP_PATH = Path(__file__).resolve().parents[1] / "app.py"
spec = importlib.util.spec_from_file_location("finance_tracker_app_commit3", APP_PATH)
app = importlib.util.module_from_spec(spec)
spec.loader.exec_module(app)


class Update3Commit3Tests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        app.DB_PATH = str(Path(self.tmp.name) / "finance_data_test.db")
        app.init_db()

    def tearDown(self):
        self.tmp.cleanup()

    def test_allocation_tables_exist(self):
        conn = app.get_conn()
        try:
            tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        finally:
            conn.close()
        self.assertIn("paycheck_allocation_rules", tables)
        self.assertIn("paycheck_allocation_plans", tables)
        self.assertIn("paycheck_allocation_items", tables)

    def test_percentage_and_fixed_rules_calculate_from_paycheck(self):
        app.add_allocation_rule("Savings", "Savings", "percentage", 20, 10)
        app.add_allocation_rule("Bills", "Bills", "fixed", 300, 20)
        report = app.calculate_paycheck_allocation(2000)
        by_name = {i["rule_name"]: i["amount"] for i in report["items"]}
        self.assertEqual(by_name["Savings"], 400.0)
        self.assertEqual(by_name["Bills"], 300.0)
        self.assertEqual(report["allocated_amount"], 700.0)
        self.assertEqual(report["unallocated_amount"], 1300.0)
        self.assertEqual(report["overallocated_amount"], 0.0)

    def test_remainder_rule_receives_only_what_is_left(self):
        app.add_allocation_rule("Investing", "Investments", "percentage", 10, 10)
        app.add_allocation_rule("Bills", "Bills", "fixed", 500, 20)
        app.add_allocation_rule("Flexible", "Spending", "remainder", 0, 100)
        report = app.calculate_paycheck_allocation(1500)
        by_name = {i["rule_name"]: i["amount"] for i in report["items"]}
        self.assertEqual(by_name["Investing"], 150.0)
        self.assertEqual(by_name["Bills"], 500.0)
        self.assertEqual(by_name["Flexible"], 850.0)
        self.assertEqual(report["allocated_amount"], 1500.0)
        self.assertEqual(report["unallocated_amount"], 0.0)

    def test_only_one_active_remainder_rule_is_allowed(self):
        first = app.add_allocation_rule("Leftover", "Other", "remainder", 0, 100)
        with self.assertRaises(ValueError):
            app.add_allocation_rule("Second leftover", "Savings", "remainder", 0, 110)
        app.set_allocation_rule_active(first, False)
        second = app.add_allocation_rule("Second leftover", "Savings", "remainder", 0, 110)
        self.assertIsInstance(second, int)

    def test_inactive_rule_is_excluded_from_calculation(self):
        active = app.add_allocation_rule("Savings", "Savings", "percentage", 10, 10)
        inactive = app.add_allocation_rule("Investing", "Investments", "percentage", 10, 20)
        app.set_allocation_rule_active(inactive, False)
        report = app.calculate_paycheck_allocation(1000)
        self.assertEqual([i["rule_name"] for i in report["items"]], ["Savings"])
        self.assertEqual(report["allocated_amount"], 100.0)

    def test_overallocated_plan_is_reported_and_cannot_be_saved(self):
        app.add_allocation_rule("Large fixed", "Bills", "fixed", 900, 10)
        app.add_allocation_rule("Savings", "Savings", "percentage", 25, 20)
        report = app.calculate_paycheck_allocation(1000)
        self.assertEqual(report["allocated_amount"], 1150.0)
        self.assertEqual(report["overallocated_amount"], 150.0)
        with self.assertRaises(ValueError):
            app.save_paycheck_allocation_plan("2026-09-29", 1000, "Should fail")

    def test_saved_plan_persists_snapshot_items(self):
        rule_id = app.add_allocation_rule("Savings", "Savings", "percentage", 20, 10)
        plan_id, report = app.save_paycheck_allocation_plan("2026-09-29", 1000, "Payday")
        self.assertEqual(report["allocated_amount"], 200.0)
        app.update_allocation_rule(rule_id, "Savings updated", "Savings", "percentage", 30, 10, "Changed later")
        items = app.get_allocation_plan_items(plan_id)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0][2], "Savings")
        self.assertEqual(items[0][5], 20.0)
        self.assertEqual(items[0][6], 200.0)

    def test_saved_plan_records_unallocated_amount(self):
        app.add_allocation_rule("Savings", "Savings", "percentage", 25, 10)
        plan_id, _ = app.save_paycheck_allocation_plan("2026-09-29", 800)
        plan = app.get_recent_allocation_plans(1)[0]
        self.assertEqual(plan[0], plan_id)
        self.assertEqual(plan[2], 800.0)
        self.assertEqual(plan[3], 200.0)
        self.assertEqual(plan[4], 600.0)

    def test_rule_validation_rejects_invalid_percentage(self):
        with self.assertRaises(ValueError):
            app.add_allocation_rule("Too much", "Savings", "percentage", 101, 10)
        with self.assertRaises(ValueError):
            app.add_allocation_rule("Bad bucket", "Vacation", "fixed", 100, 10)


if __name__ == "__main__":
    unittest.main()
