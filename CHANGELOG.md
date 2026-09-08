# Changelog

All notable changes to the Personal Finance Manager are documented here.

## [Unreleased]

### Update 2 - Commit 2: CSV Import Foundation

#### Added
- Added flexible CSV parsing for common bank transaction exports.
- Added date, description, amount, debit/credit, and external-ID field detection.
- Added normalized signed-amount conversion during import.
- Added CSV import preview with row validation feedback.
- Added account selection before importing transactions.
- Added `source="csv"`, `external_id`, and `imported_at` population for imported rows.
- Added account `last_import` timestamp updates after successful imports.

#### Safety / Scope
- Imported transactions are never used to overwrite the account's current balance.
- Invalid rows are skipped and reported rather than partially inserted.
- Duplicate detection is intentionally deferred to the next commit; re-importing the same CSV can currently create duplicates.
- Real personal bank exports were not committed or bundled. Synthetic CSV data is used for automated tests.

#### Tests
- Verified ISO and common U.S. date formats.
- Verified signed amounts and parenthesized negative amounts.
- Verified debit/credit column conversion.
- Verified external-ID preservation.
- Verified invalid-row handling.
- Verified database insertion and `last_import` updates.

### Update 2 - Commit 1: Transaction Data Model

#### Added
- Added normalized `transactions` table linked to `accounts` through `account_id`.
- Added signed-amount convention: positive values represent money in; negative values represent money out.
- Added transaction provenance fields for future CSV imports (`source`, `external_id`, `imported_at`).
- Added indexes for account/date lookups and future external-ID matching.
- Added transaction DAL helpers: `add_transaction()`, `get_transactions()`, and `get_transaction_count()`.
- Enabled SQLite foreign-key enforcement on application connections.

#### Changed
- Corrected the Accounts balance formatter to use the existing `fmt_money()` helper.

#### Deferred
- Duplicate detection rules.
- Transfer pairing.
- Transaction management UI.

### Update 1 - Commit 1: Project Foundation

#### Added

- Initial project documentation.
- Project context and development roadmap.
- Architecture and database documentation.
- Architecture decision record for separating accounts from transactions.
- Initial `accounts` database table.
- Initial account data-access functions: `add_account()` and `get_accounts()`.
- Git privacy rules for personal financial data.

#### Changed

- Updated the database path so packaged executables store `finance_data.db` beside the executable instead of inside a temporary PyInstaller extraction directory.
- Updated `build.py` to match the current project layout where `app.py` is in the project root.
- Updated `build.py` so the personal SQLite database is not bundled into the executable.

#### Notes

The Accounts UI and transaction-to-account relationships are intentionally deferred to later commits. The current commit establishes the foundation without changing the existing transaction screens.
