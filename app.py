from datetime import date, datetime, time, timedelta

import streamlit as st

from pawpal_system import (
    Category, Frequency, Owner, Pet, Priority, Scheduler, SupplyItem, Task,
    TimeBlock, TimePreference,
)

st.set_page_config(page_title="PawPal+", page_icon="🐾", layout="wide")

PRIORITY_ICON = {Priority.HIGH: "🔴", Priority.MEDIUM: "🟡", Priority.LOW: "🟢"}
SPECIES_ICON = {"dog": "🐶", "cat": "🐱"}
WEEKDAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

# Streamlit reruns this whole script on every click, so the Owner lives in
# session_state. It is only created the first time the page loads.
if "owner" not in st.session_state:
    st.session_state.owner = Owner(name="Jordan", available_minutes=120)
owner = st.session_state.owner
scheduler = Scheduler(owner)

# Pet photos are a display-only extra, so they live here instead of in the Pet class.
if "photos" not in st.session_state:
    st.session_state.photos = {}
photos = st.session_state.photos


def finish(message):
    """Remember a message, then redraw the page so every tab shows fresh data."""
    st.session_state.flash = message
    st.rerun()


def task_line(task):
    return f"**{task.due_time:%a %b %d, %H:%M}-{task.end_time():%H:%M}** · {task.pet_name} · {task.description}"


def load_sample():
    """Fill the app with example pets, tasks, busy time, and a supply reminder."""
    if owner.get_pet("Buddy") is not None or owner.get_pet("Luna") is not None:
        finish("A pet named Buddy or Luna already exists, so the sample data was not loaded.")
    today = date.today()

    def at(hour, minute=0, days_ago=0):
        return datetime.combine(today - timedelta(days=days_ago), time(hour, minute))

    owner.add_pet(Pet(name="Buddy", species="dog", age=3, weight_lbs=45.0))
    owner.add_pet(Pet(name="Luna", species="cat", age=5, weight_lbs=9.5))
    buddy, luna = owner.get_pet("Buddy"), owner.get_pet("Luna")
    buddy.add_task(Task("Morning walk", at(7, 30), 30, Category.WALK, Priority.HIGH,
                        Frequency.DAILY, TimePreference.MORNING))
    buddy.add_task(Task("Breakfast", at(8, 0), 10, Category.FEEDING, Priority.HIGH, Frequency.DAILY))
    buddy.add_task(Task("Evening walk", at(18, 0), 30, Category.WALK, Priority.MEDIUM, Frequency.DAILY))
    luna.add_task(Task("Thyroid pill", at(8, 15), 5, Category.MEDICATION, Priority.HIGH,
                       Frequency.DAILY, must_do=True))
    luna.add_task(Task("Clean litter box", at(7, 30), 10, Category.GROOMING, Priority.MEDIUM))
    luna.add_task(Task("Feather wand play", at(19, 0), 15, Category.ENRICHMENT, Priority.LOW))
    luna.add_task(Task("Refill water fountain", at(9, 0, days_ago=2), 5, Category.FEEDING,
                       Priority.MEDIUM, Frequency.DAILY))
    owner.add_busy_block(TimeBlock("Evening class", [WEEKDAYS[today.weekday()]], time(17, 45), time(18, 15)))
    owner.add_supply(SupplyItem("Dog food", 30, today - timedelta(days=27), "Buddy", 5))
    finish("Sample data loaded. Explore the tabs!")


if "flash" in st.session_state:
    st.toast(st.session_state.pop("flash"))

# ------------------------------------------------------------------ sidebar
with st.sidebar:
    st.header("🐾 PawPal+")
    owner.name = st.text_input("Your name", value=owner.name, key="owner_name")
    owner.available_minutes = st.slider(
        "Minutes available for pet care today", 15, 480,
        value=owner.available_minutes, step=15, key="minutes")
    st.divider()
    st.caption("Want to try it out?")
    if st.button("Load sample data"):
        load_sample()
    with st.expander("Danger zone"):
        confirm_reset = st.checkbox("Yes, delete everything", key="confirm_reset")
        if st.button("Reset all data", disabled=not confirm_reset):
            st.session_state.owner = Owner(name=owner.name, available_minutes=owner.available_minutes)
            st.session_state.photos = {}
            finish("Everything was reset.")

