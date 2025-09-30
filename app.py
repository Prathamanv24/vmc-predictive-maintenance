
import streamlit as st
import pandas as pd
from datetime import datetime, date
from pathlib import Path
import os

# --- Simple user login system ---
USERS = {
    "companyA": "pass123",
    "companyB": "vmc456",
    "companyC": "maint789",
    "companyD": "tool321",
    "companyE": "life999"
}

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.company = None

if not st.session_state.logged_in:
    st.title("🔑 Company Login")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        if username in USERS and USERS[username] == password:
            st.session_state.logged_in = True
            st.session_state.company = username
            st.success(f"✅ Logged in as {username}")
        else:
            st.error("❌ Invalid username or password")
    st.stop()

# --- Set company-specific folder ---
COMPANY = st.session_state.company
DATA_FOLDER = os.path.join("data", COMPANY)
os.makedirs(DATA_FOLDER, exist_ok=True)

# Update your file paths to save under this company folder
FILES = {
    "shift": os.path.join(DATA_FOLDER, "shift.csv"),
    "production": os.path.join(DATA_FOLDER, "production.csv"),
    "checklist": os.path.join(DATA_FOLDER, "checklist.csv"),
    "problems": os.path.join(DATA_FOLDER, "problems.csv"),
    "tools": os.path.join(DATA_FOLDER, "tools.csv"),
    "logbook": os.path.join(DATA_FOLDER, "logbook.csv"),
}

# -----------------------------
# App Config
# -----------------------------
st.set_page_config(page_title="VMC Predictive Maintenance Assistant", layout="wide")
st.title("🛠️ VMC Predictive Maintenance Assistant")
st.caption("Shift checklists • Tool/Spindle life • Troubleshooting • Handover & Logbook")

DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)

FILES = {
    "checklists": DATA_DIR / "checklists.csv",
    "production": DATA_DIR / "production.csv",
    "tools": DATA_DIR / "tools.csv",
    "diagnostics": DATA_DIR / "diagnostics.csv",
    "handover": DATA_DIR / "handover.csv"
}

# -----------------------------
# Helpers
# -----------------------------
def init_csv(path: Path, cols: list):
    if not path.exists():
        pd.DataFrame(columns=cols).to_csv(path, index=False)

def save_row(path: Path, row: dict):
    df = pd.read_csv(path) if path.exists() else pd.DataFrame()
    df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
    # pandas writes utf-8 by default
    df.to_csv(path, index=False)

# Initialize storage
init_csv(FILES["checklists"], [
    "timestamp","shift_date","shift","operator","machine_id","phase",
    # before
    "power_ok","tooling_setup_ok","workpiece_setup_ok",
    "coolant_ok","lubrication_ok","cleanliness_ok","safety_ok",
    "home_positions_ok","program_ok","spindle_ok","air_ok",
    # after
    "tool_wear_check","dimension_check","coolant_topup","chip_cleaning",
    "machine_condition","program_logs","shutdown_ok","faults_reported",
    "notes"
])

init_csv(FILES["production"], [
    "timestamp","shift_date","shift","operator","machine_id",
    "job_id","material","parts_done","avg_cycle_time_min","scrap_count","notes"
])

init_csv(FILES["tools"], [
    "timestamp","shift_date","shift","operator","machine_id",
    "tool_id","tool_name","expected_minutes","minutes_used_today","minutes_used_total",
    "expected_cycles","cycles_used_today","cycles_used_total","status","notes"
])

init_csv(FILES["diagnostics"], [
    "timestamp","shift_date","shift","operator","machine_id",
    "issue_text","matched_issue","severity","operator_can_fix","actions",
    "tool_hours_left","spindle_hours_left","notes"
])

init_csv(FILES["handover"], [
    "timestamp","shift_date","shift","operator","machine_id",
    "prev_parts_done","prev_avg_cycle","prev_notes","incoming_notes"
])

