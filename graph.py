"""
Orchestrator: light-weight agent that coordinates booking flow.
This is a simple deterministic flow (no external LLM required).
"""

from datetime import datetime
import uuid
import pandas as pd

class Orchestrator:
    def __init__(self, patient_db, schedule_tool, messaging, exporter, form_sender):
        self.patient_db = patient_db
        self.schedule_tool = schedule_tool
        self.messaging = messaging
        self.exporter = exporter
        self.form_sender = form_sender

        # appointments DataFrame kept in-memory; exporter can write it out
        cols = [
            "appt_id","patient_id","patient_name","patient_email","patient_phone",
            "doctor","location","date","start","end","duration","status",
            "reason","insurance_carrier","member_id","group_no",
            "forms_sent_at","forms_completed","reminder1","reminder2","reminder3",
            "cancel_reason","created_at","exported_at"
        ]
        self.appointments_df = pd.DataFrame(columns=cols)

    def start_booking(self, name, dob, phone, email, preferred_doctor, reason,
                      insurer="", member_id="", group_no="", slot=None):
        # 1. Identify patient
        patient, status, score = self.patient_db.match_patient(name, dob, phone, email)
        if status == "new":
            patient = self.patient_db.create_patient(name, dob, phone, email, preferred_doctor)

        # 2. Determine duration
        duration = 60 if status == "new" else 30

        # 3. Pick slot
        if slot is None:
            slots = self.schedule_tool.find_slots(preferred_doctor, duration)
            if not slots:
                return {"status": "error", "message": "No available slots found. Try a different doctor or day."}
            slot = slots[0]  # fallback if UI didn’t pass a slot

        # 4. Book the slot
        booked = self.schedule_tool.book_slot(preferred_doctor, slot)
        if not booked:
            return {"status": "error", "message": "Failed to book slot due to conflict. Try again."}

        # 5. Create appointment record
        appt_id = f"APPT-{uuid.uuid4().hex[:8]}"
        appt = {
            "appt_id": appt_id,
            "patient_id": patient["patient_id"],
            "patient_name": patient["name"],
            "patient_email": patient["email"],
            "patient_phone": str(patient["phone"]),  # ensure string for Arrow
            "doctor": preferred_doctor,
            "location": "Main Clinic",
            "date": slot["date"].isoformat(),
            "start": slot["start_time"],
            "end": slot["end_time"],
            "duration": duration,
            "status": "confirmed",
            "reason": reason,
            "insurance_carrier": insurer or patient.get("primary_insurer", ""),
            "member_id": member_id or patient.get("member_id", ""),
            "group_no": group_no or patient.get("group_no", ""),
            "forms_sent_at": "",
            "forms_completed": False,
            "reminder1": "",
            "reminder2": "",
            "reminder3": "",
            "cancel_reason": "",
            "created_at": datetime.utcnow().isoformat(),
            "exported_at": ""
        }
        self.appointments_df = pd.concat([self.appointments_df, pd.DataFrame([appt])], ignore_index=True)

        # 6. Send confirmation
        self.messaging.send_confirmation(appt)

        # 7. Send intake form (per requirement only after confirmation)
        self.form_sender.send_form(appt["patient_email"], appt_id)
        self.appointments_df.loc[self.appointments_df.appt_id == appt_id, "forms_sent_at"] = datetime.utcnow().isoformat()

        return {
            "status": "ok",
            "message": f"Booked {preferred_doctor} on {slot['date'].isoformat()} {slot['start_time']}. Appointment ID: {appt_id}",
            "appt": appt
        }

    def export_appointments(self, path="data/appointments_export.xlsx"):
        self.appointments_df["exported_at"] = datetime.utcnow().isoformat()
        self.exporter.export(self.appointments_df)

    def trigger_reminders(self):
        """
        Simulate reminders:
        - R1: after 10s from booking
        - R2: after 20s
        - R3: after 30s
        (For demo only; in production this would be scheduled jobs)
        """
        now = datetime.utcnow()
        for idx, row in self.appointments_df.iterrows():
            created_at = datetime.fromisoformat(row["created_at"])
            delta = (now - created_at).total_seconds()
            appt_id = row["appt_id"]

            # Reminder 1
            if delta > 10 and not row["reminder1"]:
                self.messaging.send_reminder(row, 1)
                self.appointments_df.loc[idx, "reminder1"] = now.isoformat()

            # Reminder 2
            if delta > 20 and not row["reminder2"]:
                self.messaging.send_reminder(row, 2)
                self.appointments_df.loc[idx, "reminder2"] = now.isoformat()

            # Reminder 3
            if delta > 30 and not row["reminder3"]:
                self.messaging.send_reminder(row, 3)
                self.appointments_df.loc[idx, "reminder3"] = now.isoformat()
