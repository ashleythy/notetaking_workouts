# Workout Tracker

A Streamlit app for logging, reviewing, and generating insights on workouts using natural language. 

This is done by having the user input a free-text workout note. The app then uses the Groq API to parse it into structured data, which is stored in a local SQLite database, and later used for insights generation.

## Features

- **Log Workout** — submit a free-text note (e.g. *"bench press 3x10 at 60kg, felt strong"*); the app parses it into structured exercise data for review before saving
- **View Logs** — browse past entries in a filterable table by date range, exercise, and feeling; export as CSV
- **Insights** — view an AI-generated summary of activity for a selected period, alongside charts for workout frequency, volume, and progression

## Setup

1. Clone the repo and install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Create a `.env` file in the project root with your Groq API key:
   ```
   GROQ_API_KEY=your_key_here
   ```

3. Run the app:
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
│   ├── database.py         # SQLite read/write functions
│   └── groq_client.py      # Groq API calls for parsing and summarisation
└── utils/
    └── chart_helpers.py    # Plotly chart builders
```

## Requirements

- Python 3.10+
- [Groq API key](https://console.groq.com)
