#!/usr/bin/env python3
"""
Seed sample advisors into the local JSON store via the API.
Run with the backend server up: USE_JSON_STORE=true uvicorn src.main:app --port 8000
Then: python scripts/seed_advisors.py
Or call POST /api/admin/seed (see main.py) with the server running.
"""
import os
import sys

# Run from backend directory
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

USE_JSON_STORE = os.getenv("USE_JSON_STORE", "true").lower() in ("1", "true", "yes")
if not USE_JSON_STORE:
    print("This script is for local JSON store. Set USE_JSON_STORE=true.")
    sys.exit(1)

from pathlib import Path
from src.utils import json_store

SEED_ADVISORS = [
    {
        "npn": "12345678",
        "first_name": "Jane",
        "last_name": "Smith",
        "email": "jane.smith@example.com",
        "phone": "555-0101",
        "broker_dealer": "Example BD",
        "license_states": ["CA", "TX", "NY"],
        "status": "pending",
    },
    {
        "npn": "87654321",
        "first_name": "John",
        "last_name": "Doe",
        "email": "john.doe@example.com",
        "phone": "555-0102",
        "broker_dealer": "Example BD",
        "license_states": ["CA", "FL"],
        "status": "pending",
    },
    {
        "npn": "11223344",
        "first_name": "Maria",
        "last_name": "Garcia",
        "email": "maria.garcia@example.com",
        "phone": "555-0103",
        "broker_dealer": "Another BD",
        "license_states": ["TX", "AZ", "NM"],
        "status": "completed",
    },
]


def main():
    created = []
    for data in SEED_ADVISORS:
        try:
            advisor_id = json_store.create_advisor(data)
            created.append({"id": advisor_id, "npn": data["npn"], "name": f"{data['first_name']} {data['last_name']}"})
        except ValueError as e:
            if "NPN already exists" in str(e):
                print(f"Skip (already exists): NPN {data['npn']}")
            else:
                raise
    print(f"Seeded {len(created)} advisors:")
    for a in created:
        print(f"  - {a['id']}  NPN {a['npn']}  {a['name']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