# -----------------------------
# Knowledge Base (VMC issues → causes/steps/escalation)
# -----------------------------
KB = [
    # (name, keywords, causes, op_steps, when_escalate, esc_steps)
    ("tool wear / dull tool",
     ["tool wear","worn tool","dull","burr","poor finish","blunt"],
     ["Tool life reached","Incorrect speed/feed","Poor coolant direction","Hard material/scale"],
     ["Pause cycle and inspect edge","Replace/resharpen tool and set offset",
      "Reduce feed/speed by 10–20%","Aim coolant at cutting zone"],
     "Frequent wear/breakage persists after corrections",
     ["Check holder/collet clamping & balance","Measure spindle runout","Maintenance to check ATC alignment & spindle"]),
    ("tool breakage",
     ["tool break","broken tool","snap","fracture"],
     ["Too aggressive DOC/feed","Interrupted cut/chatter","Wrong tool material/geometry"],
     ["Stop machine; remove fragments","Load fresh tool, set offset",
      "Reduce DOC/feed; add ramping/pecking","Increase coolant flow / through-tool if available"],
     "Repeated breakage or damage to holder/spindle taper",
     ["Inspect holder & taper surfaces","Check runout/balance","Maintenance spindle inspection"]),
    ("chatter / vibration on cut",
     ["chatter","vibration","buzz","machine shaking","resonance"],
     ["Imbalanced tool / excessive overhang","Resonant spindle speed","Loose workholding/fixtures"],
     ["Tighten workholding and fixtures","Clean tapers; re-seat tool",
      "Change spindle speed ±10–20% to avoid resonance","Shorten tool overhang if possible"],
     "Chatter persists across tools/speeds",
     ["Maintenance to check spindle bearings/alignment","Dynamic balance test on tool/holder"]),
    ("poor surface finish",
     ["poor surface","rough finish","tool marks","lines on surface","finish bad"],
     ["Dull tool","Chatter/looseness","Incorrect feed/speed","Coolant misdirection"],
     ["Replace/inspect tool","Tighten clamps/fixtures",
      "Adjust feed/speed per tool chart","Add finishing pass with lighter cut"],
     "Finish poor after corrections",
     ["Check spindle runout and axis backlash","Maintenance to tune servo/inspect ballscrews"]),
    ("burr formation / edge not clean",
     ["burr","sharp edges","edge not clean","ragged edge"],
     ["Tool dullness","Incorrect chip load","Material smearing"],
     ["Increase feed slightly for shearing","Use sharper tool/geometry","Add dedicated deburr pass"],
     "Persistent burr despite parameter and tool changes",
     ["Investigate material condition/heat treatment","Check runout and tool alignment"]),
    ("spindle overheating",
     ["overheat","hot spindle","thermal alarm","high temperature"],
     ["Insufficient lubrication","Blocked coolant","Aggressive parameters","Bearing degradation"],
     ["Reduce load (feed/DOC)","Verify coolant flow; clean filters/nozzles","Run cool-down for 5–10 minutes"],
     "Temp remains high or alarm reappears",
     ["Maintenance to inspect lube system & bearings","Check motor fan/heat exchanger"]),
    ("spindle abnormal noise",
     ["spindle noise","rattling","whine","grinding"],
     ["Bearing wear","Unbalanced tool","Loose taper/holder"],
     ["Stop and inspect tool/holder","Clean & re-seat taper surfaces","Test run at lower RPM; observe"],
     "Noise persists with different tools/speeds",
     ["Maintenance bearing condition check","Runout and vibration analysis"]),
    ("axis backlash / position error",
     ["backlash","position error","accuracy issue","servo alarm","repeatability issue"],
     ["Loose couplings/ballscrew wear","Encoder fault","Servo tuning drift"],
     ["Re-home machine; verify zeros","Check fixtures for looseness","Run test part at reduced feed"],
     "Repeated errors or accuracy out of spec",
     ["Maintenance to check encoders/couplings/ballscrew preload","Servo tuning & alignment check"]),
    ("coolant flow issue / no coolant",
     ["no coolant","coolant not flowing","coolant pump off","dry cutting","coolant low"],
     ["Low tank level","Clogged filters/nozzles","Pump/valve failure"],
     ["Refill tank; set correct concentration","Clean/replace filters; clear nozzles","Ensure pump on/valves open"],
     "Pump will not start or flow not restored",
     ["Maintenance to test pump motor/wiring","Inspect valves/seals"]),
    ("coolant leakage",
     ["coolant leak","coolant on floor","leaking hose","coolant dripping"],
     ["Loose fittings","Cracked hose/pipe","Seal failure"],
     ["Tighten fittings","Replace damaged hoses","Use drip tray and clean area"],
     "Leak continues or source unknown",
     ["Maintenance to pressure test lines","Replace seals/fittings as needed"]),
    ("hydraulic pressure low / leak",
     ["hydraulic leak","low pressure","clamp failure","unclamp issue"],
     ["Low fluid level","Damaged seals/hoses","Pump/valve malfunction"],
     ["Top up hydraulic oil","Avoid operation until pressure stable","Inspect for visible leaks"],
     "Pressure unstable or significant leak",
     ["Maintenance to replace seals/hoses","Test pump/valves"]),
    ("ATC tool change stuck",
     ["atc stuck","tool change error","magazine jam","gripper stuck","toolchanger jam"],
     ["Sensor misread","Air pressure low","Mechanical jam"],
     ["Reset ATC per SOP","Check air supply and pressure","Clear chips from carousel/arm","Lubricate moving parts"],
     "Stuck repeatedly or alarms persist",
     ["Maintenance to adjust sensors/actuators","Inspect gripper and alignment"]),
    ("electrical trip / breaker",
     ["power trip","breaker trip","short circuit","overload"],
     ["Supply instability","Shorted cable/motor","Overcurrent from jam"],
     ["Power cycle after 2 minutes","Inspect for burnt smell/visible damage","Run machine idle to observe"],
     "Trips reoccur or visible damage present",
     ["Electrician to test supply quality/insulation","Investigate motor windings"]),
    ("voltage fluctuation / low voltage",
     ["voltage drop","low voltage","flicker","brownout"],
     ["Utility fluctuation","Undersized cabling","Loose terminals"],
     ["Use stabilizer/UPS where applicable","Tighten terminals (qualified personnel)","Reduce non-essential loads"],
     "Frequent fluctuations affecting machining",
     ["Electrical team to analyze feeder and grounding"]),
    ("program error / alarm",
     ["program error","g-code error","macro error","alarm","nc alarm"],
     ["Syntax error or wrong modal state","Wrong tool number/offset","Work offset mismatch"],
     ["Simulate program; dry run","Verify tool/offset table","Re-post with correct post-processor"],
     "Alarms persist with correct data",
     ["Review controller diagnostics","Escalate to NC programmer/maintenance"]),
    ("dimension out of tolerance",
     ["dimension out","oversize","undersize","tolerance fail","size variation"],
     ["Tool wear or runout","Thermal growth","Incorrect tool comp"],
     ["Update tool wear comp","Perform thermal compensation/warm-up","Add finish pass with lighter DOC"],
     "Variation remains high after actions",
     ["Inspect spindle runout and axis backlash","Fixture/part stability review"]),
    ("poor clamping / part movement",
     ["part moved","clamp loose","fixture slip","jaw slip"],
     ["Insufficient clamp force","Chip under clamp","Wrong jaws/soft jaws"],
     ["Re-clamp; clean contact areas","Use torque wrench where applicable","Verify jaw selection and seating"],
     "Repeated movement or marks on part",
     ["Fixture redesign or maintenance check","Hydraulic/pneumatic clamping check"]),
    ("chip evacuation issue",
     ["chip jam","chips clogging","conveyor jam","chip build-up"],
     ["Low coolant flow","Conveyor jam","Inadequate chip break"],
     ["Increase coolant/chip flush","Clear conveyor guards; restart","Use chip-breaking cycle/program"],
     "Persistent jamming or motor trips",
     ["Maintenance to service conveyor","Review toolpath for chip control"]),
    ("es top / interlock issues",
     ["e-stop stuck","interlock fault","guard error","safety interlock"],
     ["Damaged button/contact","Sensor misalignment","Wiring fault"],
     ["Reset or twist-release per SOP","Inspect sensor alignment (door)","If unresolved, stop use and escalate"],
     "Any uncertainty with safety devices",
     ["Immediate maintenance escalation; lockout/tagout"]),
    ("air pressure low",
     ["air pressure low","pneumatic low","air leak","air failure"],
     ["Compressor issue","Leak in lines","Regulator setting"],
     ["Check compressor status","Listen for leaks; tighten fittings","Set regulator per spec"],
     "Air cannot be maintained",
     ["Maintenance to test valves/regulators","Leak test with soapy water"]),
    ("spindle orientation error",
     ["spindle orient error","orient alarm","orient fault"],
     ["Encoder fault","Parameter drift","Drive issue"],
     ["Power cycle; re-home","Check program/toolchange conditions","Reduce load and retry"],
     "Error repeats frequently",
     ["Maintenance to check encoder/drive parameters"]),
    ("thermal growth affecting accuracy",
     ["thermal growth","warmup not done","drift with time"],
     ["No warm-up cycle","High continuous load","Ambient temp variation"],
     ["Run spindle warm-up routine","Schedule cool-down intervals","Enable thermal comp if available"],
     "Accuracy still drifts after warm-up",
     ["Maintenance to verify compensation tables"]),
    ("probe / measurement error",
     ["probe not triggering","probe error","touch probe issue","probing alarm"],
     ["Dirty stylus","Wrong calibration","Cable/battery issue"],
     ["Clean/replace stylus tip","Recalibrate probe","Check battery/cable"],
     "Probe unreliable across parts",
     ["Maintenance to service probe system"]),
    ("axis overtravel / soft limit",
     ["overtravel","soft limit","limit alarm"],
     ["Work offset wrong","Programmed move beyond limits","Tool length/fixture error"],
     ["Check work offsets and tool length","Jog back within range","Adjust program/toolpath"],
     "Repeat overtravels with correct data",
     ["Maintenance to verify limit switches/parameters"]),
    ("tool pick/place error (ATC)",
     ["wrong tool picked","tool pocket mismatch","tool id error"],
     ["Tool table mismatch","Pocket sensor fault","Magazine mapping error"],
     ["Verify tool table vs program","Re-map pocket numbers","Clear chips in pockets"],
     "Recurrent mismatch",
     ["Maintenance to tune pocket sensors & mapping"]),
]

