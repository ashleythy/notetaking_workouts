import sqlite3
from pathlib import Path
from dataclasses import fields
from loguru import logger

from .config import DB_PATH
from .models import WorkoutEntryRaw, WorkoutEntryParsed


def get_conn() -> sqlite3.Connection:
    """Establish sqlite3 connection. """
    DB_PATH.parent.mkdir(exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """
    Create tables in db for workout_entries_raw and workout_entries_parsed. 

    Raise:
        Exception: If any database operation fails.

    Notes: 
    1. Table workout_entries_raw contains raw user-input entries and other metadata such as entry date, time etc.
    2. Table workout_entries_parsed contains the parsed entries.
    """
    try:
        with get_conn() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS workout_entries_raw (
                    entry_id      INTEGER PRIMARY KEY AUTOINCREMENT,
                    raw_text      TEXT NOT NULL,
                    workout_date  DATE NOT NULL,
                    created_at    DATETIME DEFAULT CURRENT_TIMESTAMP,
                    parse_status  TEXT DEFAULT 'ok'
                );

                CREATE TABLE IF NOT EXISTS workout_entries_parsed (
                    entry_id      INTEGER NOT NULL REFERENCES workout_entries_raw(entry_id),
                    exercise_name TEXT NOT NULL,
                    sets          INTEGER,
                    reps          INTEGER,
                    duration_min  REAL,
                    weight_kg     REAL,
                    feelings      TEXT,
                    thoughts      TEXT,
                    others        TEXT
                );
            """)
    except Exception as e: 
        logger.error(f"Failed to initialise db: {e}")
        raise


def save_entry(raw_text: str, workout_date: str, exercises: list[dict], parse_status: str = "ok") -> None:
    """
    Saves a workout entry to the database, by inserting:
    - A single raw entry into `workout_entries_raw`
    - One or more parsed exercise entries into `workout_entries_parsed`

    The parsed entries are linked to the raw entry via `entry_id`.

    The columns inserted into each table are dynamically derived from
    the corresponding dataclasses (`WorkoutEntryRaw`, `WorkoutEntryParsed`).

    Args:
        raw_text (str): Original, unstructured user input
        workout_date (str): Date of the workout (for e.g. "2025-12-12")
        exercises (list[dict]): List of parsed exercise dictionaries
            Each dict should match fields in `WorkoutEntryParsed`
        parse_status (str, optional): Status of parsing (default: "ok")

    Raises:
        Exception: If any database insert fails
    """
    logger.info("Saving entry")

    # Get variables defined in dataclasses
    # WorkoutEntryRaw
    raw_vars = [i.name for i in fields(WorkoutEntryRaw)]
    raw_vars_for_sql = ", ".join(raw_vars)
    raw_sql_placeholders = ", ".join(["?"]*len(raw_vars))

    # WorkoutEntryParsed
    parsed_vars = [i.name for i in fields(WorkoutEntryParsed)]
    parsed_vars_for_sql = ", ".join(["entry_id"] + parsed_vars)
    parsed_sql_placeholders = ", ".join(["?"]*(len(parsed_vars)+1))

    try:
        with get_conn() as conn:
            cur = conn.execute(
                f"INSERT INTO workout_entries_raw ({raw_vars_for_sql}) VALUES ({raw_sql_placeholders})",
                (raw_text, workout_date, parse_status)
            )
            entry_id = cur.lastrowid

            conn.executemany(
                f"INSERT INTO workout_entries_parsed ({parsed_vars_for_sql}) VALUES ({parsed_sql_placeholders})", 
                [(entry_id, *[e.get(var) for var in parsed_vars]) for e in exercises]
            )
        logger.debug(f"Successfully saved entry (id: {entry_id})")

    except Exception as e: 
        logger.error(f"Failed to save entry: {e}", exc_info=True)
        raise


def save_failed_entry(raw_text: str, workout_date: str) -> None:
    """
    Saves a failed workout entry to the database, by inserting:
    - A single record into `workout_entries_raw` with `parse_status` set to `"failed"`
    - It is used when parsing of an entry was unsuccessful, allowing the raw input to be
    stored for debugging or reprocessing later.

    Args:
        raw_text (str): Original, unstructured user input that failed to parse
        workout_date (str): Date of the workout

    Raises:
        Exception: If the database insert fails
    """
    logger.info("Saving failed entry")

    # Get variables defined in dataclass
    raw_vars = [i.name for i in fields(WorkoutEntryRaw)]
    raw_vars_for_sql = ", ".join(["entry_id"] + raw_vars)
    raw_sql_placeholders = ", ".join(["?"] * (len(raw_vars) + 1))

    try:
        with get_conn() as conn:
            cur = conn.execute(
                f"INSERT INTO workout_entries_raw ({raw_vars_for_sql}) VALUES ({raw_sql_placeholders})",
                (raw_text, workout_date, "failed")
            )
        logger.debug(f"Successfully saved failed entry (id: {cur.lastrowid})")

    except Exception:
        logger.error("Failed to save failed entry", exc_info=True)
        raise


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
