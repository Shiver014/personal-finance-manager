# Finance Tracker Roadmap

Last updated: 2026-09-29

The project is developed incrementally using the convention **Update # - Commit #**. Each commit should represent one logical change, preserve existing behavior, and be tested before moving forward.

## Update 1 - Foundation / Accounts — Complete

- [x] Existing Tkinter dashboard and financial tracking screens
- [x] SQLite persistence
- [x] Accounts table and data-access functions
- [x] Accounts management UI
- [x] Add and edit accounts
- [x] Deactivate/reactivate accounts without deleting history
- [x] Local database remains outside Git

## Update 2 - Banking Foundation — Complete

### Commit 1 - Transaction Data Model — Complete
- [x] Normalized `transactions` table
- [x] Each transaction belongs to one account through `account_id`
- [x] Signed amount convention: positive = inflow, negative = outflow
- [x] Transaction/account indexes and foreign-key support

### Commit 2 - CSV Import Foundation — Complete
- [x] Import transactions into a selected active account
- [x] Flexible CSV header matching
- [x] Common date and amount parsing
- [x] Support amount or debit/credit layouts
- [x] Preview valid rows before import
- [x] Record import source and last-import timestamp
- [x] Tested with Addition Financial and SoFi banking exports

### Commit 3 - Duplicate Detection — Complete
- [x] Prefer bank-provided external/reference IDs when available
- [x] SHA-256 fallback fingerprints when an external ID is unavailable
- [x] Fingerprints include account, date, normalized description, amount, and occurrence number
- [x] Preserve legitimate repeated same-day identical transactions
- [x] Backfill fingerprints for older CSV-imported rows
- [x] Report imported, duplicate, and invalid-row counts

### Commit 4 - Transfer Detection & Handling — Complete
- [x] Detect conservative equal-and-opposite transfer candidates across owned accounts
- [x] Require different accounts and dates within a three-day window
- [x] Exclude ambiguous many-to-one/one-to-many matches
- [x] Require manual confirmation before classification
- [x] Link both sides with `linked_transaction_id`
- [x] Classify confirmed pairs as `transaction_type='transfer'` and `category='Transfer'`
- [x] Support unlinking confirmed transfers
- [x] Real-data validation: all 21 detected candidate pairs were manually checked against banking records and confirmed as true internal transfers

### Commit 5 - Transactions Viewer & Filtering — Complete
- [x] Read-only Transactions page
- [x] Filter by account
- [x] Filter by transaction type
- [x] Filter by category
- [x] Filter by date range
- [x] Search transaction descriptions
- [x] Reset filters
- [x] Display non-transfer inflow/outflow summaries separately from transfer entries

### Commit 6 - Account Reconciliation & Balance Accuracy — Complete
- [x] `account_reconciliations` history table
- [x] Store bank-confirmed balance and reconciliation date
- [x] Preserve reconciliation history
- [x] Calculate expected balance from the prior reconciliation plus signed account activity
- [x] Include transfers in individual-account balance movement
- [x] Calculate reconciliation difference/variance
- [x] Update `accounts.current_balance` to the latest bank-confirmed balance
- [x] Accounts UI reconciliation workflow and history
- [x] Exclude Roth IRA and Stocks from cash-account reconciliation
- [x] Real-data acceptance completed and Commit 6 pushed

## Update 3 - Budgeting / Allocation / Savings Goals — Current

### Commit 1 - Budget Data Model & Transaction Categories — Complete
- [x] Canonical `budget_categories` table
- [x] Seed default expense and income categories safely
- [x] Add/edit/activate/deactivate category management
- [x] Assign categories to one or more normalized transactions
- [x] Clear transaction categories without deleting transactions
- [x] Protect confirmed transfers from ordinary categorization
- [x] Keep transaction type synchronized with assigned category type
- [x] `monthly_budgets` table with one budget per expense category/month
- [x] Normalize budget months to the first day of the month
- [x] Monthly budget upsert/update behavior
- [x] Preserve legacy paycheck/expense tables without automatic migration or double-counting
- [x] Complete real-data acceptance test and move forward to Commit 2

### Commit 2 - Budget Planning UI & Budget-vs-Actual Reporting — Implemented / Acceptance Testing
- [x] Dedicated Budget sidebar page
- [x] Previous/current/next month navigation
- [x] Set or edit one monthly budget per expense category
- [x] Remove a monthly budget without deleting transaction history
- [x] Category-level planned, actual, remaining, percent-used, and status reporting
- [x] Monthly summary totals for planned, categorized spend, and remaining
- [x] Surface uncategorized bank outflow separately
- [x] Use normalized `transactions` only for actual spending
- [x] Exclude confirmed transfers from budget actuals
- [x] Keep legacy `paychecks` / `expenses` out of normalized budget actuals
- [x] Treat positive expense-category activity as a reduction of net category spending
- [ ] Complete real-data acceptance test and commit/push Commit 2

### Planned Next Commits
- [ ] Paycheck allocation rules
- [ ] Savings goals
- [ ] Continue connecting budgeting reports to normalized banking transactions

## Update 4 - Investments

- [ ] Roth IRA model
- [ ] Brokerage/stock accounts
- [ ] Investment holdings
- [ ] Contributions
- [ ] Purchases/sales as asset/cash exchanges rather than ordinary expenses
- [ ] Cost basis
- [ ] Dividends
- [ ] Asset allocation
- [ ] Portfolio performance
- [ ] Market-value reconciliation for investment accounts

## Update 5 - Forecasting / Net Worth

- [ ] Cash-flow forecast
- [ ] Net-worth reporting
- [ ] Compound-interest calculator
- [ ] HYSA vs. savings comparison
- [ ] Investment scenario analysis
- [ ] Net-worth projection
- [ ] Retirement projection

## Update 6 - Optional Automation / Production

- [ ] Optional financial-data aggregation integration
- [ ] Automatic transaction synchronization
- [ ] Scheduled updates
- [ ] Production packaging improvements
- [ ] Expand automated test coverage
