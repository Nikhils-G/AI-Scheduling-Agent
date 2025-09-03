import pandas as pd
from datetime import datetime
import difflib
import uuid

class PatientDB:
    def __init__(self, csv_path):
        self.csv_path = csv_path
        try:
            self.df = pd.read_csv(csv_path, parse_dates=["dob","last_visit_date"], dayfirst=False)
        except Exception:
            self.df = pd.DataFrame(columns=[
                "patient_id","name","dob","gender","email","phone","address","city","state","zip",
                "primary_insurer","member_id","group_no","preferred_doctor","is_returning","last_visit_date"
            ])
            self.df.to_csv(self.csv_path, index=False)

    def _save(self):
        self.df.to_csv(self.csv_path, index=False)

    def match_patient(self, name, dob, phone=None, email=None):
        """Return (patient_dict, 'new'|'returning', score)"""
        # exact matches by email or phone or name+dob
        dob_val = pd.to_datetime(dob).date()
        if email:
            row = self.df[self.df['email'].astype(str).str.lower()==email.lower()]
            if not row.empty:
                return (row.iloc[0].to_dict(), "returning", 1.0)
        if phone:
            row = self.df[self.df['phone'].astype(str).str.replace(r"\D","",regex=True)==''.join(filter(str.isdigit, phone))]
            if not row.empty:
                return (row.iloc[0].to_dict(), "returning", 1.0)
        # name + dob fuzzy
        candidates = []
        for idx, r in self.df.iterrows():
            try:
                r_dob = pd.to_datetime(r["dob"]).date()
            except Exception:
                continue
            name_score = difflib.SequenceMatcher(None, str(r["name"]).lower(), name.lower()).ratio()
            if r_dob == dob_val and name_score > 0.7:
                return (r.to_dict(), "returning", name_score)
            candidates.append((r.to_dict(), name_score))
        # fallback: no match
        return (None, "new", 0.0)

    def create_patient(self, name, dob, phone, email, preferred_doctor):
        pid = f"P{uuid.uuid4().hex[:6].upper()}"
        row = {
            "patient_id": pid,
            "name": name,
            "dob": pd.to_datetime(dob).date(),
            "gender": "",
            "email": email,
            "phone": phone,
            "address": "",
            "city": "",
            "state": "",
            "zip": "",
            "primary_insurer": "",
            "member_id": "",
            "group_no": "",
            "preferred_doctor": preferred_doctor,
            "is_returning": False,
            "last_visit_date": ""
        }
        self.df = pd.concat([self.df, pd.DataFrame([row])], ignore_index=True)
        self._save()
        return row

    def get_patient(self, patient_id):
        r = self.df[self.df.patient_id==patient_id]
        return r.iloc[0].to_dict() if not r.empty else None
