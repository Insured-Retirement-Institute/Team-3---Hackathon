from __future__ import annotations

import logging
import os
import uuid
from datetime import datetime
from typing import Any

import httpx

from src.models.advisor import CarrierSubmission
from src.utils.database import SessionLocal
from src.utils import json_store

logger = logging.getLogger(__name__)

# Same Bearer token as main.py; required when this service calls /api/carrier/* on the same host
AUTH_TOKEN = os.getenv("AUTH_TOKEN", "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJpc3MiOiJJUi1EZW1vIiwiZXhwIjoxOTk5OTk5OTk5fQ.dummy")
AUTH_HEADERS = {"Authorization": f"Bearer {AUTH_TOKEN}"}


def build_flat_payload(advisor: dict[str, Any], carrier_id: str, states: list[str]) -> dict[str, Any]:
    """Flat shape: carrierId, advisor, statesRequested (used by flat-format carrier endpoint)."""
    return {
        "carrierId": carrier_id,
        "advisor": {
            "advisor_id": str(advisor.get("advisor_id") or advisor.get("id") or ""),
            "npn": advisor.get("npn"),
            "first_name": advisor.get("first_name"),
            "last_name": advisor.get("last_name"),
            "email": advisor.get("email"),
            "phone": advisor.get("phone"),
            "broker_dealer": advisor.get("broker_dealer"),
            "license_states": advisor.get("license_states") or [],
        },
        "statesRequested": states,
    }


def build_nested_payload(advisor: dict[str, Any], carrier_id: str, states: list[str]) -> dict[str, Any]:
    """Nested shape: meta, agent, appointment (used by nested-format carrier endpoint)."""
    return {
        "meta": {"carrier_id": carrier_id},
        "agent": {
            "advisor_id": str(advisor.get("advisor_id") or advisor.get("id") or ""),
            "npn": advisor.get("npn"),
            "name": {"first": advisor.get("first_name"), "last": advisor.get("last_name")},
            "contacts": [
                {"type": "email", "value": advisor.get("email")},
                {"type": "phone", "value": advisor.get("phone")},
            ],
            "broker_dealer": advisor.get("broker_dealer"),
            "license_states": advisor.get("license_states") or [],
        },
        "appointment": {"states": states},
    }