# -----------------------------
# RUL (Remaining Useful Life) Estimation
# -----------------------------
def estimate_rul(spindle_hours, tool_cycles, avg_temp_c, vibration_mm_s, coolant_ok, last_service_h):
    BASE_TOOL_LIFE_CYCLES = 500.0
    BASE_SPINDLE_LIFE_H = 8000.0
    tool_factor = 1.0 + (0.2 if avg_temp_c>60 else 0) + (0.15 if vibration_mm_s>3 else 0) + (0.25 if not coolant_ok else 0)
    spindle_factor = 1.0 + (0.15 if avg_temp_c>60 else 0) + (0.2 if vibration_mm_s>3 else 0) + (0.1 if last_service_h>1000 else 0)
    tool_left_cycles = max(0.0, BASE_TOOL_LIFE_CYCLES - tool_cycles*tool_factor)
    tool_left_hours = round(tool_left_cycles*0.25,1)  # assume avg 0.25 min per cycle
    spindle_left_hours = round(max(0.0, BASE_SPINDLE_LIFE_H - spindle_hours*spindle_factor),1)
    return tool_left_hours, spindle_left_hours, round(tool_factor,2), round(spindle_factor,2)

# -----------------------------
# Sidebar (Shift context)
# -----------------------------
with st.sidebar:
    st.subheader("Shift Info")
    shift_date = st.date_input("Shift Date", value=date.today())
    shift = st.selectbox("Shift", ["A","B","C"])
    operator = st.text_input("Operator Name")
    machine_id = st.text_input("Machine ID", value="VMC-101")
    st.markdown("---")
    st.caption("All data saved locally in ./data/*.csv (UTF-8).")

