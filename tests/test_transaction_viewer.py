import importlib.util
import os
import tempfile
import unittest
from pathlib import Path

APP_PATH = Path(__file__).resolve().parents[1] / "app.py"
spec = importlib.util.spec_from_file_location("finance_app_viewer_tests", APP_PATH)
app = importlib.util.module_from_spec(spec)
spec.loader.exec_module(app)


class TransactionViewerQueryTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        app.DB_PATH = os.path.join(self.temp_dir.name, "finance_data_test.db")
        app.init_db()
        self.a1 = app.add_account("Addition Financial", "Checking", "Checking")
        self.a2 = app.add_account("SoFi", "Checking", "Checking")
        app.add_transaction(self.a1, "2026-09-01", "PAYROLL ACME", 1000, category="Income", transaction_type="income")
        app.add_transaction(self.a1, "2026-09-02", "GROCERY STORE", -75, category="Groceries", transaction_type="expense")
        app.add_transaction(self.a2, "2026-09-03", "TRANSFER FROM ADDITION", 200, category="Transfer", transaction_type="transfer")

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_all_transactions_are_newest_first(self):
        rows = app.get_filtered_transactions()
        self.assertEqual([r[1] for r in rows], ["2026-09-03", "2026-09-02", "2026-09-01"])

    def test_account_and_type_filters(self):
        rows = app.get_filtered_transactions(account_id=self.a1, transaction_type="expense")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0][4], "GROCERY STORE")

    def test_date_category_and_search_filters(self):
        rows = app.get_filtered_transactions(date_from="2026-09-02", date_to="2026-09-03", category="Groceries", search_text="grocery")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0][5], -75)

    def test_filter_options(self):
        categories, types = app.get_transaction_filter_options()
        self.assertIn("Transfer", categories)
        self.assertIn("expense", types)
