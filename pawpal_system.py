"""PawPal+ logic layer: class skeletons generated from diagrams/uml_draft.mmd.

Every method is a stub (raises NotImplementedError). Fill them in one class at a time.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, time
from enum import Enum
from typing import Optional


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class Priority(Enum):
    LOW = 1
    MEDIUM = 2
    HIGH = 3


class Category(Enum):
    FEEDING = "feeding"
    WALK = "walk"
    MEDICATION = "medication"
    GROOMING = "grooming"
    ENRICHMENT = "enrichment"
    APPOINTMENT = "appointment"


class Frequency(Enum):
    ONCE = "once"
    DAILY = "daily"
    WEEKLY = "weekly"


class TimePreference(Enum):
    MORNING = "morning"
    AFTERNOON = "afternoon"
    EVENING = "evening"
    ANYTIME = "anytime"


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class Task:
    """A single pet care activity."""
    id: int
    description: str
    due_time: datetime
    duration_minutes: int
    category: Category = Category.FEEDING
    priority: Priority = Priority.MEDIUM
    frequency: Frequency = Frequency.ONCE
    preferred_time: TimePreference = TimePreference.ANYTIME
    must_do: bool = False
    is_complete: bool = False
    completion_history: list[datetime] = field(default_factory=list)
    pet_name: str = ""

    def end_time(self) -> datetime:
        """Return due_time plus duration_minutes."""
        raise NotImplementedError

    def overlaps_with(self, other: Task) -> bool:
        """Return True if this task's time window overlaps the other's."""
        raise NotImplementedError

    def is_overdue(self, now: datetime) -> bool:
        """Return True if the task is incomplete and its due time has passed."""
        raise NotImplementedError

    def mark_complete(self, when: Optional[datetime] = None) -> Optional[Task]:
        """Mark done, log the time, and return the next occurrence if recurring (else None)."""
        raise NotImplementedError

    def next_occurrence(self) -> Optional[Task]:
        """Return a new Task for the next day/week, or None if frequency is ONCE."""
        raise NotImplementedError

    def last_completed(self) -> Optional[datetime]:
        """Return the most recent completion time, or None."""
        raise NotImplementedError

    def to_dict(self) -> dict:
        """Return a JSON-friendly dict of this task."""
        raise NotImplementedError


@dataclass
class Pet:
    """One animal and the tasks that belong to it."""
    name: str
    species: str
    age: int
    weight_lbs: float = 0.0
    notes: str = ""
    tasks: list[Task] = field(default_factory=list)

    def add_task(self, task: Task) -> None:
        """Attach a task to this pet (set task.pet_name)."""
        raise NotImplementedError

    def remove_task(self, task_id: int) -> None:
        """Remove the task with the given id."""
        raise NotImplementedError

    def get_tasks(self, pending_only: bool = False) -> list[Task]:
        """Return all tasks, or only incomplete ones."""
        raise NotImplementedError

    def update_weight(self, new_weight: float) -> None:
        """Update weight_lbs."""
        raise NotImplementedError

    def to_dict(self) -> dict:
        """Return a JSON-friendly dict of this pet and its tasks."""
        raise NotImplementedError


@dataclass
class TimeBlock:
    """A recurring stretch of time when the owner is busy (e.g. work)."""
    label: str
    days: list[str]
    start: time
    end: time

    def overlaps_with(self, start: datetime, end: datetime) -> bool:
        """Return True if the given window overlaps this block on a matching weekday."""
        raise NotImplementedError


@dataclass
class SupplyItem:
    """Something bought on a cycle (food, litter, flea medication, ...)."""
    id: int
    name: str
    restock_every_days: int
    last_purchased: date
    pet_name: str = ""          # empty means a shared household item
    remind_days_before: int = 3
    notes: str = ""

    def next_due_date(self) -> date:
        """Return last_purchased plus restock_every_days."""
        raise NotImplementedError

    def is_due(self, today: date) -> bool:
        """Return True if today is within the reminder window of next_due_date()."""
        raise NotImplementedError

    def mark_purchased(self, on_date: Optional[date] = None) -> None:
        """Reset the cycle by setting last_purchased."""
        raise NotImplementedError


@dataclass
class Owner:
    """The person: holds pets, busy time, and supply reminders."""
    name: str
    available_minutes: int = 120
    pets: list[Pet] = field(default_factory=list)
    busy_blocks: list[TimeBlock] = field(default_factory=list)
    supplies: list[SupplyItem] = field(default_factory=list)

    def add_pet(self, pet: Pet) -> None:
        raise NotImplementedError

    def remove_pet(self, name: str) -> None:
        raise NotImplementedError

    def get_pet(self, name: str) -> Optional[Pet]:
        raise NotImplementedError

    def add_busy_block(self, block: TimeBlock) -> None:
        raise NotImplementedError

    def add_supply(self, item: SupplyItem) -> None:
        raise NotImplementedError

    def remove_supply(self, item_id: int) -> None:
        raise NotImplementedError

    def save_to_json(self, path: str) -> None:
        """Write the owner, pets, tasks, blocks, and supplies to a JSON file."""
        raise NotImplementedError

    @staticmethod
    def load_from_json(path: str) -> Owner:
        """Rebuild an Owner from a JSON file."""
        raise NotImplementedError


@dataclass
class Conflict:
    """A scheduling clash: task vs task, or task vs owner busy time."""
    task_a: Task
    message: str
    task_b: Optional[Task] = None
    busy_block: Optional[TimeBlock] = None


@dataclass
class ScheduledItem:
    """A task placed in the plan, plus the reason it was placed there."""
    task: Task
    reason: str


@dataclass
class DailyPlan:
    """The scheduler's output for one day."""
    day: date
    items: list[ScheduledItem] = field(default_factory=list)
    skipped: list[Task] = field(default_factory=list)
    overdue: list[Task] = field(default_factory=list)
    reminders: list[SupplyItem] = field(default_factory=list)

    def total_minutes(self) -> int:
        """Sum the duration of all scheduled items."""
        raise NotImplementedError

    def summary(self) -> str:
        """Return a readable text version of the plan, with reasons."""
        raise NotImplementedError


# ---------------------------------------------------------------------------
# Scheduler (the "brain": works across all of the owner's pets)
# ---------------------------------------------------------------------------

class Scheduler:
    def __init__(self, owner: Owner) -> None:
        self.owner = owner

    def get_all_tasks(self) -> list[Task]:
        """Flatten every pet's tasks into one list."""
        raise NotImplementedError

    def sort_by_time(self, tasks: list[Task]) -> list[Task]:
        raise NotImplementedError

    def sort_by_priority(self, tasks: list[Task]) -> list[Task]:
        raise NotImplementedError

    def filter_tasks(
        self,
        pet_name: Optional[str] = None,
        category: Optional[Category] = None,
        status: Optional[str] = None,   # "pending" or "complete"
    ) -> list[Task]:
        raise NotImplementedError

    def detect_conflicts(self) -> list[Conflict]:
        """Find overlapping tasks and tasks that land in owner busy blocks."""
        raise NotImplementedError

    def get_overdue_tasks(self, now: datetime) -> list[Task]:
        raise NotImplementedError

    def complete_task(self, task_id: int) -> None:
        """Complete a task and add the next occurrence to its pet if recurring."""
        raise NotImplementedError

    def get_due_reminders(self, today: date) -> list[SupplyItem]:
        raise NotImplementedError

    def build_daily_plan(self, day: date) -> DailyPlan:
        """Pick and order the day's tasks within available_minutes, with reasons."""
        raise NotImplementedError
