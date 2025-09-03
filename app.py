import streamlit as st
from datetime import date
from tools.patient_db import PatientDB
from tools.schedule_excel import ScheduleExcel
from tools.messaging import Messaging
from tools.export_excel import Exporter
from tools.forms import FormSender
from graph import Orchestrator

st.set_page_config(page_title=" AI Scheduling Agent ", layout="wide")

# Initialize tools
PATIENT_CSV = "data/patients.csv"
SCHEDULE_XLSX = "data/schedules.xlsx"
INTAKE_PDF = "data/intake_form.pdf"
APPT_EXPORT = "data/appointments_export.xlsx"
LOG_FILE = "data/messaging.log"

patient_db = PatientDB(PATIENT_CSV)
schedule_tool = ScheduleExcel(SCHEDULE_XLSX)
messaging = Messaging(log_path=LOG_FILE)
exporter = Exporter(APPT_EXPORT)
form_sender = FormSender(INTAKE_PDF)

# keep orchestrator persistent in Streamlit session
if "orch" not in st.session_state:
    st.session_state["orch"] = Orchestrator(patient_db, schedule_tool, messaging, exporter, form_sender)
orch = st.session_state["orch"]

# Extra UI polish
st.markdown("""
<style>
    /* General font & background */
    body, .stApp {
        font-family: 'Segoe UI', sans-serif;
        background: #f9fbfd;
    }

    /* Main header */
    .main-header {
        font-size: 3.2rem !important;
        font-weight: 700;
        text-align: center;
        background: linear-gradient(90deg, #2c3e50, #3498db);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 1rem;
        animation: fadeInDown 1s ease-in-out;
    }

    /* Section headers */
    .section-header {
        font-size: 1.6rem;
        font-weight: 600;
        color: #34495e;
        border-left: 5px solid #3498db;
        padding-left: 0.6rem;
        margin-top: 2rem;
        margin-bottom: 1rem;
        animation: fadeIn 1s ease-in;
    }

    /* Divider animation */
    .divider {
        border-top: 2px dashed #d0d7de;
        margin: 1.5rem 0;
        animation: grow 1.2s ease-in-out;
    }

    /* Card-style containers */
    .stContainer {
        background: white;
        padding: 1.2rem;
        border-radius: 12px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.05);
        transition: 0.3s ease;
    }
    .stContainer:hover {
        box-shadow: 0 4px 18px rgba(0,0,0,0.1);
        transform: translateY(-2px);
    }

    /* Buttons */
    button[kind="primary"], .stButton>button {
        background: linear-gradient(135deg, #3498db, #2980b9);
        color: white !important;
        border-radius: 10px;
        padding: 0.6rem 1.2rem;
        font-weight: 600;
        border: none;
        transition: all 0.25s ease;
    }
    .stButton>button:hover {
        transform: scale(1.05);
        background: linear-gradient(135deg, #2980b9, #1f618d);
    }

    /* Animations */
    @keyframes fadeIn {
        from {opacity: 0;}
        to {opacity: 1;}
    }
    @keyframes fadeInDown {
        from {opacity: 0; transform: translateY(-20px);}
        to {opacity: 1; transform: translateY(0);}
    }
    @keyframes grow {
        from {width: 0;}
        to {width: 100%;}
    }
</style>
""", unsafe_allow_html=True)


