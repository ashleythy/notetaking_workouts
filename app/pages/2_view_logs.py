import sys
import os
from datetime import date, timedelta

import pandas as pd
import streamlit as st

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from backend import database

st.title("View Logs")

# --- Filters ---
col1, col2 = st.columns(2)
with col1:
    start_date = st.date_input("From", value=date.today() - timedelta(days=30))
with col2:
    end_date = st.date_input("To", value=date.today())

all_exercises = database.get_all_exercise_names()
all_feelings = database.get_all_feelings()

col3, col4 = st.columns(2)
with col3:
    selected_exercises = st.multiselect("Exercise", options=all_exercises, placeholder="All exercises")
with col4:
    selected_feelings = st.multiselect("Feeling", options=all_feelings, placeholder="All feelings")

# --- Data ---
rows = database.get_exercises(
    start_date=start_date.strftime("%Y-%m-%d"),
    end_date=end_date.strftime("%Y-%m-%d"),
    exercise_names=selected_exercises or None,
    feelings=selected_feelings or None,
)

if not rows:
    st.info("No workouts logged yet for the selected filters.")
    st.stop()

df = pd.DataFrame(rows)
df = df.drop(columns=["entry_id"])
df = df.rename(columns={
    "workout_date": "Date",
    "exercise_name": "Exercise",
    "sets": "Sets",
    "reps": "Reps",
    "duration_min": "Duration (min)",
    "weight_kg": "Weight (kg)",
    "feeling": "Feeling",
    "notes": "Notes",
})

st.dataframe(df, use_container_width=True, hide_index=True)
st.caption(f"{len(df)} row(s) shown")

# --- CSV Download ---
csv = df.to_csv(index=False).encode("utf-8")
st.download_button(
    label="Download as CSV",
    data=csv,
    file_name=f"workouts_{start_date}_{end_date}.csv",
    mime="text/csv",
)