tab_dash, tab_pets, tab_tasks, tab_care, tab_plan = st.tabs(
    ["📊 Dashboard", "🐾 Pets", "📝 Tasks", "🛒 Busy time & supplies", "📅 Daily plan"])

# ---------------------------------------------------------------- dashboard
with tab_dash:
    st.header(f"Hi {owner.name}! 👋")
    pending = scheduler.filter_tasks(status="pending")
    overdue_now = scheduler.get_overdue_tasks(datetime.now())
    conflicts = scheduler.detect_conflicts()
    reminders = scheduler.get_due_reminders(date.today())

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Pets", len(owner.pets))
    m2.metric("Pending tasks", len(pending))
    m3.metric("Past due", len(overdue_now))
    m4.metric("Conflicts", len(conflicts))

    pets_with_photos = [p for p in owner.pets if p.name in photos]
    if pets_with_photos:
        photo_cols = st.columns(min(len(pets_with_photos), 6))
        for photo_col, pet in zip(photo_cols, pets_with_photos):
            photo_col.image(photos[pet.name], caption=pet.name, width=120)

    st.subheader("⏭️ Next up")
    upcoming = [t for t in pending if t.due_time >= datetime.now()][:3]
    if upcoming:
        for task in upcoming:
            st.write(f"{PRIORITY_ICON[task.priority]} {task_line(task)}")
    else:
        st.info("Nothing coming up. Add tasks in the Tasks tab, or load the sample data from the sidebar.")

    st.subheader("⚠️ Scheduling conflicts")
    if not conflicts:
        st.success("No scheduling conflicts.")
    if conflicts:
        st.caption("Nothing is changed automatically. Use a button to apply a suggestion, or fix it yourself.")
    for n, conflict in enumerate(conflicts):
        mover = conflict.task_b or conflict.task_a        # suggest moving the later task
        slot = scheduler.suggest_free_slot(mover)
        text_col, button_col = st.columns([5, 2])
        text_col.warning(f"{conflict.message}.")
        if slot is None:
            button_col.caption("No free time left that day.")
        elif button_col.button(f"Move '{mover.description}' to {slot:%H:%M}", key=f"fix_{n}_{mover.id}"):
            mover.due_time = slot
            finish(f"Moved '{mover.description}' to {slot:%H:%M}.")

    if reminders:
        st.subheader("🛒 Supplies to buy")
        for supply in reminders:
            text_col, button_col = st.columns([5, 2])
            who = f" for {supply.pet_name}" if supply.pet_name else ""
            text_col.info(f"Buy {supply.name}{who} (due {supply.next_due_date():%b %d})")
            if button_col.button("Bought it today", key=f"buy_dash_{supply.id}"):
                supply.mark_purchased(date.today())
                finish(f"Nice! {supply.name} reminder reset.")

