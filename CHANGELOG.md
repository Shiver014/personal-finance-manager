## [Unreleased] - Development Database Separation

### Changed
- Added a dedicated `finance_data_test.db` sandbox database for development.
- Updated `app.py` to use a single `DATABASE_FILE` setting for database selection.
- Added `finance_data_test.db` to `.gitignore` so test data is not committed.
- Updated `build.py` and project context documentation to describe the configurable runtime database.

# Changelog

All notable changes to the Personal Finance Manager are documented here.

## [Unreleased]

### Sprint 1 - Commit 1: Project Foundation

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
