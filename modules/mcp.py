from dataclasses import dataclass
from typing import Optional, Dict, Any
# from .security import require_scope  # Uncomment if real scopes are enforced

@dataclass
class ToolCallResult:
    ok: bool
    message: str
    payload: Optional[dict] = None

class MCPRegistry:
    def __init__(self):
        self.tools = [
            {"name": "get_vitals", "description": "Return current vitals for a patient", "scope": "vitals:read"},
            {"name": "check_thresholds", "description": "Check current vitals against risk thresholds", "scope": "vitals:read"},
            {"name": "alert_doctor", "description": "Notify doctor about an event (requires consent)", "scope": "alerts:write"},
        ]
        self.patients: Dict[str, Dict[str, Any]] = {}

    def get_patient(self, patient_id: str) -> Optional[Dict[str, Any]]:
        return self.patients.get(patient_id)

    def list_tools(self):
        return self.tools

    def execute(self, tool_name: str, patient_id: Optional[str] = None, prompt: Optional[str] = None) -> ToolCallResult:
        if tool_name == "get_vitals":
            p = self.get_patient(patient_id)
            if not p:
                return ToolCallResult(False, f"Patient {patient_id} not found", {})
            return ToolCallResult(True, "Vitals retrieved", p.get("vitals", {}))

        if tool_name == "check_thresholds":
            p = self.get_patient(patient_id)
            if not p:
                return ToolCallResult(False, f"Patient {patient_id} not found", {})

            v = p.get("vitals", {})
            alerts = []
            if v.get("spo2", 100) < 95:
                alerts.append("Low SpO₂ detected")
            hr = v.get("heart_rate")
            if hr is not None and hr > 120:
                alerts.append("High heart rate detected")
            temp = v.get("temperature")
            if temp is not None and temp > 38:
                alerts.append("High fever detected")

            return ToolCallResult(True, "Thresholds checked", {"alerts": alerts})

        if tool_name == "alert_doctor":
            return ToolCallResult(True, "Doctor alerted successfully", {})

        return ToolCallResult(False, f"Unknown tool: {tool_name}", {})
