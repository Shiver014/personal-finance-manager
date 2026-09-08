# Personal Finance Manager

A desktop Personal Financial Management System (PFMS) built with Python, Tkinter, and SQLite.

The project is designed to bring banking, budgeting, forecasting, and investment analysis into one application while keeping personal financial data locally controlled by the user.

## Current Status

**Development stage:** Update 2 - Banking & Transactions

### Current application capabilities

- Dashboard with financial summaries
- Paycheck tracking
- Expense tracking
- Loan tracking and payments
- Subscription tracking
- Recurring financial entries
- SQLite-backed local storage
- Financial account management
- Normalized transaction data model linked to accounts

### Planned capabilities

- CSV transaction import foundation with preview and validation
- Addition Financial CSV imports
- SoFi Checking/Savings CSV imports
- Transaction browsing and filtering UI
- Transfer tracking between accounts
- Budgeting and paycheck allocation
- Net worth tracking
- Roth IRA and investment tracking
- Investment scenario forecasting
- HYSA vs. savings opportunity-cost analysis
- Retirement and long-term financial forecasting
- Optional automated bank connectivity

## Technology Stack

| Layer | Technology |
| --- | --- |
| Language | Python |
| Desktop UI | Tkinter / ttk |
| Database | SQLite |
| Packaging | PyInstaller |
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
├── docs/
│   ├── architecture.md
│   ├── database.md
│   ├── roadmap.md
│   └── decisions.md
├── imports/          # Local financial CSVs; ignored by Git
├── backups/          # Local database backups; ignored by Git
└── finance_data.db  # Local database; ignored by Git
```

## Privacy and Security

This application is intended to work with personal financial data locally. The repository must **never** contain:

- Bank transaction CSVs
- Account numbers
- Brokerage exports
- Personal financial databases
- API keys or credentials
- Other private financial information

The `.gitignore` file is configured to keep local financial data out of Git, but users should still verify `git status` before committing.

## Running the Application

From the project root:

```bash
python app.py
```

The application creates `finance_data.db` automatically if it does not already exist.

## Building the Executable

From the project root:

```bash
python build.py
```

The executable is created in `dist/`. The SQLite database is intentionally kept outside the executable so the user's financial data remains a separate local file.

## Development Workflow

The project is being developed incrementally through documented sprints and commits. Each commit should be small, testable, and focused on one logical objective.

See:

- `project_context.md` for the current project context
- `CHANGELOG.md` for implementation history
- `docs/architecture.md` for architectural decisions
- `docs/database.md` for the database model
- `docs/roadmap.md` for planned features
- `docs/decisions.md` for important design decisions
