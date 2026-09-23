# Changelog

## 2026-09-13

### Update 2 - Commit 4: Transfer Detection & Handling

- Added conservative internal-transfer candidate detection using equal-and-opposite amounts across different owned accounts within a three-day window.
- Ambiguous matches are intentionally excluded from suggestions.
- Added manual Transfer Review UI so candidates are never classified automatically.
- Confirmed transfer pairs are linked bidirectionally through `linked_transaction_id`.
- Confirmed transfer transactions are classified with `transaction_type="transfer"` and category `Transfer`.
- Added the ability to unlink a confirmed transfer without deleting either transaction.
- CSV import results now report when potential transfer pairs are ready for review.
- Added migration/index support for `linked_transaction_id`.
- Added automated transfer detection, confirmation, ambiguity, date-window, unlink, and migration tests.

## 2026-09-13

### Update 2 - Commit 3: Duplicate Detection

- Added duplicate-aware CSV imports.
- Bank-provided `external_id` values are used as the primary duplicate key when present.
- Transactions without external IDs use a SHA-256 fingerprint based on account, date, normalized description, signed amount, and occurrence number.
- Added a `fingerprint` column and index to `transactions` with safe backfill for older imported rows.
- Import results now report new transactions, duplicates skipped, and invalid rows skipped.
- Legitimate identical same-day transactions are preserved through occurrence numbering.
- Transfer pairing remains deferred to Update 2 - Commit 4.


All notable changes to the Personal Finance Manager are documented here.

## [Unreleased]

### Update 2 - Commit 5: Transactions Viewer & Filtering

#### Added
- Added a Transactions page to the main sidebar.
- Added read-only browsing of normalized banking transactions with account names.
- Added filters for account, transaction type, category, date range, and description text.
- Added transaction summary totals for non-transfer inflows, non-transfer outflows, and transfer entries.
- Added Reset Filters and YYYY-MM-DD date validation.

#### Safety / Scope
- The viewer is read-only; this commit does not edit or delete banking transactions.
- Confirmed transfers remain excluded from inflow/outflow summary totals.
- Existing CSV import, duplicate detection, and transfer handling behavior is preserved.

#### Tests
- Added transaction query tests for ordering, account/type filtering, date/category/search filtering, and filter-option discovery.
- Full automated suite: 19 tests passing.

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
- Duplicate detection was added in Update 2 - Commit 3.
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
