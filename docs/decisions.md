# Architecture Decisions

Last updated: 2026-09-29

## ADR-001: Accounts Are Separate From Transactions

**Status:** Accepted

Financial accounts are persistent entities; transactions are events that occur on those accounts. Transactions therefore reference an `account_id` rather than duplicating institution/account metadata.

**Consequences:** multiple institutions and account types are supported, account history survives deactivation, transfers can connect two account-specific transactions, and future net-worth reporting can aggregate account values.

---

## ADR-002: Keep Personal Financial Data Outside Git

**Status:** Accepted

SQLite production databases, bank/brokerage CSV exports, import folders, backups containing personal data, and secrets must not be committed to the repository.

**Reason:** the public/project code history should contain software and documentation, not sensitive financial records.

---

## ADR-003: Keep the Application in One Python Module for Now

**Status:** Accepted

Continue using `app.py` while the domain model is still evolving. Organize code into clear sections and reusable functions. Split into modules only when doing so creates a concrete maintenance/testing benefit.

---

## ADR-004: Signed Transaction Amounts

**Status:** Accepted

Normalized banking transactions use one signed `amount` field:

```text
positive = money into the account
negative = money out of the account
```

This simplifies account-level arithmetic, transfer matching, filtering, and future cash-flow reporting.

---

## ADR-005: CSV Imports Belong to a Selected Account

**Status:** Accepted

Every bank CSV import must target one active account. A transaction is stored only under the account that actually experienced it.

**Consequence:** importing the same financial event into unrelated owned accounts is not valid simply because all accounts belong to the same user.

---

## ADR-006: Duplicate Detection Uses Bank IDs First and Fingerprints Second

**Status:** Accepted

When an external/reference ID exists, it is the preferred duplicate key within the account. Otherwise, Finance Tracker uses a deterministic SHA-256 fingerprint based on account, date, normalized description, signed amount, and occurrence number.

**Reason:** bank-provided IDs are strongest when available, while occurrence-aware fingerprints protect against reimports without incorrectly removing legitimate identical same-day transactions.

---

## ADR-007: Internal Transfers Are Two Linked Transactions, Not Income/Expense

**Status:** Accepted

A transfer between owned accounts remains two account-specific transaction rows: one negative source transaction and one positive destination transaction. Confirmed pairs are linked through `linked_transaction_id` and classified as `transfer` / `Transfer`.

Transfer detection is intentionally conservative: equal-and-opposite amount, different accounts, dates within the configured window, and an unambiguous one-to-one match. Classification requires user confirmation and can be undone through unlinking.

**Reporting consequence:** transfers are excluded from income/spending totals but included when measuring an individual account's balance movement.

**Validation:** 21 high-confidence candidate pairs in the current real dataset were manually compared with banking records and all 21 were confirmed as genuine internal transfers.

---

## ADR-008: Transaction Viewer Is Read-Only During the Banking Foundation

**Status:** Accepted

The Transactions page provides inspection, searching, filtering, and summary totals but does not directly edit/delete normalized banking transactions yet.

**Reason:** during the banking foundation, preserving imported financial history is safer than exposing broad editing controls before categorization and audit behavior are fully designed.

---

## ADR-009: Reconciliation Uses Bank-Confirmed Snapshots

**Status:** Accepted

Do not assume imported transactions represent an account's complete lifetime history and do not blindly calculate the current bank balance from all imported rows.

The first reconciliation establishes a trusted bank-confirmed baseline. Later reconciliations calculate:

```text
expected balance = prior confirmed balance + signed activity since prior reconciliation
variance = new bank balance - expected balance
```

Each reconciliation is stored as history. The latest bank-confirmed balance becomes `accounts.current_balance`.

**Consequence:** missing/partial historical CSV coverage does not invalidate the entire balance model, and discrepancies can be surfaced explicitly.

---

## ADR-010: Cash Reconciliation Excludes Investment Accounts

**Status:** Accepted

Roth IRA and Stocks accounts do not use the checking/savings reconciliation workflow.

**Reason:** investment balances can change because of security prices, purchases, sales, dividends, and cash positions. Treating market-value changes as ordinary banking transactions would produce incorrect reconciliation results.

Investment holdings and market-value reconciliation are deferred to Update 4.

---

## ADR-011: Preserve History Instead of Destructive Cleanup

**Status:** Accepted

Prefer deactivation, linking/unlinking, classifications, and historical snapshots over destructive deletion when modeling financial history.

This applies especially to closed accounts, confirmed transfers, and reconciliation records. Destructive maintenance against real financial data should be preceded by a database backup and explicit validation.

---

## ADR-012: Canonical Categories Classify Normalized Transactions

**Status:** Accepted

Update 3 introduces `budget_categories` as the canonical list of expense/income categories. The existing `transactions.category` text field is retained for compatibility, but assignments are made through the canonical category records.

Assigning a canonical category updates both the category name and `transaction_type` (`expense` or `income`). Confirmed transfers are protected from this workflow because transfer classification has different accounting meaning.

Category names are globally unique case-insensitively because normalized transactions currently store the category name as text. Categories are deactivated rather than deleted so historical assignments remain understandable.

---

## ADR-013: New Budget Actuals Will Use the Normalized Transaction Ledger

**Status:** Accepted

The older `paychecks` and `expenses` tables remain in place during Update 3 for backward compatibility, but they are not automatically merged with imported banking transactions.

Future budget-vs-actual reporting should use normalized `transactions` as the source of actual banking activity and exclude confirmed transfers from income/spending totals.

**Reason:** counting both manually entered legacy rows and imported normalized transactions could double-count the same real-world activity. A later explicit migration may change this, but Commit 1 preserves both systems without silently combining them.

---

## ADR-014: Monthly Budgets Are Expense-Category Plans

**Status:** Accepted

`monthly_budgets` stores one planned amount per expense category per month. Months are normalized to the first day (`YYYY-MM-01`) and repeated saves update the existing category/month record.

Income categories are not valid monthly spending budgets. Paycheck allocation will be modeled separately in a later Update 3 commit rather than overloading the monthly expense budget table.
