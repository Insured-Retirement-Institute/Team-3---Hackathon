from __future__ import annotations

import json
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any


def _backend_dir() -> Path:
    return Path(__file__).resolve().parents[2]


def _data_dir() -> Path:
    d = _backend_dir() / "local_data"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _atomic_write_json(path: Path, data: Any) -> None:
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    with tmp_path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, sort_keys=True)
    os.replace(tmp_path, path)


def _advisors_path() -> Path:
    return _data_dir() / "advisors.json"


def _submissions_path() -> Path:
    return _data_dir() / "carrier_submissions.json"


def _payloads_dir() -> Path:
    d = _data_dir() / "carrier_payloads"
    d.mkdir(parents=True, exist_ok=True)
    return d


def save_carrier_payload(payload: dict[str, Any]) -> str:
    payload_id = f"payload-{uuid.uuid4()}.json"
    path = _payloads_dir() / payload_id
    _atomic_write_json(path, payload)
    return str(path.relative_to(_backend_dir()))


def load_carrier_payload(payload_file: str) -> dict[str, Any]:
    path = (_backend_dir() / payload_file).resolve()
    data = _load_json(path, default={})
    if not isinstance(data, dict):
        return {}
    return data


def list_advisors(status: str | None = None) -> list[dict[str, Any]]:
    data = _load_json(_advisors_path(), default=[])
    if not isinstance(data, list):
        return []

    if status:
        return [a for a in data if (a.get("status") == status)]
    return data


def get_advisor(advisor_id: str) -> dict[str, Any] | None:
    advisors = list_advisors()
    for a in advisors:
        if str(a.get("id")) == advisor_id:
            return a
    return None


def create_advisor(advisor: dict[str, Any]) -> str:
    advisors = list_advisors()

    npn = advisor.get("npn")
    if npn and any(a.get("npn") == npn for a in advisors):
        raise ValueError("Advisor with this NPN already exists")

    now = datetime.utcnow().isoformat()
    new_id = str(uuid.uuid4())
    record = {
        "id": new_id,
        "npn": advisor.get("npn"),
        "first_name": advisor.get("first_name"),
        "last_name": advisor.get("last_name"),
        "email": advisor.get("email"),
        "phone": advisor.get("phone"),
        "broker_dealer": advisor.get("broker_dealer"),
        "license_states": advisor.get("license_states") or [],
        "status": advisor.get("status") or "pending",
        "document_url": advisor.get("document_url"),
        "transfer_date": advisor.get("transfer_date"),
        "created_at": now,
        "updated_at": now,
    }

    advisors.append(record)
    _atomic_write_json(_advisors_path(), advisors)
    return new_id


def update_advisor(advisor_id: str, patch: dict[str, Any]) -> dict[str, Any] | None:
    advisors = list_advisors()
    for i, a in enumerate(advisors):
        if str(a.get("id")) != advisor_id:
            continue

        updated = {**a, **patch}
        updated["updated_at"] = datetime.utcnow().isoformat()
        advisors[i] = updated
        _atomic_write_json(_advisors_path(), advisors)
        return updated

    return None


def list_submissions(advisor_id: str | None = None, carrier_id: str | None = None) -> list[dict[str, Any]]:
    data = _load_json(_submissions_path(), default=[])
    if not isinstance(data, list):
        return []

    out: list[dict[str, Any]] = []
    for s in data:
        if advisor_id and str(s.get("advisor_id")) != advisor_id:
            continue
        if carrier_id and str(s.get("carrier_id")) != carrier_id:
            continue
        out.append(s)

    out.sort(key=lambda x: (x.get("created_at") or ""), reverse=True)
    return out


def get_submission(submission_id: str) -> dict[str, Any] | None:
    subs = list_submissions()
    for s in subs:
        if str(s.get("id")) == submission_id:
            return s
    return None


def create_submission(submission: dict[str, Any]) -> str:
    subs = list_submissions()
    now = datetime.utcnow().isoformat()
    new_id = str(uuid.uuid4())

    record = {
        "id": new_id,
        "advisor_id": submission.get("advisor_id"),
        "carrier_id": submission.get("carrier_id"),
        "integration_method": submission.get("integration_method") or "api",
        "status": submission.get("status") or "submitted",
        "agent_code": submission.get("agent_code"),
        "accepted_states": submission.get("accepted_states"),
        "rejected_states": submission.get("rejected_states"),
        "request_data": submission.get("request_data") or {},
        "response_data": submission.get("response_data") or {},
        "error_message": submission.get("error_message"),
        "submitted_at": submission.get("submitted_at"),
        "completed_at": submission.get("completed_at"),
        "created_at": now,
    }

    subs.append(record)
    _atomic_write_json(_submissions_path(), subs)
    return new_id


def update_submission(submission_id: str, patch: dict[str, Any]) -> dict[str, Any] | None:
    subs = list_submissions()
    for i, s in enumerate(subs):
        if str(s.get("id")) != submission_id:
            continue

        updated = {**s, **patch}
        subs[i] = updated
        _atomic_write_json(_submissions_path(), subs)
        return updated

    return None


def find_latest_submission(advisor_id: str, carrier_id: str) -> dict[str, Any] | None:
    subs = list_submissions(advisor_id=advisor_id, carrier_id=carrier_id)
    return subs[0] if subs else None
