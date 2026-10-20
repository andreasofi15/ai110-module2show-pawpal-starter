"""Automated tests for the PawPal+ logic layer (pawpal_system.py).

Run from the repo root with:  python -m pytest
"""

from datetime import date, datetime, time, timedelta

import pytest

from pawpal_system import (
    Category, Frequency, Owner, Pet, Priority, Scheduler, SupplyItem, Task, TimeBlock,
)

DAY = date(2026, 10, 20)   # a fixed Tuesday, so tests never depend on today's date


def at(hour, minute=0, day=DAY):
    """Shortcut for a datetime on the given day."""
    return datetime.combine(day, time(hour, minute))


@pytest.fixture
def owner():
    """An owner with two pets and 60 free minutes."""
    o = Owner(name="Sam", available_minutes=60)
    o.add_pet(Pet(name="Buddy", species="dog", age=3))
    o.add_pet(Pet(name="Luna", species="cat", age=5))
    return o


@pytest.fixture
def scheduler(owner):
    return Scheduler(owner)


# ----------------------------------------------------------------- sorting

def test_sort_by_time_orders_tasks_chronologically_across_pets(owner, scheduler):
    owner.get_pet("Buddy").add_task(Task("Evening walk", at(18), 30))
    owner.get_pet("Luna").add_task(Task("Pill", at(8, 15), 5))
    owner.get_pet("Buddy").add_task(Task("Breakfast", at(7, 30), 10))

    ordered = scheduler.sort_by_time(owner.get_all_tasks())

    assert [t.description for t in ordered] == ["Breakfast", "Pill", "Evening walk"]


def test_sort_by_time_puts_earlier_dates_first(owner, scheduler):
    owner.get_pet("Buddy").add_task(Task("Tomorrow 7am", at(7, day=DAY + timedelta(days=1)), 10))
    owner.get_pet("Buddy").add_task(Task("Today 9pm", at(21), 10))

    ordered = scheduler.sort_by_time(owner.get_all_tasks())

    assert [t.description for t in ordered] == ["Today 9pm", "Tomorrow 7am"]


def test_sort_by_time_breaks_ties_by_priority(owner, scheduler):
    owner.get_pet("Buddy").add_task(Task("Low", at(8), 10, priority=Priority.LOW))
    owner.get_pet("Luna").add_task(Task("High", at(8), 10, priority=Priority.HIGH))

    ordered = scheduler.sort_by_time(owner.get_all_tasks())

    assert [t.description for t in ordered] == ["High", "Low"]


def test_sort_by_priority_puts_high_first(owner, scheduler):
    owner.get_pet("Buddy").add_task(Task("Low", at(7), 10, priority=Priority.LOW))
    owner.get_pet("Buddy").add_task(Task("High", at(9), 10, priority=Priority.HIGH))
    owner.get_pet("Luna").add_task(Task("Medium", at(8), 10, priority=Priority.MEDIUM))

    ordered = scheduler.sort_by_priority(owner.get_all_tasks())

    assert [t.description for t in ordered] == ["High", "Medium", "Low"]


def test_sorting_with_no_tasks_returns_empty_list(owner, scheduler):
    assert scheduler.sort_by_time(owner.get_all_tasks()) == []


# --------------------------------------------------------------- recurrence

def test_daily_task_creates_next_task_for_the_following_day():
    walk = Task("Walk", at(8), 30, frequency=Frequency.DAILY)

    next_walk = walk.mark_complete(at(8, 40))

    assert walk.is_complete
    assert next_walk.due_time == at(8, day=DAY + timedelta(days=1))
    assert next_walk.is_complete is False
    assert next_walk.id != walk.id
    assert next_walk.completion_history == []


def test_weekly_task_creates_next_task_seven_days_later():
    bath = Task("Bath", at(9), 20, frequency=Frequency.WEEKLY)

    next_bath = bath.mark_complete(at(9, 5))

    assert next_bath.due_time == at(9, day=DAY + timedelta(days=7))


def test_one_time_task_creates_no_next_task():
    vet = Task("Vet visit", at(9), 60, frequency=Frequency.ONCE)

    assert vet.mark_complete(at(9, 30)) is None
    assert vet.is_complete


