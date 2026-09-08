import tkinter as tk
from tkinter import ttk, messagebox
import sqlite3
import os
import sys
from datetime import date, timedelta
import calendar

# ── Database path ─────────────────────────────────────────────────────────────
if getattr(sys, "frozen", False):
    BASE_DIR = os.path.dirname(os.path.abspath(sys.executable))
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH  = os.path.join(BASE_DIR, "finance_data.db")

# ── Palette ───────────────────────────────────────────────────────────────────
BG         = "#0f1117"
BG2        = "#1a1d27"
BG3        = "#22263a"
ACCENT     = "#4fffb0"
ACCENT2    = "#ff6b6b"
ACCENT3    = "#ffd166"
ACCENT4    = "#74b9ff"
ACCENT5    = "#c084fc"   # purple – recurring
TEXT       = "#e8eaf6"
TEXT_DIM   = "#7986a3"
BORDER     = "#2e3250"
FONT_H1    = ("Times New Roman", 24, "bold")
FONT_H2    = ("Times New Roman", 15, "bold")
FONT_BODY  = ("Times New Roman", 12)
FONT_SMALL = ("Times New Roman", 10)
FONT_MONO  = ("Times New Roman", 12)

MAX_W = 860

# ═════════════════════════════════════════════════════════════════════════════
# DATABASE
# ═════════════════════════════════════════════════════════════════════════════
def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS paychecks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        amount REAL NOT NULL, date TEXT NOT NULL, note TEXT,
        recurring_id INTEGER);
    CREATE TABLE IF NOT EXISTS expenses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        amount REAL NOT NULL, category TEXT NOT NULL,
        description TEXT, date TEXT NOT NULL,
        recurring_id INTEGER);
    CREATE TABLE IF NOT EXISTS loans (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL, principal REAL NOT NULL, balance REAL NOT NULL,
        interest_rate REAL NOT NULL, monthly_payment REAL NOT NULL,
        due_day INTEGER NOT NULL, start_date TEXT NOT NULL, note TEXT);
    CREATE TABLE IF NOT EXISTS loan_payments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        loan_id INTEGER NOT NULL, amount REAL NOT NULL,
        date TEXT NOT NULL, note TEXT, recurring_id INTEGER,
        FOREIGN KEY(loan_id) REFERENCES loans(id));
    CREATE TABLE IF NOT EXISTS subscriptions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL, amount REAL NOT NULL,
        billing_cycle TEXT NOT NULL, next_due TEXT NOT NULL,
        category TEXT, active INTEGER DEFAULT 1, note TEXT);

    -- Financial accounts represent the places where money is held.
    -- Transactions will reference these accounts in a later sprint.
    CREATE TABLE IF NOT EXISTS accounts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        institution TEXT NOT NULL,
        account_name TEXT NOT NULL,
        account_type TEXT NOT NULL,
        nickname TEXT,
        current_balance REAL DEFAULT 0,
        last_import TEXT,
        is_active INTEGER DEFAULT 1,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP);

    -- Normalized banking transactions. Each row belongs to exactly one account.
    -- Signed amount convention: positive = money in, negative = money out.
    CREATE TABLE IF NOT EXISTS transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        account_id INTEGER NOT NULL,
        transaction_date TEXT NOT NULL,
        posted_date TEXT,
        description TEXT NOT NULL,
        amount REAL NOT NULL,
        category TEXT,
        transaction_type TEXT NOT NULL DEFAULT 'uncategorized',
        source TEXT NOT NULL DEFAULT 'manual',
        external_id TEXT,
        imported_at TEXT,
        note TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(account_id) REFERENCES accounts(id));

    CREATE INDEX IF NOT EXISTS idx_transactions_account_date
        ON transactions(account_id, transaction_date);
    CREATE INDEX IF NOT EXISTS idx_transactions_external_id
        ON transactions(account_id, external_id);

    -- Recurring schedules table
    -- type: 'paycheck' | 'expense' | 'loan_payment'
    -- frequency: 'daily' | 'weekly' | 'biweekly' | 'monthly' | 'yearly'
    -- day_of_week: 0=Mon..6=Sun (for weekly/biweekly)
    -- day_of_month: 1-31 (for monthly/yearly)
    -- month_of_year: 1-12 (for yearly)
    CREATE TABLE IF NOT EXISTS recurring (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        type TEXT NOT NULL,
        label TEXT NOT NULL,
        amount REAL NOT NULL,
        frequency TEXT NOT NULL,
        day_of_week INTEGER,
        day_of_month INTEGER,
        month_of_year INTEGER,
        next_date TEXT NOT NULL,
        active INTEGER DEFAULT 1,
        -- extra fields per type
        category TEXT,
        loan_id INTEGER,
        note TEXT);
    """)
    # Migrations: safely add columns that may not exist in older DBs
    migrations = [
        ("paychecks",     "recurring_id", "INTEGER"),
        ("expenses",      "recurring_id", "INTEGER"),
        ("expenses",      "active",       "INTEGER DEFAULT 1"),
        ("loan_payments", "recurring_id", "INTEGER"),
        ("loans",         "active",       "INTEGER DEFAULT 1"),
        ("accounts",      "created_at",  "TEXT DEFAULT CURRENT_TIMESTAMP"),
    ]
    for tbl, col, typedef in migrations:
        try:
            conn.execute(f"ALTER TABLE {tbl} ADD COLUMN {col} {typedef}")
        except Exception:
            pass
    conn.commit(); conn.close()

def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

# ═════════════════════════════════════════════════════════════════════════════
# ACCOUNTS DATA ACCESS
# ═════════════════════════════════════════════════════════════════════════════
def add_account(institution, account_name, account_type, nickname="", current_balance=0.0):
    """Create an active financial account and return its database ID."""
    conn = get_conn()
    cursor = conn.execute(
        """
        INSERT INTO accounts (
            institution, account_name, account_type, nickname, current_balance
        )
        VALUES (?, ?, ?, ?, ?)
        """,
        (institution, account_name, account_type, nickname, current_balance),
    )
    conn.commit()
    account_id = cursor.lastrowid
    conn.close()
    return account_id


def update_account(account_id, institution, account_name, account_type, nickname, current_balance):
    """Update an existing financial account."""
    conn = get_conn()
    conn.execute(
        """
        UPDATE accounts
        SET institution=?, account_name=?, account_type=?, nickname=?, current_balance=?
        WHERE id=?
        """,
        (institution, account_name, account_type, nickname, current_balance, account_id),
    )
    conn.commit()
    conn.close()


def set_account_active(account_id, active):
    """Activate or deactivate an account without deleting its history."""
    conn = get_conn()
    conn.execute("UPDATE accounts SET is_active=? WHERE id=?", (1 if active else 0, account_id))
    conn.commit()
    conn.close()


def get_accounts(active_only=True):
    """Return accounts ordered by institution and account name."""
    conn = get_conn()
    if active_only:
        rows = conn.execute(
            """
            SELECT id, institution, account_name, account_type, nickname,
                   current_balance, last_import, is_active, created_at
            FROM accounts
            WHERE is_active = 1
            ORDER BY institution, account_name
            """
        ).fetchall()
    else:
        rows = conn.execute(
            """
            SELECT id, institution, account_name, account_type, nickname,
                   current_balance, last_import, is_active, created_at
            FROM accounts
            ORDER BY institution, account_name
            """
        ).fetchall()
    conn.close()
    return rows

# ═════════════════════════════════════════════════════════════════════════════
# TRANSACTIONS DATA ACCESS
# ═════════════════════════════════════════════════════════════════════════════
def add_transaction(account_id, transaction_date, description, amount,
                    posted_date=None, category=None, transaction_type="uncategorized",
                    source="manual", external_id=None, imported_at=None, note=None):
    """Create a transaction tied to one financial account and return its ID.

    Amounts use a signed convention: positive values are inflows and negative
    values are outflows. Transfer pairing and duplicate detection are handled
    in later Sprint 2 commits.
    """
    conn = get_conn()
    try:
        cursor = conn.execute(
            """
            INSERT INTO transactions (
                account_id, transaction_date, posted_date, description, amount,
                category, transaction_type, source, external_id, imported_at, note
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (account_id, transaction_date, posted_date, description, amount,
             category, transaction_type, source, external_id, imported_at, note),
        )
        conn.commit()
        return cursor.lastrowid
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def get_transactions(account_id=None):
    """Return transactions newest-first, optionally limited to one account."""
    conn = get_conn()
    if account_id is None:
        rows = conn.execute(
            """
            SELECT id, account_id, transaction_date, posted_date, description,
                   amount, category, transaction_type, source, external_id,
                   imported_at, note, created_at
            FROM transactions
            ORDER BY transaction_date DESC, id DESC
            """
        ).fetchall()
    else:
        rows = conn.execute(
            """
            SELECT id, account_id, transaction_date, posted_date, description,
                   amount, category, transaction_type, source, external_id,
                   imported_at, note, created_at
            FROM transactions
            WHERE account_id = ?
            ORDER BY transaction_date DESC, id DESC
            """,
            (account_id,),
        ).fetchall()
    conn.close()
    return rows


def get_transaction_count(account_id=None):
    """Return the number of normalized banking transactions."""
    conn = get_conn()
    if account_id is None:
        count = conn.execute("SELECT COUNT(*) FROM transactions").fetchone()[0]
    else:
        count = conn.execute(
            "SELECT COUNT(*) FROM transactions WHERE account_id = ?", (account_id,)
        ).fetchone()[0]
    conn.close()
    return count


# ═════════════════════════════════════════════════════════════════════════════
# RECURRING ENGINE
# ═════════════════════════════════════════════════════════════════════════════
FREQ_LABELS = ["daily", "weekly", "biweekly", "monthly", "yearly"]
DOW_NAMES   = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]

