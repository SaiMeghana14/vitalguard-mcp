from dataclasses import dataclass
from typing import Optional, Dict, Any
from .security import require_scope

@dataclass
class ToolCallResult:
    ok: bool
    message: str
    payload: Optional[dict] = None

class MCPRegistry:
    def __init__(self):
        # tool metadata
        self.tools = [
            {"name": "get_vitals", "description": "Return current vitals for a patient", "scope": "vitals:read"},
            {"name": "check_thresholds", "description": "Check current vitals against risk thresholds", "scope": "vitals:read"},
            {"name": "alert_doctor", "description": "Notify doctor about an event (requires consent)", "scope": "alerts:write"},
        ]

    def list_tools(self):
        return self.tools

    def execute(self, tool_name: str, patient_id: str, prompt: str = None):
        if tool_name == "get_vitals":
            p = self.get_patient(patient_id)
            if not p:
                return ToolCallResult(False, f"Patient {patient_id} not found", None)
    
            vitals = p.get("vitals", {})
            return ToolCallResult(True, "Vitals retrieved", vitals)
    
        # Always return a ToolCallResult for unknown tools
        return ToolCallResult(False, f"Unknown tool: {tool_name}", None)


        if tool_name == "check_thresholds":
            require_scope(oauth, "vitals:read")
            p = data.get(patient)
            if not p: return ToolCallResult(False, "Patient not found")
            v = p["vitals"]
            alerts = []
            if v["spo2"] < 95: alerts.append("Low SpO₂ detected")
            if v["heart_rate"] > 120: alerts.append("High heart rate detected")
            if v["temperature"] > 38: alerts.append("High fever detected")
            audit.add("check_thresholds", subject=patient, status="ok", scopes=oauth.scopes())
            return ToolCallResult(True, "Thresholds checked", {"alerts": alerts})

        if tool_name == "alert_doctor":
            require_scope(oauth, "alerts:write")
            if not consent.has_consent(patient):
                audit.add("alert_doctor", subject=patient, status="blocked_no_consent", scopes=oauth.scopes())
                return ToolCallResult(False, "Consent missing. Capture consent first.")
            audit.add("alert_doctor", subject=patient, status="sent", scopes=oauth.scopes())
            return ToolCallResult(True, "Doctor alerted successfully")

        return ToolCallResult(False, f"Unknown tool: {tool_name}")
