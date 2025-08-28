import sys
import os
import streamlit as st
import uuid
from modules import security

st.set_page_config(page_title="VitalGuard MCP", page_icon="🏥", layout="wide")

# 🔔 Show banner if running in demo mode
if getattr(security, "DEMO_MODE", False):
    st.warning("⚠️ Running in DEMO MODE — OAuth checks are skipped.")
else:
    st.success("🔒 Secure mode enabled — OAuth required.")

import json, pandas as pd, numpy as np, matplotlib.pyplot as plt, uuid, time
from pathlib import Path

# ---- Drop-in JSON loader (Option 2) ----
DATA_FILE = Path(__file__).resolve().parent / "data" / "vitals.json"

def load_vitals(file_path=DATA_FILE):
    try:
        with open(file_path, "r") as f:
            raw = json.load(f)

        rows = []
        for patient_id, records in raw.items():
            for r in records:
                rows.append({
                    "patient_id": patient_id,
                    "timestamp": pd.to_datetime(r["timestamp"]),
                    "heart_rate": r["heart_rate"],
                    "spo2": r["spo2"],
                    "bp": r["bp"],
                    "temp": r["temp"],
                })
        return pd.DataFrame(rows)

    except (FileNotFoundError, json.JSONDecodeError):
        return pd.DataFrame([])

def save_vitals(df, file_path=DATA_FILE):
    grouped = {}
    for _, row in df.iterrows():
        pid = row["patient_id"]
        grouped.setdefault(pid, []).append({
            "timestamp": row["timestamp"].strftime("%Y-%m-%d %H:%M"),
            "heart_rate": row["heart_rate"],
            "spo2": row["spo2"],
            "bp": row["bp"],
            "temp": row["temp"]
        })
    with open(file_path, "w") as f:
        json.dump(grouped, f, indent=4)

# ---- Other imports (unchanged) ----
from modules.security import OAuthGateway, require_scope, ConsentManager
from modules.mcp import MCPRegistry, ToolCallResult
from modules.analytics import AuditLog, export_logs_csv
from modules.ui import hero, kpi_card, scope_badge, section_title, success_toast, warn_toast

# ---- Load CSS ----
css_path = Path(__file__).resolve().parent / "assets" / "theme.css"

if css_path.exists():
    st.markdown(f"<style>{css_path.read_text()}</style>", unsafe_allow_html=True)
else:
    st.warning(f"CSS file not found: {css_path}")

# ---- Session State ----
if "oauth" not in st.session_state:
    st.session_state.oauth = OAuthGateway()
if "audit" not in st.session_state:
    st.session_state.audit = AuditLog()
if "consent" not in st.session_state:
    st.session_state.consent = ConsentManager()

# ---- Data ----
data = load_vitals(DATA_FILE)

# ---- Header ----
hero(title="VitalGuard MCP", subtitle="Secure Healthcare IoT Server for AI Agents", badge="MCP + OAuth (simulated)")

# ---- Tabs ----
tabs = st.tabs(["🏠 Dashboard", "🛡️ Security & Scopes", "🧾 Audit Logs", "⚙️ Settings", "ℹ️ About"])

