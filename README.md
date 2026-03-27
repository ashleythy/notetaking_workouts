# Notetaking - Workouts

A Streamlit app for logging, reviewing, and generating insights on workouts using natural language.

This is done by having the user input a free-text workout note. The app then uses the Groq API to parse it into structured data, which is stored in a Supabase (PostgreSQL) database, and later used for insights generation.

## Features

- **Log Workout** — submit a free-text note (e.g. *"bench press 3x10 at 60kg, felt strong"*); the app parses it into structured exercise data for review before saving
- **View Logs** — browse past entries in a filterable table by date range, exercise, and feeling; export as CSV
- **Insights** — view an AI-generated summary of activity for a selected period, alongside charts for workout frequency, volume, and progression

## Setup

1. Clone the repo and install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Set up a [Supabase](https://supabase.com) project and get the **Transaction pooler** connection string:
   - Go to **Project Settings → Database → Connection Pooling**
   - Copy the **Transaction mode** URL (port `6543`)

3. Create a `.env` file in the project root with your credentials:
   ```bash
   GROQ_API_KEY=your_key_here
   DATABASE_URL=postgresql://postgres.[project-ref]:[password]@aws-0-[region].pooler.supabase.com:6543/postgres
   ```
   > Use the **Transaction pooler URL** (not the direct connection URL) to ensure IPv4 compatibility.

4. Set up user authentication. Generate a bcrypt-hashed password:
   ```python
   import bcrypt
   bcrypt.hashpw("your_password".encode(), bcrypt.gensalt(12)).decode()
   ```
   Then create `.streamlit/secrets.toml` (gitignored) with the following structure:
   ```toml
   [database]
   url = "your_transaction_pooler_url"

   [groq]
   api_key = "your_groq_api_key"

   # One block per user. The key (e.g. "ashley") is used as the login username and stored as user_id in the DB.
   [auth.credentials.usernames.ashley]
   name = "Ashley"
   password = "your_bcrypt_hash"

   # Auth cookie settings — used to persist login across browser sessions
   [auth.cookie]
   name = "notetaking_workouts"        # Cookie name stored in the browser
   key = "a_random_secret_string"     # Secret used to sign the cookie — keep this private
   expiry_days = 30                   # How long the login session lasts
   ```

5. Run the app:
   ```bash
   streamlit run app/app.py
   ```

## Project Structure

```
app/
├── app.py                  # Entry point — sets up pages and initialises the database
├── pages/
│   ├── 1_log_workout.py    # Log workout page
│   ├── 2_view_logs.py      # View logs page
│   └── 3_insights.py       # Insights page
├── backend/
│   ├── config.py           # Paths, model name, and system prompts
│   ├── models.py           # Dataclasses for workout entries
│   ├── database.py         # Supabase (PostgreSQL) read/write functions
│   └── groq_client.py      # Groq API calls for parsing and summarisation
└── utils/
    └── chart_helpers.py    # Plotly chart builders
```

## Requirements

- Python 3.10+
- [Groq API key](https://console.groq.com)
- [Supabase](https://supabase.com) project (free tier works; to upgrade as needed)
- `bcrypt` (included via `streamlit-authenticator`) for password hashing

## Streamlit Cloud Deployment

Add the full contents of `.streamlit/secrets.toml` via **App Settings → Secrets** in the Streamlit Cloud dashboard — same format as the local file.
