from dataclasses import dataclass, field
from typing import Optional


@dataclass
class WorkoutEntryParsed:
    exercise_name: str
    sets: Optional[int] = None
    reps: Optional[int] = None
    duration_min: Optional[float] = None
    weight_kg: Optional[float] = None
    feelings: Optional[str] = None
    thoughts: Optional[str] = None
    others: Optional[str] = None


@dataclass
class WorkoutEntryRaw:
    raw_text: str
    workout_date: str
    parse_status: str = "ok"
