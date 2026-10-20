from datetime import date, datetime, time, timedelta

from pawpal_system import (
    Owner, Pet, Task, Scheduler, TimeBlock, SupplyItem,
    Category, Priority, Frequency, TimePreference,
)


def at(hour, minute=0):
    """Shortcut: today's date at the given time, e.g. at(8, 30)."""
    return datetime.combine(date.today(), time(hour, minute))


def print_schedule(title, tasks):
    """Print a list of tasks as a clean, aligned table."""
    print("=" * 62)
    print(f"  {title}")
    print("=" * 62)
    if not tasks:
        print("  (no tasks)")
    for t in tasks:
        status = "[x]" if t.is_complete else "[ ]"
        other_day = f"  (due {t.due_time:%b %d})" if t.due_time.date() != date.today() else ""
        print(
            f"  {t.due_time:%H:%M}-{t.end_time():%H:%M}  "
            f"{t.pet_name:<7} {t.description:<20} {t.priority.name:<7} {status}{other_day}"
        )
    print()


def print_conflicts(conflicts, scheduler):
    """Print scheduling conflicts as warnings, each with a suggested fix."""
    print("=" * 62)
    print("  CONFLICT CHECK")
    print("=" * 62)
    if not conflicts:
        print("  No conflicts found.")
    for c in conflicts:
        print(f"  WARNING: {c.message}")
        mover = c.task_b or c.task_a          # move the later task of a pair
        slot = scheduler.suggest_free_slot(mover)
        if slot:
            print(f"      suggestion: move {mover.pet_name}'s '{mover.description}' to {slot:%H:%M}")
        else:
            print(f"      suggestion: no free time left today for '{mover.description}'")
    print()


def main():
    # 1. Create the owner (with a busy block that lands on today's evening)
    owner = Owner(name="Sam", available_minutes=90)
    owner.add_busy_block(TimeBlock(
        label="Evening class",
        days=[date.today().strftime("%a")],   # today's weekday, e.g. "Sat"
        start=time(17, 45),
        end=time(18, 15),
    ))
    owner.add_supply(SupplyItem(
        name="Dog food",
        restock_every_days=30,
        last_purchased=date.today() - timedelta(days=27),
        pet_name="Buddy",
        remind_days_before=5,
    ))

    # 2. Create two pets and give them to the owner
    buddy = Pet(name="Buddy", species="dog", age=3, weight_lbs=45.0)
    luna = Pet(name="Luna", species="cat", age=5, weight_lbs=9.5)
    owner.add_pet(buddy)
    owner.add_pet(luna)

    # 3. Add tasks at different times (out of order on purpose)
    buddy.add_task(Task(
        description="Evening walk",
        due_time=at(18, 0),
        duration_minutes=30,
        category=Category.WALK,
        priority=Priority.MEDIUM,
        frequency=Frequency.DAILY,
    ))
    buddy.add_task(Task(
        description="Morning walk",
        due_time=at(7, 30),
        duration_minutes=30,
        category=Category.WALK,
        priority=Priority.HIGH,
        frequency=Frequency.DAILY,
        preferred_time=TimePreference.MORNING,
    ))
    buddy.add_task(Task(
        description="Breakfast",
        due_time=at(8, 0),
        duration_minutes=10,
        category=Category.FEEDING,
        priority=Priority.HIGH,
        frequency=Frequency.DAILY,
    ))
    luna.add_task(Task(
        description="Thyroid pill",
        due_time=at(8, 15),
        duration_minutes=5,
        category=Category.MEDICATION,
        priority=Priority.HIGH,
        frequency=Frequency.DAILY,
        must_do=True,
    ))
    luna.add_task(Task(
        description="Brush coat",
        due_time=at(7, 45),                  # overlaps Buddy's morning walk on purpose
        duration_minutes=15,
        category=Category.GROOMING,
        priority=Priority.LOW,
    ))
    luna.add_task(Task(
        description="Clean litter box",
        due_time=at(7, 30),                  # SAME start time as Buddy's morning walk
        duration_minutes=10,
        category=Category.GROOMING,
        priority=Priority.MEDIUM,
    ))
    luna.add_task(Task(
        description="Refill water fountain",
        due_time=at(9, 0) - timedelta(days=2),   # two days overdue, repeats daily
        duration_minutes=5,
        category=Category.FEEDING,
        priority=Priority.MEDIUM,
        frequency=Frequency.DAILY,
    ))
    luna.add_task(Task(
        description="Feather wand play",
        due_time=at(19, 0),
        duration_minutes=15,
        category=Category.ENRICHMENT,
        priority=Priority.LOW,
    ))

    # 4. Create the Scheduler. It reads tasks through owner.get_all_tasks()
    scheduler = Scheduler(owner)

    # 5. SORT: both pets' tasks in one time-ordered list
    print_schedule(
        f"TODAY'S SCHEDULE - {owner.name} ({date.today():%a, %b %d})",
        scheduler.filter_tasks(day=date.today()),
    )

    # 6. FILTER: by pet, then by category
    print_schedule("FILTER: Buddy's tasks only",
                   scheduler.filter_tasks(pet_name="Buddy"))
    print_schedule("FILTER: medication tasks (all pets)",
                   scheduler.filter_tasks(category=Category.MEDICATION))

    # 7. CONFLICTS: overlapping tasks and tasks during the owner's busy time
    print_conflicts(scheduler.detect_conflicts(), scheduler)

    # 8. DAILY PLAN: fits the owner's available minutes and explains each choice
    print("=" * 62)
    print(f"  DAILY PLAN (Sam has {owner.available_minutes} minutes available)")
    print("=" * 62)
    print(scheduler.build_daily_plan(date.today()).summary())
    print()

    # 9. RECURRING: the next task is created from the COMPLETION date, so a task
    #    finished late (like the overdue water fountain) never comes back overdue
    morning_walk = next(t for t in buddy.tasks if t.description == "Morning walk")
    water = next(t for t in luna.tasks if t.description == "Refill water fountain")
    print("=" * 62)
    print("  RECURRING TASKS")
    print("=" * 62)
    for task in (morning_walk, water):
        next_task = scheduler.complete_task(task.id)
        print(f"  Completed: {task.description} (was due {task.due_time:%a %b %d %H:%M})")
        print(f"      next one created for: {next_task.due_time:%a, %b %d at %H:%M}")
    print()

    # 10. FILTER BY STATUS
    print_schedule("FILTER: completed tasks", scheduler.filter_tasks(status="complete"))
    print_schedule("FILTER: Luna's pending tasks",
                   scheduler.filter_tasks(pet_name="Luna", status="pending"))


if __name__ == "__main__":
    main()
