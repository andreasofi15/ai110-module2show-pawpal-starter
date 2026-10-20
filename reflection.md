# PawPal+ Project Reflection

## 1. System Design

**a. Initial design**

# PawPal+ Project Reflection

## 1. System Design

**a. Initial design**

My initial UML started with the four required classes (Owner, Pet, Task,
Scheduler) and grew as I brainstormed requirements and real-life needs.
The draft has nine classes and four enums. I separated classes that hold
data from the one class that holds logic, so the Scheduler does the
algorithmic work across all pets.

- **Task**: one care activity (walk, feeding, medication, etc.). It stores
  its description, due time, duration, priority, category, frequency,
  completion status, and completion history. It knows how to check for
  overlap with another task, whether it is overdue, how to mark itself
  complete, and how to create its next occurrence if it recurs.
- **Pet**: one animal (name, species, age, weight, notes). It owns a list
  of its tasks and has methods to add, remove, and list them.
- **Owner**: the person. It holds the list of pets, the owner's own busy
  time blocks, and a list of recurring supply reminders. It is also the
  root of the object tree, so it handles saving to and loading from JSON.
- **TimeBlock**: a recurring stretch when the owner is busy (like work),
  so the planner can avoid scheduling tasks then.
- **SupplyItem**: something bought on a cycle (food, litter, flea
  medication) with a restock interval and a reminder window.
- **Scheduler**: the "brain." It gathers tasks across all pets, then sorts,
  filters, detects conflicts, finds overdue tasks, finds due supply
  reminders, and builds the daily plan.
- **DailyPlan and ScheduledItem**: the output of the Scheduler. Each
  scheduled task carries a plain-English reason, so the app can explain
  why it chose that plan. The plan also lists skipped tasks, overdue
  tasks, and supply reminders.
- **Conflict**: describes a clash between two tasks, or between a task and
  the owner's busy time.
- **Enums** (Priority, Category, Frequency, TimePreference): prevent typos
  and make sorting simple.

Relationships: an Owner has many Pets (aggregation), a Pet owns many Tasks
(composition, since a task is meaningless without its pet), an Owner owns
its TimeBlocks and SupplyItems, and the Scheduler uses an Owner and creates
DailyPlans and Conflicts.

**b. Design changes**

My design changed while I reviewed the diagram and turned it into a
code skeleton:

- **Conflict could not describe a task clashing with the owner's busy
  time.** It originally had two tasks only, so I redefined it with an optional second task and an optional busy block.
- **DailyPlan.total_minutes became a method instead of a stored value.**
  A stored number could drift out of sync with the items in the plan, so it is now computed from them.
- **I removed Task.edit().** Python attributes can be set directly, so
  the method added complexity without adding anything.
- **DailyPlan to SupplyItem was changed from a dependency to an
  association,** because the plan stores a list of them rather than just
  using them briefly.
- **load_from_json became a static method,** since it creates a new Owner
  rather than acting on an existing one.
- **TimeBlock.days changed from a string to a list of strings,** which
  makes it easier to check against a date.


---

## 2. Scheduling Logic and Tradeoffs

**a. Constraints and priorities**

- What constraints does your scheduler consider (for example: time, priority, preferences)?
- How did you decide which constraints mattered most?

**b. Tradeoffs**

- Describe one tradeoff your scheduler makes.
- Why is that tradeoff reasonable for this scenario?

---

## 3. AI Collaboration

**a. How you used AI**

- How did you use AI tools during this project (for example: design brainstorming, debugging, refactoring)?
- What kinds of prompts or questions were most helpful?

**b. Judgment and verification**

- Describe one moment where you did not accept an AI suggestion as-is.
- How did you evaluate or verify what the AI suggested?

---

## 4. Testing and Verification

**a. What you tested**

- What behaviors did you test?
- Why were these tests important?

**b. Confidence**

- How confident are you that your scheduler works correctly?
- What edge cases would you test next if you had more time?

---

## 5. Reflection

**a. What went well**

- What part of this project are you most satisfied with?

**b. What you would improve**

- If you had another iteration, what would you improve or redesign?

**c. Key takeaway**

- What is one important thing you learned about designing systems or working with AI on this project?
