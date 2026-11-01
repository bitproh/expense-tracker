import sqlite3
import datetime
from pathlib import Path

DB_PATH = Path(__file__).parent / "expenses.db"

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    cur = conn.cursor()
    # Categories / Budget rules:
    cur.execute("""
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            limit_per_time REAL NOT NULL,
            frequency_per_month INTEGER NOT NULL,
            monthly_budget REAL NOT NULL,
            icon TEXT DEFAULT '🏷️',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Expenses:
    cur.execute("""
        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category_id INTEGER NOT NULL,
            amount REAL NOT NULL,
            date TEXT NOT NULL,
            note TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE CASCADE
        )
    """)

    # Quick Spend Templates (1-tap quick buttons)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS quick_templates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category_id INTEGER NOT NULL,
            label TEXT NOT NULL,
            amount REAL NOT NULL,
            icon TEXT DEFAULT '⚡',
            FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE CASCADE
        )
    """)

    # Seed default category if empty
    cur.execute("SELECT COUNT(*) as cnt FROM categories")
    if cur.fetchone()["cnt"] == 0:
        cur.execute("""
            INSERT INTO categories (name, limit_per_time, frequency_per_month, monthly_budget, icon)
            VALUES (?, ?, ?, ?, ?)
        """, ("Food", 250.0, 8, 2000.0, "🍔"))
        
        today_str = datetime.date.today().strftime("%Y-%m-%d")
        cur.execute("""
            INSERT INTO expenses (category_id, amount, date, note)
            VALUES (1, 280.0, ?, 'Dinner outside (slightly exceeded limit)')
        """, (today_str,))

    # Seed default quick templates if empty
    cur.execute("SELECT COUNT(*) as cnt FROM quick_templates")
    if cur.fetchone()["cnt"] == 0:
        cur.execute("SELECT id FROM categories WHERE name = 'Food'")
        food_row = cur.fetchone()
        if food_row:
            fid = food_row["id"]
            default_templates = [
                (fid, "Chai & Snack", 50.0, "☕"),
                (fid, "Daily Meal / Thali", 150.0, "🍱"),
                (fid, "Standard Food Target", 250.0, "🍔"),
            ]
            cur.executemany("""
                INSERT INTO quick_templates (category_id, label, amount, icon)
                VALUES (?, ?, ?, ?)
            """, default_templates)

    conn.commit()
    conn.close()

def get_categories():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM categories ORDER BY name ASC")
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def add_category(name, limit_per_time, frequency_per_month, icon='🏷️'):
    monthly_budget = float(limit_per_time) * int(frequency_per_month)
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            INSERT INTO categories (name, limit_per_time, frequency_per_month, monthly_budget, icon)
            VALUES (?, ?, ?, ?, ?)
        """, (name.strip(), float(limit_per_time), int(frequency_per_month), monthly_budget, icon.strip() or '🏷️'))
        conn.commit()
        return True, "Category added successfully!"
    except sqlite3.IntegrityError:
        return False, f"Category '{name}' already exists."
    finally:
        conn.close()

def update_category(cat_id, name, limit_per_time, frequency_per_month, icon='🏷️'):
    monthly_budget = float(limit_per_time) * int(frequency_per_month)
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            UPDATE categories
            SET name = ?, limit_per_time = ?, frequency_per_month = ?, monthly_budget = ?, icon = ?
            WHERE id = ?
        """, (name.strip(), float(limit_per_time), int(frequency_per_month), monthly_budget, icon.strip() or '🏷️', cat_id))
        conn.commit()
        return True, "Category updated!"
    except sqlite3.IntegrityError:
        return False, f"Category name '{name}' already in use."
    finally:
        conn.close()

