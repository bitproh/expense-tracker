import sqlite3
import datetime
import hashlib
from pathlib import Path

DB_PATH = Path(__file__).parent / "expenses.db"

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def hash_password(password: str) -> str:
    """Standard SHA-256 password hash (no external package dependency)."""
    return hashlib.sha256(password.encode("utf-8")).hexdigest()

def init_db():
    conn = get_connection()
    cur = conn.cursor()

    # 1. Users Table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            name TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # 2. Categories Table with user_id
    cur.execute("""
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            name TEXT NOT NULL,
            limit_per_time REAL NOT NULL,
            frequency_per_month INTEGER NOT NULL,
            monthly_budget REAL NOT NULL,
            icon TEXT DEFAULT '🏷️',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            UNIQUE(user_id, name)
        )
    """)

    # 3. Expenses Table with user_id
    cur.execute("""
        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            category_id INTEGER NOT NULL,
            amount REAL NOT NULL,
            date TEXT NOT NULL,
            note TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE CASCADE
        )
    """)

    # 4. Quick Templates Table with user_id
    cur.execute("""
        CREATE TABLE IF NOT EXISTS quick_templates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            category_id INTEGER NOT NULL,
            label TEXT NOT NULL,
            amount REAL NOT NULL,
            icon TEXT DEFAULT '⚡',
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE CASCADE
        )
    """)

    # 5. Rollover Adjustments Table with user_id
    cur.execute("""
        CREATE TABLE IF NOT EXISTS rollover_adjustments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            category_id INTEGER NOT NULL,
            year INTEGER NOT NULL,
            month INTEGER NOT NULL,
            adjustment REAL DEFAULT 0.0,
            UNIQUE(user_id, category_id, year, month),
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE CASCADE
        )
    """)

    # Auto-migration: check if user_id column exists in legacy tables
    for table in ["categories", "expenses", "quick_templates", "rollover_adjustments"]:
        cur.execute(f"PRAGMA table_info({table})")
        cols = [c["name"] for c in cur.fetchall()]
        if "user_id" not in cols:
            cur.execute(f"ALTER TABLE {table} ADD COLUMN user_id INTEGER DEFAULT 1")

    # Create default demo user if empty
    cur.execute("SELECT COUNT(*) as cnt FROM users")
    if cur.fetchone()["cnt"] == 0:
        default_pwd_hash = hash_password("demo123")
        cur.execute("""
            INSERT INTO users (username, password_hash, name)
            VALUES (?, ?, ?)
        """, ("demo", default_pwd_hash, "Demo User"))
        default_uid = cur.lastrowid
        
        # Link existing unassigned records to demo user
        cur.execute("UPDATE categories SET user_id = ? WHERE user_id IS NULL OR user_id = 0", (default_uid,))
        cur.execute("UPDATE expenses SET user_id = ? WHERE user_id IS NULL OR user_id = 0", (default_uid,))
        cur.execute("UPDATE quick_templates SET user_id = ? WHERE user_id IS NULL OR user_id = 0", (default_uid,))
        cur.execute("UPDATE rollover_adjustments SET user_id = ? WHERE user_id IS NULL OR user_id = 0", (default_uid,))

        # Add initial sample categories for demo user if none exist
        cur.execute("SELECT COUNT(*) as cnt FROM categories WHERE user_id = ?", (default_uid,))
        if cur.fetchone()["cnt"] == 0:
            seed_user_defaults(cur, default_uid)

    conn.commit()
    conn.close()