# --------------------------------------------------------------------- pets
with tab_pets:
    st.subheader("Add a pet")
    with st.form("add_pet_form", clear_on_submit=True):
        c1, c2, c3, c4 = st.columns(4)
        new_pet_name = c1.text_input("Pet name")
        new_species = c2.selectbox("Species", ["dog", "cat", "other"])
        new_age = c3.number_input("Age (years)", min_value=0, max_value=40, value=1)
        new_weight = c4.number_input("Weight (lbs)", min_value=0.1, max_value=300.0, value=10.0, step=0.5)
        pet_submitted = st.form_submit_button("Add pet")
    if pet_submitted:
        if not new_pet_name.strip():
            st.error("Please enter a pet name.")
        else:
            try:
                owner.add_pet(Pet(name=new_pet_name.strip(), species=new_species,
                                  age=int(new_age), weight_lbs=float(new_weight)))
            except ValueError as error:
                st.error(str(error))
            else:
                finish(f"Added {new_pet_name.strip()}!")

    st.subheader("Your pets")
    if not owner.pets:
        st.info("No pets yet. Add one above.")
    for pet in owner.pets:
        open_tasks = len(pet.get_tasks(pending_only=True))
        title = f"{SPECIES_ICON.get(pet.species, '🐾')} {pet.name} · {pet.species}, {pet.age} yr · {open_tasks} pending"
        with st.expander(title):
            photo_col, left, right = st.columns([1, 1, 1])
            if pet.name in photos:
                photo_col.image(photos[pet.name], width=160)
                if photo_col.button("Remove photo", key=f"photo_remove_{pet.name}"):
                    photos.pop(pet.name, None)
                    finish(f"Removed {pet.name}'s photo.")
            else:
                photo_col.caption("No photo yet 📷")
            new_photo = photo_col.file_uploader("Upload a photo", type=["png", "jpg", "jpeg"],
                                                key=f"photo_upload_{pet.name}")
            if new_photo is not None and photo_col.button("Save photo", key=f"photo_save_{pet.name}"):
                if new_photo.size > 5_000_000:
                    photo_col.error("That photo is over 5 MB. Please pick a smaller one.")
                else:
                    photos[pet.name] = new_photo.getvalue()
                    finish(f"Saved a photo of {pet.name}!")
            new_w = left.number_input("Weight (lbs)", min_value=0.1, max_value=300.0,
                                      value=float(max(pet.weight_lbs, 0.1)), step=0.5,
                                      key=f"weight_{pet.name}")
            if left.button("Update weight", key=f"weight_btn_{pet.name}"):
                pet.update_weight(float(new_w))
                finish(f"{pet.name}'s weight is now {new_w} lbs.")
            new_notes = right.text_area("Notes (allergies, habits, vet info)", value=pet.notes,
                                        key=f"notes_{pet.name}")
            if right.button("Save notes", key=f"notes_btn_{pet.name}"):
                pet.notes = new_notes
                finish(f"Saved notes for {pet.name}.")
            sure = st.checkbox(f"Yes, remove {pet.name} and all of its tasks", key=f"sure_{pet.name}")
            if st.button(f"Remove {pet.name}", disabled=not sure, key=f"remove_{pet.name}"):
                owner.remove_pet(pet.name)
                photos.pop(pet.name, None)
                finish(f"Removed {pet.name}.")

