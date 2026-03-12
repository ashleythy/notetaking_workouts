import os
import sys

import streamlit as st

# Make sure backend imports work regardless of working directory
sys.path.insert(0, os.path.dirname(__file__))

from backend.database import init_db
from backend.groq_client import _get_client

st.set_page_config(page_title="Workout Tracker", page_icon="🏋️", layout="centered")

# Verify API key on startup
try:
    _get_client()
except EnvironmentError as e:
    st.error(str(e))
    st.stop()

# Initialise database tables
init_db()

# Define pages
log_page = st.Page("pages/1_log_workout.py", title="Log Workout", icon="📝", default=True)
view_page = st.Page("pages/2_view_logs.py", title="View Logs", icon="📋")
insights_page = st.Page("pages/3_insights.py", title="Insights", icon="📊")

pg = st.navigation([log_page, view_page, insights_page])
pg.run()
