import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent.parent.parent / "data" / "workouts.db"


def get_conn() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_conn() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS workout_entries (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                raw_text      TEXT NOT NULL,
                workout_date  DATE NOT NULL,
                created_at    DATETIME DEFAULT CURRENT_TIMESTAMP,
                parse_status  TEXT DEFAULT 'ok'
            );

            CREATE TABLE IF NOT EXISTS exercises (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                entry_id      INTEGER NOT NULL REFERENCES workout_entries(id),
                exercise_name TEXT NOT NULL,
                sets          INTEGER,
                reps          INTEGER,
                duration_min  REAL,
                weight_kg     REAL,
                feeling       TEXT,
                notes         TEXT
            );
        """)


def save_entry(raw_text: str, workout_date: str, exercises: list[dict], parse_status: str = "ok") -> int:
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO workout_entries (raw_text, workout_date, parse_status) VALUES (?, ?, ?)",
            (raw_text, workout_date, parse_status),
        )
        entry_id = cur.lastrowid
        conn.executemany(
            """INSERT INTO exercises
               (entry_id, exercise_name, sets, reps, duration_min, weight_kg, feeling, notes)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            [
                (
                    entry_id,
                    e.get("exercise_name"),
                    e.get("sets"),
                    e.get("reps"),
                    e.get("duration_min"),
                    e.get("weight_kg"),
                    e.get("feeling"),
                    e.get("notes"),
                )
                for e in exercises
            ],
        )
    return entry_id


def save_failed_entry(raw_text: str, workout_date: str) -> int:
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO workout_entries (raw_text, workout_date, parse_status) VALUES (?, ?, 'failed')",
            (raw_text, workout_date),
        )
    return cur.lastrowid


def get_exercises(
    start_date: str | None = None,
    end_date: str | None = None,
    exercise_names: list[str] | None = None,
    feelings: list[str] | None = None,
) -> list[dict]:
    conditions = []
    params = []

    if start_date:
        conditions.append("e.workout_date >= ?")
        params.append(start_date)
    if end_date:
        conditions.append("e.workout_date <= ?")
        params.append(end_date)
    if exercise_names:
        placeholders = ",".join("?" * len(exercise_names))
        conditions.append(f"x.exercise_name IN ({placeholders})")
        params.extend(exercise_names)
    if feelings:
        placeholders = ",".join("?" * len(feelings))
        conditions.append(f"x.feeling IN ({placeholders})")
        params.extend(feelings)

    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
    query = f"""
        SELECT e.workout_date, x.exercise_name, x.sets, x.reps,
               x.duration_min, x.weight_kg, x.feeling, x.notes, e.id as entry_id
        FROM workout_entries e
        JOIN exercises x ON x.entry_id = e.id
        {where}
        ORDER BY e.workout_date DESC, e.id DESC
    """
    with get_conn() as conn:
        rows = conn.execute(query, params).fetchall()
    return [dict(r) for r in rows]


def get_all_exercise_names() -> list[str]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT DISTINCT exercise_name FROM exercises ORDER BY exercise_name"
        ).fetchall()
    return [r["exercise_name"] for r in rows]


def get_all_feelings() -> list[str]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT DISTINCT feeling FROM exercises WHERE feeling IS NOT NULL ORDER BY feeling"
        ).fetchall()
    return [r["feeling"] for r in rows]
