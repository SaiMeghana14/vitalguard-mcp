import json, pandas as pd

def load_vitals(path):
    with open(path, "r") as f:
        return json.load(f)

def get_patient_ids(data):
    return list(data.keys())

def get_patient(data, patient_id):
    return data.get(patient_id)

def vitals_dataframe(patient):
    hist = patient.get("history", [])
    if not hist:
        return None
    return pd.DataFrame(hist)