def seed_user_defaults(cur, user_id):
    """Adds default starter categories and 1-tap shortcuts for a newly registered user."""
    categories_seed = [
        ("Food", 250.0, 8, 2000.0, "🍔"),
        ("Transport", 100.0, 10, 1000.0, "🚗"),
        ("Entertainment", 300.0, 4, 1200.0, "🎬")
    ]
    for name, limit_t, freq, mbudget, icon in categories_seed:
        cur.execute("""
            INSERT INTO categories (user_id, name, limit_per_time, frequency_per_month, monthly_budget, icon)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (user_id, name, limit_t, freq, mbudget, icon))
        cat_id = cur.lastrowid

        if name == "Food":
            cur.executemany("""
                INSERT INTO quick_templates (user_id, category_id, label, amount, icon)
                VALUES (?, ?, ?, ?, ?)
            """, [
                (user_id, cat_id, "Chai & Snack", 50.0, "☕"),
                (user_id, cat_id, "Daily Meal / Thali", 150.0, "🍱"),
                (user_id, cat_id, "Standard Food Target", 250.0, "🍔")
            ])
        elif name == "Transport":
            cur.execute("""
                INSERT INTO quick_templates (user_id, category_id, label, amount, icon)
                VALUES (?, ?, ?, ?, ?)
            """, (user_id, cat_id, "Auto / Metro", 50.0, "🛺"))

# ----------------- USER AUTHENTICATION -----------------
def register_user(username, password, name=""):
    username = username.strip().lower()
    if not username:
        return False, "Username cannot be empty."
    if len(password) < 4:
        return False, "Password must be at least 4 characters long."

    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            INSERT INTO users (username, password_hash, name)
            VALUES (?, ?, ?)
        """, (username, hash_password(password), name.strip() or username.capitalize()))
        new_uid = cur.lastrowid
        seed_user_defaults(cur, new_uid)
        conn.commit()
        return True, "Account created successfully! You can now log in."
    except sqlite3.IntegrityError:
        return False, f"Username '{username}' is already taken. Please choose another."
    finally:
        conn.close()

def authenticate_user(username, password):
    username = username.strip().lower()
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT * FROM users
        WHERE username = ? AND password_hash = ?
    """, (username, hash_password(password)))
    user_row = cur.fetchone()
    conn.close()
    if user_row:
        return dict(user_row)
    return None

def get_user_by_id(user_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, username, name FROM users WHERE id = ?", (user_id,))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None

# ----------------- CATEGORIES (MULTI-USER) -----------------
def get_categories(user_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM categories WHERE user_id = ? ORDER BY name ASC", (user_id,))
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def add_category(user_id, name, limit_per_time, frequency_per_month, icon='🏷️'):
    monthly_budget = float(limit_per_time) * int(frequency_per_month)
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            INSERT INTO categories (user_id, name, limit_per_time, frequency_per_month, monthly_budget, icon)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (user_id, name.strip(), float(limit_per_time), int(frequency_per_month), monthly_budget, icon.strip() or '🏷️'))
        conn.commit()
        return True, "Category added successfully!"
    except sqlite3.IntegrityError:
        return False, f"Category '{name}' already exists in your account."
    finally:
        conn.close()

def update_category(user_id, cat_id, name, limit_per_time, frequency_per_month, icon='🏷️'):
    monthly_budget = float(limit_per_time) * int(frequency_per_month)
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            UPDATE categories
            SET name = ?, limit_per_time = ?, frequency_per_month = ?, monthly_budget = ?, icon = ?
            WHERE id = ? AND user_id = ?
        """, (name.strip(), float(limit_per_time), int(frequency_per_month), monthly_budget, icon.strip() or '🏷️', cat_id, user_id))
        conn.commit()
        return True, "Category updated!"
    except sqlite3.IntegrityError:
        return False, f"Category name '{name}' already in use."
    finally:
        conn.close()