# -----------------------------
# Tabs
# -----------------------------
tabs = st.tabs([
    "1) Handover Snapshot",
    "2) Before Shift Checklist",
    "3) Production Log",
    "4) Troubleshooting Assistant",
    "5) After Shift & Shutdown",
    "6) Tools & Life Tracking",
    "7) Logbook / Export"
])

# 1) Handover
with tabs[0]:
    st.header("Handover Snapshot — Previous Shift")
    prod_df = pd.read_csv(FILES["production"]) if FILES["production"].exists() else pd.DataFrame()
    prev = prod_df[prod_df["machine_id"]==machine_id].tail(10)
    if prev.empty:
        st.info("No previous production entries for this machine.")
    else:
        st.dataframe(prev)

    st.subheader("Record Handover Notes")
    col1, col2 = st.columns(2)
    prev_parts_done = col1.number_input("Previous shift parts done (from report)", min_value=0, step=1)
    prev_avg_cycle = col2.number_input("Previous shift avg cycle (min)", min_value=0.0, step=0.1)
    prev_notes = st.text_area("Previous shift notes / alarms (copy from log)")
    incoming_notes = st.text_area("Incoming operator notes / plan")
    if st.button("Save Handover Record"):
        save_row(FILES["handover"], {
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "shift_date": str(shift_date),
            "shift": shift,
            "operator": operator,
            "machine_id": machine_id,
            "prev_parts_done": prev_parts_done,
            "prev_avg_cycle": prev_avg_cycle,
            "prev_notes": prev_notes,
            "incoming_notes": incoming_notes
        })
        st.success("Handover saved.")

