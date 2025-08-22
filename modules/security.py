import secrets, time

class OAuthGateway:
    def __init__(self):
        self.token = None
        self._scopes = []

    def issue(self, scopes):
        self.token = secrets.token_hex(16)
        self._scopes = scopes or []
        return self.token

    def revoke(self):
        self.token = None
        self._scopes = []

    def scopes(self):
        return self._scopes

def require_scope(gateway: OAuthGateway, scope: str):
    if not gateway.token:
        raise PermissionError("Not authenticated. Please connect via OAuth.")
    if scope not in gateway.scopes():
        raise PermissionError(f"Missing required scope: {scope}")

class ConsentManager:
    def __init__(self):
        self._consents = {}  # patient_id -> record

    def capture(self, patient_id: str, purpose: str):
        self._consents[patient_id] = {
            "purpose": purpose,
            "ts": int(time.time())
        }

    def has_consent(self, patient_id: str) -> bool:
        return patient_id in self._consents

    def get(self, patient_id: str):
        return self._consents.get(patient_id)
