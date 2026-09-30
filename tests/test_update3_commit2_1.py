import importlib.util
import tempfile
import unittest
from pathlib import Path

APP_PATH = Path(__file__).resolve().parents[1] / "app.py"
spec = importlib.util.spec_from_file_location("finance_tracker_app_commit2_1", APP_PATH)
app = importlib.util.module_from_spec(spec)
spec.loader.exec_module(app)


class Update3Commit21Tests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        app.DB_PATH = str(Path(self.tmp.name) / "finance_data_test.db")
        app.init_db()

    def tearDown(self):
        self.tmp.cleanup()

    def _category(self, name):
        return next(row for row in app.get_budget_categories(active_only=False) if row[1] == name)

    def _budget_row(self, month, category_name):
        return next((row for row in app.get_monthly_budgets(month) if row[2] == category_name), None)

    def test_copy_previous_month_copies_amounts_and_notes(self):
        food = self._category("Food")
        transport = self._category("Transport")
        app.set_monthly_budget(food[0], "2026-07", 400, "Groceries and dining")
        app.set_monthly_budget(transport[0], "2026-07", 150, "Gas and tolls")

        result = app.copy_previous_month_budgets("2026-08")

        self.assertEqual(result["source_month"], "2026-07-01")
        self.assertEqual(result["target_month"], "2026-08-01")
        self.assertEqual(result["copied"], 2)
        self.assertEqual(result["skipped_existing"], 0)
        self.assertEqual(result["skipped_inactive"], 0)

        food_aug = self._budget_row("2026-08", "Food")
        transport_aug = self._budget_row("2026-08", "Transport")
        self.assertEqual(food_aug[4], 400.0)
        self.assertEqual(food_aug[5], "Groceries and dining")
        self.assertEqual(transport_aug[4], 150.0)
        self.assertEqual(transport_aug[5], "Gas and tolls")

    def test_copy_does_not_overwrite_existing_destination_budget(self):
        food = self._category("Food")
        transport = self._category("Transport")
        app.set_monthly_budget(food[0], "2026-07", 400, "July food")
        app.set_monthly_budget(transport[0], "2026-07", 150, "July transport")
        app.set_monthly_budget(food[0], "2026-08", 525, "Custom August food")

        result = app.copy_previous_month_budgets("2026-08")

        self.assertEqual(result["copied"], 1)
        self.assertEqual(result["skipped_existing"], 1)
        august_food = self._budget_row("2026-08", "Food")
        august_transport = self._budget_row("2026-08", "Transport")
        self.assertEqual(august_food[4], 525.0)
        self.assertEqual(august_food[5], "Custom August food")
        self.assertEqual(august_transport[4], 150.0)

    def test_copy_skips_inactive_source_category(self):
        food = self._category("Food")
        app.set_monthly_budget(food[0], "2026-07", 400)
        app.set_budget_category_active(food[0], False)

        result = app.copy_previous_month_budgets("2026-08")

        self.assertEqual(result["copied"], 0)
        self.assertEqual(result["skipped_inactive"], 1)
        self.assertIsNone(self._budget_row("2026-08", "Food"))

    def test_copy_with_no_previous_budgets_is_noop(self):
        result = app.copy_previous_month_budgets("2026-08")
        self.assertEqual(result["copied"], 0)
        self.assertEqual(result["skipped_existing"], 0)
        self.assertEqual(result["skipped_inactive"], 0)
        self.assertEqual(app.get_monthly_budgets("2026-08"), [])

    def test_copy_handles_january_year_boundary(self):
        food = self._category("Food")
        app.set_monthly_budget(food[0], "2025-12", 300)

        result = app.copy_previous_month_budgets("2026-01")

        self.assertEqual(result["source_month"], "2025-12-01")
        self.assertEqual(result["target_month"], "2026-01-01")
        self.assertEqual(result["copied"], 1)
        self.assertEqual(self._budget_row("2026-01", "Food")[4], 300.0)

    def test_copy_does_not_change_source_month(self):
        food = self._category("Food")
        app.set_monthly_budget(food[0], "2026-07", 400, "Original")

        app.copy_previous_month_budgets("2026-08")
        app.set_monthly_budget(food[0], "2026-08", 450, "Changed destination")

        july_food = self._budget_row("2026-07", "Food")
        self.assertEqual(july_food[4], 400.0)
        self.assertEqual(july_food[5], "Original")


if __name__ == "__main__":
    unittest.main()
