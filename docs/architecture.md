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
- `update_account()`
- `set_account_active()`
- `get_accounts()`

The Transactions data-access layer now provides:

- `add_transaction()`
- `get_transactions()`
- `get_transaction_count()`

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