def delete_category(cat_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM categories WHERE id = ?", (cat_id,))
    cur.execute("DELETE FROM expenses WHERE category_id = ?", (cat_id,))
    cur.execute("DELETE FROM quick_templates WHERE category_id = ?", (cat_id,))
    conn.commit()
    conn.close()

def add_expense(category_id, amount, expense_date, note=""):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO expenses (category_id, amount, date, note)
        VALUES (?, ?, ?, ?)
    """, (category_id, float(amount), str(expense_date), note.strip()))
    conn.commit()
    expense_id = cur.lastrowid
    conn.close()
    return expense_id

def delete_expense(expense_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM expenses WHERE id = ?", (expense_id,))
    conn.commit()
    conn.close()

def get_recent_expenses(limit=5):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT e.id, e.amount, e.date, e.note, c.id as category_id, c.name as category_name,
               c.limit_per_time, c.frequency_per_month, c.monthly_budget, c.icon
        FROM expenses e
        JOIN categories c ON e.category_id = c.id
        ORDER BY e.id DESC
        LIMIT ?
    """, (limit,))
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_monthly_expenses(year, month):
    conn = get_connection()
    cur = conn.cursor()
    prefix = f"{year:04d}-{month:02d}-%"
    cur.execute("""
        SELECT e.id, e.amount, e.date, e.note, c.id as category_id, c.name as category_name,
               c.limit_per_time, c.frequency_per_month, c.monthly_budget, c.icon
        FROM expenses e
        JOIN categories c ON e.category_id = c.id
        WHERE e.date LIKE ?
        ORDER BY e.date DESC, e.id DESC
    """, (prefix,))
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_all_expenses():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT e.id, e.amount, e.date, e.note, c.id as category_id, c.name as category_name,
               c.limit_per_time, c.frequency_per_month, c.monthly_budget, c.icon
        FROM expenses e
        JOIN categories c ON e.category_id = c.id
        ORDER BY e.date DESC, e.id DESC
    """)
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_category_monthly_stats(category_id, year, month, rolled_over_amount=0.0):
    conn = get_connection()
    cur = conn.cursor()
    prefix = f"{year:04d}-{month:02d}-%"
    
    cur.execute("SELECT * FROM categories WHERE id = ?", (category_id,))
    cat_row = cur.fetchone()
    if not cat_row:
        conn.close()
        return None
    cat = dict(cat_row)

    cur.execute("""
        SELECT COUNT(*) as count, COALESCE(SUM(amount), 0) as total_spent,
               COALESCE(AVG(amount), 0) as avg_spent
        FROM expenses
        WHERE category_id = ? AND date LIKE ?
    """, (category_id, prefix))
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

def get_rollover_from_previous_month(year, month):
    if month == 1:
        prev_year = year - 1
        prev_month = 12
    else:
        prev_year = year
        prev_month = month - 1

    cats = get_categories()
    if not cats:
        return 0.0, {}

    conn = get_connection()
    cur = conn.cursor()
    prev_prefix = f"{prev_year:04d}-{prev_month:02d}-%"
    
    cat_savings = {}
    total_savings = 0.0

    for cat in cats:
        cur.execute("""
            SELECT COALESCE(SUM(amount), 0) as spent
            FROM expenses
            WHERE category_id = ? AND date LIKE ?
        """, (cat["id"], prev_prefix))
        spent = cur.fetchone()["spent"]
        saving = max(0.0, cat["monthly_budget"] - spent)
        cat_savings[cat["id"]] = saving
        total_savings += saving

    conn.close()
    return total_savings, cat_savings

# ----------------- RESET PROVISIONS -----------------
def reset_expenses_weekly():
    """Deletes expenses from Monday of current week through Sunday."""
    today = datetime.date.today()
    start_of_week = today - datetime.timedelta(days=today.weekday())
    end_of_week = start_of_week + datetime.timedelta(days=6)
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        DELETE FROM expenses
        WHERE date >= ? AND date <= ?
    """, (str(start_of_week), str(end_of_week)))
    deleted_cnt = cur.rowcount
    conn.commit()
    conn.close()
    return deleted_cnt, str(start_of_week), str(end_of_week)

def reset_expenses_monthly(year, month):
    """Deletes expenses for specified month and year."""
    prefix = f"{year:04d}-{month:02d}-%"
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM expenses WHERE date LIKE ?", (prefix,))
    deleted_cnt = cur.rowcount
    conn.commit()
    conn.close()
    return deleted_cnt

def reset_expenses_all_time():
    """Deletes all expense entries, keeping categories intact."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM expenses")
    deleted_cnt = cur.rowcount
    conn.commit()
    conn.close()
    return deleted_cnt

# Quick Templates Management
def get_quick_templates():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT q.id, q.category_id, q.label, q.amount, q.icon, c.name as category_name
        FROM quick_templates q
        JOIN categories c ON q.category_id = c.id
        ORDER BY q.id ASC
    """)
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def add_quick_template(category_id, label, amount, icon="⚡"):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO quick_templates (category_id, label, amount, icon)
        VALUES (?, ?, ?, ?)
    """, (category_id, label.strip(), float(amount), icon.strip() or "⚡"))
    conn.commit()
    conn.close()

def delete_quick_template(template_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM quick_templates WHERE id = ?", (template_id,))
    conn.commit()
    conn.close()
