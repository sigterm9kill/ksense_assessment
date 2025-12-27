#!/usr/bin/env python3
"""
Patient Assessment Script
Retrieves all patients, processes risk scores, and submits results.
"""

import requests
import json
from typing import Dict, List, Tuple, Optional

API_KEY = "ak_1829abc2d08624cd0227b756a70d5ebd261464925a35c5f2"
BASE_URL = "https://assessment.ksensetech.com/api"
PATIENTS_ENDPOINT = f"{BASE_URL}/patients"
SUBMIT_ENDPOINT = f"{BASE_URL}/submit-assessment"

HEADERS = {
    "x-api-key": API_KEY,
    "Content-Type": "application/json"
}


def fetch_all_patients() -> List[Dict]:
    all_patients = []
    page = 1
    limit = 20

    while True:
        params = {"page": page, "limit": limit}
        response = requests.get(PATIENTS_ENDPOINT, headers=HEADERS, params=params)
        response.raise_for_status()

        payload = response.json()

        patients = payload.get("data", [])
        all_patients.extend(patients)

        pagination = payload.get("pagination", {})
        has_next = pagination.get("hasNext", False)

        print(f"Fetched page {page}: {len(patients)} patients (total: {len(all_patients)})")

        if not has_next:
            break

        page += 1

    print(f"\nTotal patients fetched: {len(all_patients)}")
    return all_patients


def calculate_bp_score(blood_pressure: Optional[str]) -> Tuple[int, bool]:
    if not blood_pressure or not isinstance(blood_pressure, str):
        return 0, False

    parts = blood_pressure.split("/")
    if len(parts) != 2:
        return 0, False

    if not parts[0].strip() or not parts[1].strip():
        return 0, False

    try:
        systolic = float(parts[0])
        diastolic = float(parts[1])
    except ValueError:
        return 0, False

    if systolic >= 140 or diastolic >= 90:
        return 4, True

    if systolic >= 130 or diastolic >= 80:
        return 3, True

    if 120 <= systolic <= 129 and diastolic < 80:
        return 2, True

    if systolic < 120 and diastolic < 80:
        return 1, True

    return 0, True


def calculate_temp_score(temperature: Optional[float]) -> Tuple[int, bool]:
    try:
        temp = float(temperature)
    except (TypeError, ValueError):
        return 0, False

    if temp <= 99.5:
        return 0, True
    if 99.6 <= temp <= 100.9:
        return 1, True
    return 2, True


def has_fever(temperature: Optional[float]) -> bool:
    try:
        return float(temperature) >= 99.6
    except (TypeError, ValueError):
        return False


def calculate_age_score(age: Optional[int]) -> Tuple[int, bool]:
    try:
        age_val = float(age)
    except (TypeError, ValueError):
        return 0, False

    if age_val > 65:
        return 2, True

    return 1, True


def process_patients(patients: List[Dict]) -> Tuple[List[str], List[str], List[str]]:
    high_risk = set()
    fever = set()
    data_quality = set()

    for patient in patients:
        patient_id = patient.get("patient_id")
        if not patient_id:
            continue

        blood_pressure = patient.get("blood_pressure")
        temperature = patient.get("temperature")
        age = patient.get("age")

        bp_score, bp_valid = calculate_bp_score(blood_pressure)
        temp_score, temp_valid = calculate_temp_score(temperature)
        age_score, age_valid = calculate_age_score(age)

        if not bp_valid or not temp_valid or not age_valid:
            data_quality.add(patient_id)

        if has_fever(temperature):
            fever.add(patient_id)

        total_risk = bp_score + temp_score + age_score

        if total_risk >= 4:
            high_risk.add(patient_id)

    return list(high_risk), list(fever), list(data_quality)


def submit_results(high_risk: List[str], fever: List[str], quality_issues: List[str]) -> Dict:
    payload = {
        "high_risk_patients": high_risk,
        "fever_patients": fever,
        "data_quality_issues": quality_issues
    }

    response = requests.post(SUBMIT_ENDPOINT, headers=HEADERS, json=payload)
    response.raise_for_status()
    return response.json()


def main():
    print("Step 1: Fetching all patients...")
    patients = fetch_all_patients()

    print("\nStep 2-3: Processing patients and calculating risk scores...")
    high_risk, fever, data_quality = process_patients(patients)

    print("\nStep 4: Results summary:")
    print(f"  High risk patients: {len(high_risk)}")
    print(f"  Fever patients: {len(fever)}")
    print(f"  Data quality issues: {len(data_quality)}")

    print("\nStep 5: Submitting results...")
    result = submit_results(high_risk, fever, data_quality)

    print("\nSubmission result:")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
