from typing import Optional
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
    Saves a failed workout entry to the database, by inserting a single record 
    into `workout_entries_raw` with `parse_status` set to `"failed"`.

    It is used when parsing of an entry was unsuccessful, allowing the raw input to be
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


# Below are functions to get respective data from the database
def get_exercises(
    start_date: Optional[str],
    end_date: Optional[str],
    exercise_names: Optional[list[str]],
    feelings: Optional[list[str]]
) -> list[dict]:
    """
    Retrieves parsed entries from the database with optional filters. 
    Filters include date range, exercise names, feelings, and thoughts. 

    Returns:
        list[dict]: List of exercise records.
    """
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
        conditions.append(f"x.feelings IN ({placeholders})")
        params.extend(feelings)

    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
    query = f"""
        SELECT 
            e.entry_id,
            e.workout_date, 
            x.exercise_name, 
            x.sets, 
            x.reps,
            x.duration_min,
            x.weight_kg, 
            x.feelings,
            x.thoughts, 
            x.others
        FROM workout_entries_raw e
        JOIN workout_entries_parsed x 
        ON x.entry_id = e.entry_id
        {where}
        ORDER BY e.workout_date DESC, e.entry_id DESC
    """
    with get_conn() as conn:
        rows = conn.execute(query, params).fetchall()
    return [dict(r) for r in rows]


def get_all_exercise_names() -> list[str]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT DISTINCT exercise_name FROM workout_entries_parsed ORDER BY exercise_name"
        ).fetchall()
    return [r["exercise_name"] for r in rows]


def get_all_feelings() -> list[str]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT DISTINCT feelings FROM workout_entries_parsed WHERE feelings IS NOT NULL ORDER BY feelings"
        ).fetchall()
    return [r["feelings"] for r in rows]
