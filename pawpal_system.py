"""PawPal+ logic layer: Task, Pet, Owner, Scheduler (plus small helper classes).

Implemented in this phase: all scheduling logic.
Still stubbed for a later phase: JSON persistence (to_dict / save_to_json / load_from_json).
"""

from __future__ import annotations

import itertools
from dataclasses import dataclass, field, replace
from datetime import date, datetime, time, timedelta
from enum import Enum
from typing import Optional

# Shared id counters so every Task / SupplyItem gets a unique id automatically.
_task_ids = itertools.count(1)
_supply_ids = itertools.count(1)

_DAY_KEYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]


def _day_key(name: str) -> str:
    """'Monday', 'mon', 'MON' -> 'mon'."""
    return name.strip().lower()[:3]


def _time_of_day(moment: datetime) -> "TimePreference":
    """Bucket a datetime into MORNING / AFTERNOON / EVENING."""
    if moment.hour < 12:
        return TimePreference.MORNING
    if moment.hour < 17:
        return TimePreference.AFTERNOON
    return TimePreference.EVENING


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
# Task
# ---------------------------------------------------------------------------

@dataclass
class Task:
    """A single pet care activity."""
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
    id: int = field(default_factory=lambda: next(_task_ids))

    def __post_init__(self) -> None:
        if self.duration_minutes <= 0:
            raise ValueError("duration_minutes must be positive")

    def end_time(self) -> datetime:
        """Return due_time plus duration_minutes."""
        return self.due_time + timedelta(minutes=self.duration_minutes)

    def overlaps_with(self, other: Task) -> bool:
        """True if the two time windows overlap (back-to-back tasks do not)."""
        return self.due_time < other.end_time() and other.due_time < self.end_time()

    def is_overdue(self, now: datetime) -> bool:
        """True if the task is incomplete and its due time has passed."""
        return (not self.is_complete) and self.due_time < now

    def mark_complete(self, when: Optional[datetime] = None) -> Optional[Task]:
        """Mark done, log the time, and return the next occurrence (None if one-time)."""
        self.is_complete = True
        self.completion_history.append(when or datetime.now())
        return self.next_occurrence()

    def next_occurrence(self) -> Optional[Task]:
        """A fresh copy of this task one day/week later, or None if frequency is ONCE."""
        if self.frequency == Frequency.DAILY:
            step = timedelta(days=1)
        elif self.frequency == Frequency.WEEKLY:
            step = timedelta(days=7)
        else:
            return None
        return replace(
            self,
            due_time=self.due_time + step,
            is_complete=False,
            completion_history=[],
            id=next(_task_ids),
        )

    def last_completed(self) -> Optional[datetime]:
        """Most recent completion time, or None."""
        return max(self.completion_history) if self.completion_history else None

    def to_dict(self) -> dict:
        raise NotImplementedError("JSON persistence comes in a later phase")


# ---------------------------------------------------------------------------
# Pet
# ---------------------------------------------------------------------------

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
        """Attach a task to this pet."""
        task.pet_name = self.name
        self.tasks.append(task)

    def remove_task(self, task_id: int) -> None:
        """Remove the task with this id (does nothing if it isn't here)."""
        self.tasks = [t for t in self.tasks if t.id != task_id]

    def get_tasks(self, pending_only: bool = False) -> list[Task]:
        """All tasks, or only incomplete ones. Returns a new list."""
        if pending_only:
            return [t for t in self.tasks if not t.is_complete]
        return list(self.tasks)

    def update_weight(self, new_weight: float) -> None:
        if new_weight <= 0:
            raise ValueError("weight must be positive")
        self.weight_lbs = new_weight

    def to_dict(self) -> dict:
        raise NotImplementedError("JSON persistence comes in a later phase")


# ---------------------------------------------------------------------------
# Owner helpers
# ---------------------------------------------------------------------------

@dataclass
class TimeBlock:
    """A recurring stretch of time when the owner is busy (e.g. work)."""
    label: str
    days: list[str]          # e.g. ["Mon", "Tue", "Wed"]
    start: time
    end: time

    def overlaps_with(self, start: datetime, end: datetime) -> bool:
        """True if [start, end) overlaps this block on any matching weekday."""
        wanted = {_day_key(d) for d in self.days}
        current = start.date()
        while current <= end.date():
            if _DAY_KEYS[current.weekday()] in wanted:
                block_start = datetime.combine(current, self.start)
                block_end = datetime.combine(current, self.end)
                if start < block_end and block_start < end:
                    return True
            current += timedelta(days=1)
        return False


