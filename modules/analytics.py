import pandas as pd, time, uuid, io

class AuditLog:
    def __init__(self):
        self._events = []

    def add(self, action: str, subject: str, status: str, scopes):
        self._events.append({
            "ts": int(time.time()),
            "trace_id": str(uuid.uuid4())[:8],
            "action": action,
            "subject": subject,
            "status": status,
            "scopes": ",".join(scopes or [])
        })

    def as_dataframe(self):
        if not self._events:
            return None
        df = pd.DataFrame(self._events)
        df["ts"] = pd.to_datetime(df["ts"], unit="s")
        return df[["ts","trace_id","action","subject","status","scopes"]]

def export_logs_csv(df: pd.DataFrame) -> bytes:
    buf = io.StringIO()
    df.to_csv(buf, index=False)
    return buf.getvalue().encode("utf-8")