# -------------------------------------------------------------------- tasks
with tab_tasks:
    st.subheader("Add a task")
    if not owner.pets:
        st.info("Add a pet first, then you can give it tasks.")
    else:
        with st.form("add_task_form", clear_on_submit=True):
            task_pet = st.selectbox("For which pet?", [p.name for p in owner.pets])
            task_description = st.text_input("Task description", value="Morning walk")
            t1, t2, t3 = st.columns(3)
            task_date = t1.date_input("Date", value=date.today())
            task_time = t2.time_input("Time", value=time(8, 0))
            task_duration = t3.number_input("Duration (minutes)", min_value=1, max_value=240, value=20)
            t4, t5, t6, t7 = st.columns(4)
            task_priority = t4.selectbox("Priority", list(Priority), index=1,
                                         format_func=lambda p: p.name.title())
            task_category = t5.selectbox("Category", list(Category),
                                         format_func=lambda c: c.value.title())
            task_frequency = t6.selectbox("Repeats", list(Frequency),
                                          format_func=lambda f: f.value.title())
            task_pref = t7.selectbox("Preferred time of day", list(TimePreference), index=3,
                                     format_func=lambda p: p.value.title())
            task_must_do = st.checkbox("Must-do (always included in the plan)")
            task_submitted = st.form_submit_button("Add task")
        if task_submitted:
            if not task_description.strip():
                st.error("Please enter a task description.")
            else:
                owner.get_pet(task_pet).add_task(Task(
                    description=task_description.strip(),
                    due_time=datetime.combine(task_date, task_time),
                    duration_minutes=int(task_duration),
                    category=task_category, priority=task_priority,
                    frequency=task_frequency, preferred_time=task_pref,
                    must_do=task_must_do))
                finish(f"Added '{task_description.strip()}' to {task_pet}.")

    st.subheader("Your tasks")
    f1, f2, f3, f4 = st.columns(4)
    pet_filter = f1.selectbox("Pet", ["All"] + [p.name for p in owner.pets], key="f_pet")
    category_filter = f2.selectbox("Category", ["All"] + [c.value.title() for c in Category], key="f_category")
    sort_choice = f3.selectbox("Sort by", ["Time", "Priority"], key="f_sort")
    search = f4.text_input("Search", key="f_search", placeholder="e.g. walk")
    status_choice = st.radio("Show", ["Pending", "Complete", "All"], horizontal=True, key="f_status")

    visible = scheduler.filter_tasks(
        pet_name=None if pet_filter == "All" else pet_filter,
        category=None if category_filter == "All" else Category(category_filter.lower()),
        status=None if status_choice == "All" else status_choice.lower())
    if search.strip():
        visible = [t for t in visible if search.strip().lower() in t.description.lower()]
    if sort_choice == "Priority":
        visible = scheduler.sort_by_priority(visible)

    if not visible:
        st.info("No tasks match these filters.")
    for task in visible[:60]:
        info_col, done_col, delete_col = st.columns([8, 1, 1])
        late = "  ⏰ past due" if task.is_overdue(datetime.now()) else ""
        info_col.markdown(f"{'✅ ' if task.is_complete else ''}{PRIORITY_ICON[task.priority]} {task_line(task)}{late}")
        details = f"{task.category.value.title()} · {task.duration_minutes} min · repeats {task.frequency.value}"
        info_col.caption(details + (" · must-do" if task.must_do else ""))
        if not task.is_complete and done_col.button("✅", key=f"done_{task.id}", help="Mark complete"):
            next_task = scheduler.complete_task(task.id)
            if next_task:
                finish(f"Done! The next one is scheduled for {next_task.due_time:%A, %b %d at %H:%M}.")
            finish("Done!")
        if delete_col.button("🗑️", key=f"delete_{task.id}", help="Delete this task"):
            owner.get_pet(task.pet_name).remove_task(task.id)
            finish(f"Deleted '{task.description}'.")
    if len(visible) > 60:
        st.caption(f"Showing the first 60 of {len(visible)} tasks. Use the filters to narrow it down.")

