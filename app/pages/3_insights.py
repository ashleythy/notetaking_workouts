"""
Streamlit third page for workout insights and trends.
Shows an AI-generated summary of activity for a selected period, alongside charts for
workout frequency, volume by exercise, and progression over time.
"""

import sys
import os
from datetime import date, timedelta

import pandas as pd
import streamlit as st
from groq import RateLimitError

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from backend import database, groq_client
from utils import chart_helpers

# Page intros
st.title("Insights")

# Date selectors and automatic filters
period = st.radio("Period", ["This Week", "Last 30 Days", "All Time", "Customise"], horizontal=True)

today = date.today()

if period == "This Week":
    start_date = today - timedelta(days=today.weekday())
    end_date = today
    period_label = "this week"

if period == "Last 30 Days":
    start_date = today - timedelta(days=30)
    end_date = today
    period_label = "the last 30 days"

if period == "All time":
    start_date = date(2000, 1, 1)
    end_date = today
    period_label = "all time"

if period == "Customise":
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input("From", value=date.today() - timedelta(days=30))
    with col2:
        end_date = st.date_input("To", value=date.today())

start_str = start_date.strftime("%Y-%m-%d")
end_str = end_date.strftime("%Y-%m-%d")

rows = database.get_exercises(start_date=start_str, end_date=end_str)

if not rows:
    st.info("No workouts logged yet for the selected period.")
    st.stop()

df = pd.DataFrame(rows)

# AI summary
st.subheader("AI Summary")
if st.button("Generate Summary", type="primary"):
    with st.spinner("Generating summary with Groq..."):
        try:
            summary = groq_client.summarize_workouts(rows, period_label, start_str, end_str)
            st.markdown(summary)
        except RateLimitError:
            st.error("Groq API rate limit hit. Wait a minute and try again.")
        except EnvironmentError as e:
            st.error(str(e))

st.divider()

# Charts
st.subheader("Workout Frequency")
st.plotly_chart(chart_helpers.frequency_chart(df), use_container_width=True)

st.subheader("Total Reps By Exercise")
st.plotly_chart(chart_helpers.volume_chart(df), use_container_width=True)

st.subheader("Progression Over Time")
exercise_names = sorted(df["exercise_name"].unique().tolist())
selected = st.selectbox("Select exercise", options=exercise_names)
metric = st.selectbox("Metric", options=["weight_kg", "reps", "sets", "duration_min"],
                      format_func=lambda x: x.replace("_", " ").title())
if selected:
    st.plotly_chart(chart_helpers.progression_chart(df, selected, metric), use_container_width=True)
