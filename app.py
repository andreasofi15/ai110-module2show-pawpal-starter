from datetime import date, datetime, time

import streamlit as st

from pawpal_system import Owner, Pet, Task, Scheduler, Category, Priority, Frequency

st.set_page_config(page_title="PawPal+", page_icon="🐾", layout="centered")

# Streamlit reruns this whole script on every click, so the Owner has to live
# in session_state. We only create it the first time the page loads.
if "owner" not in st.session_state:
    st.session_state.owner = Owner(name="Jordan", available_minutes=120)

owner = st.session_state.owner
st.title("🐾 PawPal+")

st.markdown(
    """
Welcome to the PawPal+ starter app.

This file is intentionally thin. It gives you a working Streamlit app so you can start quickly,
but **it does not implement the project logic**. Your job is to design the system and build it.

Use this app as your interactive demo once your backend classes/functions exist.
"""
)

with st.expander("Scenario", expanded=True):
    st.markdown(
        """
**PawPal+** is a pet care planning assistant. It helps a pet owner plan care tasks
for their pet(s) based on constraints like time, priority, and preferences.

You will design and implement the scheduling logic and connect it to this Streamlit UI.
"""
    )

with st.expander("What you need to build", expanded=True):
    st.markdown(
        """
At minimum, your system should:
- Represent pet care tasks (what needs to happen, how long it takes, priority)
- Represent the pet and the owner (basic info and preferences)
- Build a plan/schedule for a day that chooses and orders tasks based on constraints
- Explain the plan (why each task was chosen and when it happens)
"""
    )

st.divider()

st.subheader("Owner")
owner.name = st.text_input("Owner name", value=owner.name)
owner.available_minutes = int(st.number_input(
    "Minutes available for pet care today", min_value=10, max_value=720,
    value=owner.available_minutes, step=10,
))

st.divider()

# ---------------------------------------------------------------- Add a pet
st.subheader("Add a pet")
with st.form("add_pet_form", clear_on_submit=True):
    col1, col2 = st.columns(2)
    new_pet_name = col1.text_input("Pet name")
    new_species = col2.selectbox("Species", ["dog", "cat", "other"])
    col3, col4 = st.columns(2)
    new_age = col3.number_input("Age (years)", min_value=0, max_value=40, value=1)
    new_weight = col4.number_input("Weight (lbs)", min_value=0.1, max_value=300.0, value=10.0, step=0.5)
    pet_submitted = st.form_submit_button("Add pet")

if pet_submitted:
    if not new_pet_name.strip():
        st.error("Please enter a pet name.")
    else:
        try:
            owner.add_pet(Pet(
                name=new_pet_name.strip(),
                species=new_species,
                age=int(new_age),
                weight_lbs=float(new_weight),
            ))
            st.success(f"Added {new_pet_name.strip()}!")
        except ValueError as error:
            st.error(str(error))


st.divider()

# --------------------------------------------------------------- Add a task
st.subheader("Add a task")
if not owner.pets:
    st.info("Add a pet first, then you can give it tasks.")
else:
    with st.form("add_task_form", clear_on_submit=True):
        task_pet = st.selectbox("For which pet?", [p.name for p in owner.pets])
        task_description = st.text_input("Task description", value="Morning walk")
        col1, col2, col3 = st.columns(3)
        task_date = col1.date_input("Date", value=date.today())
        task_time = col2.time_input("Time", value=time(8, 0))
        task_duration = col3.number_input("Duration (minutes)", min_value=1, max_value=240, value=20)
        col4, col5, col6 = st.columns(3)
        task_priority = col4.selectbox(
            "Priority", list(Priority), index=1, format_func=lambda p: p.name.title())
        task_category = col5.selectbox(
            "Category", list(Category), format_func=lambda c: c.value.title())
        task_frequency = col6.selectbox(
            "Repeats", list(Frequency), format_func=lambda f: f.value.title())
        task_must_do = st.checkbox("Must-do (always included in the plan)")
        task_submitted = st.form_submit_button("Add task")

    if task_submitted:
        if not task_description.strip():
            st.error("Please enter a task description.")
        else:
            pet = owner.get_pet(task_pet)
            pet.add_task(Task(
                description=task_description.strip(),
                due_time=datetime.combine(task_date, task_time),
                duration_minutes=int(task_duration),
                category=task_category,
                priority=task_priority,
                frequency=task_frequency,
                must_do=task_must_do,
            ))
            st.success(f"Added '{task_description.strip()}' to {pet.name}.")

st.write("Your pets:")
if owner.pets:
    st.table([
        {"Name": p.name, "Species": p.species, "Age": p.age,
         "Weight (lbs)": p.weight_lbs, "Tasks": len(p.tasks)}
        for p in owner.pets
    ])
else:
    st.info("No pets yet. Add one above.")


scheduler = Scheduler(owner)
all_tasks = scheduler.sort_by_time(owner.get_all_tasks())
if all_tasks:
    st.write("All tasks (earliest first):")
    st.table([
        {"When": f"{t.due_time:%a %b %d, %H:%M}-{t.end_time():%H:%M}",
         "Pet": t.pet_name, "Task": t.description,
         "Priority": t.priority.name.title(), "Repeats": t.frequency.value.title(),
         "Done": "yes" if t.is_complete else "no"}
        for t in all_tasks
    ])

st.divider()

# ----------------------------------------------------------- Build schedule
st.subheader("Build schedule")
plan_day = st.date_input("Plan for which day?", value=date.today(), key="plan_day")

if st.button("Generate schedule"):
    if not all_tasks:
        st.warning("Add at least one task first.")
    else:
        plan = scheduler.build_daily_plan(plan_day)

        for conflict in scheduler.detect_conflicts():
            st.warning(conflict.message)

        if plan.items:
            st.success(f"{len(plan.items)} tasks scheduled ({plan.total_minutes()} of "
                       f"{owner.available_minutes} minutes).")
            st.table([
                {"Time": f"{i.task.due_time:%H:%M}-{i.task.end_time():%H:%M}",
                 "Pet": i.task.pet_name, "Task": i.task.description,
                 "Why": i.reason}
                for i in plan.items
            ])
        else:
            st.info("Nothing is scheduled for that day.")

        for t in plan.skipped:
            st.warning(f"Skipped (not enough time): {t.pet_name} - {t.description} ({t.duration_minutes} min)")
        for t in plan.overdue:
            st.error(f"Overdue: {t.pet_name} - {t.description} (was due {t.due_time:%b %d %H:%M})")
        for s in plan.reminders:
            st.info(f"Supply reminder: buy {s.name} (due {s.next_due_date():%b %d})")