# -------------------- Dashboard --------------------
with tabs[0]:
    section_title("Patient Monitoring")
    colL, colR = st.columns([1, 2], gap="large")

    with colL:
        # Always DataFrame now
        patient_ids = data["patient_id"].unique().tolist() if not data.empty else []
        patient_id = st.sidebar.selectbox("Select Patient", patient_ids)

        st.write("Available IDs:", patient_ids)
        st.write("Selected ID:", patient_id)

        patient = data[data["patient_id"] == patient_id].to_dict(orient="records")

        if not patient:
            st.error(f"❌ Patient {patient_id} not found!")
            st.stop()

        st.markdown('<div class="vg-card">', unsafe_allow_html=True)
        kpi_card("Patient", patient_id)
        kpi_card("Auth Status", "Connected" if hasattr(st.session_state, "oauth") and st.session_state.oauth.token else "Not Connected")
        st.markdown('</div>', unsafe_allow_html=True)

    with colR:
        cols = st.columns(4)
        latest = patient[-1]  # last record for this patient
        v = latest  # alias for clarity

        # >>> Conditional color alerts on KPI cards
        hr_color = "🔴" if v["heart_rate"] > 120 else "🟢"
        spo2_color = "🔴" if v["spo2"] < 95 else "🟢"
        temp_color = "🔴" if v["temp"] > 38 else "🟢"
        bp_color = "🟢"

        kpi_card(f"{hr_color} Heart Rate", f"{v['heart_rate']} bpm", cols[0])
        kpi_card(f"{spo2_color} SpO₂", f"{v['spo2']} %", cols[1])
        kpi_card(f"{temp_color} Temp", f"{v['temp']} °C", cols[2])
        kpi_card(f"{bp_color} BP", f"{v['bp']}", cols[3])

        st.markdown('<div class="vg-card">', unsafe_allow_html=True)
        st.write("### Trend (last 30 minutes)")
        if len(patient) > 0:
            df = pd.DataFrame(patient)
            fig = plt.figure()
            plt.plot(pd.to_datetime(df["timestamp"]), df["heart_rate"], label="Heart Rate")
            plt.plot(pd.to_datetime(df["timestamp"]), df["spo2"], label="SpO2")
            plt.plot(pd.to_datetime(df["timestamp"]), df["temp"], label="Temp (°C)")
            plt.legend()
            plt.xlabel("Time"); plt.ylabel("Value")
            st.pyplot(fig)
            plt.close(fig)
        else:
            st.info("No history available for this patient.")
        st.markdown('</div>', unsafe_allow_html=True)

        # Threshold checks (manual + auto)
        if st.button("🧪 Check Thresholds"):
            alerts = []
            if v["spo2"] < 95: alerts.append("Low SpO₂ detected")
            if v["heart_rate"] > 120: alerts.append("High heart rate detected")
            if v["temp"] > 38: alerts.append("High fever detected")

            st.session_state.audit.add(
                action="check_thresholds",
                subject=patient_id,
                status="ok",
                scopes=st.session_state.oauth.scopes(),
            )

            if alerts:
                warn_toast(" | ".join(alerts))
                st.error(alerts)
            else:
                success_toast("Vitals are within safe limits ✅")

        auto_alerts = []
        if v["spo2"] < 90: auto_alerts.append("🚨 CRITICAL: SpO₂ dangerously low!")
        if v["heart_rate"] > 130: auto_alerts.append("🚨 CRITICAL: Severe tachycardia!")
        if v["temp"] > 39.5: auto_alerts.append("🚨 CRITICAL: High-grade fever!")

        if auto_alerts:
            for a in auto_alerts:
                st.error(a)
            st.session_state.audit.add(
                action="auto_threshold_alert",
                subject=patient_id,
                status="triggered",
                scopes=st.session_state.oauth.scopes(),
            )

        # alert doctor
        message = st.text_input("Message to Doctor", "Critical condition detected")
        if st.button("📨 Alert Doctor (requires consent & scope)"):
            try:
                require_scope(st.session_state.oauth, "alerts:write")
                consent_ok = st.session_state.consent.has_consent(patient_id)
                if not consent_ok:
                    with st.expander("Consent required"):
                        st.write("Please capture patient consent before notifying a doctor.")
                        if st.button("✅ Capture consent now"):
                            st.session_state.consent.capture(patient_id, "Notify doctor about current condition.")
                            success_toast("Consent captured")
                # re-check consent
                if st.session_state.consent.has_consent(patient_id):
                    st.success(f"Doctor notified for {patient['name']} with message: {message}")
                    st.session_state.audit.add(
                        action="alert_doctor",
                        subject=patient_id,
                        status="sent",
                        scopes=st.session_state.oauth.scopes(),
                    )
                else:
                    st.warning("Consent not captured. Action blocked.")
            except PermissionError as e:
                st.error(str(e))
                st.session_state.audit.add(
                    action="alert_doctor",
                    subject=patient_id,
                    status="forbidden",
                    scopes=st.session_state.oauth.scopes(),
                )

# -------------------- Security & Scopes --------------------
with tabs[1]:
    section_title("OAuth (Cequence-like) Gateway — Simulated")
    st.markdown('<div class="vg-card">', unsafe_allow_html=True)
    st.write("Connect and issue a token with **scoped** permissions:")
    col1, col2 = st.columns(2)
    with col1:
        scope_read = st.checkbox("vitals:read", True)
        scope_alert = st.checkbox("alerts:write", True)
    with col2:
        scope_consent = st.checkbox("consent:manage", True)
        scope_logs = st.checkbox("logs:read", False)

    if st.button("🔐 Connect / Refresh Token"):
        scopes = []
        if scope_read: scopes.append("vitals:read")
        if scope_alert: scopes.append("alerts:write")
        if scope_consent: scopes.append("consent:manage")
        if scope_logs: scopes.append("logs:read")
        st.session_state.oauth.issue(scopes=scopes)
        success_toast("Token issued with scopes: " + ", ".join(scopes))

    if st.session_state.oauth.token:
        st.info(f"Active token: `{st.session_state.oauth.token}`")
        st.write("Scopes:", ", ".join(st.session_state.oauth.scopes()))
        if st.button("🚪 Revoke"):
            st.session_state.oauth.revoke()
            st.warning("Token revoked")
    st.markdown('</div>', unsafe_allow_html=True)

