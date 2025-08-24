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
        # mock patient store
        self.patients: Dict[str, Dict[str, Any]] = {}

    def get_patient(self, patient_id: str) -> Optional[Dict[str, Any]]:
        """Return patient dict if exists"""
        return self.patients.get(patient_id)

    def list_tools(self):
        return self.tools

    def execute(self, tool_name: str, patient_id: str, prompt: str = None) -> ToolCallResult:
        # --- Tool: Get Vitals ---
        if tool_name == "get_vitals":
            p = self.get_patient(patient_id)
            if not p:
                return ToolCallResult(False, f"Patient {patient_id} not found", None)

            vitals = p.get("vitals", {})
            return ToolCallResult(True, "Vitals retrieved", vitals)

        # --- Tool: Check Thresholds ---
        if tool_name == "check_thresholds":
            # TODO: wire actual oauth/data/audit
            p = self.get_patient(patient_id)
            if not p:
                return ToolCallResult(False, f"Patient {patient_id} not found", None)

            v = p.get("vitals", {})
            alerts = []
            if v.get("spo2", 100) < 95:
                alerts.append("Low SpO₂ detected")
            if v.get("heart_rate", 0) > 120:
                alerts.append("High heart rate detected")
            if v.get("temperature", 36.5) > 38:
                alerts.append("High fever detected")

            return ToolCallResult(True, "Thresholds checked", {"alerts": alerts})

        # --- Tool: Alert Doctor ---
        if tool_name == "alert_doctor":
            # TODO: wire actual consent + audit system
            return ToolCallResult(True, "Doctor alerted successfully", None)

        # --- Unknown tool fallback ---
        return ToolCallResult(False, f"Unknown tool: {tool_name}", None)
