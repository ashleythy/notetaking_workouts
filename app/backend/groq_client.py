import json
import os
import re
from loguru import logger

from dotenv import load_dotenv
from groq import Groq, RateLimitError

from .config import PARSE_MODEL, PARSE_SYSTEM_PROMPT, SUMMARIZE_SYSTEM_PROMPT


load_dotenv()

_client: Groq | None = None

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

    Returns:
    --------
    - dict with keys: workout_date, exercises, parse_confidence.

    Raises:
    -------
    - RateLimitError, EnvironmentError, or ValueError on failure.
    """
    response = _get_client().chat.completions.create(
        model=PARSE_MODEL,
        messages=[
            {"role": "system", "content": PARSE_SYSTEM_PROMPT},
            {"role": "user", "content": f'Today\'s date is {today}. Parse this workout note:\n"{text}"'},
        ],
        temperature=0.1,
        max_tokens=1024,
    )
    raw = response.choices[0].message.content
    logger.warning(raw)
    return _extract_json(raw)


def summarize_workouts(entries: list[dict], period_label: str, start_date: str, end_date: str) -> str:
    """
    Generate a natural language summary of workout entries for a given period.

    Args:

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
