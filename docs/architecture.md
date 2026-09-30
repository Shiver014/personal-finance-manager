# Architecture

Last updated: 2026-09-29

## Current Structure

Finance Tracker remains intentionally simple while the domain model is being developed:

```text
Tkinter / ttk UI
      |
      v
Application + domain logic in app.py
      |
      v
Data-access functions
      |
      v
SQLite (finance_data.db)
```

The application is still a single Python module. A module split is deferred until complexity creates a clear maintenance benefit.

## Current Functional Areas

`app.py` currently contains clearly separated sections for:

- Accounts
- Normalized banking transactions
- CSV import/parsing
- Duplicate detection
- Transfer detection/confirmation/unlinking
- Transaction browsing/filtering
- Account reconciliation
- Budget/category data model
- Monthly budget planning and budget-vs-actual reporting
- Transaction category management
- Dashboard
- Income/paychecks
- Expenses/subscriptions/loans
- Recurring schedules
- Shared Tkinter widgets/helpers

## Data Access Pattern

`get_conn()` is the shared SQLite connection helper and enables foreign keys for application connections. Database operations should continue to be centralized in named data-access/domain functions instead of embedding new SQL throughout UI event handlers when practical.

Examples now include:

```text
Accounts
  add_account()
  update_account()
  set_account_active()
  get_accounts()

Transactions
  add_transaction()
  get_transactions()
  get_filtered_transactions()
  get_transaction_filter_options()

Transfers
  get_transfer_candidates()
  confirm_transfer_pair()
  unlink_transfer()
  get_confirmed_transfers()

Reconciliation
  get_latest_reconciliation()
  get_reconciliation_history()
  calculate_expected_balance()
  save_reconciliation()

Budgeting / Categories
  get_budget_categories()
  add_budget_category()
  update_budget_category()
  set_budget_category_active()
  assign_transaction_category()
  set_monthly_budget()
  get_monthly_budgets()
  copy_previous_month_budgets()
  delete_monthly_budget()
  get_budget_report()
```

## Banking Data Flow

```text
Bank CSV
   |
   v
Parse + normalize
   |
   v
Duplicate check
   |
   v
transactions table -----> Transactions Viewer
   |
   +----> Transfer candidate detection
   |           |
   |           v
   |      Manual confirmation
   |           |
   |           v
   |      Linked transfer pair
   |
   +----> Account reconciliation
               |
               v
       Bank-confirmed snapshot
```

CSV imports always target a specific active account. This preserves the rule that a transaction belongs to the account that actually experienced it.

## Transfers vs. Cash Flow

Transfers have two different meanings depending on the calculation:

- **Income/spending reporting:** exclude confirmed internal transfers.
- **Individual-account balance movement:** include the signed transfer transaction.

This distinction prevents a $500 transfer from checking to savings from appearing as both $500 of spending and $500 of income while still allowing each account balance to change correctly.

## Reconciliation Architecture

Reconciliation uses snapshots rather than trying to derive a bank balance from the entire imported transaction history.

The first reconciliation establishes a trusted bank-confirmed baseline. A later reconciliation projects the expected balance from the prior snapshot plus signed transactions in the interval and compares it with the newly entered bank balance.

This design is necessary because imported CSVs may cover only part of an account's lifetime history.

Investment accounts are intentionally excluded from this cash-account process. Roth IRA and stock balances will eventually be calculated from holdings/market value in Update 4.

## UI Architecture

Current sidebar pages are:

```text
Dashboard
Accounts
Transactions
Budget
Income
Expenses
Recurring
```

The Accounts page owns banking maintenance actions such as CSV import, transfer review, and reconciliation.

Beginning with Update 3 - Commit 1, the Transactions page remains non-destructive but now supports category assignment. Users can assign or clear canonical categories and manage the active category list. Confirmed transfers remain protected from ordinary income/expense categorization.

## Budgeting Architecture

Update 3 introduces a canonical category layer and monthly budget records without replacing the legacy paycheck/expense screens yet. The normalized `transactions` table is the planned source of actual bank activity for budget-vs-actual reporting, while `paychecks` and `expenses` remain intact for backward compatibility during the transition.

```text
budget_categories -----> monthly_budgets
       |
       +-----> normalized transactions.category

legacy paychecks / expenses
       |
       +-----> preserved temporarily; not merged automatically
```

A category has an explicit `expense` or `income` type. Assigning a category to a normalized transaction also sets that transaction's classification to the category type. Transfers are excluded from this model and continue to use the transfer workflow.

Update 3 - Commit 2 adds a dedicated Budget page. The page navigates month-by-month, edits monthly category plans, and compares them with actual normalized transaction activity. Actual spending is calculated from `transactions` rows classified as `expense`; confirmed transfers and the legacy `paychecks`/`expenses` tables remain excluded. Uncategorized negative banking transactions are surfaced separately so incomplete categorization cannot silently make the budget appear healthier than the underlying bank activity.

Update 3 - Commit 2.1 adds a non-destructive copy-forward workflow for monthly plans. While viewing a target month, the user can copy saved budgets from the immediately previous calendar month. Existing destination budgets are preserved and never overwritten, inactive categories are skipped, and only plan records are copied; transaction actuals remain tied to their own transaction dates.

## Future Direction

As the project grows, the likely direction is:

```text
UI
 |
 v
Application / Domain Services
 |
 +---- Accounts & Reconciliation
 +---- Transactions & Imports
 +---- Transfers
 +---- Budgeting
 +---- Investments
 +---- Forecasting
 |
 v
Data Access Layer
 |
 v
SQLite
```

This split should happen only when it makes the code easier to test and maintain; it is not required simply for architectural appearance.