# 2) Before Shift
with tabs[1]:
    st.header("Before Shift Checklist")
    col1, col2 = st.columns(2)
    with col1:
        power_ok = st.checkbox("Machine power & control panel OK")
        tooling_setup_ok = st.checkbox("Tooling setup (tightness/calibration/correctness) OK")
        workpiece_setup_ok = st.checkbox("Workpiece clamping/positioning/alignment OK")
        coolant_ok = st.checkbox("Coolant reservoir OK")
        lubrication_ok = st.checkbox("Lubrication oil level & flow OK")
        cleanliness_ok = st.checkbox("Machine bed & work area clean")
    with col2:
        safety_ok = st.checkbox("Safety devices (guards/interlocks/E-stops) OK")
        home_positions_ok = st.checkbox("Machine zero & home set")
        program_ok = st.checkbox("CNC program loaded & verified")
        spindle_ok = st.checkbox("Spindle condition/noise OK")
        air_ok = st.checkbox("Air pressure OK (if applicable)")
    notes_before = st.text_area("Notes / observations (before shift)")
    if st.button("Save Before-Shift Checklist"):
        save_row(FILES["checklists"], {
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "shift_date": str(shift_date),"shift": shift,"operator": operator,"machine_id": machine_id,
            "phase": "before",
            "power_ok": power_ok,"tooling_setup_ok": tooling_setup_ok,"workpiece_setup_ok": workpiece_setup_ok,
            "coolant_ok": coolant_ok,"lubrication_ok": lubrication_ok,"cleanliness_ok": cleanliness_ok,"safety_ok": safety_ok,
            "home_positions_ok": home_positions_ok,"program_ok": program_ok,"spindle_ok": spindle_ok,"air_ok": air_ok,
            "tool_wear_check": None,"dimension_check": None,"coolant_topup": None,"chip_cleaning": None,
            "machine_condition": None,"program_logs": None,"shutdown_ok": None,"faults_reported": None,"notes": notes_before
        })
        st.success("Before-shift checklist saved.")