def next_occurrence(freq, current_date, day_of_week=None, day_of_month=None, month_of_year=None):
    """Compute the next date after current_date for the given frequency."""
    d = current_date
    if freq == "daily":
        return d + timedelta(days=1)
    elif freq == "weekly":
        days_ahead = (day_of_week - d.weekday()) % 7
        if days_ahead == 0: days_ahead = 7
        return d + timedelta(days=days_ahead)
    elif freq == "biweekly":
        days_ahead = (day_of_week - d.weekday()) % 7
        if days_ahead == 0: days_ahead = 14
        elif days_ahead < 7: days_ahead += 7  # skip to next occurrence 2 weeks out
        return d + timedelta(days=days_ahead)
    elif freq == "monthly":
        # same day next month
        y, m = d.year, d.month + 1
        if m > 12: y, m = y+1, 1
        dom = min(day_of_month, calendar.monthrange(y, m)[1])
        return date(y, m, dom)
    elif freq == "yearly":
        y = d.year + 1
        dom = min(day_of_month, calendar.monthrange(y, month_of_year)[1])
        return date(y, month_of_year, dom)
    return d + timedelta(days=30)

def first_occurrence(freq, day_of_week=None, day_of_month=None, month_of_year=None):
    """Compute the first future occurrence from today."""
    today = date.today()
    if freq == "daily":
        return today
    elif freq in ("weekly", "biweekly"):
        days_ahead = (day_of_week - today.weekday()) % 7
        return today + timedelta(days=days_ahead)
    elif freq == "monthly":
        dom = day_of_month or 1
        d = today.replace(day=min(dom, calendar.monthrange(today.year, today.month)[1]))
        if d < today:
            y, m = today.year, today.month + 1
            if m > 12: y, m = y+1, 1
            d = date(y, m, min(dom, calendar.monthrange(y, m)[1]))
        return d
    elif freq == "yearly":
        mon = month_of_year or today.month
        dom = day_of_month or 1
        d = date(today.year, mon, min(dom, calendar.monthrange(today.year, mon)[1]))
        if d < today:
            d = date(today.year+1, mon, min(dom, calendar.monthrange(today.year+1, mon)[1]))
        return d
    return today

def process_recurring():
    """Post any overdue recurring entries and advance their next_date. Returns count posted."""
    today = date.today()
    conn  = get_conn()
    rows  = conn.execute(
        "SELECT id,type,label,amount,frequency,day_of_week,day_of_month,"
        "month_of_year,next_date,category,loan_id,note FROM recurring WHERE active=1"
    ).fetchall()
    posted = 0
    for row in rows:
        rid,rtype,label,amount,freq,dow,dom,moy,next_date_str,cat,loan_id,note = row
        nd = date.fromisoformat(next_date_str)
        while nd <= today:
            ds = nd.isoformat()
            if rtype == "paycheck":
                conn.execute(
                    "INSERT INTO paychecks(amount,date,note,recurring_id) VALUES(?,?,?,?)",
                    (amount, ds, f"[Auto] {label}" + (f" – {note}" if note else ""), rid))
            elif rtype == "expense":
                conn.execute(
                    "INSERT INTO expenses(amount,category,description,date,recurring_id) VALUES(?,?,?,?,?)",
                    (amount, cat or "Other", label + (f" – {note}" if note else ""), ds, rid))
            elif rtype == "loan_payment" and loan_id:
                conn.execute(
                    "INSERT INTO loan_payments(loan_id,amount,date,note,recurring_id) VALUES(?,?,?,?,?)",
                    (loan_id, amount, ds, f"[Auto] {label}" + (f" – {note}" if note else ""), rid))
                conn.execute("UPDATE loans SET balance=MAX(0,balance-?) WHERE id=?", (amount, loan_id))
            posted += 1
            nd = next_occurrence(freq, nd, dow, dom, moy)
        conn.execute("UPDATE recurring SET next_date=? WHERE id=?", (nd.isoformat(), rid))
    conn.commit(); conn.close()
    return posted

# ═════════════════════════════════════════════════════════════════════════════
# HELPERS / WIDGETS
# ═════════════════════════════════════════════════════════════════════════════
def today_str(): return date.today().isoformat()

def week_bounds(d=None):
    d = d or date.today()
    s = d - timedelta(days=d.weekday())
    return s.isoformat(), (s + timedelta(days=6)).isoformat()

def month_bounds(year=None, month=None):
    y = year  or date.today().year
    m = month or date.today().month
    last = calendar.monthrange(y, m)[1]
    return f"{y:04d}-{m:02d}-01", f"{y:04d}-{m:02d}-{last:02d}"

def fmt_money(v): return f"${v:,.2f}"

def styled_entry(parent, **kw):
    return tk.Entry(parent, bg=BG3, fg=TEXT, insertbackground=ACCENT,
                    relief="flat", font=FONT_MONO, highlightthickness=1,
                    highlightcolor=ACCENT, highlightbackground=BORDER, **kw)

def styled_btn(parent, text, command, color=ACCENT, fg=BG, **kw):
    return tk.Button(parent, text=text, command=command, bg=color, fg=fg,
                     relief="flat", font=FONT_BODY, activebackground=TEXT,
                     activeforeground=BG, cursor="hand2", padx=14, pady=7, **kw)

def section_card(parent, title, bg=BG2, **kw):
    f = tk.Frame(parent, bg=bg, highlightthickness=1, highlightbackground=BORDER, **kw)
    tk.Label(f, text=title, bg=bg, fg=ACCENT, font=FONT_H2,
             anchor="w").pack(fill="x", padx=18, pady=(12,4))
    tk.Frame(f, bg=BORDER, height=1).pack(fill="x", padx=18, pady=(0,10))
    return f