def test_task_completed_late_does_not_come_back_overdue():
    stale = Task("Water", at(9, day=DAY - timedelta(days=3)), 5, frequency=Frequency.DAILY)

    next_task = stale.mark_complete(at(20))      # finished three days late

    assert next_task.due_time == at(9, day=DAY + timedelta(days=1))
    assert next_task.is_overdue(at(20)) is False


def test_scheduler_complete_task_adds_next_occurrence_to_same_pet(owner, scheduler):
    buddy = owner.get_pet("Buddy")
    walk = Task("Walk", at(8), 30, frequency=Frequency.DAILY)
    buddy.add_task(walk)

    new_task = scheduler.complete_task(walk.id, at(8, 40))

    assert len(buddy.tasks) == 2
    assert new_task in buddy.tasks
    assert new_task.pet_name == "Buddy"


def test_scheduler_complete_unknown_task_raises(scheduler):
    with pytest.raises(ValueError):
        scheduler.complete_task(99999)


# ---------------------------------------------------------------- conflicts

def test_two_tasks_at_the_exact_same_time_are_flagged(owner, scheduler):
    owner.get_pet("Buddy").add_task(Task("Walk", at(8), 30))
    owner.get_pet("Luna").add_task(Task("Litter box", at(8), 10))

    conflicts = scheduler.detect_conflicts()

    assert len(conflicts) == 1
    assert "same time" in conflicts[0].message


def test_partially_overlapping_tasks_are_flagged(owner, scheduler):
    owner.get_pet("Buddy").add_task(Task("Walk", at(7, 30), 30))
    owner.get_pet("Luna").add_task(Task("Brush", at(7, 45), 15))

    assert len(scheduler.detect_conflicts()) == 1


def test_back_to_back_tasks_are_not_conflicts(owner, scheduler):
    owner.get_pet("Buddy").add_task(Task("Walk", at(8), 30))
    owner.get_pet("Buddy").add_task(Task("Breakfast", at(8, 30), 10))

    assert scheduler.detect_conflicts() == []


def test_completed_tasks_are_ignored_by_conflict_detection(owner, scheduler):
    done = Task("Walk", at(8), 30)
    owner.get_pet("Buddy").add_task(done)
    owner.get_pet("Luna").add_task(Task("Brush", at(8), 15))
    done.mark_complete(at(8, 35))

    assert scheduler.detect_conflicts() == []


def test_task_during_owner_busy_time_is_flagged(owner, scheduler):
    owner.add_busy_block(TimeBlock("Work", ["Tue"], time(9, 0), time(17, 0)))
    owner.get_pet("Buddy").add_task(Task("Midday walk", at(10), 30))

    conflicts = scheduler.detect_conflicts()

    assert len(conflicts) == 1
    assert conflicts[0].busy_block is not None
    assert conflicts[0].task_b is None


def test_no_tasks_means_no_conflicts(scheduler):
    assert scheduler.detect_conflicts() == []


def test_suggest_free_slot_moves_task_past_the_clash(owner, scheduler):
    owner.get_pet("Buddy").add_task(Task("Walk", at(8), 30))
    second = Task("Brush", at(8), 30)
    owner.get_pet("Luna").add_task(second)

    assert scheduler.suggest_free_slot(second) == at(8, 30)


# ---------------------------------------------------------------- filtering

def test_filter_by_pet_name_is_case_insensitive_and_sorted(owner, scheduler):
    owner.get_pet("Buddy").add_task(Task("Late", at(18), 10))
    owner.get_pet("Buddy").add_task(Task("Early", at(7), 10))
    owner.get_pet("Luna").add_task(Task("Other pet", at(9), 10))

    result = scheduler.filter_tasks(pet_name="buddy")

    assert [t.description for t in result] == ["Early", "Late"]


def test_filter_by_status(owner, scheduler):
    done = Task("Done", at(7), 10)
    owner.get_pet("Buddy").add_task(done)
    owner.get_pet("Buddy").add_task(Task("Todo", at(8), 10))
    done.mark_complete(at(7, 15))

    assert [t.description for t in scheduler.filter_tasks(status="pending")] == ["Todo"]
    assert [t.description for t in scheduler.filter_tasks(status="complete")] == ["Done"]


