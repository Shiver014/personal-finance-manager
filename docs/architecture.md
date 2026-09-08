# Architecture

## Current Architecture

The application is currently a single-file desktop application:

```text
Tkinter UI
    |
    v
Application logic in app.py
    |
    v
SQLite database
```

This structure is intentionally simple while the project is being developed and learned.

## Database Access

`get_conn()` is the existing database connection helper. New database functionality should use it rather than opening connections independently throughout the UI.

The Accounts data-access layer now provides:

- `add_account()`
- `get_accounts()`

This is the beginning of a Data Access Layer (DAL). The purpose is to keep SQL operations reusable and reduce duplication between UI components.

## Why Accounts Are Separate

An account is a persistent financial entity. A transaction is an event that happens to an account.

Separating these concepts allows the system to support:

- Multiple institutions
- Multiple account types
- Historical transactions
- Account deactivation without deleting history
- Transfers between accounts
- Net-worth reporting

## Future Architecture

As complexity increases, the application may evolve toward:

```text
UI
 |
 v
Application / Domain Services
 |
 +---- Accounts
 +---- Transactions
 +---- Budgeting
 +---- Forecasting
 +---- Investments
 |
 v
Data Access Layer
 |
 v
SQLite
```

A module split will be introduced only when it provides a clear maintenance benefit.


## Update 2 - Commit 2: CSV Import Boundary

CSV parsing is kept separate from the transaction database write path. `parse_csv_transactions()` converts common bank CSV layouts into a normalized internal structure, while `import_csv_transactions()` validates the selected active account and persists the normalized rows. This keeps bank-specific column variation out of the core transaction model. Duplicate detection is intentionally not part of this boundary yet.
