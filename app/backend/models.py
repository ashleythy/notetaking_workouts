from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Exercise:
    exercise_name: str
    sets: Optional[int] = None
    reps: Optional[int] = None
    duration_min: Optional[float] = None
    weight_kg: Optional[float] = None
    feeling: Optional[str] = None
    notes: Optional[str] = None


@dataclass
class WorkoutEntry:
    raw_text: str
    workout_date: str
    exercises: list[Exercise] = field(default_factory=list)
    parse_status: str = "ok"