@dataclass
class SupplyItem:
    """Something bought on a cycle (food, litter, flea medication, ...)."""
    name: str
    restock_every_days: int
    last_purchased: date
    pet_name: str = ""            # empty = shared household item
    remind_days_before: int = 3
    notes: str = ""
    id: int = field(default_factory=lambda: next(_supply_ids))

    def next_due_date(self) -> date:
        return self.last_purchased + timedelta(days=self.restock_every_days)

    def is_due(self, today: date) -> bool:
        """True once today is inside the reminder window (or past due)."""
        return today >= self.next_due_date() - timedelta(days=self.remind_days_before)

    def mark_purchased(self, on_date: Optional[date] = None) -> None:
        self.last_purchased = on_date or date.today()


# ---------------------------------------------------------------------------
# Owner
# ---------------------------------------------------------------------------

@dataclass
class Owner:
    """The person: holds pets, busy time, and supply reminders."""
    name: str
    available_minutes: int = 120
    pets: list[Pet] = field(default_factory=list)
    busy_blocks: list[TimeBlock] = field(default_factory=list)
    supplies: list[SupplyItem] = field(default_factory=list)

    def add_pet(self, pet: Pet) -> None:
        if self.get_pet(pet.name) is not None:
            raise ValueError(f"A pet named '{pet.name}' already exists")
        self.pets.append(pet)

    def remove_pet(self, name: str) -> None:
        self.pets = [p for p in self.pets if p.name.lower() != name.lower()]

    def get_pet(self, name: str) -> Optional[Pet]:
        """Case-insensitive lookup; None if not found."""
        for pet in self.pets:
            if pet.name.lower() == name.lower():
                return pet
        return None

    def get_all_tasks(self) -> list[Task]:
        """Every task from every pet, together in one list."""
        return [task for pet in self.pets for task in pet.tasks]

    def add_busy_block(self, block: TimeBlock) -> None:
        self.busy_blocks.append(block)

    def add_supply(self, item: SupplyItem) -> None:
        self.supplies.append(item)

    def remove_supply(self, item_id: int) -> None:
        self.supplies = [s for s in self.supplies if s.id != item_id]

    def save_to_json(self, path: str) -> None:
        raise NotImplementedError("JSON persistence comes in a later phase")

    @staticmethod
    def load_from_json(path: str) -> Owner:
        raise NotImplementedError("JSON persistence comes in a later phase")


# ---------------------------------------------------------------------------
# Scheduler output types
# ---------------------------------------------------------------------------

@dataclass
class Conflict:
    """A clash: task vs task, or task vs owner busy time."""
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
        return sum(item.task.duration_minutes for item in self.items)

    def summary(self) -> str:
        """Readable text version of the plan, with the reason for each item."""
        lines = [f"Daily plan for {self.day:%A, %b %d, %Y} ({self.total_minutes()} min scheduled)"]
        if not self.items:
            lines.append("  Nothing scheduled.")
        for item in self.items:
            t = item.task
            lines.append(
                f"  {t.due_time:%H:%M}-{t.end_time():%H:%M}  {t.pet_name}: {t.description}"
                f"  [{t.priority.name}]"
            )
            lines.append(f"      why: {item.reason}")
        if self.skipped:
            lines.append("Skipped (not enough available time):")
            for t in self.skipped:
                lines.append(f"  {t.pet_name}: {t.description} ({t.duration_minutes} min)")
        if self.overdue:
            lines.append("Overdue from earlier days:")
            for t in self.overdue:
                lines.append(f"  {t.pet_name}: {t.description} (was due {t.due_time:%b %d %H:%M})")
        if self.reminders:
            lines.append("Supply reminders:")
            for s in self.reminders:
                who = f" for {s.pet_name}" if s.pet_name else ""
                lines.append(f"  Buy {s.name}{who} (due {s.next_due_date():%b %d})")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Scheduler (the "brain": always reads through Owner.get_all_tasks)
# ---------------------------------------------------------------------------