def delete_category(user_id, cat_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM categories WHERE id = ? AND user_id = ?", (cat_id, user_id))
    cur.execute("DELETE FROM expenses WHERE category_id = ? AND user_id = ?", (cat_id, user_id))
    cur.execute("DELETE FROM quick_templates WHERE category_id = ? AND user_id = ?", (cat_id, user_id))
    cur.execute("DELETE FROM rollover_adjustments WHERE category_id = ? AND user_id = ?", (cat_id, user_id))
    conn.commit()
    conn.close()

# ----------------- EXPENSES (MULTI-USER) -----------------
def add_expense(user_id, category_id, amount, expense_date, note=""):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO expenses (user_id, category_id, amount, date, note)
        VALUES (?, ?, ?, ?, ?)
    """, (user_id, category_id, float(amount), str(expense_date), note.strip()))
    conn.commit()
    expense_id = cur.lastrowid
    conn.close()
    return expense_id

def delete_expense(user_id, expense_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM expenses WHERE id = ? AND user_id = ?", (expense_id, user_id))
    conn.commit()
    conn.close()

def get_recent_expenses(user_id, limit=5):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT e.id, e.amount, e.date, e.note, c.id as category_id, c.name as category_name,
               c.limit_per_time, c.frequency_per_month, c.monthly_budget, c.icon
        FROM expenses e
        JOIN categories c ON e.category_id = c.id
        WHERE e.user_id = ?
        ORDER BY e.id DESC
        LIMIT ?
    """, (user_id, limit))
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_monthly_expenses(user_id, year, month):
    conn = get_connection()
    cur = conn.cursor()
    prefix = f"{year:04d}-{month:02d}-%"
    cur.execute("""
        SELECT e.id, e.amount, e.date, e.note, c.id as category_id, c.name as category_name,
               c.limit_per_time, c.frequency_per_month, c.monthly_budget, c.icon
        FROM expenses e
        JOIN categories c ON e.category_id = c.id
        WHERE e.user_id = ? AND e.date LIKE ?
        ORDER BY e.date DESC, e.id DESC
    """, (user_id, prefix))
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_category_monthly_stats(user_id, category_id, year, month, rolled_over_amount=0.0):
    conn = get_connection()
    cur = conn.cursor()
    prefix = f"{year:04d}-{month:02d}-%"
    
    cur.execute("SELECT * FROM categories WHERE id = ? AND user_id = ?", (category_id, user_id))
    cat_row = cur.fetchone()
    if not cat_row:
        conn.close()
        return None
    cat = dict(cat_row)

    cur.execute("""
        SELECT COUNT(*) as count, COALESCE(SUM(amount), 0) as total_spent,
               COALESCE(AVG(amount), 0) as avg_spent
        FROM expenses
        WHERE user_id = ? AND category_id = ? AND date LIKE ?
    """, (user_id, category_id, prefix))
    stat_row = cur.fetchone()
    conn.close()

    count = stat_row["count"]
    total_spent = stat_row["total_spent"]
    avg_spent = stat_row["avg_spent"]

    effective_budget = cat["monthly_budget"] + rolled_over_amount
    remaining_budget = effective_budget - total_spent
    spends_left = max(0, cat["frequency_per_month"] - count)

    if spends_left > 0:
        recommended_next_avg = max(0.0, remaining_budget / spends_left)
    else:
        recommended_next_avg = 0.0

    return {
        **cat,
        "effective_budget": effective_budget,
        "rolled_over_amount": rolled_over_amount,
        "spends_done": count,
        "total_spent": total_spent,
        "actual_avg": avg_spent,
        "remaining_budget": remaining_budget,
        "spends_left": spends_left,
        "recommended_next_avg": recommended_next_avg,
        "is_budget_exceeded": total_spent > effective_budget,
        "is_frequency_exceeded": count > cat["frequency_per_month"],
    }

