# Personal Finance Manager - Project Context

## 1. Project Goal

Build a desktop Personal Financial Management System (PFMS) that consolidates banking, budgeting, forecasting, and investment analysis into one application.

The application should help answer financial decision-making questions, not merely record transactions.

Examples of future decision-support questions:

- How should a paycheck be allocated across checking, savings, HYSA, investments, and expenses?
- How much cash flow will remain after recurring obligations?
- What happens to projected wealth if money is invested instead of kept in savings?
- What is the opportunity cost of keeping excess cash in a lower-yield account?
- How is net worth changing over time?

## 2. Current Technology

- Python
- Tkinter / ttk for the desktop interface
- SQLite for local persistence
- PyInstaller for executable packaging
- Git / GitHub for version control

## 3. Current Application State

The existing application already supports:

- Dashboard
- Paycheck tracking
- Expense tracking
- Loan tracking
- Loan payments
- Subscription tracking
- Recurring entries
- SQLite persistence

Sprint 1 established the financial account foundation. Sprint 2 is building normalized banking transactions and import workflows.

## 4. Financial Data Sources

### Addition Financial

The user has exported multiple individual account histories as CSV files. Each account must be treated as its own source account during import.

Important modeling rule:

> A transaction belongs to the account that actually experienced the transaction.

A grocery purchase from Checking affects Checking, not every account owned by the user.

### SoFi

The user has a SoFi Checking/Savings CSV export available. The SoFi Investing account cannot currently be exported as a CSV through the user's available workflow. The Roth IRA currently contains cash and is intended to be tracked and funded toward the annual contribution limit.

The application should therefore support investment-account data entry and/or another integration path without assuming that an Investing CSV is available.

## 5. Core Financial Modeling Rules

### Accounts

Accounts represent persistent places where financial assets or liabilities are held.

Examples:

- Checking
- Savings
- HYSA
- Roth IRA
- Brokerage
- Credit Card
- Loan

### Transactions

Transactions represent events that change an account balance.

A transaction should eventually reference one account directly.

### Transfers

Transfers move money between accounts owned by the user.

A transfer is not income and is not an expense. It changes the location of money while leaving total net worth unchanged, assuming no fee is involved.

### Closed Accounts

Accounts should be deactivated rather than deleted so historical transactions and reporting remain intact.

## 6. Current Database Foundation

The existing database contains tables for:

- `paychecks`
- `expenses`
- `loans`
- `loan_payments`
- `subscriptions`
- `recurring`

Sprint 1 added:

- `accounts`

Sprint 2 Commit 2.1 adds:

- `transactions`

Each normalized banking transaction references exactly one `account_id`. Positive amounts are inflows and negative amounts are outflows. CSV imports, duplicate detection, and transfer pairing remain separate later commits.

## 7. Architecture Direction

The application currently uses a single `app.py` for simplicity and learning.

As the application grows, responsibilities may eventually be separated into modules such as:

```text
app.py
 database.py
 accounts.py
 transactions.py
 budgeting.py
 forecasting.py
 investments.py
 ui/
```

We will not split the application prematurely. Refactoring should occur when the current structure creates a real maintenance problem.

## 8. Development Rules

1. Make one logical change per commit.
2. Test before moving to the next commit.
3. Preserve existing functionality.
4. Document important architectural decisions.
5. Never commit personal financial data.
6. Prefer existing project patterns before introducing new patterns.
7. Do not add features merely because they might be useful later.
8. Separate financial domain logic from UI behavior when practical.

## 9. Sprint Roadmap

### Sprint 1 - Foundation

- Accounts database model
- Account data-access layer
- Accounts UI
- Account creation/editing/deactivation

### Sprint 2 - Banking

- CSV import engine
- Addition Financial imports
- SoFi imports
- Account-specific transactions
- Duplicate detection
- Transfer detection and recording
- Reconciliation

### Sprint 3 - Budgeting

- Budget categories
- Paycheck allocation
- Monthly budgets
- Budget vs. actual
- Savings goals

### Sprint 4 - Investments

- Roth IRA tracking
- Brokerage holdings
- Cost basis
- Contributions
- Dividends
- Asset allocation

### Sprint 5 - Forecasting

- Cash-flow forecasting
- Compound-interest scenarios
- HYSA vs. savings comparisons
- Investment scenario comparisons
- Net-worth projections
- Retirement projections

### Sprint 6 - Automation

- Optional bank aggregation integration
- Automatic transaction synchronization
- Scheduled updates

## 10. Definition of Done

A commit is complete when:

- The application launches.
- The new behavior works.
- Existing behavior still works.
- Documentation is updated.
- The Git commit is created.
- The changes are pushed to GitHub.
- The developer can explain why the implementation was chosen.## Development Database

The recovered `finance_data.db` is now the application database. It remains ignored by Git. Development and migration tests should be run against copies or sandbox databases rather than intentionally modifying the production database.