# -------------------- Audit Logs --------------------
with tabs[2]:
    section_title("Audit & Observability")
    st.markdown('<div class="vg-card">', unsafe_allow_html=True)
    df = st.session_state.audit.as_dataframe()
    if df is not None and len(df) > 0:
        st.dataframe(df, use_container_width=True, height=360)
        st.download_button(
            "⬇️ Download audit_logs.csv",
            data=export_logs_csv(df),
            file_name="audit_logs.csv",
            mime="text/csv"
)

    else:
        st.info("No audit logs yet. Execute some actions first.")
    st.markdown('</div>', unsafe_allow_html=True)

# -------------------- Settings --------------------
with tabs[3]:
    section_title("Settings")
    st.write("You can extend this demo with real IoT data sources (e.g., Firebase, Blynk, MQTT).")
    st.write("Swap the simulated OAuth with a real **Cequence AI Gateway** in front of a FastAPI MCP server.")

# -------------------- About --------------------
with tabs[4]:
    section_title("About VitalGuard MCP")
    st.write("Built for the Global MCP Hackathon to demonstrate **secure, permissioned, and observable** agent-to-API interactions in healthcare.")
    st.markdown("**MCP Tools implemented:** `get_vitals`, `check_thresholds`, `alert_doctor`")
    st.markdown("**Security:** OAuth-like token, scoped access, consent capture & replay, audit logs.")
    st.markdown("**UI:** Themed KPIs, animated badges, charts, trace IDs, and exportable logs.")

# -------------------- Sidebar Toggles --------------------
st.sidebar.markdown("---")
st.sidebar.header("⚙️ Extra Panels")
show_agent_console = st.sidebar.checkbox("Show Agent Console", value=False)
show_chatbot = st.sidebar.checkbox("Show Chatbot Panel", value=False)


# -------------------- Agent Console (Sidebar Toggle) --------------------
if show_agent_console:
    section_title("🤖 Agent Console (Sidebar Mode)")

    registry = MCPRegistry()
    st.markdown('<div class="vg-card">', unsafe_allow_html=True)

    st.write("### Execute Tool As Agent")
    tools = registry.list_tools()
    tool = st.selectbox("Tool", [t["name"] for t in tools], key="sidebar_tool")

    # ✅ Use DataFrame instead of dict
    def get_patient_ids(df):
        return df["patient_id"].unique().tolist() if not df.empty else []

    valid_ids = get_patient_ids(data)
    patient_id = st.selectbox("Patient", valid_ids, key="sidebar_agent_patient")
    prompt = st.text_input("Agent Instruction", "Check thresholds and alert doctor if risky.", key="sidebar_prompt")

    if st.button("▶️ Run (Sidebar Agent)"):
        trace_id = str(uuid.uuid4())[:8]
        st.write(f"Trace ID: `{trace_id}`")

        kwargs = dict(
            tool_name=tool,
            patient_id=patient_id,
            data=data,
            oauth=st.session_state.get("oauth"),
            consent=st.session_state.get("consent"),
            audit=st.session_state.get("audit"),
            prompt=prompt,
        )

        import inspect
        sig = inspect.signature(registry.execute)
        supported = {k: v for k, v in kwargs.items() if k in sig.parameters}

        result: ToolCallResult = registry.execute(**supported)

        if result.ok:
            st.success(result.message)
            if result.payload:
                st.json(result.payload)
        else:
            st.error(result.message)
    st.markdown('</div>', unsafe_allow_html=True)


# -------------------- Chatbot Panel (Sidebar Toggle) --------------------
if show_chatbot:
    section_title("💬 Chatbot Panel")
    st.markdown('<div class="vg-card">', unsafe_allow_html=True)

    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    user_input = st.text_input("Ask a question about patients", key="chat_input")

    if st.button("Send", key="chat_send"):
        if user_input:
            # very simple heuristic "chatbot" on vitals data
            response = "I couldn’t understand your question."

            if "list patients" in user_input.lower():
                ids = data["patient_id"].unique().tolist()
                response = f"Patients available: {', '.join(ids)}"

            elif "latest vitals" in user_input.lower():
                pid = st.sidebar.selectbox("Pick patient", data["patient_id"].unique(), key="chat_pid")
                latest = data[data["patient_id"] == pid].iloc[-1].to_dict()
                response = f"Latest vitals for {pid}: {latest}"

            elif "critical" in user_input.lower():
                critical = data[(data["spo2"] < 90) | (data["heart_rate"] > 130)]
                if not critical.empty:
                    ids = critical["patient_id"].unique().tolist()
                    response = f"Critical patients: {', '.join(ids)}"
                else:
                    response = "No patients in critical state."

            st.session_state.chat_history.append({"user": user_input, "bot": response})

    # show history
    for chat in st.session_state.chat_history:
        st.write(f"👤 {chat['user']}")
        st.info(f"🤖 {chat['bot']}")

    st.markdown('</div>', unsafe_allow_html=True)
