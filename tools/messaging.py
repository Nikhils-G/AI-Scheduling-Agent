import json
from datetime import datetime

class Messaging:
    def __init__(self, log_path="data/messaging.log"):
        self.log_path = log_path

    def _log(self, payload):
        line = json.dumps({"ts": datetime.utcnow().isoformat(), **payload})
        with open(self.log_path, "a") as f:
            f.write(line + "\n")

    def send_confirmation(self, appointment):
        payload = {
            "type": "confirmation",
            "to_email": appointment.get("patient_email"),
            "to_phone": appointment.get("patient_phone"),
            "appt_id": appointment.get("appt_id"),
            "message": f"Confirmed: {appointment.get('doctor')} on {appointment.get('date')} {appointment.get('start')}",
        }
        self._log(payload)
        return True

    def send_reminder(self, appointment, reminder_number=1):
        payload = {
            "type": "reminder",
            "reminder_number": reminder_number,
            "to_email": appointment.get("patient_email"),
            "to_phone": appointment.get("patient_phone"),
            "appt_id": appointment.get("appt_id"),
            "message": f"Reminder {reminder_number} for appt {appointment.get('appt_id')}"
        }
        self._log(payload)
        return True

    def send_sms(self, phone, text):
        payload = {"type":"sms","to":phone,"message":text}
        self._log(payload)
        return True

    def send_email(self, email, subject, body, attachments=None):
        payload = {"type":"email","to":email,"subject":subject,"body":body,"attachments":attachments or []}
        self._log(payload)
        return True
