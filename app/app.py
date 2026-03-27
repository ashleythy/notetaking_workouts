import os
import sys

import streamlit as st
import streamlit_authenticator as stauth

sys.path.insert(0, os.path.dirname(__file__))

from backend.database import init_db
from backend.groq_client import _get_client

st.set_page_config(page_title="Notetaking - Workouts", page_icon="🏋️", layout="centered")

# Authentication
credentials = {
    "usernames": {
        username: dict(data)
        for username, data in st.secrets["auth"]["credentials"]["usernames"].items()
    }
}
authenticator = stauth.Authenticate(
    credentials,
    st.secrets["auth"]["cookie"]["name"],
    st.secrets["auth"]["cookie"]["key"],
    st.secrets["auth"]["cookie"]["expiry_days"],
)
authenticator.login()

if st.session_state["authentication_status"] is False:
    st.error("Username or password is incorrect.")
    st.stop()
elif st.session_state["authentication_status"] is None:
    st.info("Please log in to continue.")
    st.stop()

# Authenticated — store username as user_id for the session
st.session_state["user_id"] = st.session_state["username"]
st.sidebar.markdown(f"👋 Welcome, **{st.session_state['name']}**")
authenticator.logout(location="sidebar")

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
