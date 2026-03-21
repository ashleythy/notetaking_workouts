import sys
import os
import pandas as pd
from datetime import date
from loguru import logger
from dataclasses import fields
import streamlit as st
from groq import RateLimitError

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from backend import database, groq_client
from backend.models import WorkoutEntryParsed


# Page intro
st.title("Log Workout")
st.write("Type your workout in any format")

# Form for submission
with st.form("workout_form"):
    raw_text = st.text_area("What did you do?", height=150, placeholder="e.g. bench press 3x10 at 60kg, felt strong. felt intimidated as the gym was crowded, sad")
    date_override = st.date_input("Workout date", value=date.today())
    submitted = st.form_submit_button("Submit & Parse")

# If something was submitted in the form
if submitted and raw_text.strip():
    logger.info(f"Entry submitted: {raw_text.strip()}")
    logger.info("Parsing entry")
    with st.spinner("Parsing entry with Groq..."):
        today_str = date_override.strftime("%Y-%m-%d")
        try:
            parsed = groq_client.parse_workout(raw_text.strip(), today_str)
            logger.debug("Successful parsing")
        except RateLimitError:
            logger.error("Error parsing entry: API RateLimitError")
            st.error("Groq API rate limit hit. Wait a minute and try again.")
            st.stop()
        except ValueError as e:
            logger.error(f"Error parsing entry: {e}")
            st.error(f"Could not parse response. Raw note saved.\n\n{e}")
            database.save_failed_entry(raw_text.strip(), today_str)
            st.stop()

    # Parse entry into variables as expected in workout.workout_entries_parsed db table
    logger.info("Checking parsed results")
    confidence = parsed.get("parse_confidence", "n/a")
    exercises = parsed.get("exercises", [])
    workout_date = parsed.get("workout_date", today_str)

    # Flag wrongly parsed entries
    # If parse_confidence is low and no exercises were found
    if confidence == "low" and not exercises:
        logger.warning("Parsed exercises don't look right")
        st.warning("This doesn't look like a workout note. Try being more specific.")
        st.stop()

    # If parse_confidence is low in general
    if confidence == "low":
        logger.warning("Low overall confidence in parsing entry")
        st.warning("I wasn't fully sure about some fields — please review before saving.")

    # Compile dataframe
    logger.info("Compiling dataframe")
    df = pd.DataFrame(exercises)
    required_cols = [f.name for f in fields(WorkoutEntryParsed)]
    missing_cols = [i for i in required_cols if i not in required_cols]
    df[missing_cols] = None

    # Persist data during webapp reruns
    st.session_state["exercise_df"] = df[required_cols].copy()
    st.session_state["workout_date"] = workout_date
    st.session_state["raw_text"] = raw_text.strip()
    st.session_state.setdefault("editor_version", 0)
    st.session_state["editor_version"] += 1

# Persisted data
if "exercise_df" in st.session_state:
    st.subheader("Parsed results")
    st.caption("Edit any values below before confirming. Select rows for deletion.")

    display_df = st.session_state["exercise_df"].copy()
    display_df.insert(0, "select", False)

    # Allow users to remove rows from the parsed table
    logger.info("Enabling dataframe editor")
    edited_df = st.data_editor(
        display_df,
        key=f"exercise_editor_{st.session_state.get('editor_version', 0)}",
        use_container_width=True,
        num_rows="dynamic",
        column_config={
            "select": st.column_config.CheckboxColumn("Select"),
            "exercise_name": st.column_config.TextColumn("Exercise", required=True),
            "sets": st.column_config.NumberColumn("Sets", min_value=1, step=1),
            "reps": st.column_config.NumberColumn("Reps", min_value=1, step=1),
            "duration_min": st.column_config.NumberColumn("Duration (min)", min_value=0.0, step=0.5),
            "weight_kg": st.column_config.NumberColumn("Weight (kg)", min_value=0.0, step=0.5),
            "feelings": st.column_config.TextColumn("Feelings", required=False),
            "thoughts": st.column_config.TextColumn("Thoughts", required=False),
            "others": st.column_config.TextColumn("Others", required=False),
        },
    )

    col1, col2, col3 = st.columns([1, 1, 1])
    with col1:
        if st.button("Delete selected row(s)", type="secondary"):
            remaining = edited_df[~edited_df["select"]].drop(columns=["select"])
            st.session_state["exercise_df"] = remaining.reset_index(drop=True)
            st.session_state["editor_version"] = st.session_state.get("editor_version", 0) + 1
            st.rerun()

    with col2:
        if st.button("Confirm & Save", type="primary"):
            exercises_to_save = edited_df.drop(columns=["select"]).to_dict(orient="records")
            # Remove rows with no exercise name
            exercises_to_save = [e for e in exercises_to_save if e.get("exercise_name")]
            if not exercises_to_save:
                logger.warning("No exercises to save")
                st.error("No exercises to save. Make sure at least one row has an extracted exercise")
            else:
                database.save_entry(st.session_state["raw_text"], st.session_state["workout_date"], exercises_to_save)
                st.success(f"Saved {len(exercises_to_save)} exercise(s) for {st.session_state['workout_date']}!")
                st.balloons()
                del st.session_state["exercise_df"]

    with col3:
        if st.button("Delete table (restart)"):
            del st.session_state["exercise_df"]
            st.rerun()

elif submitted and not raw_text.strip():
    st.warning("Please enter something before parsing.")
