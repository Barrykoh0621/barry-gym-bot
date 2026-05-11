"""
Barry's Gym - Database module (SQLite)
"""

import sqlite3
import os
from datetime import datetime, date

DB_PATH = os.environ.get("DB_PATH", "gym.db")


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS members (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            phone TEXT UNIQUE NOT NULL,
            membership_type TEXT NOT NULL DEFAULT 'regular',
            start_date DATE NOT NULL,
            expiry_date DATE NOT NULL,
            payment_status TEXT NOT NULL DEFAULT 'pending',
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            member_id INTEGER NOT NULL,
            check_in TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            check_out TIMESTAMP,
            FOREIGN KEY (member_id) REFERENCES members(id)
        )
    """)
    conn.commit()
    conn.close()


# ── Members ──────────────────────────────────────────────────

def get_all_members(search=None):
    conn = get_db()
    if search:
        q = f"%{search}%"
        rows = conn.execute(
            "SELECT * FROM members WHERE name LIKE ? OR phone LIKE ? ORDER BY name",
            (q, q)
        ).fetchall()
    else:
        rows = conn.execute("SELECT * FROM members ORDER BY name").fetchall()
    conn.close()
    return rows


def get_member(member_id):
    conn = get_db()
    row = conn.execute("SELECT * FROM members WHERE id = ?", (member_id,)).fetchone()
    conn.close()
    return row


def get_member_by_phone(phone):
    clean = phone.replace("+", "").replace("-", "").replace(" ", "")
    conn = get_db()
    row = conn.execute(
        "SELECT * FROM members WHERE replace(replace(replace(phone,'+',''),'-',''),' ','') = ?",
        (clean,)
    ).fetchone()
    conn.close()
    return row


def add_member(name, phone, membership_type, start_date, expiry_date, payment_status, notes=""):
    conn = get_db()
    conn.execute(
        """INSERT INTO members (name, phone, membership_type, start_date, expiry_date, payment_status, notes)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (name, phone, membership_type, start_date, expiry_date, payment_status, notes)
    )
    conn.commit()
    conn.close()


def update_member(member_id, name, phone, membership_type, start_date, expiry_date, payment_status, notes=""):
    conn = get_db()
    conn.execute(
        """UPDATE members SET name=?, phone=?, membership_type=?, start_date=?,
           expiry_date=?, payment_status=?, notes=? WHERE id=?""",
        (name, phone, membership_type, start_date, expiry_date, payment_status, notes, member_id)
    )
    conn.commit()
    conn.close()


def delete_member(member_id):
    conn = get_db()
    conn.execute("DELETE FROM attendance WHERE member_id = ?", (member_id,))
    conn.execute("DELETE FROM members WHERE id = ?", (member_id,))
    conn.commit()
    conn.close()


# ── Attendance ────────────────────────────────────────────────

def checkin(member_id):
    """Record check-in. Returns True if successful, False if already checked in."""
    conn = get_db()
    today = date.today().isoformat()
    existing = conn.execute(
        """SELECT id FROM attendance
           WHERE member_id = ? AND date(check_in) = ? AND check_out IS NULL""",
        (member_id, today)
    ).fetchone()
    if existing:
        conn.close()
        return False
    conn.execute(
        "INSERT INTO attendance (member_id, check_in) VALUES (?, ?)",
        (member_id, datetime.now().isoformat())
    )
    conn.commit()
    conn.close()
    return True


def checkout(member_id):
    """Record check-out. Returns True if successful, False if not checked in."""
    conn = get_db()
    today = date.today().isoformat()
    row = conn.execute(
        """SELECT id FROM attendance
           WHERE member_id = ? AND date(check_in) = ? AND check_out IS NULL""",
        (member_id, today)
    ).fetchone()
    if not row:
        conn.close()
        return False
    conn.execute(
        "UPDATE attendance SET check_out = ? WHERE id = ?",
        (datetime.now().isoformat(), row["id"])
    )
    conn.commit()
    conn.close()
    return True


def get_attendance(filter_date=None, member_id=None):
    conn = get_db()
    query = """
        SELECT a.*, m.name as member_name, m.phone as member_phone
        FROM attendance a
        JOIN members m ON a.member_id = m.id
        WHERE 1=1
    """
    params = []
    if filter_date:
        query += " AND date(a.check_in) = ?"
        params.append(filter_date)
    if member_id:
        query += " AND a.member_id = ?"
        params.append(member_id)
    query += " ORDER BY a.check_in DESC"
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return rows


def get_today_checkin_count():
    conn = get_db()
    today = date.today().isoformat()
    count = conn.execute(
        "SELECT COUNT(*) FROM attendance WHERE date(check_in) = ?", (today,)
    ).fetchone()[0]
    conn.close()
    return count


def get_dashboard_stats():
    conn = get_db()
    today = date.today().isoformat()
    total = conn.execute("SELECT COUNT(*) FROM members").fetchone()[0]
    active = conn.execute(
        "SELECT COUNT(*) FROM members WHERE expiry_date >= ?", (today,)
    ).fetchone()[0]
    today_checkins = conn.execute(
        "SELECT COUNT(*) FROM attendance WHERE date(check_in) = ?", (today,)
    ).fetchone()[0]
    pending_payment = conn.execute(
        "SELECT COUNT(*) FROM members WHERE payment_status IN ('pending','overdue')"
    ).fetchone()[0]
    expiring_soon = conn.execute(
        """SELECT * FROM members
           WHERE expiry_date BETWEEN ? AND date(?, '+7 days')
           ORDER BY expiry_date""",
        (today, today)
    ).fetchall()
    recent_checkins = conn.execute(
        """SELECT a.*, m.name as member_name
           FROM attendance a JOIN members m ON a.member_id = m.id
           WHERE date(a.check_in) = ?
           ORDER BY a.check_in DESC LIMIT 10""",
        (today,)
    ).fetchall()
    conn.close()
    return {
        "total_members": total,
        "active_members": active,
        "today_checkins": today_checkins,
        "pending_payment": pending_payment,
        "expiring_soon": list(expiring_soon),
        "recent_checkins": list(recent_checkins),
    }
