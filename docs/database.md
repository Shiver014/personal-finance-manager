# Database Design

Last updated: 2026-09-29

Finance Tracker uses SQLite. Personal production databases and financial exports are intentionally excluded from Git.

## Core Tables

### `accounts`
Represents persistent places where money or investments are held.

| Column | Purpose |
| --- | --- |
| `id` | Primary key |
| `institution` | Bank, credit union, brokerage, etc. |
| `account_name` | Account name |
| `account_type` | Checking, Savings, Savings Plus, Roth IRA, Stocks, etc. |
| `nickname` | Optional display nickname |
| `current_balance` | Latest balance recorded for the account; Commit 6 uses the latest bank-confirmed reconciliation balance for reconciled cash accounts |
| `last_import` | Timestamp of latest CSV import |
| `is_active` | Active/inactive flag; accounts are deactivated rather than deleted |
| `created_at` | Creation timestamp |

### `transactions`
Normalized banking transaction history. Each transaction belongs to exactly one account.

| Column | Purpose |
| --- | --- |
| `id` | Primary key |
| `account_id` | Owning account |
| `transaction_date` | Transaction date |
| `posted_date` | Optional posted date |
| `description` | Bank/payee description |
| `amount` | Signed amount: positive = money in, negative = money out |
| `category` | Optional category; confirmed transfers use `Transfer` |
| `transaction_type` | Classification; defaults to `uncategorized`, confirmed transfers use `transfer` |
| `source` | Source such as `manual` or `csv` |
| `external_id` | Bank/reference ID when supplied |
| `fingerprint` | SHA-256 fallback duplicate key |
| `linked_transaction_id` | Opposite-side transaction ID for a confirmed internal transfer |
| `imported_at` | Import timestamp |
| `note` | Optional note |
| `created_at` | Creation timestamp |

Indexes exist for account/date, account/external ID, account/fingerprint, and linked transfers.

### `account_reconciliations`
Added in Update 2 - Commit 6. Stores bank-confirmed balance snapshots without discarding prior reconciliations.

```sql
CREATE TABLE IF NOT EXISTS account_reconciliations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    account_id INTEGER NOT NULL,
    reconciliation_date TEXT NOT NULL,
    bank_balance REAL NOT NULL,
    expected_balance REAL,
    difference REAL,
    note TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(account_id) REFERENCES accounts(id)
);
```

`expected_balance` is `NULL` for the first reconciliation because no trusted prior baseline exists. For later reconciliations:

```text
expected balance
= prior bank-confirmed balance
+ signed transactions after prior reconciliation through new reconciliation date

difference
= actual bank balance - expected balance
```

All signed transactions count in this account-level calculation, including internal transfers, because a transfer changes the balance of each individual account even though it does not change total wealth.

Cash-account reconciliation currently excludes Roth IRA and Stocks. Their balances depend on market value and belong to the investment model planned for Update 4.


### `budget_categories`
Added in Update 3 - Commit 1. Stores the canonical category list used to classify normalized transactions and define future budgets.

| Column | Purpose |
| --- | --- |
| `id` | Primary key |
| `name` | Globally unique category name (case-insensitive) |
| `category_type` | `expense` or `income` |
| `is_active` | Active/inactive flag; deactivation preserves history |
| `is_system` | Indicates a seeded default category |
| `created_at` | Creation timestamp |

Default categories are seeded when the category table is first created/empty; later user renames and deactivations are preserved. `Transfer` is intentionally reserved and is not stored as a normal budget category.

### `monthly_budgets`
Added in Update 3 - Commit 1. Stores one planned amount per expense category per month.

| Column | Purpose |
| --- | --- |
| `id` | Primary key |
| `category_id` | Expense category being budgeted |
| `budget_month` | Month normalized to `YYYY-MM-01` |
| `amount` | Planned non-negative monthly amount |
| `note` | Optional note |
| `created_at` | Creation timestamp |
| `updated_at` | Latest update timestamp |

The `(category_id, budget_month)` pair is unique. Saving the same category/month again updates the existing budget rather than creating a duplicate.

### Category Assignment on `transactions`

The existing `transactions.category` text field remains in place for compatibility with the banking model. A canonical category assignment updates both:

```text
transactions.category         = canonical category name
transactions.transaction_type = category_type (`expense` or `income`)
```

Confirmed internal transfers cannot be reclassified through category assignment. Clearing a normal category resets the row to `category=NULL` and `transaction_type='uncategorized'`. Renaming a canonical category also updates normalized transaction rows already using that category name.


## Budget-vs-Actual Reporting

Update 3 - Commit 2 does not add another persistence table. It derives the monthly report from the existing canonical categories, `monthly_budgets`, and normalized `transactions`.

For a selected month and expense category:

```text
actual spend = -SUM(normalized transaction amounts classified as expense)
remaining    = planned budget - actual spend
```

Because expense-category actuals use the signed transaction ledger, a positive expense-category refund reduces net spending. Confirmed transfers are excluded because they use `transaction_type='transfer'`. Legacy `expenses` and `paychecks` rows are not merged into these actuals.

Negative normalized transactions that are still uncategorized are reported separately as **Uncategorized Outflow**. This amount is intentionally not assigned to a budget category until the user categorizes those transactions.

Removing a monthly budget deletes only the plan for that category/month. It does not delete or alter transaction history.

## Existing Legacy/Application Tables

### `paychecks`
Stores paycheck income events, including optional recurring schedule linkage.

### `expenses`
Stores manually tracked expenses, categories, recurring linkage, and active state.

### `loans`
Stores loan principal, current balance, interest rate, payment amount, due day, start date, notes, and active state.

### `loan_payments`
Stores payments associated with loans.

### `subscriptions`
Stores subscription obligations, billing cycle, next due date, category, active state, and notes.

### `recurring`
Stores schedules for automatic paycheck, expense, and loan-payment posting.

## Duplicate Detection

CSV imports use two levels of duplicate protection:

1. If the bank supplies an external/reference ID, duplicate detection uses `(account_id, external_id)`.
2. Otherwise, Finance Tracker creates a SHA-256 fingerprint from account ID, transaction date, normalized description, signed amount, and occurrence number.

The occurrence number allows legitimate identical same-day rows to coexist while still detecting the same imported file on a later import.

## Transfer Model

An internal transfer remains two transaction rows because two real accounts experienced activity.

```text
Addition Checking    -$500
SoFi Checking        +$500
Net wealth change       $0
```

Once confirmed, the two rows link to one another through `linked_transaction_id`. Both are classified as transfers. Reporting must exclude transfers from income/expense totals while retaining them for individual-account balance calculations.

## Budgeting Transition Rule

Update 3 does not automatically migrate or merge the legacy `paychecks` and `expenses` tables into normalized banking transactions. This avoids double-counting while the budgeting workflow is introduced. Future budget-vs-actual reporting should use normalized `transactions` as the source for actual bank activity unless a later migration explicitly changes that design.

## Data Preservation Rules

- Do not delete an account simply because it is closed; deactivate it.
- Do not duplicate a transaction across accounts.
- Do not classify transfers between owned accounts as income or spending.
- Do not commit production databases or financial exports to Git.
- Do not assume an imported CSV contains the complete lifetime history of an account.
- Preserve reconciliation snapshots as history instead of overwriting previous snapshots.
