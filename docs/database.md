# Database Design

## Existing Tables

### paychecks
Stores income events entered as paychecks.

### expenses
Stores expense events and their categories.

### loans
Stores loan-level information such as principal, balance, interest rate, and payment amount.

### loan_payments
Stores payments associated with loans.

### subscriptions
Stores recurring subscription obligations.

### recurring
Stores schedules used to automatically post recurring financial events.

## New Table: accounts

```sql
CREATE TABLE IF NOT EXISTS accounts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    institution TEXT NOT NULL,
    account_name TEXT NOT NULL,
    account_type TEXT NOT NULL,
    nickname TEXT,
    current_balance REAL DEFAULT 0,
    last_import TEXT,
    is_active INTEGER DEFAULT 1,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
```

### Column Purpose

| Column | Purpose |
| --- | --- |
| `id` | Unique identifier for the account |
| `institution` | Bank, credit union, brokerage, or other institution |
| `account_name` | Name of the account at the institution |
| `account_type` | Checking, savings, HYSA, Roth IRA, etc. |
| `nickname` | Optional user-friendly label |
| `current_balance` | Current balance recorded for the account |
| `last_import` | Date/time of the most recent import or synchronization |
| `is_active` | Allows an account to be deactivated without deleting history |
| `created_at` | Timestamp for when the account record was created |

## Important Modeling Rule

A transaction should eventually reference the account that actually experienced the transaction.

For example:

```text
Addition Financial Checking
    |
    +---- Grocery purchase - $75
```

The grocery purchase should not be duplicated across the user's other accounts merely because the accounts are owned by the same person.

## Transfers

A transfer between two owned accounts should eventually be represented using the source and destination accounts rather than being classified as income or expense.

Example:

```text
Checking  -$500
Savings   +$500

Total assets: unchanged
```

## Future Normalization

The current `paychecks` and `expenses` tables predate the Accounts model. Future commits will evaluate how to connect those records to accounts without breaking existing data.

The preferred direction is to introduce account foreign keys and migration logic rather than deleting or recreating existing financial history.


## Update 2 - Commit 2: CSV Import

CSV imports write normalized rows into `transactions`. Imported rows use `source='csv'` and record `imported_at`; a bank-provided transaction/reference identifier is stored in `external_id` when available. The importer does not overwrite `accounts.current_balance`, because a CSV may represent only a partial history. The account's `last_import` timestamp is updated after a successful import. Duplicate detection is deliberately deferred to the next commit.
