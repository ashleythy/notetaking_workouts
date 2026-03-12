import json
import os
import re

from dotenv import load_dotenv
from groq import Groq, RateLimitError

load_dotenv()

_client: Groq | None = None

PARSE_MODEL = "llama-3.1-70b-versatile"

PARSE_SYSTEM_PROMPT = """You are a workout log parser. Extract all exercises from the user's note.
Return ONLY a valid JSON object — no explanation, no markdown fences.

Schema:
{
  "workout_date": "YYYY-MM-DD or null if not mentioned",
  "exercises": [
    {
      "exercise_name": "string (normalised, e.g. 'push-ups' not 'pushups')",
      "sets": integer or null,
      "reps": integer or null,
      "duration_min": number or null,
      "weight_kg": number or null,
      "feeling": "string or null",
      "notes": "string or null"
    }
  ],
  "parse_confidence": "high | medium | low"
}

Rules:
- "3x10" means sets=3, reps=10
- "30 squats" means sets=null, reps=30
- Feeling words: map to one of: tired, sore, strong, easy, hard, okay — pick closest match or null
- If nothing is mentioned for a field, use null
- If workout_date is null, the caller will substitute today's date
- Return parse_confidence="low" if the input is ambiguous or unrelated to exercise
- Return parse_confidence="low" with empty exercises array if there are no exercises"""

SUMMARIZE_SYSTEM_PROMPT = """You are a friendly fitness coach reviewing a user's workout log.
Given a JSON array of workout entries for the requested period, provide:
1. A 2-3 sentence overall summary of activity volume and consistency
2. Top 3 observations (as bullet points) about trends, improvements, or gaps
3. One concrete suggestion for next week

Be encouraging but honest. Use plain language, no jargon.
Keep the response under 200 words."""


def _get_client() -> Groq:
    global _client
    if _client is None:
        api_key = os.environ.get("GROQ_API_KEY")
        if not api_key:
            raise EnvironmentError("GROQ_API_KEY not set. Add it to a .env file.")
        _client = Groq(api_key=api_key)
    return _client


def _extract_json(raw: str) -> dict:
    cleaned = re.sub(r"```json|```", "", raw).strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if match:
            return json.loads(match.group())
        raise ValueError(f"Could not extract JSON from Groq response: {raw[:200]}")


def parse_workout(text: str, today: str) -> dict:
    """
    Parse free-form workout text into structured JSON.
    Returns dict with keys: workout_date, exercises, parse_confidence.
    Raises RateLimitError, EnvironmentError, or ValueError on failure.
    """
    response = _get_client().chat.completions.create(
        model=PARSE_MODEL,
        messages=[
            {"role": "system", "content": PARSE_SYSTEM_PROMPT},
            {"role": "user", "content": f'Today\'s date is {today}. Parse this workout note:\n"{text}"'},
        ],
        temperature=0.1,
        max_tokens=512,
    )
    raw = response.choices[0].message.content
    return _extract_json(raw)


def summarize_workouts(entries: list[dict], period_label: str, start_date: str, end_date: str) -> str:
    """
    Generate a natural language summary of workout entries for a given period.
    entries: list of exercise row dicts from the database.
    Returns a plain-text summary string.
    Raises RateLimitError, EnvironmentError on failure.
    """
    entries_json = json.dumps(entries, default=str, indent=2)
    response = _get_client().chat.completions.create(
        model=PARSE_MODEL,
        messages=[
            {"role": "system", "content": SUMMARIZE_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    f"Summarise my workouts for {period_label} ({start_date} to {end_date}):\n\n"
                    f"{entries_json}"
                ),
            },
        ],
        temperature=0.7,
        max_tokens=400,
    )
    return response.choices[0].message.content.strip()