async def dispatch_carrier_submissions(submission_ids: list[str], carrier_base_url: str) -> None:
    logger.info("[CARRIER] Dispatch started: %s submission(s), base_url=%s", len(submission_ids), carrier_base_url)
    use_json_store = os.getenv("USE_JSON_STORE", "true").lower() in {"1", "true", "yes"}
    if use_json_store:
        async with httpx.AsyncClient(base_url=carrier_base_url, timeout=30.0) as client:
            for submission_id in submission_ids:
                submission = json_store.get_submission(submission_id)
                if not submission:
                    logger.warning("CarrierSubmission not found for dispatch: %s", submission_id)
                    continue

                request_data: dict[str, Any] = submission.get("request_data") or {}
                carrier_format = (request_data.get("carrier_format") or "").lower()
                payload = request_data.get("payload")
                payload_file = request_data.get("payload_file")
                if (not payload) and payload_file:
                    payload = json_store.load_carrier_payload(str(payload_file))

                if not payload:
                    json_store.update_submission(submission_id, {"status": "error", "error_message": "Missing payload in request_data"})
                    continue

                if carrier_format == "flat":
                    path = "/api/carrier/standard/simple/appointments"
                elif carrier_format == "nested":
                    path = "/api/carrier/standard/structured/appointments"
                elif carrier_format == "custom_yaml":
                    path = "/api/carrier/custom/appointments"
                else:
                    json_store.update_submission(submission_id, {"status": "error", "error_message": f"Unknown carrier_format: {carrier_format}"})
                    continue

                full_url = carrier_base_url.rstrip("/") + path
                cid = submission.get("carrier_id")
                logger.info(
                    "[CARRIER] Hitting carrier API: POST %s (carrier_id=%s, format=%s)",
                    full_url,
                    cid,
                    carrier_format,
                )

                try:
                    resp = await client.post(path, json=payload, headers=AUTH_HEADERS)
                    resp.raise_for_status()
                    resp_json = resp.json()
                    logger.info(
                        "[CARRIER] Carrier API responded: %s carrier_id=%s status=%s keys=%s",
                        path,
                        cid,
                        resp.status_code,
                        list(resp_json.keys()) if isinstance(resp_json, dict) else resp_json,
                    )

                    response_data: dict[str, Any] = submission.get("response_data") or {}
                    response_data["carrier_api_response"] = resp_json
                    response_data["carrier_api_called_at"] = datetime.utcnow().isoformat()

                    json_store.update_submission(
                        submission_id,
                        {
                            "status": "sent_to_carrier",
                            "error_message": None,
                            "response_data": response_data,
                        },
                    )
                except Exception as e:
                    response_data = submission.get("response_data") or {}
                    response_data["carrier_api_error"] = str(e)
                    response_data["carrier_api_called_at"] = datetime.utcnow().isoformat()

                    json_store.update_submission(
                        submission_id,
                        {
                            "status": "error",
                            "error_message": str(e),
                            "response_data": response_data,
                        },
                    )

                    logger.exception("Carrier dispatch failed submission=%s", submission_id)

        return

    db = SessionLocal()
    try:
        async with httpx.AsyncClient(base_url=carrier_base_url, timeout=30.0) as client:
            for submission_id in submission_ids:
                try:
                    submission_uuid = uuid.UUID(submission_id)
                except ValueError:
                    logger.warning("Invalid submission_id (not UUID): %s", submission_id)
                    continue

                submission = db.query(CarrierSubmission).filter(CarrierSubmission.id == submission_uuid).first()
                if not submission:
                    logger.warning("CarrierSubmission not found for dispatch: %s", submission_id)
                    continue

                request_data: dict[str, Any] = submission.request_data or {}
                carrier_format = (request_data.get("carrier_format") or "").lower()
                payload = request_data.get("payload")

                if not payload:
                    submission.status = "error"
                    submission.error_message = "Missing payload in request_data"
                    db.add(submission)
                    db.commit()
                    continue

                if carrier_format == "flat":
                    path = "/api/carrier/standard/simple/appointments"
                elif carrier_format == "nested":
                    path = "/api/carrier/standard/structured/appointments"
                elif carrier_format == "custom_yaml":
                    path = "/api/carrier/custom/appointments"
                else:
                    submission.status = "error"
                    submission.error_message = f"Unknown carrier_format: {carrier_format}"
                    db.add(submission)
                    db.commit()
                    continue

                full_url = carrier_base_url.rstrip("/") + path
                logger.info(
                    "[CARRIER] Hitting carrier API: POST %s (carrier_id=%s, format=%s)",
                    full_url,
                    submission.carrier_name,
                    carrier_format,
                )

                try:
                    resp = await client.post(path, json=payload, headers=AUTH_HEADERS)
                    resp.raise_for_status()
                    resp_json = resp.json()
                    logger.info(
                        "[CARRIER] Carrier API responded: %s carrier_id=%s status=%s keys=%s",
                        path,
                        submission.carrier_name,
                        resp.status_code,
                        list(resp_json.keys()) if isinstance(resp_json, dict) else resp_json,
                    )

                    response_data: dict[str, Any] = submission.response_data or {}
                    response_data["carrier_api_response"] = resp_json
                    response_data["carrier_api_called_at"] = datetime.utcnow().isoformat()
                    submission.response_data = response_data

                    submission.status = "sent_to_carrier"
                    submission.error_message = None
                except Exception as e:
                    submission.status = "error"
                    submission.error_message = str(e)

                    response_data = submission.response_data or {}
                    response_data["carrier_api_error"] = str(e)
                    response_data["carrier_api_called_at"] = datetime.utcnow().isoformat()
                    submission.response_data = response_data

                    logger.exception("Carrier dispatch failed submission=%s", submission.id)

                db.add(submission)
                db.commit()

    finally:
        db.close()