# 3) Production
with tabs[2]:
    st.header("Production Log (Shift)")
    c1, c2, c3 = st.columns(3)
    job_id = c1.text_input("Job/WO ID")
    material = c2.text_input("Material", value="Aluminium")
    parts_done = c3.number_input("Parts done (this entry)", min_value=0, step=1)
    avg_cycle_time_min = st.number_input("Average cycle time (min)", min_value=0.0, step=0.1)
    scrap_count = st.number_input("Scrap/rework count", min_value=0, step=1)
    prod_notes = st.text_area("Notes (production)")
    if st.button("Save Production Entry"):
        save_row(FILES["production"], {
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "shift_date": str(shift_date),"shift": shift,"operator": operator,"machine_id": machine_id,
            "job_id": job_id,"material": material,"parts_done": parts_done,
            "avg_cycle_time_min": avg_cycle_time_min,"scrap_count": scrap_count,"notes": prod_notes
        })
        st.success("Production entry saved.")
    st.subheader("Recent production")
    prod_df = pd.read_csv(FILES["production"]) if FILES["production"].exists() else pd.DataFrame()
    st.dataframe(prod_df[prod_df["machine_id"]==machine_id].tail(20))

# 4) Troubleshooting
with tabs[3]:
    st.header("Troubleshooting Assistant")
    st.caption("Enter one or more issues separated by commas. The bot will process them one by one.")
    issues_text = st.text_area("Describe issues", placeholder="e.g., tool wear problem, chatter, coolant leak")
    st.subheader("Machine context for severity & RUL")
    c1,c2,c3 = st.columns(3)
    spindle_hours = c1.number_input("Spindle hours (lifetime)", min_value=0.0, step=1.0, value=4200.0)
    tool_cycles = c2.number_input("Tool cycles (lifetime)", min_value=0.0, step=10.0, value=1450.0)
    avg_temp_c = c3.number_input("Average temp (°C)", min_value=0.0, step=0.5, value=58.0)
    c4,c5 = st.columns(2)
    vibration_mm_s = c4.number_input("Vibration (mm/s)", min_value=0.0, step=0.1, value=4.3)
    coolant_ok_flag = c5.selectbox("Coolant condition", ["OK","Not OK"]) == "OK"
    last_service_h = st.number_input("Hours since last service", min_value=0.0, step=10.0, value=1200.0)

    def find_kb(issue):
        t = issue.lower()
        for name, keywords, causes, ops, esc_when, esc_steps in KB:
            if any(kw in t for kw in keywords):
                return name, causes, ops, esc_when, esc_steps
        return ("general machining issue",
                ["Unclear description; need more detail","Check basic parameters & clamping"],
                ["Stop machine safely","Verify program, offsets, clamps, coolant","Retry at reduced feed"],
                "If symptoms persist or safety risk present",
                ["Escalate to maintenance","Document alarms and observed behavior"])

    if st.button("Diagnose Issues"):
        if not issues_text.strip():
            st.warning("Enter at least one issue.")
        else:
            txt = issues_text.lower()
            for sep in [" and ", ";", "|", "/", "\\"]:
                txt = txt.replace(sep, ",")
            issues = [p.strip() for p in txt.split(",") if p.strip()]

            tool_left_h, spindle_left_h, tf, sf = estimate_rul(spindle_hours, tool_cycles, avg_temp_c, vibration_mm_s, coolant_ok_flag, last_service_h)

            for i, issue in enumerate(issues, start=1):
                name, causes, ops, esc_when, esc_steps = find_kb(issue)
                # heuristic severity
                severity = "Low"
                if vibration_mm_s>4 or "overheat" in issue or "thermal" in issue:
                    severity = "High"
                elif avg_temp_c>55 or "leak" in issue:
                    severity = "Medium"

                operator_can_fix = not (name in ["axis backlash / position error","electrical trip / breaker","hydraulic pressure low / leak","ATC tool change stuck"] and severity!="Low")

                st.markdown(f"### Issue {i}: {name}")
                st.write(f"**Operator described:** _{issue}_")
                st.write(f"**Possible causes:** {', '.join(causes)}")
                st.write(f"**Severity:** {severity}")
                st.write(f"**Estimated RUL:** Tool ≈ **{tool_left_h} h**, Spindle ≈ **{spindle_left_h} h** (factors: tool {tf}, spindle {sf})")

                if operator_can_fix:
                    st.success("Operator can attempt the following steps:")
                    for step in ops:
                        st.write(f"- {step}")
                    actions = "; ".join(ops)
                else:
                    st.error("Complex/severe — escalate to maintenance.")
                    st.write("**Escalation steps:**")
                    for step in esc_steps:
                        st.write(f"- {step}")
                    actions = "; ".join(esc_steps)

                save_row(FILES["diagnostics"], {
                    "timestamp": datetime.now().isoformat(timespec="seconds"),
                    "shift_date": str(shift_date),"shift": shift,"operator": operator,"machine_id": machine_id,
                    "issue_text": issue,"matched_issue": name,"severity": severity,
                    "operator_can_fix": operator_can_fix,"actions": actions,
                    "tool_hours_left": tool_left_h,"spindle_hours_left": spindle_left_h,"notes": ""
                })

