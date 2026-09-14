import importlib.util
import os
import sqlite3
import tempfile
import unittest
from pathlib import Path

APP_PATH = Path(__file__).resolve().parents[1] / "app.py"
spec = importlib.util.spec_from_file_location("finance_app_transfer_tests", APP_PATH)
app = importlib.util.module_from_spec(spec)
spec.loader.exec_module(app)


class TransferTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        app.DB_PATH = os.path.join(self.temp_dir.name, "finance_data_test.db")
        app.init_db()
        self.checking = app.add_account("Addition Financial", "Checking", "Checking")
        self.savings = app.add_account("SoFi", "Checking", "Checking")
        self.third = app.add_account("Addition Financial", "Savings", "Savings")

    def tearDown(self):
        self.temp_dir.cleanup()

    def add_tx(self, account_id, tx_date, description, amount):
        return app.add_transaction(account_id, tx_date, description, amount, source="csv")

    def test_unique_equal_opposite_pair_is_candidate(self):
        out_id = self.add_tx(self.checking, "2026-09-01", "TRANSFER TO SOFI", -500.00)
        in_id = self.add_tx(self.savings, "2026-09-02", "TRANSFER FROM ADDITION", 500.00)
        candidates = app.get_transfer_candidates()
        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0][0][0], out_id)
        self.assertEqual(candidates[0][1][0], in_id)

    def test_same_account_is_not_candidate(self):
        self.add_tx(self.checking, "2026-09-01", "OUT", -100.00)
        self.add_tx(self.checking, "2026-09-01", "IN", 100.00)
        self.assertEqual(app.get_transfer_candidates(), [])

    def test_outside_date_window_is_not_candidate(self):
        self.add_tx(self.checking, "2026-09-01", "TRANSFER OUT", -200.00)
        self.add_tx(self.savings, "2026-09-07", "TRANSFER IN", 200.00)
        self.assertEqual(app.get_transfer_candidates(max_days=3), [])

    def test_ambiguous_matches_are_not_auto_suggested(self):
        self.add_tx(self.checking, "2026-09-01", "TRANSFER OUT", -75.00)
        self.add_tx(self.savings, "2026-09-01", "TRANSFER IN", 75.00)
        self.add_tx(self.third, "2026-09-01", "ANOTHER CREDIT", 75.00)
        self.assertEqual(app.get_transfer_candidates(), [])

    def test_confirm_transfer_links_both_sides(self):
        out_id = self.add_tx(self.checking, "2026-09-01", "TRANSFER OUT", -350.00)
        in_id = self.add_tx(self.savings, "2026-09-02", "TRANSFER IN", 350.00)
        app.confirm_transfer_pair(out_id, in_id)

        conn = sqlite3.connect(app.DB_PATH)
        out = conn.execute(
            "SELECT transaction_type, category, linked_transaction_id FROM transactions WHERE id=?",
            (out_id,),
        ).fetchone()
        inc = conn.execute(
            "SELECT transaction_type, category, linked_transaction_id FROM transactions WHERE id=?",
            (in_id,),
        ).fetchone()
        conn.close()
        self.assertEqual(out, ("transfer", "Transfer", in_id))
        self.assertEqual(inc, ("transfer", "Transfer", out_id))
        self.assertEqual(app.get_transfer_candidates(), [])

    def test_confirm_rejects_unequal_amounts(self):
        out_id = self.add_tx(self.checking, "2026-09-01", "OUT", -100.00)
        in_id = self.add_tx(self.savings, "2026-09-01", "IN", 90.00)
        with self.assertRaises(ValueError):
            app.confirm_transfer_pair(out_id, in_id)

    def test_unlink_preserves_transactions(self):
        out_id = self.add_tx(self.checking, "2026-09-01", "TRANSFER OUT", -125.00)
        in_id = self.add_tx(self.savings, "2026-09-02", "TRANSFER IN", 125.00)
        app.confirm_transfer_pair(out_id, in_id)
        self.assertTrue(app.unlink_transfer(out_id))

        conn = sqlite3.connect(app.DB_PATH)
        rows = conn.execute(
            "SELECT id, transaction_type, category, linked_transaction_id FROM transactions ORDER BY id"
        ).fetchall()
        conn.close()
        self.assertEqual(len(rows), 2)
        for _, tx_type, category, linked_id in rows:
            self.assertEqual(tx_type, "uncategorized")
            self.assertIsNone(category)
            self.assertIsNone(linked_id)

    def test_migration_adds_linked_transaction_id(self):
        # Column should exist on a freshly initialized database, and repeated
        # initialization should remain safe.
        app.init_db()
        conn = sqlite3.connect(app.DB_PATH)
        columns = [row[1] for row in conn.execute("PRAGMA table_info(transactions)")]
        conn.close()
        self.assertIn("linked_transaction_id", columns)


if __name__ == "__main__":
    unittest.main()
