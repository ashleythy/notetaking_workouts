"""
Database access layer using Supabase (PostgreSQL).

Connection URL is read from:
- Streamlit Cloud: st.secrets["database"]["url"]
- Local dev: DATABASE_URL in .env
"""

from typing import Optional
from dataclasses import fields
from loguru import logger
import math
import os

import psycopg2
import psycopg2.extras
import streamlit as st
from dotenv import load_dotenv

from .models import WorkoutEntryRaw, WorkoutEntryParsed

load_dotenv()


def _get_db_url() -> str:
    try:
        return st.secrets["database"]["url"]
    except Exception:
        url = os.environ.get("DATABASE_URL")
        if not url:
            raise EnvironmentError("DATABASE_URL not set. Add it to .env (local) or Streamlit secrets (cloud).")
        return url


def get_conn():
    """Establish a PostgreSQL connection with dict-like row results."""
    return psycopg2.connect(_get_db_url(), cursor_factory=psycopg2.extras.RealDictCursor)


def init_db():
    """
    Create tables in db for workout_entries_raw and workout_entries_parsed.

    Raise:
        Exception: If any database operation fails.
    """
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS workout_entries_raw (
                    entry_id      SERIAL PRIMARY KEY,
                    raw_text      TEXT NOT NULL,
                    workout_date  DATE NOT NULL,
                    created_at    TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
                    parse_status  TEXT DEFAULT 'ok',
                    user_id       VARCHAR
                )
            """)
            cur.execute("""
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
                )
            """)
            # Add user_id to existing tables if not present
            cur.execute("ALTER TABLE workout_entries_raw ADD COLUMN IF NOT EXISTS user_id VARCHAR")
        conn.commit()
    except Exception as e:
        conn.rollback()
        logger.error(f"Failed to initialise db: {e}")
        raise
    finally:
        conn.close()


def save_entry(raw_text: str, workout_date: str, exercises: list[dict], user_id: str, parse_status: str = "ok") -> None:
    """
    Saves a workout entry to the database, by inserting:
    - A single raw entry into `workout_entries_raw`
    - One or more parsed exercise entries into `workout_entries_parsed`

    The parsed entries are linked to the raw entry via `entry_id`.

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

    def _clean(val):
        """Convert NaN/inf floats (from pandas empty cells) to None for PostgreSQL."""
        if isinstance(val, float) and (math.isnan(val) or math.isinf(val)):
            return None
        return val

    parsed_vars = [f.name for f in fields(WorkoutEntryParsed)]
    parsed_cols = ", ".join(["entry_id"] + parsed_vars)
    parsed_placeholders = ", ".join(["%s"] * (len(parsed_vars) + 1))

    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO workout_entries_raw (raw_text, workout_date, parse_status, user_id) VALUES (%s, %s, %s, %s) RETURNING entry_id",
                (raw_text, workout_date, parse_status, user_id),
            )
            entry_id = cur.fetchone()["entry_id"]

            cur.executemany(
                f"INSERT INTO workout_entries_parsed ({parsed_cols}) VALUES ({parsed_placeholders})",
                [(entry_id, *[_clean(e.get(var)) for var in parsed_vars]) for e in exercises],
            )
        conn.commit()
        logger.debug(f"Successfully saved entry (id: {entry_id})")
    except Exception as e:
        conn.rollback()
        logger.error(f"Failed to save entry: {e}", exc_info=True)
        raise
    finally:
        conn.close()


def save_failed_entry(raw_text: str, workout_date: str, user_id: str) -> None:
    """
    Saves a failed workout entry to `workout_entries_raw` with parse_status='failed'.

    Args:
        raw_text (str): Original, unstructured user input that failed to parse
        workout_date (str): Date of the workout

    Raises:
        Exception: If the database insert fails
    """
    logger.info("Saving failed entry")
    entry = WorkoutEntryRaw(raw_text=raw_text, workout_date=workout_date, parse_status="failed")
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO workout_entries_raw (raw_text, workout_date, parse_status, user_id) VALUES (%s, %s, %s, %s)",
                (entry.raw_text, entry.workout_date, entry.parse_status, user_id),
            )
        conn.commit()
        logger.debug("Successfully saved failed entry")
    except Exception as e:
        conn.rollback()
        logger.error(f"Failed to save failed entry: {e}", exc_info=True)
        raise
    finally:
        conn.close()


def get_exercises(
    start_date: Optional[str],
    end_date: Optional[str],
    user_id: str = None,
    exercise_names: Optional[list[str]] = None,
    feelings: Optional[list[str]] = None,
) -> list[dict]:
    """
    Retrieves parsed entries from the database with optional filters.

    Returns:
        list[dict]: List of exercise records.
    """
    conditions = []
    params = []

    if user_id:
        conditions.append("e.user_id = %s")
        params.append(user_id)
    if start_date:
        conditions.append("e.workout_date >= %s")
        params.append(start_date)
    if end_date:
        conditions.append("e.workout_date <= %s")
        params.append(end_date)
    if exercise_names:
        conditions.append("x.exercise_name = ANY(%s)")
        params.append(exercise_names)
    if feelings:
        conditions.append("x.feelings = ANY(%s)")
        params.append(feelings)

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
        JOIN workout_entries_parsed x ON x.entry_id = e.entry_id
        {where}
        ORDER BY e.workout_date DESC, e.entry_id DESC
    """
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(query, params)
            rows = cur.fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_all_exercise_names(user_id: str = None) -> list[str]:
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            if user_id:
                cur.execute(
                    "SELECT DISTINCT x.exercise_name FROM workout_entries_parsed x JOIN workout_entries_raw e ON e.entry_id = x.entry_id WHERE e.user_id = %s ORDER BY x.exercise_name",
                    (user_id,),
                )
            else:
                cur.execute("SELECT DISTINCT exercise_name FROM workout_entries_parsed ORDER BY exercise_name")
            return [r["exercise_name"] for r in cur.fetchall()]
    finally:
        conn.close()


def get_all_feelings(user_id: str = None) -> list[str]:
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            if user_id:
                cur.execute(
                    "SELECT DISTINCT x.feelings FROM workout_entries_parsed x JOIN workout_entries_raw e ON e.entry_id = x.entry_id WHERE x.feelings IS NOT NULL AND e.user_id = %s ORDER BY x.feelings",
                    (user_id,),
                )
            else:
                cur.execute("SELECT DISTINCT feelings FROM workout_entries_parsed WHERE feelings IS NOT NULL ORDER BY feelings")
            return [r["feelings"] for r in cur.fetchall()]
    finally:
        conn.close()
