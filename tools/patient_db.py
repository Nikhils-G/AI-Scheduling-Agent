# tools/patient_db.py
import pandas as pd
import difflib
import uuid
import re
import unicodedata
from datetime import datetime
from typing import Tuple, Dict, Optional

PHONE_RE = re.compile(r"\D+")

def _clean_text(s: Optional[str]) -> str:
    if s is None:
        return ""
    s = str(s).strip().lower()
    # normalize unicode (remove accents), remove punctuation, collapse whitespace
    s = unicodedata.normalize("NFKD", s)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    s = re.sub(r"[^\w\s]", " ", s)  # remove punctuation -> spaces
    s = re.sub(r"\s+", " ", s).strip()
    return s

def _norm_phone(s: Optional[str]) -> str:
    if not s:
        return ""
    return PHONE_RE.sub("", str(s))

def _norm_dob(val) -> str:
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return ""
    try:
        # try pandas flexible parse
        dt = pd.to_datetime(val, errors='coerce')
        if pd.isna(dt):
            # fallback try plain iso parse
            return str(val)
        return dt.date().isoformat()
    except Exception:
        try:
            return datetime.fromisoformat(str(val)).date().isoformat()
        except Exception:
            return str(val)

class PatientDB:
    def __init__(self, csv_path: str):
        self.csv_path = csv_path
        try:
            self.df = pd.read_csv(csv_path, dtype=str)
        except Exception:
            cols = [
                "patient_id","name","dob","gender","email","phone","address","city","state","zip",
                "primary_insurer","member_id","group_no","preferred_doctor","is_returning","last_visit_date"
            ]
            self.df = pd.DataFrame(columns=cols)
            self._save()

        # ensure columns exist
        for c in ["email","phone","name","dob"]:
            if c not in self.df.columns:
                self.df[c] = ""

        # build normalized helper columns
        self._refresh_norm_columns()

    def _refresh_norm_columns(self):
        self.df["email_norm"] = self.df["email"].astype(str).apply(lambda x: (x or "").strip().lower())
        self.df["phone_norm"] = self.df["phone"].astype(str).apply(_norm_phone)
        self.df["name_norm"] = self.df["name"].astype(str).apply(_clean_text)
        self.df["dob_norm"] = self.df["dob"].apply(_norm_dob)

    def _save(self):
        # save original DataFrame (without helper cols)
        save_df = self.df.copy()
        for c in ["email_norm","phone_norm","name_norm","dob_norm"]:
            if c in save_df.columns:
                save_df.drop(columns=[c], inplace=True)
        save_df.to_csv(self.csv_path, index=False)

    def _new_patient_dict(self, name, dob, phone, email, preferred_doctor=None) -> Dict:
        new = {
            "patient_id": f"P{uuid.uuid4().hex[:6].upper()}",
            "name": name or "",
            "dob": pd.to_datetime(dob, errors='coerce').date().isoformat() if dob and not pd.isna(pd.to_datetime(dob, errors='coerce')) else (str(dob) if dob else ""),
            "gender": "",
            "email": email or "",
            "phone": phone or "",
            "address": "",
            "city": "",
            "state": "",
            "zip": "",
            "primary_insurer": "",
            "member_id": "",
            "group_no": "",
            "preferred_doctor": preferred_doctor or "",
            "is_returning": False,
            "last_visit_date": ""
        }
        return new

    def match_patient(self, name: str, dob, phone: Optional[str]=None, email: Optional[str]=None,
                      fuzzy_threshold: float = 0.65) -> Tuple[Dict, str, float]:
        """
        Returns (patient_dict, status, score)
        - patient_dict is ALWAYS a dict (matched or constructed)
        - status: "returning" or "new"
        - score: 0.0..1.0 confidence
        """
        name_q = _clean_text(name or "")
        email_q = (email or "").strip().lower()
        phone_q = _norm_phone(phone or "")
        dob_q = _norm_dob(dob)

        # 1) exact email
        if email_q:
            rows = self.df[self.df["email_norm"] == email_q]
            if not rows.empty:
                return (rows.iloc[0].to_dict(), "returning", 1.0)

        # 2) exact phone
        if phone_q:
            rows = self.df[self.df["phone_norm"] == phone_q]
            if not rows.empty:
                return (rows.iloc[0].to_dict(), "returning", 1.0)

        # 3) fuzzy name with DOB boost
        best = None
        best_score = 0.0
        for _, row in self.df.iterrows():
            row_name = row.get("name_norm", "")
            if not row_name and not name_q:
                continue
            name_score = difflib.SequenceMatcher(None, name_q, row_name).ratio() if name_q else 0.0
            dob_score = 1.0 if (dob_q and str(row.get("dob_norm","")) == dob_q) else 0.0
            combined = 0.7 * name_score + 0.3 * dob_score
            if combined > best_score:
                best_score = combined
                best = row

        if best is not None and best_score >= float(fuzzy_threshold):
            return (best.to_dict(), "returning", round(float(best_score), 3))

        # fallback -> new (return constructed dict)
        return (self._new_patient_dict(name, dob, phone, email), "new", 0.0)

    def debug_candidates(self, name: str, dob, top_k:int=10):
        """Return top candidates with scores for inspection."""
        name_q = _clean_text(name or "")
        dob_q = _norm_dob(dob)
        cands = []
        for _, row in self.df.iterrows():
            row_name = row.get("name_norm","")
            name_score = difflib.SequenceMatcher(None, name_q, row_name).ratio() if name_q else 0.0
            dob_score = 1.0 if (dob_q and str(row.get("dob_norm","")) == dob_q) else 0.0
            combined = 0.7 * name_score + 0.3 * dob_score
            cands.append({
                "patient_id": row.get("patient_id"),
                "name": row.get("name"),
                "dob_norm": row.get("dob_norm"),
                "name_score": round(name_score,3),
                "combined": round(combined,3)
            })
        cands.sort(key=lambda x: x["combined"], reverse=True)
        return cands[:top_k]

    def create_patient(self, name, dob, phone, email, preferred_doctor):
        new_row = self._new_patient_dict(name, dob, phone, email, preferred_doctor)
        # append to df
        self.df = pd.concat([self.df, pd.DataFrame([new_row])], ignore_index=True)
        # refresh helper columns and save
        self._refresh_norm_columns()
        self._save()
        return new_row

    def get_patient(self, patient_id: str) -> Optional[Dict]:
        r = self.df[self.df.get("patient_id","") == patient_id]
        return r.iloc[0].to_dict() if not r.empty else None
