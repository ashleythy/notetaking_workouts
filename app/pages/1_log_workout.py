import sys
import os
from datetime import date

import streamlit as st
from groq import RateLimitError

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from backend import database, groq_client

st.title("Log Workout")
st.write("Type your workout in any format — e.g. *'3x10 pushups, 20 squats, felt tired'*")

with st.form("workout_form"):
    raw_text = st.text_area("What did you do?", height=150, placeholder="e.g. bench press 3x10 at 60kg, felt strong")
    date_override = st.date_input("Workout date", value=date.today())
    submitted = st.form_submit_button("Parse")

if submitted and raw_text.strip():
    with st.spinner("Parsing with Groq..."):
        today_str = date_override.strftime("%Y-%m-%d")
        try:
            parsed = groq_client.parse_workout(raw_text.strip(), today_str)
        except RateLimitError:
            st.error("Groq API rate limit hit. Wait a minute and try again.")
            st.stop()
        except ValueError as e:
            st.error(f"Could not parse response. Raw note saved.\n\n{e}")
            database.save_failed_entry(raw_text.strip(), today_str)
            st.stop()

    confidence = parsed.get("parse_confidence", "high")
    exercises = parsed.get("exercises", [])
    workout_date = parsed.get("workout_date") or today_str

    if confidence == "low" and not exercises:
        st.warning("This doesn't look like a workout note. Try being more specific.")
        st.stop()

    if confidence == "low":
        st.warning("I wasn't fully sure about some fields — please review before saving.")

    st.subheader("Parsed result")
    st.caption("Edit any values below before confirming.")

    import pandas as pd
    df = pd.DataFrame(exercises)
    # Ensure all expected columns exist
    for col in ["exercise_name", "sets", "reps", "duration_min", "weight_kg", "feeling", "notes"]:
        if col not in df.columns:
            df[col] = None

    edited_df = st.data_editor(
        df[["exercise_name", "sets", "reps", "duration_min", "weight_kg", "feeling", "notes"]],
        use_container_width=True,
        num_rows="dynamic",
        column_config={
            "exercise_name": st.column_config.TextColumn("Exercise", required=True),
            "sets": st.column_config.NumberColumn("Sets", min_value=1, step=1),
            "reps": st.column_config.NumberColumn("Reps", min_value=1, step=1),
            "duration_min": st.column_config.NumberColumn("Duration (min)", min_value=0.0, step=0.5),
            "weight_kg": st.column_config.NumberColumn("Weight (kg)", min_value=0.0, step=0.5),
            "feeling": st.column_config.SelectboxColumn(
                "Feeling", options=["tired", "sore", "strong", "easy", "hard", "okay"]
            ),
            "notes": st.column_config.TextColumn("Notes"),
        },
    )

    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("Confirm & Save", type="primary"):
            exercises_to_save = edited_df.to_dict(orient="records")
            # Remove rows with no exercise name
            exercises_to_save = [e for e in exercises_to_save if e.get("exercise_name")]
            if not exercises_to_save:
                st.error("No exercises to save. Make sure at least one row has an exercise name.")
            else:
                database.save_entry(raw_text.strip(), workout_date, exercises_to_save)
                st.success(f"Saved {len(exercises_to_save)} exercise(s) for {workout_date}!")
                st.balloons()

    with col2:
        if st.button("Discard"):
            st.rerun()

elif submitted and not raw_text.strip():
    st.warning("Please enter something before parsing.")