# ------------------------------------------------------ busy time & supplies
with tab_care:
    left, right = st.columns(2)

    with left:
        st.subheader("🗓️ Your busy time")
        st.caption("The scheduler warns you when a task lands in one of these.")
        with st.form("busy_form", clear_on_submit=True):
            busy_label = st.text_input("What is it?", value="Work")
            busy_days = st.multiselect("Days", WEEKDAYS, default=["Mon", "Tue", "Wed", "Thu", "Fri"])
            b1, b2 = st.columns(2)
            busy_start = b1.time_input("From", value=time(9, 0))
            busy_end = b2.time_input("Until", value=time(17, 0))
            busy_submitted = st.form_submit_button("Add busy time")
        if busy_submitted:
            if not busy_label.strip() or not busy_days:
                st.error("Give it a name and pick at least one day.")
            elif busy_end <= busy_start:
                st.error("The end time must be after the start time.")
            else:
                owner.add_busy_block(TimeBlock(busy_label.strip(), busy_days, busy_start, busy_end))
                finish(f"Added busy time: {busy_label.strip()}.")
        if not owner.busy_blocks:
            st.info("No busy time added yet.")
        for i, block in enumerate(owner.busy_blocks):
            row, remove_col = st.columns([5, 1])
            row.write(f"**{block.label}** · {', '.join(block.days)} · {block.start:%H:%M}-{block.end:%H:%M}")
            if remove_col.button("🗑️", key=f"remove_block_{i}", help="Remove"):
                owner.busy_blocks.pop(i)
                finish(f"Removed {block.label}.")

    with right:
        st.subheader("🛒 Supplies")
        st.caption("Food, litter, flea medicine: anything you buy on a cycle.")
        with st.form("supply_form", clear_on_submit=True):
            supply_name = st.text_input("Item", value="Dog food")
            s1, s2 = st.columns(2)
            supply_every = s1.number_input("Buy again every (days)", min_value=1, max_value=365, value=30)
            supply_remind = s2.number_input("Remind me (days before)", min_value=0, max_value=60, value=3)
            s3, s4 = st.columns(2)
            supply_last = s3.date_input("Last bought", value=date.today())
            supply_for = s4.selectbox("For", ["Household"] + [p.name for p in owner.pets])
            supply_submitted = st.form_submit_button("Add supply")
        if supply_submitted:
            if not supply_name.strip():
                st.error("Please enter an item name.")
            else:
                owner.add_supply(SupplyItem(
                    name=supply_name.strip(), restock_every_days=int(supply_every),
                    last_purchased=supply_last,
                    pet_name="" if supply_for == "Household" else supply_for,
                    remind_days_before=int(supply_remind)))
                finish(f"Added {supply_name.strip()}.")
        if not owner.supplies:
            st.info("No supplies tracked yet.")
        for supply in sorted(owner.supplies, key=lambda s: s.next_due_date()):
            info_col, bought_col, remove_col = st.columns([5, 2, 1])
            soon = "  ⚠️ buy soon" if supply.is_due(date.today()) else ""
            who = f" ({supply.pet_name})" if supply.pet_name else ""
            info_col.write(f"**{supply.name}**{who} · next due {supply.next_due_date():%b %d}{soon}")
            if bought_col.button("Bought today", key=f"bought_{supply.id}"):
                supply.mark_purchased(date.today())
                finish(f"{supply.name} reminder reset.")
            if remove_col.button("🗑️", key=f"remove_supply_{supply.id}", help="Remove"):
                owner.remove_supply(supply.id)
                finish(f"Removed {supply.name}.")

# ---------------------------------------------------------------- daily plan
with tab_plan:
    p1, p2 = st.columns([3, 1])
    plan_day = p1.date_input("Plan for which day?", value=date.today(), key="plan_day")
    show_reasons = p2.toggle("Show reasons", value=True, key="show_reasons")

    if not owner.get_all_tasks():
        st.info("Add some tasks (or load the sample data from the sidebar) to see a plan.")
    else:
        plan = scheduler.build_daily_plan(plan_day)
        used, budget = plan.total_minutes(), owner.available_minutes

        n1, n2, n3 = st.columns(3)
        n1.metric("Tasks scheduled", len(plan.items))
        n2.metric("Minutes used", f"{used} / {budget}")
        n3.metric("Skipped", len(plan.skipped))
        st.progress(min(used / budget, 1.0), text=f"{used} of {budget} minutes used")
        if used > budget:
            st.warning("Your must-do tasks need more time than you set aside today.")
        if scheduler.detect_conflicts():
            st.warning("Some tasks clash. You can fix them on the Dashboard tab.")

        if plan.items:
            rows = []
            for item in plan.items:
                row = {"Time": f"{item.task.due_time:%H:%M}-{item.task.end_time():%H:%M}",
                       "Pet": item.task.pet_name, "Task": item.task.description,
                       "Priority": item.task.priority.name.title()}
                if show_reasons:
                    row["Why"] = item.reason
                rows.append(row)
            st.table(rows)
        else:
            st.info("Nothing is scheduled for that day.")

        for task in plan.skipped:
            st.warning(f"Skipped (not enough time): {task.pet_name} - {task.description} ({task.duration_minutes} min)")
        for task in plan.overdue:
            st.error(f"Overdue: {task.pet_name} - {task.description} (was due {task.due_time:%b %d %H:%M})")
        for supply in plan.reminders:
            st.info(f"Supply reminder: buy {supply.name} (due {supply.next_due_date():%b %d})")

        st.download_button("⬇️ Download this plan", plan.summary(),
                           file_name=f"pawpal_plan_{plan_day}.txt")