def test_filter_by_category_and_day(owner, scheduler):
    owner.get_pet("Buddy").add_task(Task("Walk today", at(8), 30, category=Category.WALK))
    owner.get_pet("Luna").add_task(
        Task("Walk tomorrow", at(8, day=DAY + timedelta(days=1)), 30, category=Category.WALK))
    owner.get_pet("Luna").add_task(Task("Feed", at(9), 10, category=Category.FEEDING))

    result = scheduler.filter_tasks(category=Category.WALK, day=DAY)

    assert [t.description for t in result] == ["Walk today"]


def test_filter_rejects_an_invalid_status(scheduler):
    with pytest.raises(ValueError):
        scheduler.filter_tasks(status="finished")


def test_pet_with_no_tasks_is_handled(owner, scheduler):
    luna = owner.get_pet("Luna")

    assert luna.get_tasks() == []
    assert scheduler.filter_tasks(pet_name="Luna") == []


# --------------------------------------------------------------- daily plan

def test_must_do_task_is_included_even_when_it_exceeds_available_time(owner, scheduler):
    owner.available_minutes = 10
    owner.get_pet("Luna").add_task(Task("Medication", at(8), 30, must_do=True))
    owner.get_pet("Buddy").add_task(Task("Play", at(9), 5, priority=Priority.HIGH))

    plan = scheduler.build_daily_plan(DAY)

    assert [i.task.description for i in plan.items] == ["Medication"]
    assert [t.description for t in plan.skipped] == ["Play"]


def test_plan_fills_time_by_priority_and_lists_what_was_skipped(owner, scheduler):
    # available_minutes is 60: must-do 10 + high 30 = 40, medium 30 won't fit, low 20 fits.
    buddy = owner.get_pet("Buddy")
    buddy.add_task(Task("Must", at(7), 10, priority=Priority.LOW, must_do=True))
    buddy.add_task(Task("High", at(8), 30, priority=Priority.HIGH))
    buddy.add_task(Task("Medium", at(9), 30, priority=Priority.MEDIUM))
    buddy.add_task(Task("Low", at(10), 20, priority=Priority.LOW))

    plan = scheduler.build_daily_plan(DAY)

    assert [i.task.description for i in plan.items] == ["Must", "High", "Low"]   # time order
    assert [t.description for t in plan.skipped] == ["Medium"]
    assert plan.total_minutes() == 60
    assert all(item.reason for item in plan.items)


def test_overdue_tasks_are_listed_separately_from_the_plan(owner, scheduler):
    stale = Task("Missed pill", at(8, day=DAY - timedelta(days=2)), 5)
    owner.get_pet("Luna").add_task(stale)
    owner.get_pet("Luna").add_task(Task("Today", at(9), 10))

    plan = scheduler.build_daily_plan(DAY)

    assert plan.overdue == [stale]
    assert [i.task.description for i in plan.items] == ["Today"]


# ------------------------------------------------------ models and supplies

def test_mark_complete_records_completion_time():
    task = Task("Walk", at(8), 30)

    task.mark_complete(at(8, 45))

    assert task.is_complete
    assert task.last_completed() == at(8, 45)


def test_task_rejects_a_non_positive_duration():
    with pytest.raises(ValueError):
        Task("Bad", at(8), 0)


def test_add_task_stamps_the_pets_name_on_the_task(owner):
    task = Task("Walk", at(8), 30)

    owner.get_pet("Buddy").add_task(task)

    assert task.pet_name == "Buddy"


def test_owner_rejects_a_duplicate_pet_name(owner):
    with pytest.raises(ValueError):
        owner.add_pet(Pet(name="buddy", species="dog", age=1))


def test_supply_reminder_appears_inside_its_window():
    food = SupplyItem("Dog food", restock_every_days=30, last_purchased=date(2026, 10, 1),
                      remind_days_before=5)

    assert food.next_due_date() == date(2026, 10, 31)
    assert food.is_due(date(2026, 10, 25)) is False
    assert food.is_due(date(2026, 10, 26)) is True
    assert food.is_due(date(2026, 11, 2)) is True