# ----------------- ROLLOVER VALUE & ADJUSTMENT (MULTI-USER) -----------------
def get_rollover_from_previous_month(user_id, year, month):
    if month == 1:
        prev_year = year - 1
        prev_month = 12
    else:
        prev_year = year
        prev_month = month - 1

    cats = get_categories(user_id)
    if not cats:
        return 0.0, {}, {}, {}

    conn = get_connection()
    cur = conn.cursor()
    prev_prefix = f"{prev_year:04d}-{prev_month:02d}-%"
    
    cat_base_savings = {}
    cat_adjustments = {}
    cat_final_savings = {}
    total_savings = 0.0

    try:
        for cat in cats:
            cur.execute("""
                SELECT COALESCE(SUM(amount), 0) as spent
                FROM expenses
                WHERE user_id = ? AND category_id = ? AND date LIKE ?
            """, (user_id, cat["id"], prev_prefix))
            row = cur.fetchone()
            spent = row["spent"] if row else 0.0
            base_saving = max(0.0, cat["monthly_budget"] - spent)
            cat_base_savings[cat["id"]] = base_saving

            # Fetch manual adjustment
            cur.execute("""
                SELECT adjustment FROM rollover_adjustments
                WHERE user_id = ? AND category_id = ? AND year = ? AND month = ?
            """, (user_id, cat["id"], year, month))
            adj_row = cur.fetchone()
            adj = adj_row["adjustment"] if adj_row else 0.0
            cat_adjustments[cat["id"]] = adj

            # Final saving
            final_val = max(0.0, base_saving + adj)
            cat_final_savings[cat["id"]] = final_val
            total_savings += final_val
    finally:
        conn.close()

    return total_savings, cat_final_savings, cat_base_savings, cat_adjustments

def set_rollover_adjustment(user_id, category_id, year, month, adjustment_value):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO rollover_adjustments (user_id, category_id, year, month, adjustment)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(user_id, category_id, year, month)
        DO UPDATE SET adjustment = excluded.adjustment
    """, (user_id, category_id, year, month, float(adjustment_value)))
    conn.commit()
    conn.close()

def reset_category_rollover(user_id, category_id, year, month, base_saving):
    set_rollover_adjustment(user_id, category_id, year, month, -float(base_saving))

def reset_all_rollovers_for_month(user_id, year, month):
    result = get_rollover_from_previous_month(user_id, year, month)
    cat_base_savings = result[2]
    for cat_id, base_saving in cat_base_savings.items():
        reset_category_rollover(user_id, cat_id, year, month, base_saving)

# ----------------- RESET PROVISIONS (MULTI-USER) -----------------
def reset_expenses_weekly(user_id):
    today = datetime.date.today()
    start_of_week = today - datetime.timedelta(days=today.weekday())
    end_of_week = start_of_week + datetime.timedelta(days=6)
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        DELETE FROM expenses
        WHERE user_id = ? AND date >= ? AND date <= ?
    """, (user_id, str(start_of_week), str(end_of_week)))
    deleted_cnt = cur.rowcount
    conn.commit()
    conn.close()
    return deleted_cnt, str(start_of_week), str(end_of_week)

def reset_expenses_monthly(user_id, year, month):
    prefix = f"{year:04d}-{month:02d}-%"
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM expenses WHERE user_id = ? AND date LIKE ?", (user_id, prefix))
    deleted_cnt = cur.rowcount
    conn.commit()
    conn.close()
    return deleted_cnt

def reset_expenses_all_time(user_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM expenses WHERE user_id = ?", (user_id,))
    deleted_cnt = cur.rowcount
    conn.commit()
    conn.close()
    return deleted_cnt

# ----------------- QUICK TEMPLATES (MULTI-USER) -----------------
def get_quick_templates(user_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT q.id, q.category_id, q.label, q.amount, q.icon, c.name as category_name
        FROM quick_templates q
        JOIN categories c ON q.category_id = c.id
        WHERE q.user_id = ?
        ORDER BY q.id ASC
    """, (user_id,))
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def add_quick_template(user_id, category_id, label, amount, icon="⚡"):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO quick_templates (user_id, category_id, label, amount, icon)
        VALUES (?, ?, ?, ?, ?)
    """, (user_id, category_id, label.strip(), float(amount), icon.strip() or "⚡"))
    conn.commit()
    conn.close()

def delete_quick_template(user_id, template_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM quick_templates WHERE id = ? AND user_id = ?", (template_id, user_id))
    conn.commit()
    conn.close()
