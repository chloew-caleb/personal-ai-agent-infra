"""Tiered retention and decay for a typed memory store (simplified).

Importance 1-5 maps to a lifetime. Expired records drop out of the
agent's default context but are NOT deleted, so they stay searchable.
"""
from datetime import datetime, timedelta, timezone
import sqlite3

LIFETIME_DAYS = {1: 3, 2: 14, 3: 60, 4: 365, 5: None}   # None = permanent

# Long-form journal entries lose importance as they age.
DECAY_THRESHOLDS = [(121, 1), (46, 2), (15, 3), (0, 4)]  # (min age in days, importance)

SCHEMA = """
CREATE TABLE IF NOT EXISTS memories (
    id INTEGER PRIMARY KEY,
    type TEXT NOT NULL,              -- fact | preference | event | note | journal
    content TEXT NOT NULL,
    importance INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    expires_at TEXT,
    is_deleted INTEGER DEFAULT 0,
    hits INTEGER DEFAULT 0,          -- usage credit: times actually used in a reply
    last_used_at TEXT
);
"""


def expiry_for(importance: int, now: datetime):
    days = LIFETIME_DAYS[importance]
    return None if days is None else (now + timedelta(days=days)).isoformat()


def write(conn: sqlite3.Connection, type_: str, content: str, importance: int) -> int:
    now = datetime.now(timezone.utc)
    cur = conn.execute(
        "INSERT INTO memories (type, content, importance, created_at, expires_at) VALUES (?,?,?,?,?)",
        (type_, content, importance, now.isoformat(), expiry_for(importance, now)),
    )
    conn.commit()
    return cur.lastrowid


def active(conn: sqlite3.Connection, type_: str, limit: int = 20):
    """Records that belong in the agent's default context."""
    now = datetime.now(timezone.utc).isoformat()
    return conn.execute(
        "SELECT id, content FROM memories WHERE type=? AND is_deleted=0 "
        "AND (expires_at IS NULL OR expires_at > ?) ORDER BY created_at DESC LIMIT ?",
        (type_, now, limit),
    ).fetchall()


def target_importance(age_days: int) -> int:
    for min_days, imp in DECAY_THRESHOLDS:
        if age_days >= min_days:
            return imp
    return 4


def run_decay(conn: sqlite3.Connection) -> int:
    """Daily job: lower the importance of aging journal entries."""
    now = datetime.now(timezone.utc)
    changed = 0
    for id_, imp, created in conn.execute(
        "SELECT id, importance, created_at FROM memories WHERE type='journal' AND is_deleted=0"
    ).fetchall():
        age = (now - datetime.fromisoformat(created)).days
        target = target_importance(age)
        if target < imp:
            conn.execute("UPDATE memories SET importance=? WHERE id=?", (target, id_))
            changed += 1
    conn.commit()
    return changed


def touch(conn: sqlite3.Connection, ids):
    """Usage credit: record which retrieved memories were actually used."""
    now = datetime.now(timezone.utc).isoformat()
    conn.executemany("UPDATE memories SET hits = hits + 1, last_used_at=? WHERE id=?", [(now, i) for i in ids])
    conn.commit()


if __name__ == "__main__":
    c = sqlite3.connect(":memory:")
    c.executescript(SCHEMA)
    i = write(c, "note", "pick up the dry cleaning", 1)
    j = write(c, "fact", "prefers still water", 5)
    print(active(c, "note"), active(c, "fact"))
    touch(c, [j])
    print(run_decay(c))