class ScrollFrame(tk.Frame):
    def __init__(self, parent, bg=BG, **kw):
        super().__init__(parent, bg=bg, **kw)
        self.canvas = tk.Canvas(self, bg=bg, highlightthickness=0)
        self.sb     = tk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.inner  = tk.Frame(self.canvas, bg=bg)
        self.inner.bind("<Configure>", lambda e: self.canvas.configure(
            scrollregion=self.canvas.bbox("all")))
        self._win = self.canvas.create_window((0,0), window=self.inner, anchor="nw")
        self.canvas.configure(yscrollcommand=self.sb.set)
        self.canvas.bind("<Configure>", self._resize)
        self.sb.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)
        self.bind_all("<MouseWheel>",
            lambda e: self.canvas.yview_scroll(-1*(e.delta//120), "units"))
    def _resize(self, event):
        self.canvas.itemconfig(self._win, width=event.width)

def form_row(parent, label_text, widget_factory, bg=BG2):
    row = tk.Frame(parent, bg=bg)
    row.pack(fill="x", padx=24, pady=5)
    row.columnconfigure(0, weight=1); row.columnconfigure(1, weight=2)
    tk.Label(row, text=label_text, bg=bg, fg=TEXT, font=FONT_BODY, anchor="w").grid(row=0,column=0,sticky="w")
    w = widget_factory(row)
    w.grid(row=0, column=1, sticky="ew", padx=(12,0))
    return w

_tree_styled = False
def _style_tree():
    global _tree_styled
    if _tree_styled: return
    s = ttk.Style()
    # 'vista'/'xpnative' (Windows default themes) ignore custom Treeview
    # colors entirely and always render a white background. 'clam' is a
    # theme that actually honors background/foreground overrides.
    try:
        s.theme_use("clam")
    except tk.TclError:
        pass
    s.configure("Treeview", background=BG3, foreground=TEXT,
                 fieldbackground=BG3, font=FONT_SMALL, rowheight=26,
                 borderwidth=0)
    s.configure("Treeview.Heading", background=BG2, foreground=ACCENT,
                 font=FONT_SMALL, borderwidth=0)
    s.map("Treeview",
          background=[("selected", BG)],
          foreground=[("selected", ACCENT)])
    s.map("Treeview.Heading", background=[("active", BG2)])
    _tree_styled = True

def make_tree(parent, cols, widths, height=10):
    _style_tree()
    t = ttk.Treeview(parent, columns=cols, show="headings", height=height)
    for c,w in zip(cols, widths):
        t.heading(c, text=c); t.column(c, width=w)
    return t

# ═════════════════════════════════════════════════════════════════════════════
# RECURRING DIALOG  (shared by Income, Expenses, Loans tabs)
# ═════════════════════════════════════════════════════════════════════════════
EXPENSE_CATS = ["Food","Transport","Shopping","Entertainment","Health","Utilities","Other"]

class RecurringDialog(tk.Toplevel):
    """
    Universal dialog to add/edit a recurring schedule.
    rtype: 'paycheck' | 'expense' | 'loan_payment'
    existing: row tuple from recurring table (for edit), or None
    loans: list of (id, name) for loan_payment type
    on_save: callback()
    """
    def __init__(self, parent, rtype, on_save, existing=None, loans=None):
        super().__init__(parent)
        self.rtype    = rtype
        self.on_save  = on_save
        self.existing = existing
        self.loans    = loans or []

        titles = {"paycheck":"Recurring Paycheck","expense":"Recurring Expense","loan_payment":"Recurring Loan Payment"}
        self.title(titles.get(rtype,"Recurring"))
        self.configure(bg=BG)
        self.geometry("500x560")
        self.resizable(False, False)

        tk.Label(self, text=f"🔁  {titles.get(rtype,'')}",
                 bg=BG, fg=ACCENT5, font=FONT_H2).pack(pady=14)

        # ── Fields ────────────────────────────────────────────────────────
        self._vars = {}
        inner = tk.Frame(self, bg=BG); inner.pack(fill="x", padx=28)
        inner.columnconfigure(0, weight=1); inner.columnconfigure(1, weight=2)

        def row(lbl, key, widget_fn, r):
            tk.Label(inner, text=lbl, bg=BG, fg=TEXT, font=FONT_SMALL,
                     anchor="w").grid(row=r, column=0, sticky="w", pady=5)
            w = widget_fn(inner)
            w.grid(row=r, column=1, sticky="ew", padx=(10,0), pady=5)
            return w

        r = 0
        # Label
        self._label_e = row("Label / Name", "label",
            lambda p: styled_entry(p, width=26), r); r+=1

        # Amount
        self._amt_e = row("Amount ($)", "amt",
            lambda p: styled_entry(p, width=16), r); r+=1

        # Frequency
        self._freq_var = tk.StringVar(value="monthly")
        freq_cb = row("Frequency", "freq",
            lambda p: ttk.Combobox(p, textvariable=self._freq_var,
                                   values=FREQ_LABELS, width=14, font=FONT_BODY,
                                   state="readonly"), r); r+=1
        self._freq_var.trace_add("write", lambda *_: self._update_freq_fields())

        # Day-of-week (weekly/biweekly)
        self._dow_var = tk.StringVar(value="Monday")
        self._dow_row_idx = r
        self._dow_lbl = tk.Label(inner, text="Day of Week", bg=BG, fg=TEXT, font=FONT_SMALL, anchor="w")
        self._dow_cb  = ttk.Combobox(inner, textvariable=self._dow_var,
                                      values=DOW_NAMES, width=14, font=FONT_BODY, state="readonly")
        r+=1

        # Day-of-month (monthly/yearly)
        self._dom_var = tk.StringVar(value="1")
        self._dom_row_idx = r
        self._dom_lbl = tk.Label(inner, text="Day of Month", bg=BG, fg=TEXT, font=FONT_SMALL, anchor="w")
        self._dom_e   = styled_entry(inner, width=6)
        r+=1

        # Month-of-year (yearly)
        self._moy_var = tk.StringVar(value="January")
        MOY = ["January","February","March","April","May","June",
               "July","August","September","October","November","December"]
        self._moy_row_idx = r
        self._moy_lbl = tk.Label(inner, text="Month", bg=BG, fg=TEXT, font=FONT_SMALL, anchor="w")
        self._moy_cb  = ttk.Combobox(inner, textvariable=self._moy_var,
                                      values=MOY, width=14, font=FONT_BODY, state="readonly")
        r+=1

        # Category (expense only)
        self._cat_var = tk.StringVar(value=EXPENSE_CATS[0])
        if rtype == "expense":
            row("Category", "cat",
                lambda p: ttk.Combobox(p, textvariable=self._cat_var,
                                       values=EXPENSE_CATS, width=14, font=FONT_BODY,
                                       state="readonly"), r); r+=1

        # Loan selector (loan_payment only)
        self._loan_var = tk.StringVar()
        if rtype == "loan_payment":
            loan_names = [f"{lid}: {lname}" for lid,lname in self.loans]
            if loan_names: self._loan_var.set(loan_names[0])
            row("Loan", "loan",
                lambda p: ttk.Combobox(p, textvariable=self._loan_var,
                                       values=loan_names, width=22, font=FONT_BODY,
                                       state="readonly"), r); r+=1

        # Note
        self._note_e = row("Note (optional)", "note",
            lambda p: styled_entry(p, width=26), r); r+=1

        # Active toggle
        self._active_var = tk.IntVar(value=1)
        af = tk.Frame(self, bg=BG); af.pack(fill="x", padx=28, pady=4)
        tk.Checkbutton(af, text="Active (auto-post enabled)", variable=self._active_var,
                       bg=BG, fg=TEXT, selectcolor=BG3, activebackground=BG,
                       font=FONT_SMALL).pack(side="left")

        styled_btn(self, "  Save Schedule  ", self._save, color=ACCENT5, fg=BG).pack(pady=16)

        # ── Pre-fill if editing ───────────────────────────────────────────
        if existing:
            _,_,label,amount,freq,dow,dom,moy,next_date,active,cat,loan_id_ex,note = existing
            self._label_e.insert(0, label)
            self._amt_e.insert(0, str(amount))
            self._freq_var.set(freq)
            if dow  is not None: self._dow_var.set(DOW_NAMES[dow])
            if dom  is not None: self._dom_e.delete(0,"end"); self._dom_e.insert(0, str(dom))
            if moy  is not None: self._moy_var.set(MOY[moy-1])
            if cat:  self._cat_var.set(cat)
            if note: self._note_e.insert(0, note)
            self._active_var.set(active)
            if rtype == "loan_payment" and loan_id_ex:
                for ln in [f"{lid}: {lname}" for lid,lname in self.loans]:
                    if ln.startswith(str(loan_id_ex)+":"):
                        self._loan_var.set(ln); break

        self._update_freq_fields()

    def _update_freq_fields(self):
        freq = self._freq_var.get()
        # hide all dynamic rows first
        for w in [self._dow_lbl, self._dow_cb, self._dom_lbl,
                  self._dom_e, self._moy_lbl, self._moy_cb]:
            w.grid_remove()
        inner = self._dow_lbl.master
        if freq in ("weekly","biweekly"):
            self._dow_lbl.grid(row=self._dow_row_idx, column=0, sticky="w", pady=5)
            self._dow_cb.grid( row=self._dow_row_idx, column=1, sticky="ew", padx=(10,0), pady=5)
        if freq in ("monthly","yearly"):
            self._dom_lbl.grid(row=self._dom_row_idx, column=0, sticky="w", pady=5)
            self._dom_e.grid(  row=self._dom_row_idx, column=1, sticky="ew", padx=(10,0), pady=5)
            if not self._dom_e.get(): self._dom_e.insert(0,"1")
        if freq == "yearly":
            self._moy_lbl.grid(row=self._moy_row_idx, column=0, sticky="w", pady=5)
            self._moy_cb.grid( row=self._moy_row_idx, column=1, sticky="ew", padx=(10,0), pady=5)

    def _save(self):
        label  = self._label_e.get().strip()
        note   = self._note_e.get().strip()
        freq   = self._freq_var.get()
        active = self._active_var.get()
        if not label: messagebox.showerror("Error","Label is required."); return
        try: amount = float(self._amt_e.get())
        except ValueError: messagebox.showerror("Error","Enter a valid amount."); return

        dow = DOW_NAMES.index(self._dow_var.get()) if freq in ("weekly","biweekly") else None
        dom = None; moy = None
        if freq in ("monthly","yearly"):
            try: dom = int(self._dom_e.get())
            except ValueError: messagebox.showerror("Error","Enter a valid day of month."); return
        MOY_LIST = ["January","February","March","April","May","June",
                    "July","August","September","October","November","December"]
        if freq == "yearly":
            moy = MOY_LIST.index(self._moy_var.get()) + 1

        cat     = self._cat_var.get() if self.rtype == "expense" else None
        loan_id = None
        if self.rtype == "loan_payment":
            lv = self._loan_var.get()
            if not lv: messagebox.showerror("Error","Select a loan."); return
            loan_id = int(lv.split(":")[0])

        if self.existing:
            nd_str = self.existing[8]  # keep existing next_date
        else:
            nd = first_occurrence(freq, dow, dom, moy)
            nd_str = nd.isoformat()

        conn = get_conn()
        if self.existing:
            conn.execute("""UPDATE recurring SET type=?,label=?,amount=?,frequency=?,
                day_of_week=?,day_of_month=?,month_of_year=?,next_date=?,active=?,
                category=?,loan_id=?,note=? WHERE id=?""",
                (self.rtype, label, amount, freq, dow, dom, moy, nd_str,
                 active, cat, loan_id, note, self.existing[0]))
        else:
            conn.execute("""INSERT INTO recurring(type,label,amount,frequency,
                day_of_week,day_of_month,month_of_year,next_date,active,
                category,loan_id,note) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""",
                (self.rtype, label, amount, freq, dow, dom, moy, nd_str,
                 active, cat, loan_id, note))
        conn.commit(); conn.close()
        self.destroy()
        self.on_save()

# ═════════════════════════════════════════════════════════════════════════════
# RECURRING MANAGER TAB
# ═════════════════════════════════════════════════════════════════════════════
class RecurringTab(tk.Frame):
    def __init__(self, parent, on_change):
        super().__init__(parent, bg=BG)
        self.on_change = on_change
        self._build()

    def _build(self):
        top = tk.Frame(self, bg=BG); top.pack(fill="x", padx=40, pady=14)
        tk.Label(top, text="🔁  Recurring Schedules", bg=BG, fg=ACCENT5, font=FONT_H2).pack(side="left")
        # Add buttons
        br = tk.Frame(top, bg=BG); br.pack(side="right")
        styled_btn(br,"＋ Paycheck",     lambda: self._add("paycheck"),     color=ACCENT,  fg=BG).pack(side="left",padx=3)
        styled_btn(br,"＋ Expense",      lambda: self._add("expense"),      color=ACCENT2       ).pack(side="left",padx=3)
        styled_btn(br,"＋ Loan Payment", lambda: self._add("loan_payment"), color=ACCENT3, fg=BG).pack(side="left",padx=3)

        self.sf = ScrollFrame(self, bg=BG)
        self.sf.pack(fill="both", expand=True, padx=40, pady=(0,16))
        self.inner = self.sf.inner
        self._load()

    def _add(self, rtype):
        loans = []
        if rtype == "loan_payment":
            loans = get_conn().execute("SELECT id,name FROM loans").fetchall()
            if not loans:
                messagebox.showinfo("No Loans","Add a loan first before scheduling recurring payments.")
                return
        RecurringDialog(self, rtype, self._refresh_all, loans=loans)

    def _refresh_all(self):
        self._load(); self.on_change()

    def _load(self):
        for w in self.inner.winfo_children(): w.destroy()
        rows = get_conn().execute(
            "SELECT id,type,label,amount,frequency,day_of_week,day_of_month,"
            "month_of_year,next_date,active,category,loan_id,note FROM recurring ORDER BY type,label"
        ).fetchall()
        if not rows:
            tk.Label(self.inner,
                     text="No recurring schedules yet.\nUse the buttons above to add paychecks, expenses, or loan payments that auto-post on schedule.",
                     bg=BG, fg=TEXT_DIM, font=FONT_BODY, justify="center").pack(pady=50)
            return

        # Group by type
        groups = {"paycheck":[],"expense":[],"loan_payment":[]}
        for r in rows: groups[r[1]].append(r)

        type_info = [
            ("paycheck",     "📥  Recurring Paychecks",      ACCENT),
            ("expense",      "📤  Recurring Expenses",        ACCENT2),
            ("loan_payment", "🏦  Recurring Loan Payments",   ACCENT3),
        ]
        for rtype, title, clr in type_info:
            grp = groups[rtype]
            if not grp: continue
            card = section_card(self.inner, title)
            card.pack(fill="x", pady=6)

            # Header row
            hdr = tk.Frame(card, bg=BG2); hdr.pack(fill="x", padx=18, pady=(0,4))
            hdr.columnconfigure((0,1,2,3,4,5), weight=1)
            for i,h in enumerate(["Label","Amount","Frequency","Next Date","Status",""]):
                tk.Label(hdr,text=h,bg=BG2,fg=TEXT_DIM,font=FONT_SMALL,
                         anchor="w").grid(row=0,column=i,sticky="ew",padx=4)

            for rec in grp:
                self._rec_row(card, rec, clr)
            tk.Frame(card, bg=BG2, height=8).pack()

    def _rec_row(self, card, rec, clr):
        rid,rtype,label,amount,freq,dow,dom,moy,next_date,active,cat,loan_id,note = rec
        bg_ = BG2 if active else BG3
        r = tk.Frame(card, bg=bg_, highlightthickness=1, highlightbackground=BORDER)
        r.pack(fill="x", padx=18, pady=3)
        r.columnconfigure((0,1,2,3,4,5), weight=1)

        freq_pretty = freq.capitalize()
        if freq in ("weekly","biweekly") and dow is not None:
            freq_pretty += f" ({DOW_NAMES[dow][:3]})"
        elif freq in ("monthly","yearly") and dom is not None:
            freq_pretty += f" (day {dom})"

        vals = [label, fmt_money(amount), freq_pretty, next_date,
                "Active" if active else "Paused"]
        fgs  = [TEXT if active else TEXT_DIM, clr, TEXT_DIM, ACCENT4 if active else TEXT_DIM,
                ACCENT if active else TEXT_DIM]
        for i,(v,fg) in enumerate(zip(vals,fgs)):
            tk.Label(r,text=v,bg=bg_,fg=fg,font=FONT_SMALL,
                     anchor="w",padx=6,pady=6).grid(row=0,column=i,sticky="ew")

        # Action buttons cell
        bf = tk.Frame(r, bg=bg_)
        bf.grid(row=0, column=5, sticky="ew", padx=4)
        tk.Button(bf, text="✏", bg=bg_, fg=ACCENT4, relief="flat",
                  cursor="hand2", font=FONT_SMALL,
                  command=lambda rec=rec: self._edit(rec)).pack(side="left", padx=2)
        tk.Button(bf, text="⏸" if active else "▶", bg=bg_,
                  fg=ACCENT3 if active else ACCENT, relief="flat",
                  cursor="hand2", font=FONT_SMALL,
                  command=lambda rid=rid,a=active: self._toggle(rid,a)).pack(side="left",padx=2)
        tk.Button(bf, text="🗑", bg=bg_, fg=ACCENT2, relief="flat",
                  cursor="hand2", font=FONT_SMALL,
                  command=lambda rid=rid: self._delete(rid)).pack(side="left",padx=2)

    def _edit(self, rec):
        loans = get_conn().execute("SELECT id,name FROM loans").fetchall()
        RecurringDialog(self, rec[1], self._refresh_all, existing=rec, loans=loans)

    def _toggle(self, rid, currently_active):
        conn = get_conn()
        conn.execute("UPDATE recurring SET active=? WHERE id=?",(0 if currently_active else 1, rid))
        conn.commit(); conn.close()
        self._refresh_all()

    def _delete(self, rid):
        if not messagebox.askyesno("Delete","Delete this recurring schedule?\n(Past entries already posted are kept.)"): return
        conn = get_conn()
        conn.execute("DELETE FROM recurring WHERE id=?",(rid,))
        conn.commit(); conn.close()
        self._refresh_all()

# ═════════════════════════════════════════════════════════════════════════════
# DASHBOARD
# ═════════════════════════════════════════════════════════════════════════════
class DashboardTab(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent, bg=BG)
        self._build()

    def _build(self):
        hdr = tk.Frame(self, bg=BG)
        hdr.pack(fill="x", padx=40, pady=(18,4))
        tk.Label(hdr, text="💰  FINANCE TRACKER", bg=BG, fg=ACCENT, font=FONT_H1).pack(side="left")
        tk.Label(hdr, text=date.today().strftime("%A, %B %d %Y"),
                 bg=BG, fg=TEXT_DIM, font=FONT_BODY).pack(side="right", pady=6)

        fbar = tk.Frame(self, bg=BG); fbar.pack(fill="x", padx=40, pady=(0,10))
        tk.Label(fbar, text="View:", bg=BG, fg=TEXT_DIM, font=FONT_SMALL).pack(side="left")
        self.view_var = tk.StringVar(value="month")
        for v,t in [("week","This Week"),("month","This Month")]:
            tk.Radiobutton(fbar, text=t, variable=self.view_var, value=v,
                           bg=BG, fg=TEXT, selectcolor=BG3, activebackground=BG,
                           font=FONT_SMALL, command=self.refresh).pack(side="left",padx=8)

        self.sf = ScrollFrame(self, bg=BG)
        self.sf.pack(fill="both", expand=True, padx=40, pady=(0,16))
        self.inner = self.sf.inner
        self.refresh()

    def refresh(self):
        for w in self.inner.winfo_children(): w.destroy()
        conn = get_conn(); c = conn.cursor()
        if self.view_var.get() == "week":
            s,e = week_bounds(); period = "This Week"
        else:
            s,e = month_bounds(); period = "This Month"

        income  = c.execute("SELECT COALESCE(SUM(amount),0) FROM paychecks WHERE date BETWEEN ? AND ?",(s,e)).fetchone()[0]
        expense = c.execute("SELECT COALESCE(SUM(amount),0) FROM expenses  WHERE date BETWEEN ? AND ?",(s,e)).fetchone()[0]
        sub_mo  = c.execute("SELECT COALESCE(SUM(amount),0) FROM subscriptions WHERE active=1 AND billing_cycle='monthly'").fetchone()[0]
        sub_yr  = c.execute("SELECT COALESCE(SUM(amount),0) FROM subscriptions WHERE active=1 AND billing_cycle='yearly'").fetchone()[0]
        loan_mo = c.execute("SELECT COALESCE(SUM(monthly_payment),0) FROM loans").fetchone()[0]
        rec_cnt = c.execute("SELECT COUNT(*) FROM recurring WHERE active=1").fetchone()[0]
        net     = income - expense - sub_mo - (sub_yr/12) - loan_mo
        conn.close()

        kf = tk.Frame(self.inner, bg=BG); kf.pack(fill="x", pady=(4,12))
        kf.columnconfigure((0,1,2,3), weight=1)
        for i,(title,val,clr,sub) in enumerate([
            ("INCOME",   fmt_money(income),  ACCENT,                        period),
            ("EXPENSES", fmt_money(expense), ACCENT2,                       period),
            ("LOANS",    fmt_money(loan_mo), ACCENT3,                       "Monthly due"),
            ("NET",      fmt_money(net),     ACCENT4 if net>=0 else ACCENT2,"Est. remaining"),
        ]):
            cf = tk.Frame(kf,bg=BG3,highlightthickness=1,highlightbackground=BORDER)
            cf.grid(row=0,column=i,padx=5,pady=4,sticky="nsew",ipady=12)
            tk.Label(cf,text=title,bg=BG3,fg=TEXT_DIM,font=FONT_SMALL).pack(pady=(10,2))
            tk.Label(cf,text=val,  bg=BG3,fg=clr,font=("Times New Roman",17,"bold")).pack()
            tk.Label(cf,text=sub,  bg=BG3,fg=TEXT_DIM,font=FONT_SMALL).pack(pady=(2,10))

        if rec_cnt:
            ri = tk.Frame(self.inner, bg=BG3, highlightthickness=1, highlightbackground=ACCENT5)
            ri.pack(fill="x", pady=(0,8))
            tk.Label(ri, text=f"🔁  {rec_cnt} active recurring schedule{'s' if rec_cnt!=1 else ''}  —  entries auto-posted on launch",
                     bg=BG3, fg=ACCENT5, font=FONT_SMALL).pack(padx=18, pady=8)

        self._recent_paychecks()
        self._recent_expenses()
        self._loans_summary()
        self._subs_summary()

    def _row(self, card, values, fg_list):
        r = tk.Frame(card, bg=BG2); r.pack(fill="x", padx=18, pady=3)
        for i in range(len(values)):
            r.columnconfigure(i, weight=1)
        for i,(v,fg) in enumerate(zip(values,fg_list)):
            tk.Label(r,text=v,bg=BG2,fg=fg,font=FONT_SMALL,
                     anchor="w").grid(row=0,column=i,sticky="ew",padx=4)

    def _recent_paychecks(self):
        card = section_card(self.inner,"📥  Recent Paychecks"); card.pack(fill="x",pady=5)
        rows = get_conn().execute("SELECT date,amount,note FROM paychecks ORDER BY date DESC LIMIT 5").fetchall()
        if not rows:
            tk.Label(card,text="No paychecks logged yet.",bg=BG2,fg=TEXT_DIM,font=FONT_SMALL).pack(padx=18,anchor="w",pady=6)
        else:
            for d,a,n in rows:
                is_auto = n and n.startswith("[Auto]")
                self._row(card,[d,fmt_money(a),n or "","🔁" if is_auto else ""],
                          [TEXT_DIM,ACCENT,TEXT_DIM,ACCENT5])
        tk.Frame(card,bg=BG2,height=8).pack()

    def _recent_expenses(self):
        card = section_card(self.inner,"📤  Recent Expenses"); card.pack(fill="x",pady=5)
        rows = get_conn().execute("SELECT date,category,description,amount FROM expenses ORDER BY date DESC LIMIT 6").fetchall()
        if not rows:
            tk.Label(card,text="No expenses logged yet.",bg=BG2,fg=TEXT_DIM,font=FONT_SMALL).pack(padx=18,anchor="w",pady=6)
        else:
            for d,cat,desc,a in rows:
                self._row(card,[d,f"[{cat}]",desc or "",fmt_money(a)],
                          [TEXT_DIM,ACCENT3,TEXT,ACCENT2])
        tk.Frame(card,bg=BG2,height=8).pack()

    def _loans_summary(self):
        card = section_card(self.inner,"🏦  Active Loans"); card.pack(fill="x",pady=5)
        rows = get_conn().execute("SELECT name,balance,monthly_payment,interest_rate FROM loans ORDER BY balance DESC").fetchall()
        if not rows:
            tk.Label(card,text="No loans tracked.",bg=BG2,fg=TEXT_DIM,font=FONT_SMALL).pack(padx=18,anchor="w",pady=6)
        else:
            for name,bal,pay,rate in rows:
                self._row(card,[name,f"Balance: {fmt_money(bal)}",f"Payment: {fmt_money(pay)}/mo",f"{rate}% APR"],
                          [TEXT,ACCENT2,ACCENT3,TEXT_DIM])
        tk.Frame(card,bg=BG2,height=8).pack()

    def _subs_summary(self):
        card = section_card(self.inner,"🔄  Subscriptions"); card.pack(fill="x",pady=5)
        rows = get_conn().execute("SELECT name,amount,billing_cycle,next_due,active FROM subscriptions ORDER BY next_due").fetchall()
        if not rows:
            tk.Label(card,text="No subscriptions tracked.",bg=BG2,fg=TEXT_DIM,font=FONT_SMALL).pack(padx=18,anchor="w",pady=6)
        else:
            for name,amt,cycle,nxt,active in rows:
                self._row(card,[("● " if active else "○ ")+name,fmt_money(amt)+f"/{cycle[:2]}",
                                f"Next: {nxt}","Active" if active else "Paused"],
                          [ACCENT if active else TEXT_DIM,ACCENT4,TEXT_DIM,
                           ACCENT if active else TEXT_DIM])
        tk.Frame(card,bg=BG2,height=8).pack()

# ═════════════════════════════════════════════════════════════════════════════
# INCOME TAB
# ═════════════════════════════════════════════════════════════════════════════
class IncomeTab(tk.Frame):
    def __init__(self, parent, on_change):
        super().__init__(parent, bg=BG)
        self.on_change = on_change
        self._build()

    def _build(self):
        sf = ScrollFrame(self, bg=BG)
        sf.pack(fill="both", expand=True, padx=40, pady=16)
        body = sf.inner

        form = section_card(body,"➕  Log Paycheck"); form.pack(fill="x",pady=(0,14))
        self.amt_e  = form_row(form,"Amount ($)", lambda p: styled_entry(p,width=20))
        self.date_e = form_row(form,"Date",       lambda p: styled_entry(p,width=16))
        self.note_e = form_row(form,"Note",       lambda p: styled_entry(p,width=34))
        self.date_e.insert(0, today_str())
        br = tk.Frame(form,bg=BG2); br.pack(fill="x",padx=24,pady=(6,16))
        styled_btn(br,"  Log Paycheck  ",self._log).pack(side="left",padx=(0,8))
        styled_btn(br,"🔁  Add Recurring",self._add_recurring,color=ACCENT5,fg=BG).pack(side="left")

        hist = section_card(body,"📋  Paycheck History"); hist.pack(fill="x",pady=(0,14))
        fb = tk.Frame(hist,bg=BG2); fb.pack(fill="x",padx=18,pady=(0,8))
        self.period = tk.StringVar(value="month")
        tk.Label(fb,text="Filter:",bg=BG2,fg=TEXT_DIM,font=FONT_SMALL).pack(side="left")
        for v,t in [("week","Week"),("month","Month"),("all","All")]:
            tk.Radiobutton(fb,text=t,variable=self.period,value=v,bg=BG2,fg=TEXT,
                           selectcolor=BG3,activebackground=BG2,font=FONT_SMALL,
                           command=self._load).pack(side="left",padx=6)
        self.tree = make_tree(hist,("Date","Amount","Note","Auto"),(120,130,350,60))
        self.tree.pack(fill="both",expand=True,padx=18,pady=(0,6))
        br2 = tk.Frame(hist,bg=BG2); br2.pack(fill="x",padx=18,pady=(0,14))
        styled_btn(br2,"Delete Selected",self._delete,color=ACCENT2).pack(side="left")
        self._load()

    def _add_recurring(self):
        RecurringDialog(self,"paycheck",lambda: (self._load(),self.on_change()))

    def _log(self):
        try: amt = float(self.amt_e.get())
        except ValueError: messagebox.showerror("Error","Enter a valid amount."); return
        conn = get_conn()
        conn.execute("INSERT INTO paychecks(amount,date,note) VALUES(?,?,?)",
                     (amt,self.date_e.get().strip() or today_str(),self.note_e.get().strip()))
        conn.commit(); conn.close()
        self.amt_e.delete(0,"end"); self.note_e.delete(0,"end")
        self._load(); self.on_change()

    def _load(self):
        for r in self.tree.get_children(): self.tree.delete(r)
        p = self.period.get(); conn = get_conn()
        if p == "week":    s,e=week_bounds();  rows=conn.execute("SELECT id,date,amount,note,recurring_id FROM paychecks WHERE date BETWEEN ? AND ? ORDER BY date DESC",(s,e)).fetchall()
        elif p == "month": s,e=month_bounds(); rows=conn.execute("SELECT id,date,amount,note,recurring_id FROM paychecks WHERE date BETWEEN ? AND ? ORDER BY date DESC",(s,e)).fetchall()
        else:              rows=conn.execute("SELECT id,date,amount,note,recurring_id FROM paychecks ORDER BY date DESC").fetchall()
        conn.close()
        for rid,d,a,n,rec in rows:
            self.tree.insert("","end",iid=str(rid),
                             values=(d,fmt_money(a),n or "","🔁" if rec else ""))

    def _delete(self):
        sel = self.tree.selection()
        if not sel: return
        if not messagebox.askyesno("Delete","Delete selected paycheck(s)?"): return
        conn = get_conn()
        for s in sel: conn.execute("DELETE FROM paychecks WHERE id=?",(int(s),))
        conn.commit(); conn.close()
        self._load(); self.on_change()

# ═════════════════════════════════════════════════════════════════════════════
# COMBINED EXPENSES TAB  (Expenses + Subscriptions + Loans)
# ═════════════════════════════════════════════════════════════════════════════

# ── Shared dialog helpers ─────────────────────────────────────────────────────
def _dlg_row(win, label, default=""):
    row = tk.Frame(win, bg=BG); row.pack(fill="x", padx=28, pady=4)
    row.columnconfigure(0, weight=1); row.columnconfigure(1, weight=2)
    tk.Label(row, text=label, bg=BG, fg=TEXT, font=FONT_SMALL, anchor="w").grid(row=0,column=0,sticky="w")
    e = styled_entry(row, width=24); e.grid(row=0,column=1,sticky="ew",padx=(10,0))
    e.insert(0, str(default)); return e

def _dlg_row_widget(win, label, widget):
    row = tk.Frame(win, bg=BG); row.pack(fill="x", padx=28, pady=4)
    row.columnconfigure(0, weight=1); row.columnconfigure(1, weight=2)
    tk.Label(row, text=label, bg=BG, fg=TEXT, font=FONT_SMALL, anchor="w").grid(row=0,column=0,sticky="w")
    widget.grid(row=0,column=1,sticky="ew",padx=(10,0))
    return widget

class CombinedExpensesTab(tk.Frame):
    def __init__(self, parent, on_change):
        super().__init__(parent, bg=BG)
        self.on_change = on_change
        self._build()

    def _build(self):
        top = tk.Frame(self, bg=BG)
        top.pack(fill="x", padx=40, pady=(14,4))
        styled_btn(top,"＋ Expense",      self._add_expense_dialog, color=ACCENT2).pack(side="left",padx=(0,6))
        styled_btn(top,"＋ Subscription", self._add_sub_dialog,     color=ACCENT4,fg=BG).pack(side="left",padx=(0,6))
        styled_btn(top,"＋ Loan",         self._add_loan_dialog,    color=ACCENT3,fg=BG).pack(side="left",padx=(0,6))
        styled_btn(top,"🔁 Recurring",    self._add_recurring_dialog,color=ACCENT5,fg=BG).pack(side="left")
        self.summary_lbl = tk.Label(top, bg=BG, fg=TEXT_DIM, font=FONT_SMALL)
        self.summary_lbl.pack(side="right")

        fbar = tk.Frame(self, bg=BG); fbar.pack(fill="x", padx=40, pady=(0,8))
        tk.Label(fbar, text="Expenses filter:", bg=BG, fg=TEXT_DIM, font=FONT_SMALL).pack(side="left")
        self.period = tk.StringVar(value="month")
        for v,t in [("week","Week"),("month","Month"),("all","All time")]:
            tk.Radiobutton(fbar,text=t,variable=self.period,value=v,bg=BG,fg=TEXT,
                           selectcolor=BG3,activebackground=BG,font=FONT_SMALL,
                           command=self._reload).pack(side="left",padx=6)

        self.sf   = ScrollFrame(self, bg=BG)
        self.sf.pack(fill="both", expand=True, padx=40, pady=(0,16))
        self.body = self.sf.inner
        self._reload()

    def _reload(self):
        for w in self.body.winfo_children(): w.destroy()
        self._build_expenses_section()
        self._build_subs_section()
        self._build_loans_section()
        self._update_summary()

    def _update_summary(self):
        conn = get_conn()
        s,e  = month_bounds()
        exp     = conn.execute("SELECT COALESCE(SUM(amount),0) FROM expenses WHERE active=1 AND date BETWEEN ? AND ?",(s,e)).fetchone()[0]
        sub_mo  = conn.execute("SELECT COALESCE(SUM(amount),0) FROM subscriptions WHERE active=1 AND billing_cycle='monthly'").fetchone()[0]
        sub_yr  = conn.execute("SELECT COALESCE(SUM(amount),0) FROM subscriptions WHERE active=1 AND billing_cycle='yearly'").fetchone()[0]
        loan_mo = conn.execute("SELECT COALESCE(SUM(monthly_payment),0) FROM loans WHERE active=1").fetchone()[0]
        conn.close()
        total = exp + sub_mo + (sub_yr/12) + loan_mo
        self.summary_lbl.config(text=f"Active monthly total: ${total:,.2f}")

    # ── SECTION 1: Expenses ───────────────────────────────────────────────
    def _build_expenses_section(self):
        card = section_card(self.body,"📤  Expenses"); card.pack(fill="x",pady=(0,8))
        p = self.period.get(); conn = get_conn()
        if p == "week":    s,e=week_bounds();  rows=conn.execute("SELECT id,date,category,description,amount,recurring_id,active FROM expenses WHERE date BETWEEN ? AND ? ORDER BY date DESC",(s,e)).fetchall()
        elif p == "month": s,e=month_bounds(); rows=conn.execute("SELECT id,date,category,description,amount,recurring_id,active FROM expenses WHERE date BETWEEN ? AND ? ORDER BY date DESC",(s,e)).fetchall()
        else:              rows=conn.execute("SELECT id,date,category,description,amount,recurring_id,active FROM expenses ORDER BY date DESC").fetchall()
        conn.close()
        if not rows:
            tk.Label(card,text="No expenses yet.",bg=BG2,fg=TEXT_DIM,font=FONT_SMALL).pack(padx=18,anchor="w",pady=8)
        else:
            hdr = tk.Frame(card,bg=BG3); hdr.pack(fill="x",padx=18,pady=(0,2))
            for i,lbl in enumerate(["Date","Category","Description","Amount","","Enabled"]):
                hdr.columnconfigure(i,weight=1)
                tk.Label(hdr,text=lbl,bg=BG3,fg=TEXT_DIM,font=FONT_SMALL,anchor="w",padx=6,pady=4).grid(row=0,column=i,sticky="ew")
            for row in rows: self._expense_row(card,row)
        tk.Frame(card,bg=BG2,height=8).pack()

    def _expense_row(self, parent, row):
        rid,d,cat,desc,amt,rec,active = row
        bg_ = BG2 if active else BG3
        r = tk.Frame(parent,bg=bg_); r.pack(fill="x",padx=18,pady=1)
        for i in range(6): r.columnconfigure(i,weight=1)
        vals = [d, cat, desc or "", f"${amt:,.2f}", "🔁" if rec else ""]
        fgs  = [TEXT_DIM, ACCENT3 if active else TEXT_DIM, TEXT if active else TEXT_DIM,
                ACCENT2 if active else TEXT_DIM, ACCENT5]
        for i,(v,fg) in enumerate(zip(vals,fgs)):
            tk.Label(r,text=v,bg=bg_,fg=fg,font=FONT_SMALL,anchor="w",padx=6,pady=5).grid(row=0,column=i,sticky="ew")
        bf = tk.Frame(r,bg=bg_); bf.grid(row=0,column=5,sticky="ew",padx=4)
        tk.Button(bf,text="✓ On" if active else "✗ Off",bg=bg_,fg=ACCENT if active else TEXT_DIM,
                  relief="flat",cursor="hand2",font=FONT_SMALL,
                  command=lambda i=rid:self._toggle_expense(i)).pack(side="left",padx=2)
        tk.Button(bf,text="🗑",bg=bg_,fg=ACCENT2,relief="flat",cursor="hand2",font=FONT_SMALL,
                  command=lambda i=rid:self._delete_expense(i)).pack(side="left",padx=2)

    def _toggle_expense(self,eid):
        conn=get_conn(); conn.execute("UPDATE expenses SET active=1-active WHERE id=?",(eid,)); conn.commit(); conn.close(); self._reload(); self.on_change()
    def _delete_expense(self,eid):
        if not messagebox.askyesno("Delete","Delete this expense?"): return
        conn=get_conn(); conn.execute("DELETE FROM expenses WHERE id=?",(eid,)); conn.commit(); conn.close(); self._reload(); self.on_change()
    def _add_expense_dialog(self):
        win=tk.Toplevel(); win.title("Add Expense"); win.configure(bg=BG); win.geometry("440x340"); win.resizable(False,False)
        tk.Label(win,text="➕  Add Expense",bg=BG,fg=ACCENT2,font=FONT_H2).pack(pady=14)
        amt_e=_dlg_row(win,"Amount ($)"); cat_var=tk.StringVar(value=EXPENSE_CATS[0])
        _dlg_row_widget(win,"Category",ttk.Combobox(win,textvariable=cat_var,values=EXPENSE_CATS,width=18,font=FONT_BODY))
        desc_e=_dlg_row(win,"Description"); date_e=_dlg_row(win,"Date",today_str())
        def save():
            try: amt=float(amt_e.get())
            except ValueError: messagebox.showerror("Error","Enter a valid amount."); return
            conn=get_conn(); conn.execute("INSERT INTO expenses(amount,category,description,date,active) VALUES(?,?,?,?,1)",(amt,cat_var.get(),desc_e.get().strip(),date_e.get().strip() or today_str())); conn.commit(); conn.close(); win.destroy(); self._reload(); self.on_change()
        styled_btn(win,"  Save  ",save,color=ACCENT2).pack(pady=14)

    # ── SECTION 2: Subscriptions ──────────────────────────────────────────
    def _build_subs_section(self):
        conn=get_conn()
        subs=conn.execute("SELECT id,name,amount,billing_cycle,next_due,category,active,note FROM subscriptions ORDER BY next_due").fetchall()
        conn.close()
        card=section_card(self.body,"🔄  Subscriptions"); card.pack(fill="x",pady=(0,8))
        if not subs:
            tk.Label(card,text="No subscriptions yet.",bg=BG2,fg=TEXT_DIM,font=FONT_SMALL).pack(padx=18,anchor="w",pady=8)
        else:
            hdr=tk.Frame(card,bg=BG3); hdr.pack(fill="x",padx=18,pady=(0,2))
            for i,lbl in enumerate(["Name","Amount","Cycle","Next Due","Enabled"]):
                hdr.columnconfigure(i,weight=1)
                tk.Label(hdr,text=lbl,bg=BG3,fg=TEXT_DIM,font=FONT_SMALL,anchor="w",padx=6,pady=4).grid(row=0,column=i,sticky="ew")
            for s in subs: self._sub_row(card,s)
        tk.Frame(card,bg=BG2,height=8).pack()

    def _sub_row(self,parent,sub):
        sid,name,amt,cycle,nxt,cat,active,note=sub
        bg_=BG2 if active else BG3
        r=tk.Frame(parent,bg=bg_); r.pack(fill="x",padx=18,pady=1)
        for i in range(5): r.columnconfigure(i,weight=1)
        vals=[("● " if active else "○ ")+name, f"${amt:,.2f}", cycle.capitalize(), nxt]
        fgs=[ACCENT4 if active else TEXT_DIM, ACCENT4 if active else TEXT_DIM, TEXT_DIM, ACCENT3 if active else TEXT_DIM]
        for i,(v,fg) in enumerate(zip(vals,fgs)):
            tk.Label(r,text=v,bg=bg_,fg=fg,font=FONT_SMALL,anchor="w",padx=6,pady=5).grid(row=0,column=i,sticky="ew")
        bf=tk.Frame(r,bg=bg_); bf.grid(row=0,column=4,sticky="ew",padx=4)
        tk.Button(bf,text="✓ On" if active else "✗ Off",bg=bg_,fg=ACCENT if active else TEXT_DIM,
                  relief="flat",cursor="hand2",font=FONT_SMALL,
                  command=lambda s=sub:self._toggle_sub(s)).pack(side="left",padx=2)
        tk.Button(bf,text="✏",bg=bg_,fg=ACCENT4,relief="flat",cursor="hand2",font=FONT_SMALL,
                  command=lambda s=sub:self._add_sub_dialog(s)).pack(side="left",padx=2)
        tk.Button(bf,text="🗑",bg=bg_,fg=ACCENT2,relief="flat",cursor="hand2",font=FONT_SMALL,
                  command=lambda s=sid:self._delete_sub(s)).pack(side="left",padx=2)

    def _toggle_sub(self,sub):
        conn=get_conn(); conn.execute("UPDATE subscriptions SET active=1-active WHERE id=?",(sub[0],)); conn.commit(); conn.close(); self._reload(); self.on_change()
    def _delete_sub(self,sid):
        if not messagebox.askyesno("Delete","Delete this subscription?"): return
        conn=get_conn(); conn.execute("DELETE FROM subscriptions WHERE id=?",(sid,)); conn.commit(); conn.close(); self._reload(); self.on_change()
    def _add_sub_dialog(self,sub=None):
        win=tk.Toplevel(); win.title("Subscription"); win.configure(bg=BG); win.geometry("440x400"); win.resizable(False,False)
        tk.Label(win,text="Subscription",bg=BG,fg=ACCENT4,font=FONT_H2).pack(pady=14)
        d={}
        if sub: _,name,amt,cycle,nxt,cat,active,note=sub; d=dict(name=name,amt=amt,cycle=cycle,nxt=nxt,cat=cat or "",note=note or "")
        name_e=_dlg_row(win,"Name",d.get("name","")); amt_e=_dlg_row(win,"Amount ($)",d.get("amt",""))
        cat_e=_dlg_row(win,"Category",d.get("cat","")); nxt_e=_dlg_row(win,"Next Due Date",d.get("nxt",today_str()))
        note_e=_dlg_row(win,"Note",d.get("note",""))
        cycle_var=tk.StringVar(value=d.get("cycle","monthly"))
        _dlg_row_widget(win,"Billing Cycle",ttk.Combobox(win,textvariable=cycle_var,values=["monthly","yearly","weekly"],width=16,font=FONT_BODY))
        def save():
            try: name=name_e.get().strip(); amt=float(amt_e.get()); cat=cat_e.get().strip(); nxt=nxt_e.get().strip(); note=note_e.get().strip(); cyc=cycle_var.get()
            except ValueError: messagebox.showerror("Error","Check fields."); return
            conn=get_conn()
            if sub: conn.execute("UPDATE subscriptions SET name=?,amount=?,billing_cycle=?,next_due=?,category=?,note=? WHERE id=?",(name,amt,cyc,nxt,cat,note,sub[0]))
            else:   conn.execute("INSERT INTO subscriptions(name,amount,billing_cycle,next_due,category,note) VALUES(?,?,?,?,?,?)",(name,amt,cyc,nxt,cat,note))
            conn.commit(); conn.close(); win.destroy(); self._reload(); self.on_change()
        styled_btn(win,"  Save  ",save,color=ACCENT4,fg=BG).pack(pady=14)

    # ── SECTION 3: Loans ─────────────────────────────────────────────────
    def _build_loans_section(self):
        conn=get_conn()
        loans=conn.execute("SELECT id,name,principal,balance,interest_rate,monthly_payment,due_day,start_date,note,active FROM loans").fetchall()
        conn.close()
        card=section_card(self.body,"🏦  Loans"); card.pack(fill="x",pady=(0,8))
        if not loans:
            tk.Label(card,text="No loans yet.",bg=BG2,fg=TEXT_DIM,font=FONT_SMALL).pack(padx=18,anchor="w",pady=8)
        else:
            for loan in loans: self._loan_card(card,loan)
        tk.Frame(card,bg=BG2,height=8).pack()

    def _loan_card(self,parent,loan):
        lid,name,principal,balance,rate,payment,due_day,start,note,active=loan
        bg_=BG2 if active else BG3
        pct=((principal-balance)/principal*100) if principal else 0
        outer=tk.Frame(parent,bg=bg_,highlightthickness=1,highlightbackground=BORDER)
        outer.pack(fill="x",padx=18,pady=4)
        tr=tk.Frame(outer,bg=bg_); tr.pack(fill="x",padx=12,pady=(8,4))
        tk.Label(tr,text=("● " if active else "○ ")+name,bg=bg_,
                 fg=TEXT if active else TEXT_DIM,font=FONT_H2).pack(side="left")
        bf=tk.Frame(tr,bg=bg_); bf.pack(side="right")
        tk.Button(bf,text="✓ On" if active else "✗ Off",bg=bg_,fg=ACCENT if active else TEXT_DIM,
                  relief="flat",cursor="hand2",font=FONT_SMALL,
                  command=lambda l=lid:self._toggle_loan(l)).pack(side="left",padx=4)
        tk.Button(bf,text="Log Payment",bg=bg_,fg=ACCENT,relief="flat",cursor="hand2",font=FONT_SMALL,
                  command=lambda l=lid:self._log_loan_payment(l)).pack(side="left",padx=4)
        tk.Button(bf,text="✏",bg=bg_,fg=ACCENT4,relief="flat",cursor="hand2",font=FONT_SMALL,
                  command=lambda l=loan:self._add_loan_dialog(l)).pack(side="left",padx=4)
        tk.Button(bf,text="🗑",bg=bg_,fg=ACCENT2,relief="flat",cursor="hand2",font=FONT_SMALL,
                  command=lambda l=lid:self._delete_loan(l)).pack(side="left",padx=4)
        pb=tk.Frame(outer,bg=BORDER,height=8); pb.pack(fill="x",padx=12,pady=(0,4))
        tk.Frame(pb,bg=ACCENT3 if active else TEXT_DIM,height=8).place(x=0,y=0,relwidth=pct/100,relheight=1)
        tk.Label(outer,text=f"{pct:.1f}% paid off",bg=bg_,fg=TEXT_DIM,font=FONT_SMALL).pack(anchor="e",padx=12)
        dg=tk.Frame(outer,bg=bg_); dg.pack(fill="x",padx=12,pady=(0,8))
        dg.columnconfigure((0,1,2,3,4),weight=1)
        for i,(k,v,c) in enumerate([("Principal",f"${principal:,.2f}",TEXT if active else TEXT_DIM),
                                     ("Balance",  f"${balance:,.2f}",  ACCENT2 if active else TEXT_DIM),
                                     ("Rate",     f"{rate}% APR",       TEXT_DIM),
                                     ("Payment",  f"${payment:,.2f}/mo",ACCENT3 if active else TEXT_DIM),
                                     ("Due day",  f"{due_day} of month",TEXT_DIM)]):
            f=tk.Frame(dg,bg=BG3 if active else BG2,padx=6,pady=6)
            f.grid(row=0,column=i,padx=3,sticky="nsew")
            tk.Label(f,text=k,bg=f["bg"],fg=TEXT_DIM,font=FONT_SMALL).pack()
            tk.Label(f,text=v,bg=f["bg"],fg=c,font=FONT_BODY).pack()
        if note: tk.Label(outer,text=f"Note: {note}",bg=bg_,fg=TEXT_DIM,font=FONT_SMALL).pack(padx=12,anchor="w",pady=(0,6))

    def _toggle_loan(self,lid):
        conn=get_conn(); conn.execute("UPDATE loans SET active=1-active WHERE id=?",(lid,)); conn.commit(); conn.close(); self._reload(); self.on_change()
    def _delete_loan(self,lid):
        if not messagebox.askyesno("Delete","Delete this loan and all payment history?"): return
        conn=get_conn(); conn.execute("DELETE FROM loan_payments WHERE loan_id=?",(lid,)); conn.execute("DELETE FROM loans WHERE id=?",(lid,)); conn.commit(); conn.close(); self._reload(); self.on_change()
    def _add_loan_dialog(self,loan=None):
        win=tk.Toplevel(); win.title("Loan"); win.configure(bg=BG); win.geometry("460x500"); win.resizable(False,False)
        tk.Label(win,text="Edit Loan" if loan else "Add Loan",bg=BG,fg=ACCENT3,font=FONT_H2).pack(pady=14)
        d={}
        if loan:
            lid,name,principal,balance,rate,payment,due_day,start,note,active=loan
            d=dict(name=name,principal=principal,balance=balance,rate=rate,payment=payment,due_day=due_day,start=start,note=note or "")
        name_e=_dlg_row(win,"Loan Name",d.get("name","")); prin_e=_dlg_row(win,"Original Amount ($)",d.get("principal",""))
        bal_e=_dlg_row(win,"Current Balance ($)",d.get("balance","")); rate_e=_dlg_row(win,"Interest Rate (%)",d.get("rate",""))
        pay_e=_dlg_row(win,"Monthly Payment ($)",d.get("payment","")); due_e=_dlg_row(win,"Due Day (1-31)",d.get("due_day",1))
        start_e=_dlg_row(win,"Start Date",d.get("start",today_str())); note_e=_dlg_row(win,"Note",d.get("note",""))
        def save():
            try:
                name=name_e.get().strip(); prin=float(prin_e.get()); bal=float(bal_e.get())
                rate_v=float(rate_e.get()); pay=float(pay_e.get()); due=int(due_e.get())
                start=start_e.get().strip(); note=note_e.get().strip()
            except ValueError: messagebox.showerror("Error","Check numeric fields."); return
            conn=get_conn()
            if loan: conn.execute("UPDATE loans SET name=?,principal=?,balance=?,interest_rate=?,monthly_payment=?,due_day=?,start_date=?,note=? WHERE id=?",(name,prin,bal,rate_v,pay,due,start,note,loan[0]))
            else:    conn.execute("INSERT INTO loans(name,principal,balance,interest_rate,monthly_payment,due_day,start_date,note,active) VALUES(?,?,?,?,?,?,?,?,1)",(name,prin,bal,rate_v,pay,due,start,note))
            conn.commit(); conn.close(); win.destroy(); self._reload(); self.on_change()
        styled_btn(win,"  Save  ",save,color=ACCENT3,fg=BG).pack(pady=16)
    def _log_loan_payment(self,loan_id):
        win=tk.Toplevel(); win.title("Log Payment"); win.configure(bg=BG); win.geometry("380x260"); win.resizable(False,False)
        tk.Label(win,text="Log Loan Payment",bg=BG,fg=ACCENT,font=FONT_H2).pack(pady=14)
        amt_e=_dlg_row(win,"Amount ($)"); date_e=_dlg_row(win,"Date",today_str()); note_e=_dlg_row(win,"Note")
        def save():
            try: amt=float(amt_e.get())
            except ValueError: messagebox.showerror("Error","Enter valid amount."); return
            conn=get_conn()
            conn.execute("INSERT INTO loan_payments(loan_id,amount,date,note) VALUES(?,?,?,?)",(loan_id,amt,date_e.get().strip() or today_str(),note_e.get().strip()))
            conn.execute("UPDATE loans SET balance=MAX(0,balance-?) WHERE id=?",(amt,loan_id))
            conn.commit(); conn.close(); win.destroy(); self._reload(); self.on_change()
        styled_btn(win,"  Save Payment  ",save).pack(pady=14)
    def _add_recurring_dialog(self):
        RecurringDialog(self,"expense",lambda:(self._reload(),self.on_change()))

# ═════════════════════════════════════════════════════════════════════════════
# ACCOUNTS UI
# ═════════════════════════════════════════════════════════════════════════════
ACCOUNT_TYPES = ["Checking", "Savings", "Savings Plus", "Roth IRA", "Stocks"]

class AccountDialog(tk.Toplevel):
    def __init__(self, parent, account=None, on_save=None):
        super().__init__(parent)
        self.title("Edit Account" if account else "Add Account")
        self.configure(bg=BG)
        self.geometry("460x430")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()
        self.on_save = on_save
        self.account = account

        tk.Label(self, text="Edit Account" if account else "Add Account",
                 bg=BG, fg=ACCENT, font=FONT_H2).pack(pady=(18, 12))

        values = {
            "institution": account[1] if account else "",
            "account_name": account[2] if account else "",
            "account_type": account[3] if account else ACCOUNT_TYPES[0],
            "nickname": account[4] if account else "",
            "current_balance": account[5] if account else 0.0,
        }

        body = tk.Frame(self, bg=BG)
        body.pack(fill="x", padx=28)

        def row(label, value="", combo_values=None):
            f = tk.Frame(body, bg=BG)
            f.pack(fill="x", pady=6)
            tk.Label(f, text=label, bg=BG, fg=TEXT_DIM, font=FONT_BODY, width=18, anchor="w").pack(side="left")
            if combo_values is not None:
                w = ttk.Combobox(f, values=combo_values, state="readonly", font=FONT_BODY)
                w.set(value)
            else:
                w = tk.Entry(f, bg=BG3, fg=TEXT, insertbackground=TEXT,
                             relief="flat", font=FONT_BODY)
                w.insert(0, str(value))
            w.pack(side="left", fill="x", expand=True, ipady=5)
            return w

        inst_e = row("Institution", values["institution"])
        name_e = row("Account Name", values["account_name"])
        type_e = row("Account Type", values["account_type"], ACCOUNT_TYPES)
        nick_e = row("Nickname", values["nickname"])
        bal_e = row("Current Balance ($)", values["current_balance"])

        def save():
            institution = inst_e.get().strip()
            account_name = name_e.get().strip()
            account_type = type_e.get().strip()
            nickname = nick_e.get().strip()
            if not institution or not account_name or not account_type:
                messagebox.showerror("Missing Information", "Institution, Account Name, and Account Type are required.", parent=self)
                return
            try:
                balance = float(bal_e.get().replace(",", "").replace("$", "").strip() or 0)
            except ValueError:
                messagebox.showerror("Invalid Balance", "Enter a valid numeric balance.", parent=self)
                return
            if self.account:
                update_account(self.account[0], institution, account_name, account_type, nickname, balance)
            else:
                add_account(institution, account_name, account_type, nickname, balance)
            self.destroy()
            if self.on_save:
                self.on_save()

        styled_btn(self, "  Save Account  ", save, color=ACCENT3, fg=BG).pack(pady=18)


class AccountsTab(tk.Frame):
    def __init__(self, parent, on_change=None):
        super().__init__(parent, bg=BG)
        self.on_change = on_change
        self._build()
        self.refresh()

    def _build(self):
        header = tk.Frame(self, bg=BG)
        header.pack(fill="x", padx=28, pady=(26, 10))
        tk.Label(header, text="Accounts", bg=BG, fg=TEXT, font=FONT_H1).pack(side="left")
        styled_btn(header, "+ Add Account", self._add, color=ACCENT3, fg=BG).pack(side="right")

        self.summary = tk.Label(self, text="", bg=BG, fg=TEXT_DIM, font=FONT_BODY, anchor="w")
        self.summary.pack(fill="x", padx=30, pady=(0, 12))

        card = tk.Frame(self, bg=BG2, highlightbackground=BORDER, highlightthickness=1)
        card.pack(fill="both", expand=True, padx=28, pady=(0, 28))

        cols = ("institution", "account", "type", "nickname", "balance", "status")
        self.tree = ttk.Treeview(card, columns=cols, show="headings", height=16)
        headings = {
            "institution":"Institution", "account":"Account", "type":"Type",
            "nickname":"Nickname", "balance":"Balance", "status":"Status"
        }
        widths = {"institution":150, "account":150, "type":120, "nickname":140, "balance":120, "status":90}
        for c in cols:
            self.tree.heading(c, text=headings[c])
            self.tree.column(c, width=widths[c], anchor="w")
        self.tree.column("balance", anchor="e")
        self.tree.pack(side="left", fill="both", expand=True, padx=10, pady=10)

        scroll = ttk.Scrollbar(card, orient="vertical", command=self.tree.yview)
        scroll.pack(side="right", fill="y", pady=10)
        self.tree.configure(yscrollcommand=scroll.set)
        self.tree.bind("<Double-1>", lambda e: self._edit())

        controls = tk.Frame(self, bg=BG)
        controls.pack(fill="x", padx=28, pady=(0, 20))
        styled_btn(controls, "Edit Selected", self._edit, color=ACCENT).pack(side="left")
        styled_btn(controls, "Deactivate / Reactivate", self._toggle_active, color=ACCENT5).pack(side="left", padx=8)

    def refresh(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        rows = get_accounts(active_only=False)
        total = sum(float(r[5] or 0) for r in rows if r[7])
        active_count = sum(1 for r in rows if r[7])
        self.summary.configure(text=f"{active_count} active account(s)  •  Total tracked balance: {fmt_money(total)}")
        for r in rows:
            self.tree.insert("", "end", iid=str(r[0]), values=(
                r[1], r[2], r[3], r[4] or "—", fmt_money(r[5] or 0), "Active" if r[7] else "Inactive"
            ))

    def _selected(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo("Select Account", "Select an account first.", parent=self)
            return None
        account_id = int(sel[0])
        return next((r for r in get_accounts(active_only=False) if r[0] == account_id), None)

    def _add(self):
        AccountDialog(self, on_save=self._changed)

    def _edit(self):
        account = self._selected()
        if account:
            AccountDialog(self, account=account, on_save=self._changed)

    def _toggle_active(self):
        account = self._selected()
        if not account:
            return
        new_state = not bool(account[7])
        set_account_active(account[0], new_state)
        self._changed()

    def _changed(self):
        self.refresh()
        if self.on_change:
            self.on_change()


# ═════════════════════════════════════════════════════════════════════════════
# SIDEBAR NAV
# ═════════════════════════════════════════════════════════════════════════════
SIDEBAR_W = 200

NAV_ITEMS = [
    ("Dashboard", "💰", ACCENT),
    ("Accounts",  "🏦", ACCENT3),
    ("Income",    "📥", ACCENT),
    ("Expenses",  "📤", ACCENT2),
    ("Recurring", "🔁", ACCENT5),
]

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        init_db()
        posted = process_recurring()

        self.title("Finance Tracker")
        self.geometry("1200x780")
        self.minsize(960, 640)
        self.configure(bg=BG)

        # ── Root layout: sidebar | divider | content ──────────────────────
        root = tk.Frame(self, bg=BG)
        root.pack(fill="both", expand=True)

        # Sidebar
        self.sidebar = tk.Frame(root, bg=BG2, width=SIDEBAR_W)
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)

        # Divider
        tk.Frame(root, bg=BORDER, width=1).pack(side="left", fill="y")

        # Content area (all pages stacked here)
        self.content = tk.Frame(root, bg=BG)
        self.content.pack(side="left", fill="both", expand=True)

        # ── Sidebar: logo ─────────────────────────────────────────────────
        logo_frame = tk.Frame(self.sidebar, bg=BG2)
        logo_frame.pack(fill="x", pady=(24, 8))
        tk.Label(logo_frame, text="💰", bg=BG2, fg=ACCENT,
                 font=("Times New Roman", 28)).pack()
        tk.Label(logo_frame, text="FINANCE", bg=BG2, fg=ACCENT,
                 font=("Times New Roman", 13, "bold")).pack()
        tk.Label(logo_frame, text="TRACKER", bg=BG2, fg=TEXT_DIM,
                 font=("Times New Roman", 10)).pack()

        tk.Frame(self.sidebar, bg=BORDER, height=1).pack(fill="x", padx=16, pady=(12, 20))

        # ── Sidebar: nav buttons ──────────────────────────────────────────
        self._nav_btns = {}
        self._active_page = tk.StringVar(value="Dashboard")

        for name, icon, clr in NAV_ITEMS:
            btn = self._make_nav_btn(name, icon, clr)
            self._nav_btns[name] = btn

        # ── Sidebar: date at bottom ───────────────────────────────────────
        tk.Frame(self.sidebar, bg=BORDER, height=1).pack(fill="x", padx=16, pady=(20, 10))
        tk.Label(self.sidebar,
                 text=date.today().strftime("%b %d, %Y"),
                 bg=BG2, fg=TEXT_DIM, font=FONT_SMALL).pack(pady=(0, 16))

        # ── Build all pages ───────────────────────────────────────────────
        self.dash = DashboardTab(self.content)
        self.acct = AccountsTab(self.content,        self._refresh)
        self.inc  = IncomeTab(self.content,          self._refresh)
        self.exp  = CombinedExpensesTab(self.content, self._refresh)
        self.rec  = RecurringTab(self.content,        self._refresh)

        self._pages = {
            "Dashboard": self.dash,
            "Accounts":  self.acct,
            "Income":    self.inc,
            "Expenses":  self.exp,
            "Recurring": self.rec,
        }

        # Stack all pages in the content frame
        for page in self._pages.values():
            page.place(relx=0, rely=0, relwidth=1, relheight=1)

        # Show dashboard first
        self._show("Dashboard")

        # Recurring auto-post popup
        if posted:
            self.after(800, lambda: messagebox.showinfo(
                "Recurring Auto-Post",
                f"✅  {posted} recurring entr{'ies' if posted!=1 else 'y'} were automatically posted since your last session."))

    def _make_nav_btn(self, name, icon, clr):
        frame = tk.Frame(self.sidebar, bg=BG2, cursor="hand2")
        frame.pack(fill="x", padx=10, pady=2)

        indicator = tk.Frame(frame, bg=BG2, width=4)
        indicator.pack(side="left", fill="y")

        inner = tk.Frame(frame, bg=BG2)
        inner.pack(side="left", fill="both", expand=True, padx=(6, 10), pady=6)

        icon_lbl = tk.Label(inner, text=icon, bg=BG2, fg=clr,
                            font=("Times New Roman", 14))
        icon_lbl.pack(side="left", padx=(4, 8))

        text_lbl = tk.Label(inner, text=name, bg=BG2, fg=TEXT_DIM,
                            font=FONT_BODY, anchor="w")
        text_lbl.pack(side="left", fill="x", expand=True)

        def on_click(n=name):
            self._show(n)

        def on_enter(e, f=frame, il=icon_lbl, tl=text_lbl, n=name):
            if self._active_page.get() != n:
                f.configure(bg=BG3)
                il.configure(bg=BG3)
                tl.configure(bg=BG3)
                indicator.configure(bg=BG3)
                inner.configure(bg=BG3)

        def on_leave(e, f=frame, il=icon_lbl, tl=text_lbl, n=name):
            if self._active_page.get() != n:
                f.configure(bg=BG2)
                il.configure(bg=BG2)
                tl.configure(bg=BG2)
                indicator.configure(bg=BG2)
                inner.configure(bg=BG2)

        for w in [frame, inner, icon_lbl, text_lbl]:
            w.bind("<Button-1>", lambda e, n=name: on_click(n))
            w.bind("<Enter>", on_enter)
            w.bind("<Leave>", on_leave)

        # Store references to sub-widgets for active state updates
        frame._indicator = indicator
        frame._icon_lbl  = icon_lbl
        frame._text_lbl  = text_lbl
        frame._inner     = inner
        frame._clr       = clr

        return frame

    def _show(self, name):
        # Deactivate old
        prev = self._active_page.get()
        if prev in self._nav_btns:
            f = self._nav_btns[prev]
            for w in [f, f._inner, f._icon_lbl, f._text_lbl, f._indicator]:
                w.configure(bg=BG2)
            f._text_lbl.configure(fg=TEXT_DIM)

        # Activate new
        self._active_page.set(name)
        f = self._nav_btns[name]
        for w in [f, f._inner, f._icon_lbl, f._text_lbl]:
            w.configure(bg=BG3)
        f._indicator.configure(bg=f._clr)       # coloured left bar
        f._text_lbl.configure(fg=TEXT)

        # Raise the right page
        self._pages[name].lift()

    def _refresh(self):
        self.dash.refresh()

if __name__ == "__main__":
    App().mainloop()