# Header
st.markdown('<p class="main-header">AI Scheduling Agent</p>', unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.markdown("### Admin Panel")
    st.markdown("---")
    if st.button("Export Appointments", use_container_width=True):
        orch.export_appointments()
        st.success(f"Exported to {APPT_EXPORT}")
    if st.button("Run Reminder Simulation", use_container_width=True):
        orch.trigger_reminders()
        st.success("Reminders checked & sent (if due).")
    st.markdown("---")
    st.markdown("**Messaging Log:**")
    if st.button("Show Log", use_container_width=True):
        try:
            st.code(open(LOG_FILE).read())
        except FileNotFoundError:
            st.info("No logs yet.")

# Main content
st.markdown('<div class="section-header">Booking Flow</div>', unsafe_allow_html=True)
col1, col2 = st.columns([2, 1])

with col1:
    with st.container():
        st.markdown("#### Patient Details")
        name = st.text_input("Full name", key="name")
        dob = st.date_input("Date of birth", value=date(1990,1,1),min_value=date(1950, 1, 1),
    max_value=date(2025, 12, 31), key="dob")
        phone = st.text_input("Phone number", key="phone")
        email = st.text_input("Email", key="email")
        doctor = st.selectbox("Preferred doctor", schedule_tool.list_doctors(), key="doctor")
        reason = st.text_area("Reason for visit (short)", key="reason", help="Chief complaint")

    with st.container():
        st.markdown("#### Insurance Details")
        insurer = st.text_input("Insurance carrier", key="insurer")
        member_id = st.text_input("Member ID", key="member_id")
        group_no = st.text_input("Group Number", key="group_no")

    # ------------------- Slot selection with AI suggestion -------------------
    st.markdown("#### Select Appointment Slot")
    days = schedule_tool.upcoming_days(7)
    selected_day = st.selectbox("Select Day", days, key="day_for_booking")

    # default suggestion values
    predicted_status = None
    predicted_duration = None
    suggestion_text = "No suggestion yet"

    # Only call match when user entered at least one identifying field
    if any([name.strip(), email.strip(), phone.strip()]):
        try:
            patient_match, status, score = patient_db.match_patient(name.strip(), dob, phone.strip(), email.strip())
            # DEBUG UI: show matcher result + candidate list (helps debug fuzzy failures)
            try:
                st.caption(f"DEBUG: matcher -> status={status}, score={score}, matched_id={patient_match.get('patient_id') if patient_match else None}")
                top_candidates = patient_db.debug_candidates(name.strip(), dob, top_k=5)
                st.write("DEBUG candidates:", top_candidates)
            except Exception:
                # If debug helpers are missing or fail, ignore the debug display
                pass

            predicted_status = status
            predicted_duration = 60 if status == "new" else 30
            suggestion_text = f"Agent suggests {predicted_duration}m slot (patient: {status})"
        except Exception as e:
            # If match fails for any reason, keep suggestion empty but do not crash UI
            suggestion_text = "Agent suggestion unavailable"

    st.markdown(f"**Suggestion:** {suggestion_text}")

    # load available slots for chosen doctor/day
    slots = schedule_tool.available_slots(doctor, selected_day)
    slot_choice = None

    if not slots:
        st.info("No available slots for that day/doctor.")
    else:
        # build readable labels
        slot_labels = []
        for s in slots:
            # try to build robust label even if keys vary
            date_label = str(s.get("date", ""))
            start = str(s.get("start_time", s.get("start", "")))
            end = str(s.get("end_time", s.get("end", "")))
            length = s.get("slot_length")
            # fallback to duration or compute if missing
            if length is None:
                length = s.get("duration", "")
            slot_labels.append(f"{date_label} {start} - {end} ({length}m)")

        # find first slot matching predicted_duration (if we have one)
        suggested_index = None
        if predicted_duration is not None:
            for i, s in enumerate(slots):
                try:
                    length = int(s.get("slot_length", s.get("duration", 0)))
                except Exception:
                    try:
                        length = int(str(s.get("slot_length", "")).split()[0])
                    except Exception:
                        length = None
                if length == int(predicted_duration):
                    suggested_index = i
                    break

        # display selectbox with pre-selected suggestion if any
        if suggested_index is not None:
            chosen_idx = st.selectbox("Available Slots (agent suggested one)", range(len(slots)),
                                      format_func=lambda i: slot_labels[i],
                                      index=suggested_index, key="slot_select_idx")
        else:
            chosen_idx = st.selectbox("Available Slots", range(len(slots)),
                                      format_func=lambda i: slot_labels[i], key="slot_select_idx")

        slot_choice = slots[chosen_idx]
        # show small note so user knows why it was suggested
        if suggested_index is not None and chosen_idx == suggested_index:
            st.success("Suggested slot selected by agent (you can change it).")
        elif suggested_index is not None:
            st.info("Agent suggested a different slot; you selected another.")
    # -------------------------------------------------------------------------

    if st.button("Start booking", key="booking_btn", use_container_width=True):
        result = orch.start_booking(
            name=name.strip(),
            dob=dob,
            phone=phone.strip(),
            email=email.strip(),
            preferred_doctor=doctor,
            reason=reason.strip(),
            insurer=insurer.strip(),
            member_id=member_id.strip(),
            group_no=group_no.strip(),
            slot=slot_choice  # NEW
        )
        st.session_state["last_result"] = result
        if result["status"] == "ok":
            st.success(result["message"])
        else:
            st.error(result["message"])

    if "last_result" in st.session_state:
        res = st.session_state["last_result"]
        st.markdown("#### Last Action Result")
        st.json(res)

with col2:
    st.markdown("#### Doctor Availability")
    doc = st.selectbox("Select Doctor", schedule_tool.list_doctors(), key="doc_side")
    days = schedule_tool.upcoming_days(7)
    selected_day = st.selectbox("Select Day", days, key="day_side")
    slots = schedule_tool.available_slots(doc, selected_day)
    if slots:
        for s in slots[:15]:
            st.write(f"{s['date']} {s['start_time']} - {s['end_time']} ({s['slot_length']}m)")
        if len(slots) > 15:
            st.info(f"Showing 15 of {len(slots)} available slots")
    else:
        st.info("No available slots for that day.")

st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
st.markdown("#### Manual Actions")
c1, c2, c3 = st.columns(3)
with c1:
    if st.button("Send Test Reminder (R1)", use_container_width=True):
        if orch.appointments_df.empty:
            st.info("No appointments to remind.")
        else:
            appt = orch.appointments_df.iloc[-1].to_dict()
            messaging.send_reminder(appt, 1)
            st.success("Reminder sent (logged).")
with c2:
    if st.button("Send Intake Form", use_container_width=True):
        if orch.appointments_df.empty:
            st.info("No appointments.")
        else:
            appt = orch.appointments_df.iloc[-1].to_dict()
            form_sender.send_form(appt["patient_email"], appt["appt_id"])
            st.success("Form send simulated.")
with c3:
    if st.button("Show Appointments", use_container_width=True):
        st.dataframe(orch.appointments_df.astype(str))

st.markdown("---")
st.caption("This demo app uses file-backed CSV/XLSX for storage. It's intentionally simple for easy review.")
