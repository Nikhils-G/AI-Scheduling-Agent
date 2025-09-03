import os
import shutil
from datetime import datetime

class FormSender:
    def __init__(self, intake_pdf_path, out_folder="data/forms_sent"):
        self.intake_pdf_path = intake_pdf_path
        self.out_folder = out_folder
        os.makedirs(out_folder, exist_ok=True)

    def send_form(self, patient_email, appt_id):
        """
        Simulate sending form: copy the intake PDF to data/forms_sent/<appt_id>_intake.pdf
        and log a small metadata file.
        """
        if not os.path.exists(self.intake_pdf_path):
            raise FileNotFoundError("Intake PDF not found.")
        dest = os.path.join(self.out_folder, f"{appt_id}_intake.pdf")
        shutil.copyfile(self.intake_pdf_path, dest)
        # write metadata
        meta = {
            "appt_id": appt_id,
            "patient_email": patient_email,
            "sent_at": datetime.utcnow().isoformat(),
            "file": dest
        }
        with open(os.path.join(self.out_folder, f"{appt_id}_meta.json"), "w") as f:
            import json
            json.dump(meta, f, indent=2)
        return dest