# 5) After Shift
with tabs[4]:
    st.header("After Shift Checklist & Shutdown")
    c1,c2 = st.columns(2)
    with c1:
        tool_wear_check = st.checkbox("Tools inspected for wear/damage")
        dimension_check = st.checkbox("Output dimensions verified")
        coolant_topup = st.checkbox("Coolant/lube topped up; leaks checked")
        chip_cleaning = st.checkbox("Chips/debris removed; holders cleaned")
    with c2:
        machine_condition = st.checkbox("No unusual noise/vibration/errors (uncheck if any)")
        program_logs = st.checkbox("Program status saved; alarms documented")
        shutdown_ok = st.checkbox("Proper shutdown & securing performed")
        faults_reported = st.checkbox("Faults (if any) communicated to next shift/maintenance")
    notes_after = st.text_area("Notes / observations (after shift)")
    if st.button("Save After-Shift Checklist"):
        save_row(FILES["checklists"], {
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "shift_date": str(shift_date),"shift": shift,"operator": operator,"machine_id": machine_id,
            "phase": "after",
            "power_ok": None,"tooling_setup_ok": None,"workpiece_setup_ok": None,
            "coolant_ok": None,"lubrication_ok": None,"cleanliness_ok": None,"safety_ok": None,
            "home_positions_ok": None,"program_ok": None,"spindle_ok": None,"air_ok": None,
            "tool_wear_check": tool_wear_check,"dimension_check": dimension_check,"coolant_topup": coolant_topup,"chip_cleaning": chip_cleaning,
            "machine_condition": machine_condition,"program_logs": program_logs,"shutdown_ok": shutdown_ok,"faults_reported": faults_reported,
            "notes": notes_after
        })
        st.success("After-shift checklist saved.")

# 6) Tools
with tabs[5]:
    st.header("Tools & Life Tracking")
    c1,c2,c3 = st.columns(3)
    tool_id = c1.text_input("Tool ID", placeholder="T05")
    tool_name = c2.text_input("Tool name", placeholder="Ø10 Endmill")
    expected_minutes = c3.number_input("Expected life (minutes)", min_value=0, step=10, value=500)
    c4,c5,c6 = st.columns(3)
    #minutes_today = c4.number_input("Minutes used (today)", min_value=0, step=5, value=0)
    #minutes_total = c5.number_input("Minutes used (total)", min_value=0, step=5, value=0)
    expected_cycles = c4.number_input("Expected life (cycles)", min_value=0, step=50, value=500)
    c7,c8,c9 = st.columns(3)
    cycles_today = c7.number_input("Cycles used (today)", min_value=0, step=1, value=0)
    cycles_total = c8.number_input("Cycles used (total)", min_value=0, step=1, value=0)
    status = c9.selectbox("Status", ["OK","Monitor","Replace Soon","Replace Now"])
    t_notes = st.text_input("Notes (tool)")
    if st.button("Save/Update Tool"):
        save_row(FILES["tools"], {
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "shift_date": str(shift_date),"shift": shift,"operator": operator,"machine_id": machine_id,
            "tool_id": tool_id,"tool_name": tool_name,
            #"expected_minutes": expected_minutes,"minutes_used_today": minutes_today,"minutes_used_total": minutes_total,
            "expected_cycles": expected_cycles,"cycles_used_today": cycles_today,"cycles_used_total": cycles_total,
            "status": status,"notes": t_notes
        })
        st.success("Tool entry saved.")
    st.subheader("Tools registry")
    tool_df = pd.read_csv(FILES["tools"]) if FILES["tools"].exists() else pd.DataFrame()
    if not tool_df.empty:
        view = tool_df[tool_df["machine_id"]==machine_id].copy()
        if not view.empty:
            for _, r in view.iterrows():
                try:
                    exp_m = float(r.get("expected_minutes",0) or 0)
                    used_m = float(r.get("minutes_used_total",0) or 0)
                    if exp_m>0 and used_m/exp_m>=0.9:
                        st.warning(f"Tool {r['tool_id']} nearing end of life ({used_m}/{exp_m} min). Plan replacement.")
                except Exception:
                    pass
            st.dataframe(view.tail(30))
        else:
            st.info("No tools logged for this machine yet.")
    else:
        st.info("No tools data yet.")

