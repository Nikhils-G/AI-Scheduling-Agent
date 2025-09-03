# AI Scheduling Agent 

This project is a **medical appointment scheduling system** built to automate booking, reduce patient no-shows, and streamline clinic operations. It is designed as a lightweight, rule-based agent that simulates the real challenges clinics face — managing patients, calendars, reminders, and insurance information.

The system integrates with mock data (patients in CSV, doctor schedules in Excel, and intake forms in PDF) and demonstrates a full workflow:

* Patient lookup (new vs returning)
* Smart scheduling (60 min for new, 30 min for returning)
* Calendar slot management
* Insurance collection
* Appointment confirmation & export
* Intake form distribution
* Automated 3-step reminders

---

##  Features

1. **Patient Recognition**

   * Matches patients by **email, phone, or fuzzy name + DOB**.
   * Differentiates between new and returning patients automatically.

2. **Smart Scheduling**

   * New patients → 60 minutes
   * Returning patients → 30 minutes

3. **Calendar Integration**

   * Doctor schedules stored in Excel.
   * Available slots shown and booked without conflicts.

4. **Insurance Collection**

   * Captures carrier, member ID, and group number.

5. **Appointment Confirmation**

   * Confirms bookings and exports them to Excel for admin review.

6. **Form Distribution**

   * Emails intake forms after confirmation.

7. **Automated Reminders**

   * 3 reminder steps (R1, R2, R3).
   * Later reminders ask about form completion and cancellation reasons.

---

## ⚙️ Tech Stack

* **Python** (core logic)
* **Streamlit** (UI for demo and admin panel)
* **Pandas** (CSV + Excel integration)
* **PyArrow** (dataframe compatibility)
* **UUID** (unique IDs for patients & appointments)
* **difflib** (fuzzy matching for patient lookup)

---

## Data Sources

* `patients.csv` → Patient database (50 synthetic records).
* `schedules.xlsx` → Doctor availability (simulated calendar).
* `intake_form.pdf` → Sample intake form template.
* `appointments_export.xlsx` → Generated exports for admin review.

---

## Fuzzy Matching Explained

A key part of this agent is detecting patients even if there’s a **typo in their name**. This is done using:

```python
from difflib import SequenceMatcher
score = SequenceMatcher(None, input_name.lower(), db_name.lower()).ratio()
```

### 1. How `SequenceMatcher().ratio()` Works

It’s **mathematics, not randomness**:

$$
\text{ratio} = \frac{2 \times M}{T}
$$

* **M** = number of matching characters (in order)
* **T** = total characters across both strings

Example:

* DB: `"Vidur Bera"` (10 chars)
* Input: `"Vidurr Beraa"` (12 chars)
* Matching subsequence = `"Vidur Bera"` (10 chars)

$$
M = 10, \; T = 10 + 12 = 22
$$

$$
\text{ratio} = \frac{2 \times 10}{22} = 0.91
$$

Score = **0.91 → high similarity** ✅

---

### 2. Why AI-like?

Instead of `==` exact match, it measures **closeness**:

* `"Vidur Bera"` vs `"Vidurr Beraa"` → 0.91
* `"Vidur Bera"` vs `"Vidur Bora"` → 0.95
* `"Vidur Bera"` vs `"Anita Rao"` → 0.0

This mimics human reasoning: we know `"Vidurr Beraa"` is probably `"Vidur Bera"`.

---

### 3. AI Evidence with DOB Rule

The agent combines **fuzzy score + DOB**:

```python
if r_dob == dob_val and name_score > 0.7:
    return returning
```

* If DOB matches **and** name\_score > 0.7 → Returning patient.
* Else → New patient.

This hybrid logic = **AI heuristic (rules + similarity measure)**.

---

### 4. Why `"name_score":1` but `"combined":0.7`?

* Sometimes the name is an exact match → score = 1.0.
* But the system applies a **threshold (0.7)** to confirm.
* So `"combined":0.7` means: the system’s **confidence threshold** for recognition.

---

## 📊 Example Experiments

We validated the agent with three experiments:

1. **Returning patient (exact email match)** → Found instantly.
2. **Returning patient (typo in name, DOB match)** → Fuzzy score > 0.7, recognized correctly.
3. **New patient** → No match, created a new record, sent intake form.

All three confirm the system’s logic is working correctly.

---

## Why This Matters

* Clinics lose revenue from no-shows and scheduling errors.
* This system shows how automation + fuzzy reasoning can **reduce errors, save time, and increase efficiency**.
* While it’s lightweight and deterministic, the fuzzy matching and rule-based logic make it behave like an **AI scheduling agent**.

---

## Conclusion

This project demonstrates a **working medical scheduling system** that uses simple yet powerful logic to automate real-world clinic workflows. By combining fuzzy matching, business rules, and reminders, it delivers an AI-like experience without relying on heavy models.
