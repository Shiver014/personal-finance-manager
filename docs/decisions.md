# Architecture Decisions

## ADR-001: Accounts Are Separate From Transactions

**Status:** Accepted

**Decision:**

Represent financial accounts as their own database entities rather than embedding account information directly inside each transaction record.

**Reasoning:**

Accounts are persistent entities, while transactions are events. An account can exist for years and contain many transactions. Separating the two avoids repeated institution/account metadata and provides a clean relationship for future transfers, reconciliation, and reporting.

**Consequences:**

- Multiple financial institutions can be represented.
- Historical transactions can remain when an account is deactivated.
- Transactions can eventually reference an `account_id`.
- Transfers can reference source and destination accounts.
- Net-worth reporting can aggregate balances by account.

---

## ADR-002: Keep Personal Financial Data Outside Git

**Status:** Accepted

**Decision:**

Do not commit SQLite databases, bank CSV exports, brokerage exports, or other personal financial data to the public repository.

**Reasoning:**

Financial exports may contain sensitive transaction information and account identifiers. The repository should contain application code and documentation, not personal financial records.

**Consequences:**

- `finance_data.db` is ignored.
- `imports/` is ignored.
- CSV and common financial-export formats are ignored.
- The application must be able to create its database locally.

---

## ADR-003: Keep the Application in One Python Module for Now

**Status:** Accepted

**Decision:**

Continue using a single `app.py` until the current structure creates a measurable maintenance problem.

**Reasoning:**

The project is also a learning exercise. Splitting the application too early would add architectural complexity before the domain model is stable.

**Consequences:**

- The application remains easy to navigate while learning.
- New database operations should still be organized into clearly labeled sections.
- A future module split remains available when justified.


---

## ADR-004: Use Signed Amounts for Normalized Transactions

**Status:** Accepted

**Decision:**

Store normalized transaction amounts from the perspective of the account: positive for inflows and negative for outflows.

**Reasoning:**

A single signed amount works consistently across checking, savings, and investment cash activity and simplifies account-level cash-flow calculations.

**Consequences:**

- Import adapters must normalize each institution's debit/credit format into this convention.
- Transfers will naturally produce a negative record in the source account and a positive record in the destination account.
- Duplicate detection and transfer pairing remain separate concerns.