# 7) Logbook + Export
with tabs[6]:
    st.header("Logbook & Export")
    st.subheader("Checklists")
    if FILES["checklists"].exists():
        st.dataframe(pd.read_csv(FILES["checklists"]).tail(100))
    else:
        st.info("No checklists yet.")
    st.subheader("Production")
    if FILES["production"].exists():
        st.dataframe(pd.read_csv(FILES["production"]).tail(100))
    else:
        st.info("No production yet.")
    st.subheader("Diagnostics")
    if FILES["diagnostics"].exists():
        st.dataframe(pd.read_csv(FILES["diagnostics"]).tail(100))
    else:
        st.info("No diagnostics yet.")
    st.subheader("Tools")
    if FILES["tools"].exists():
        st.dataframe(pd.read_csv(FILES["tools"]).tail(100))
    else:
        st.info("No tools yet.")

    st.markdown("---")
    st.subheader("Generate Handover Report (Markdown download)")
    import io
    buf = io.StringIO()
    buf.write(f"# VMC Handover Report\n")
    buf.write(f"- Date: {shift_date} | Shift: {shift} | Operator: {operator} | Machine: {machine_id}\n\n")

    if FILES["checklists"].exists():
        before = pd.read_csv(FILES["checklists"])
        before = before[(before["machine_id"]==machine_id)&(before["phase"]=="before")].tail(1)
        if not before.empty:
            buf.write("## Before Shift Summary\n")
            row = before.iloc[0].to_dict()
            for k in ["power_ok","tooling_setup_ok","workpiece_setup_ok","coolant_ok","lubrication_ok","cleanliness_ok","safety_ok","home_positions_ok","program_ok","spindle_ok","air_ok"]:
                buf.write(f"- {k}: {row.get(k)}\n")
            buf.write(f"- Notes: {row.get('notes','')}\n\n")
    if FILES["production"].exists():
        p = pd.read_csv(FILES["production"])
        p = p[p["machine_id"]==machine_id]
        if not p.empty:
            buf.write("## Production Summary (recent)\n")
            last = p.tail(5)
            for _, r in last.iterrows():
                buf.write(f"- {r['timestamp']} — Job {r['job_id']}: {r['parts_done']} pcs @ {r['avg_cycle_time_min']} min; scrap {r['scrap_count']}\n")
            buf.write("\n")
    if FILES["diagnostics"].exists():
        d = pd.read_csv(FILES["diagnostics"])
        d = d[d["machine_id"]==machine_id].tail(5)
        if not d.empty:
            buf.write("## Diagnostics (recent)\n")
            for _, r in d.iterrows():
                buf.write(f"- {r['timestamp']} — {r['matched_issue']} (sev: {r['severity']}) actions: {r['actions']}\n")
            buf.write("\n")
    if FILES["tools"].exists():
        t = pd.read_csv(FILES["tools"])
        t = t[t["machine_id"]==machine_id].tail(5)
        if not t.empty:
            buf.write("## Tools (recent updates)\n")
            for _, r in t.iterrows():
                buf.write(f"- {r['timestamp']} — {r['tool_id']} {r['tool_name']} status: {r['status']} used {r['minutes_used_total']}/{r['expected_minutes']} min\n")
            buf.write("\n")

    st.download_button("Download Handover Report (.md)", buf.getvalue(), file_name=f"handover_{machine_id}_{shift}_{shift_date}.md")


