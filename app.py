import sys
import os

print("Current working directory:", os.getcwd())
print("Python path:", sys.path)
print("Folder contents:", os.listdir("."))

import streamlit as st
import json, pandas as pd, numpy as np, matplotlib.pyplot as plt, uuid, time
from pathlib import Path

from modules.data_io import load_vitals, get_patient_ids, get_patient, vitals_dataframe
from modules.security import OAuthGateway, require_scope, ConsentManager
from modules.mcp import MCPRegistry, ToolCallResult
from modules.analytics import AuditLog, export_logs_csv
from modules.ui import hero, kpi_card, scope_badge, section_title, success_toast, warn_toast

st.set_page_config(page_title="VitalGuard MCP", page_icon="🏥", layout="wide")

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
DATA_FILE = Path(__file__).resolve().parent / "data" / "vitals.json"
data = load_vitals(DATA_FILE)

# ---- Header ----
hero(title="VitalGuard MCP", subtitle="Secure Healthcare IoT Server for AI Agents", badge="MCP + OAuth (simulated)")

# ---- Tabs ----
tabs = st.tabs(["🏠 Dashboard", "🤖 Agent Console", "🛡️ Security & Scopes", "🧾 Audit Logs", "⚙️ Settings", "ℹ️ About"])

# -------------------- Dashboard --------------------
with tabs[0]:
    section_title("Patient Monitoring")
    colL, colR = st.columns([1, 2], gap="large")

    with colL:
        # Select patient ID from keys
        patient_id = st.sidebar.selectbox(
            "Select Patient",
            list(data.keys())
        )

        st.write("Available IDs:", list(data.keys()))
        st.write("Selected ID:", patient_id)

        # Fetch patient data (list of vitals for this ID)
        patient = data.get(patient_id, None)

        if not patient:
            st.error(f"❌ Patient {patient_id} not found!")
            st.stop()

        st.markdown('<div class="vg-card">', unsafe_allow_html=True)
        kpi_card("Patient", patient_id)
        kpi_card("Auth Status", "Connected" if hasattr(st.session_state, "oauth") and st.session_state.oauth.token else "Not Connected")
        st.markdown('</div>', unsafe_allow_html=True)

        if st.button("🔄 Refresh simulated vitals"):
            # mutate a bit for demo
            p = data[patient_id]
            v = p["vitals"]
            v["heart_rate"] = int(np.clip(v["heart_rate"] + np.random.randint(-5,6), 60, 140))
            v["spo2"] = int(np.clip(v["spo2"] + np.random.randint(-2,3), 85, 100))
            v["temperature"] = float(np.clip(v["temperature"] + np.random.uniform(-0.2,0.2), 35.5, 40.0))
            data[patient_id] = p
            with open(DATA_FILE, "w") as f:
                json.dump(data, f, indent=2)
            success_toast("Vitals updated")

    with colR:
        cols = st.columns(4)
        latest = patient[-1]  # last record for this patient
        v = latest  # alias for clarity

        # >>> Added: conditional color alerts on KPI cards
        hr_color = "🔴" if v["heart_rate"] > 120 else "🟢"
        spo2_color = "🔴" if v["spo2"] < 95 else "🟢"
        temp_color = "🔴" if v["temp"] > 38 else "🟢"
        bp_color = "🟢"  # (could extend later)

        kpi_card(f"{hr_color} Heart Rate", f"{v['heart_rate']} bpm", cols[0])
        kpi_card(f"{spo2_color} SpO₂", f"{v['spo2']} %", cols[1])
        kpi_card(f"{temp_color} Temp", f"{v['temp']} °C", cols[2])
        kpi_card(f"{bp_color} BP", f"{v['bp']}", cols[3])

        st.markdown('<div class="vg-card">', unsafe_allow_html=True)
        st.write("### Trend (last 30 minutes)")
        df = vitals_dataframe(patient)
        if df is not None and len(df) > 0:
            fig = plt.figure()
            st.write(df.head())
            plt.plot(pd.to_datetime(df["timestamp"]), df["heart_rate"], label="Heart Rate")
            plt.plot(pd.to_datetime(df["ts"]), df["spo2"], label="SpO2")
            plt.plot(pd.to_datetime(df["ts"]), df["temp"], label="Temp (°C)")
            plt.legend()
            plt.xlabel("Time"); plt.ylabel("Value")
            st.pyplot(fig)
            plt.close(fig)
        else:
            st.info("No history available for this patient.")
        st.markdown('</div>', unsafe_allow_html=True)

        # threshold check (manual)
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

        # >>> Added: auto-check vitals thresholds every load
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


# -------------------- Agent Console --------------------
with tabs[1]:
    section_title("MCP Agent Console")

    registry = MCPRegistry()
    colA, colB = st.columns([1,2], gap="large")

    with colA:
        st.markdown('<div class="vg-card">', unsafe_allow_html=True)
        st.write("### Connected OAuth")
        if st.session_state.oauth.token:
            st.success(f"Token: {st.session_state.oauth.token[:8]}...")
            st.write("Scopes:", ", ".join(st.session_state.oauth.scopes()))
        else:
            st.warning("No token. Connect under **Security & Scopes** tab.")
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('<div class="vg-card">', unsafe_allow_html=True)
        st.write("### Available Tools")
        tools = registry.list_tools()
        for t in tools:
            st.markdown(f"- `{t['name']}` — {t['description']}")
        st.markdown('</div>', unsafe_allow_html=True)

    with colB:
        st.markdown('<div class="vg-card">', unsafe_allow_html=True)
        st.write("### Execute Tool As Agent")
        tool = st.selectbox("Tool", [t["name"] for t in tools])
        patient_id = st.selectbox("Patient", get_patient_ids(data), key="agent_patient")
        prompt = st.text_input("Agent Instruction", "Check thresholds and alert doctor if risky.")

        if st.button("▶️ Run"):
            trace_id = str(uuid.uuid4())[:8]
            st.write(f"Trace ID: `{trace_id}`")
            # Simulated MCP execution
            result: ToolCallResult = registry.execute(
                tool_name=tool,
                patient=patient_id,
                data=data,
                oauth=st.session_state.oauth,
                consent=st.session_state.consent,
                audit=st.session_state.audit,
                prompt=prompt,
            )
            if result.ok:
                st.success(result.message)
                if result.payload is not None:
                    st.json(result.payload)
            else:
                st.error(result.message)
        st.markdown('</div>', unsafe_allow_html=True)

# -------------------- Security & Scopes --------------------
with tabs[2]:
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
with tabs[3]:
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
with tabs[4]:
    section_title("Settings")
    st.write("You can extend this demo with real IoT data sources (e.g., Firebase, Blynk, MQTT).")
    st.write("Swap the simulated OAuth with a real **Cequence AI Gateway** in front of a FastAPI MCP server.")

# -------------------- About --------------------
with tabs[5]:
    section_title("About VitalGuard MCP")
    st.write("Built for the Global MCP Hackathon to demonstrate **secure, permissioned, and observable** agent-to-API interactions in healthcare.")
    st.markdown("**MCP Tools implemented:** `get_vitals`, `check_thresholds`, `alert_doctor`")
    st.markdown("**Security:** OAuth-like token, scoped access, consent capture & replay, audit logs.")
    st.markdown("**UI:** Themed KPIs, animated badges, charts, trace IDs, and exportable logs.")
