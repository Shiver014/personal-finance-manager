# Personal Finance Manager

A local-first desktop Personal Financial Management System (PFMS) built with **Python**, **Tkinter/ttk**, and **SQLite**.

The project is designed to bring everyday banking, transaction analysis, budgeting, account reconciliation, forecasting, and investment tracking into one desktop application while keeping personal financial data under the user's local control.

## Project Status

**Current development stage:** Update 3 — Budgeting & Paycheck Allocation  
**Current implementation:** Update 3 - Commit 2 — Budget Planning & Budget-vs-Actual Reporting

| Update | Focus | Status |
| --- | --- | --- |
| Update 1 | Foundation & account management | Complete |
| Update 2 | Banking, transactions, transfers & reconciliation | Complete |
| Update 3 | Budgeting, paycheck allocation & savings goals | In progress |
| Update 4 | Investments & Roth IRA / brokerage tracking | Planned |
| Update 5 | Forecasting, net worth & long-term scenarios | Planned |
| Update 6 | Optional automation / bank connectivity | Planned |

## Current Features

### Banking & Accounts

- Create, edit, deactivate, and reactivate financial accounts without deleting history
- Track current balances and account metadata
- Import bank transactions from CSV files into a normalized transaction ledger
- Flexible CSV parsing for common date, description, amount, debit/credit, and transaction-ID fields
- Duplicate detection using bank-provided IDs when available and deterministic SHA-256 fingerprints as a fallback
- Preserve signed transaction amounts: positive values represent inflows and negative values represent outflows
- Review high-confidence internal transfer candidates before confirmation
- Link both sides of confirmed transfers while keeping them separate from income and expense reporting
- Reconcile checking and savings accounts against bank-confirmed balances
- Preserve reconciliation history and calculate expected balances from prior reconciliation snapshots

### Transactions

- Browse normalized transactions across all tracked accounts
- Filter by account, transaction type, category, date range, and description
- Assign reusable expense or income categories to transactions
- Clear transaction categories without deleting the transaction
- Manage custom categories through activation/deactivation instead of destructive deletion
- Protect confirmed transfers from accidental income/expense categorization

### Budgeting

- Create monthly budgets by expense category
- Edit or remove a monthly budget without changing transaction history
- Compare planned budget amounts against categorized banking activity
- Track remaining budget and percentage used by category
- Identify categories that are on track, at their limit, or over budget
- Show uncategorized monthly outflow separately so incomplete categorization is visible
- Exclude confirmed internal transfers from budget spending
- Treat positive activity inside an expense category as a reduction to net spending, such as a refund
- Keep budget actuals month-specific based on each transaction's transaction date

### Existing Personal Finance Tools

- Dashboard summaries
- Manual paycheck tracking
- Manual expense tracking
- Loan tracking and payment history
- Subscription tracking
- Recurring paycheck, expense, and loan-payment schedules
- Automatic posting of overdue recurring entries at application startup

## Important Data Model Rule

The project currently contains both the original manual finance tables (`paychecks`, `expenses`, and related features) and the newer normalized banking `transactions` ledger.

**Budget actuals use the normalized transaction ledger only.** Legacy manual paycheck and expense rows are intentionally not merged into budget actuals yet because doing so could double-count real financial activity that already exists in imported bank transactions.

This separation will be revisited as the application continues through Update 3.

## Technology Stack

| Layer | Technology |
| --- | --- |
| Language | Python |
| Desktop UI | Tkinter / ttk |
| Database | SQLite |
| Packaging | PyInstaller |
| Testing | Python `unittest` |
| Version Control | Git / GitHub |

## Project Structure

```text
personal-finance-manager/
├── app.py
├── build.py
├── README.md
├── CHANGELOG.md
├── project_context.md
├── LICENSE
├── .gitignore
├── tests/
│   ├── test_update3_commit1.py
│   └── test_update3_commit2.py
├── docs/
│   ├── architecture.md
│   ├── database.md
│   ├── roadmap.md
│   └── decisions.md
├── imports/          # Local bank CSVs; ignored by Git
├── backups/          # Local database backups; ignored by Git
└── finance_data.db   # Local SQLite database; ignored by Git
```

## Running the Application

From the project root:

```bash
python app.py
```

The application creates `finance_data.db` automatically when no database exists and applies compatible schema additions during startup.

Before testing a new development commit against real financial data, create a backup of the existing database.

## Running Tests

From the project root:

```bash
python -m py_compile app.py
python -m unittest discover -s tests -v
```

Automated development tests use temporary SQLite databases so the project's real financial database is not required for test execution.

## Building the Executable

From the project root:

```bash
python build.py
```

PyInstaller creates the executable in `dist/`. The SQLite database is intentionally kept outside the executable so financial data remains separate from the packaged application.

## Privacy & Security

This project is designed around local control of personal financial information. The Git repository must **never** contain private financial data such as:

- Bank transaction CSVs
- Personal SQLite databases
- Account or routing numbers
- Brokerage exports
- API keys, secrets, or credentials
- Backups containing real financial history
- Other personally identifiable financial information

The `.gitignore` file is intended to exclude these files, but always verify the staging area before committing:

```bash
git status
git diff --cached
```

## Development Workflow

Development is intentionally incremental. Each commit should represent one focused, testable change and should preserve existing behavior unless the commit explicitly documents a migration.

The project uses the naming convention:

```text
Update # - Commit #
```

Examples:

```text
Update 2 - Commit 4: Transfer Detection & Handling
Update 2 - Commit 6: Account Reconciliation & Balance Accuracy
Update 3 - Commit 1: Budget Data Model & Transaction Categories
Update 3 - Commit 2: Budget Planning & Budget-vs-Actual Reporting
```

For additional project detail, see:

- `project_context.md` — current implementation context
- `CHANGELOG.md` — implementation history
- `docs/architecture.md` — architecture and component responsibilities
- `docs/database.md` — SQLite schema and data-model notes
- `docs/roadmap.md` — planned development sequence
- `docs/decisions.md` — important design decisions and tradeoffs

## Next Planned Work

The next Update 3 work is expected to focus on **paycheck allocation**, followed by **savings goals** and tighter integration between planned spending and actual normalized banking activity.

Later updates will add investment tracking, net-worth reporting, forecasting, long-term financial scenarios, and optional automated connectivity.
