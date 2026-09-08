import csv
import importlib.util
import os
import sqlite3
import tempfile
import unittest
from pathlib import Path

APP_PATH = Path(__file__).resolve().parents[1] / "app.py"
spec = importlib.util.spec_from_file_location("finance_app", APP_PATH)
app = importlib.util.module_from_spec(spec)
spec.loader.exec_module(app)


class CSVImportTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        app.DB_PATH = os.path.join(self.temp_dir.name, "finance_data_test.db")
        app.init_db()
        self.account_id = app.add_account(
            "Synthetic Bank", "Checking", "Checking", current_balance=1000
        )

    def tearDown(self):
        self.temp_dir.cleanup()

    def write_csv(self, name, rows):
        path = os.path.join(self.temp_dir.name, name)
        with open(path, "w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerows(rows)
        return path

    def test_amount_csv_and_invalid_row(self):
        path = self.write_csv("synthetic.csv", [
            ["Date", "Description", "Amount", "Transaction ID"],
            ["08/01/2026", "PAYROLL", "1500.00", "abc-1"],
            ["08/02/2026", "GROCERY", "-84.23", "abc-2"],
            ["08/03/2026", "COFFEE", "(5.75)", "abc-3"],
            ["bad-date", "BAD ROW", "10", "bad-1"],
        ])

        rows, errors = app.parse_csv_transactions(path)
        self.assertEqual(len(rows), 3)
        self.assertEqual(len(errors), 1)
        self.assertEqual(rows[0]["transaction_date"], "2026-08-01")
        self.assertEqual(rows[0]["amount"], 1500.0)
        self.assertEqual(rows[1]["amount"], -84.23)
        self.assertEqual(rows[2]["amount"], -5.75)
        self.assertEqual(rows[0]["external_id"], "abc-1")

    def test_debit_credit_conversion(self):
        path = self.write_csv("debit_credit.csv", [
            ["Posted Date", "Memo", "Debit", "Credit", "Reference"],
            ["08/04/2026", "TRANSFER IN", "", "250.00", "ref-1"],
            ["08/05/2026", "ATM", "40.00", "", "ref-2"],
        ])

        rows, errors = app.parse_csv_transactions(path)
        self.assertEqual(errors, [])
        self.assertEqual([r["amount"] for r in rows], [250.0, -40.0])

    def test_import_persists_rows_and_last_import(self):
        path = self.write_csv("import.csv", [
            ["Date", "Description", "Amount", "Transaction ID"],
            ["08/01/2026", "PAYROLL", "1500.00", "abc-1"],
            ["08/02/2026", "GROCERY", "-84.23", "abc-2"],
        ])

        inserted, errors = app.import_csv_transactions(path, self.account_id)
        self.assertEqual(inserted, 2)
        self.assertEqual(errors, [])

        transactions = app.get_transactions(self.account_id)
        self.assertEqual(len(transactions), 2)
        self.assertTrue(all(row[8] == "csv" for row in transactions))

        conn = sqlite3.connect(app.DB_PATH)
        last_import = conn.execute(
            "SELECT last_import FROM accounts WHERE id=?", (self.account_id,)
        ).fetchone()[0]
        conn.close()
        self.assertTrue(last_import)

    def test_duplicate_detection_is_deferred(self):
        path = self.write_csv("repeat.csv", [
            ["Date", "Description", "Amount", "Transaction ID"],
            ["08/01/2026", "PAYROLL", "1500.00", "abc-1"],
        ])

        app.import_csv_transactions(path, self.account_id)
        app.import_csv_transactions(path, self.account_id)
        self.assertEqual(app.get_transaction_count(self.account_id), 2)


if __name__ == "__main__":
    unittest.main()