class Scheduler:
    def __init__(self, owner: Owner) -> None:
        self.owner = owner

    # -- sorting ------------------------------------------------------------

    def sort_by_time(self, tasks: list[Task]) -> list[Task]:
        """Earliest first; ties broken by higher priority."""
        return sorted(tasks, key=lambda t: (t.due_time, -t.priority.value))

    def sort_by_priority(self, tasks: list[Task]) -> list[Task]:
        """Highest priority first; ties broken by earliest time."""
        return sorted(tasks, key=lambda t: (-t.priority.value, t.due_time))

    # -- filtering ----------------------------------------------------------

    def filter_tasks(
        self,
        pet_name: Optional[str] = None,
        category: Optional[Category] = None,
        status: Optional[str] = None,      # "pending" or "complete"
    ) -> list[Task]:
        """Filter tasks across ALL pets. Any argument left as None is ignored."""
        if status not in (None, "pending", "complete"):
            raise ValueError("status must be 'pending', 'complete', or None")
        results = self.owner.get_all_tasks()
        if pet_name is not None:
            results = [t for t in results if t.pet_name.lower() == pet_name.lower()]
        if category is not None:
            results = [t for t in results if t.category == category]
        if status == "pending":
            results = [t for t in results if not t.is_complete]
        elif status == "complete":
            results = [t for t in results if t.is_complete]
        return results

    # -- conflicts ----------------------------------------------------------

    def detect_conflicts(self) -> list[Conflict]:
        """Overlapping pending tasks (any pets) and tasks inside owner busy blocks.

        The owner can't do two things at once, so tasks for DIFFERENT pets
        conflict too.
        """
        pending = self.sort_by_time([t for t in self.owner.get_all_tasks() if not t.is_complete])
        conflicts: list[Conflict] = []

        for a, b in itertools.combinations(pending, 2):
            if a.overlaps_with(b):
                conflicts.append(Conflict(
                    task_a=a,
                    task_b=b,
                    message=(
                        f"{a.pet_name}: '{a.description}' ({a.due_time:%b %d %H:%M}-{a.end_time():%H:%M}) "
                        f"overlaps {b.pet_name}: '{b.description}' "
                        f"({b.due_time:%H:%M}-{b.end_time():%H:%M})"
                    ),
                ))

        for task in pending:
            for block in self.owner.busy_blocks:
                if block.overlaps_with(task.due_time, task.end_time()):
                    conflicts.append(Conflict(
                        task_a=task,
                        busy_block=block,
                        message=(
                            f"{task.pet_name}: '{task.description}' ({task.due_time:%b %d %H:%M}) "
                            f"falls during your '{block.label}' time"
                        ),
                    ))
        return conflicts

    # -- overdue / completion / reminders -----------------------------------

    def get_overdue_tasks(self, now: datetime) -> list[Task]:
        return self.sort_by_time([t for t in self.owner.get_all_tasks() if t.is_overdue(now)])

    def complete_task(self, task_id: int, when: Optional[datetime] = None) -> Optional[Task]:
        """Complete a task; if it recurs, add the next occurrence to the same pet.

        Returns the new task (or None for one-time tasks).
        """
        for task in self.owner.get_all_tasks():
            if task.id == task_id:
                next_task = task.mark_complete(when)
                if next_task is not None:
                    pet = self.owner.get_pet(task.pet_name)
                    if pet is not None:
                        pet.add_task(next_task)
                return next_task
        raise ValueError(f"No task with id {task_id}")

    def get_due_reminders(self, today: date) -> list[SupplyItem]:
        due = [s for s in self.owner.supplies if s.is_due(today)]
        return sorted(due, key=lambda s: s.next_due_date())

    # -- the daily plan -----------------------------------------------------

    def build_daily_plan(self, day: date) -> DailyPlan:
        """Choose and order the day's tasks, within the owner's available minutes.

        1. Must-do tasks are always included (even if they exceed the budget).
        2. Remaining tasks are added highest priority first while time remains.
        3. Whatever doesn't fit goes in `skipped`.
        4. Chosen tasks are shown in time order, each with a plain-English reason.
        """
        pending = [t for t in self.owner.get_all_tasks() if not t.is_complete]
        todays = [t for t in pending if t.due_time.date() == day]

        chosen: list[Task] = [t for t in todays if t.must_do]
        used = sum(t.duration_minutes for t in chosen)
        skipped: list[Task] = []

        optional = self.sort_by_priority([t for t in todays if not t.must_do])
        for task in optional:
            if used + task.duration_minutes <= self.owner.available_minutes:
                chosen.append(task)
                used += task.duration_minutes
            else:
                skipped.append(task)

        items = [ScheduledItem(t, self._explain(t)) for t in self.sort_by_time(chosen)]
        return DailyPlan(
            day=day,
            items=items,
            skipped=self.sort_by_time(skipped),
            overdue=self.get_overdue_tasks(datetime.combine(day, time.min)),
            reminders=self.get_due_reminders(day),
        )

    def _explain(self, task: Task) -> str:
        """Build the plain-English reason a task was scheduled."""
        parts = ["must-do task, always included" if task.must_do
                 else f"{task.priority.name.lower()} priority and fits your available time"]
        if task.preferred_time != TimePreference.ANYTIME:
            if _time_of_day(task.due_time) == task.preferred_time:
                parts.append(f"matches the {task.preferred_time.value} preference")
            else:
                parts.append(f"outside the preferred {task.preferred_time.value} window")
        for block in self.owner.busy_blocks:
            if block.overlaps_with(task.due_time, task.end_time()):
                parts.append(f"heads-up: falls during '{block.label}'")
        if task.frequency != Frequency.ONCE:
            parts.append(f"repeats {task.frequency.value}")
        text = "; ".join(parts)
        return text[0].upper() + text[1:]
