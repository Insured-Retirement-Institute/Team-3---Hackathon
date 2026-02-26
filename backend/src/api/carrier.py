from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from fastapi import APIRouter, Body, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from src.models.advisor import Advisor, CarrierSubmission
from src.utils.database import get_db
from src.utils import json_store

router = APIRouter()


class AdvisorPayload(BaseModel):
    advisor_id: str
    npn: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    broker_dealer: Optional[str] = None
    license_states: List[str] = Field(default_factory=list)


# ---------- Standard flat format (expandable in Swagger) ----------
class StandardFlatAdvisorRequest(BaseModel):
    """Advisor block for standard flat carrier format."""
    advisor_id: Optional[str] = Field(None, description="Advisor UUID or id")
    id: Optional[str] = Field(None, description="Alias for advisor_id")
    npn: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    broker_dealer: Optional[str] = None
    brokerDealer: Optional[str] = None
    license_states: Optional[List[str]] = Field(default_factory=list)
    licenseStates: Optional[List[str]] = None


class StandardFlatAppointmentRequest(BaseModel):
    """Standard flat carrier appointment request (carrierId + advisor + statesRequested)."""
    carrierId: str = Field(..., description="Carrier ID (e.g. 1)")
    advisor: StandardFlatAdvisorRequest = Field(..., description="Advisor details")
    statesRequested: List[str] = Field(default_factory=list, description="Requested state codes")


class CarrierAAppointmentRequest(BaseModel):
    """Alias for OpenAPI; use StandardFlatAppointmentRequest in routes."""
    carrierId: str
    advisor: StandardFlatAdvisorRequest
    statesRequested: List[str] = Field(default_factory=list)


class CarrierAAppointmentResponse(BaseModel):
    carrierId: str
    carrierTrackingId: str
    status: str
    acceptedStates: List[str] = Field(default_factory=list)


# ---------- Standard nested format (expandable in Swagger) ----------
class StandardNestedMetaRequest(BaseModel):
    """Meta block for standard nested carrier format."""
    carrier_id: Optional[str] = Field(None, description="Carrier ID")
    carrierId: Optional[str] = None


class StandardNestedNameRequest(BaseModel):
    first: Optional[str] = None
    last: Optional[str] = None


class StandardNestedContactRequest(BaseModel):
    type: Optional[str] = Field(None, description="e.g. email, phone")
    value: Optional[str] = None


class StandardNestedAgentRequest(BaseModel):
    """Agent block for standard nested carrier format."""
    advisor_id: Optional[str] = Field(None, description="Advisor UUID or id")
    id: Optional[str] = None
    npn: Optional[str] = None
    name: Optional[StandardNestedNameRequest] = None
    contacts: Optional[List[StandardNestedContactRequest]] = Field(default_factory=list)
    broker_dealer: Optional[str] = None
    brokerDealer: Optional[str] = None
    license_states: Optional[List[str]] = Field(default_factory=list)
    licenseStates: Optional[List[str]] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None


class StandardNestedAppointmentBlockRequest(BaseModel):
    """Appointment block (states) for standard nested format."""
    states: Optional[List[str]] = Field(default_factory=list, description="Requested state codes")


class StandardNestedAppointmentRequest(BaseModel):
    """Standard nested carrier appointment request (meta + agent + appointment)."""
    meta: StandardNestedMetaRequest = Field(..., description="Carrier meta")
    agent: StandardNestedAgentRequest = Field(..., description="Agent details")
    appointment: StandardNestedAppointmentBlockRequest = Field(..., description="Appointment / states")


class CarrierBAppointmentRequest(BaseModel):
    """Alias for OpenAPI; use StandardNestedAppointmentRequest in routes."""
    meta: StandardNestedMetaRequest
    agent: StandardNestedAgentRequest
    appointment: StandardNestedAppointmentBlockRequest


class CarrierBAppointmentResponse(BaseModel):
    meta: Dict[str, Any]
    result: Dict[str, Any]


class CarrierStatusUpdateRequest(BaseModel):
    submission_id: Optional[str] = None
    advisor_id: Optional[str] = None
    carrier_id: str
    status: str
    agent_code: Optional[str] = None
    failure_reason: Optional[str] = None
    submitted_states: List[str] = Field(default_factory=list)
    accepted_states: List[str] = Field(default_factory=list)
    rejected_states: List[str] = Field(default_factory=list)


def _to_dict(obj: Any) -> dict:
    """Convert Pydantic model to dict for normalizer compatibility."""
    if hasattr(obj, "model_dump"):
        return obj.model_dump()
    return dict(obj) if obj else {}


def _normalize_advisor_from_a(req: CarrierAAppointmentRequest) -> Tuple[str, AdvisorPayload, List[str]]:
    carrier_id = req.carrierId
    a = _to_dict(req.advisor)
    advisor_id = str(a.get("advisor_id") or a.get("id") or "")
    if not advisor_id:
        raise HTTPException(400, "advisor_id is required")

    payload = AdvisorPayload(
        advisor_id=advisor_id,
        npn=str(a.get("npn") or ""),
        first_name=a.get("first_name") or a.get("firstName"),
        last_name=a.get("last_name") or a.get("lastName"),
        email=a.get("email"),
        phone=a.get("phone"),
        broker_dealer=a.get("broker_dealer") or a.get("brokerDealer"),
        license_states=list(a.get("license_states") or a.get("licenseStates") or []),
    )
    return carrier_id, payload, req.statesRequested


def _normalize_advisor_from_b(req: CarrierBAppointmentRequest) -> Tuple[str, AdvisorPayload, List[str]]:
    meta = _to_dict(req.meta)
    carrier_id = str(meta.get("carrier_id") or meta.get("carrierId") or "")
    if not carrier_id:
        raise HTTPException(400, "carrier_id is required")

    agent = _to_dict(req.agent)
    advisor_id = str(agent.get("advisor_id") or agent.get("id") or "")
    if not advisor_id:
        raise HTTPException(400, "advisor_id is required")

    name = agent.get("name") or {}
    contacts = agent.get("contacts") or []
    email = None
    phone = None
    for c in contacts:
        if not isinstance(c, dict):
            continue
        if c.get("type") == "email" and not email:
            email = c.get("value")
        if c.get("type") == "phone" and not phone:
            phone = c.get("value")

    payload = AdvisorPayload(
        advisor_id=advisor_id,
        npn=str(agent.get("npn") or ""),
        first_name=name.get("first") or agent.get("first_name"),
        last_name=name.get("last") or agent.get("last_name"),
        email=email,
        phone=phone,
        broker_dealer=agent.get("broker_dealer") or agent.get("brokerDealer"),
        license_states=list(agent.get("license_states") or agent.get("licenseStates") or []),
    )

    appointment = _to_dict(req.appointment)
    states = appointment.get("states") if appointment else None
    return carrier_id, payload, list(states or [])


@router.post(
    "/standard/simple/appointments",
    response_model=CarrierAAppointmentResponse,
    summary="Standard simple appointment",
    description="Standard carrier format: carrierId + advisor + statesRequested. Used for carrier ID 1 and others with the simple (single-level) template.",
)
async def standard_simple_appointments(req: StandardFlatAppointmentRequest):
    """Standard simple (single-level) carrier endpoint (carrier ID 1 and others)."""
    # Normalizer expects CarrierAAppointmentRequest shape
    carrier_id, _advisor, requested_states = _normalize_advisor_from_a(CarrierAAppointmentRequest(carrierId=req.carrierId, advisor=req.advisor, statesRequested=req.statesRequested))
    tracking_id = f"1-{uuid.uuid4().hex[:10]}"
    return CarrierAAppointmentResponse(
        carrierId=carrier_id,
        carrierTrackingId=tracking_id,
        status="submitted",
        acceptedStates=requested_states,
    )


@router.post(
    "/standard/structured/appointments",
    response_model=CarrierBAppointmentResponse,
    summary="Standard structured appointment",
    description="Standard carrier format: meta + agent + appointment (hierarchical). Used for carrier ID 2.",
)
async def standard_structured_appointments(req: StandardNestedAppointmentRequest):
    """Standard structured (hierarchical) carrier endpoint (carrier ID 2)."""
    carrier_id, _advisor, requested_states = _normalize_advisor_from_b(CarrierBAppointmentRequest(meta=req.meta, agent=req.agent, appointment=req.appointment))
    tracking_id = f"2-{uuid.uuid4().hex[:10]}"
    return CarrierBAppointmentResponse(
        meta={"carrier_id": carrier_id, "carrier_tracking_id": tracking_id},
        result={"status": "submitted", "accepted_states": requested_states},
    )


class CustomApplicantRequest(BaseModel):
    """Applicant block (example for custom/Bedrock format)."""
    id: Optional[str] = None
    national_producer_number: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email_address: Optional[str] = None
    phone_number: Optional[str] = None
    broker_dealer: Optional[str] = None
    licensed_states: Optional[List[str]] = None


class CustomApplicationRequest(BaseModel):
    """Application block (example for custom/Bedrock format)."""
    carrier_code: Optional[str] = None
    applicant: Optional[CustomApplicantRequest] = None
    jurisdictions: Optional[List[str]] = None


class CustomAppointmentRequest(BaseModel):
    """Custom carrier payload (Bedrock/custom YAML shape). Extra fields allowed."""
    model_config = {"extra": "allow"}
    application: Optional[CustomApplicationRequest] = Field(None, description="Example shape; actual shape depends on carrier YAML")


@router.post(
    "/custom/appointments",
    summary="Custom format appointment",
    description="Custom carrier format: payload shape defined by carrier YAML (Bedrock transform). Used when carrier has custom format uploaded.",
)
async def custom_appointments(payload: CustomAppointmentRequest):
    """
    Accept any JSON payload (custom YAML / Bedrock-generated format).
    Used when request_data.carrier_format is 'custom_yaml'. Returns a generic success response.
    """
    tracking_id = f"custom-{uuid.uuid4().hex[:10]}"
    return {
        "carrier_tracking_id": tracking_id,
        "status": "submitted",
        "message": "Custom format payload received",
    }


@router.post("/appointments/status")
async def carrier_update_status(req: CarrierStatusUpdateRequest, db: Session = Depends(get_db)):
    if db is None:
        submission = None
        if req.submission_id:
            submission = json_store.get_submission(req.submission_id)

        if not submission:
            if not req.advisor_id:
                raise HTTPException(400, "advisor_id is required when submission_id is not provided")
            submission = json_store.find_latest_submission(req.advisor_id, req.carrier_id)

        if not submission:
            raise HTTPException(404, "Carrier submission not found")

        request_data = submission.get("request_data") or {}
        request_data["submitted_states"] = req.submitted_states

        response_data = submission.get("response_data") or {}
        response_data["status_update"] = req.model_dump()
        response_data["state_decision"] = {
            "submitted_states": req.submitted_states,
            "accepted_states": req.accepted_states,
            "rejected_states": req.rejected_states,
        }

        patch = {
            "status": req.status,
            "agent_code": req.agent_code,
            "accepted_states": req.accepted_states,
            "rejected_states": req.rejected_states,
            "request_data": request_data,
            "response_data": response_data,
            "error_message": req.failure_reason,
        }

        if req.status.lower() in {"completed", "finished", "done"}:
            patch["completed_at"] = datetime.utcnow().isoformat()
            json_store.update_advisor(str(submission.get("advisor_id")), {"status": "completed"})

        updated = json_store.update_submission(str(submission.get("id")), patch)
        if not updated:
            raise HTTPException(500, "Failed to update submission")

        return {
            "success": True,
            "submission_id": str(updated.get("id")),
            "advisor_id": str(updated.get("advisor_id")),
            "carrier_id": str(updated.get("carrier_id")),
            "status": updated.get("status"),
            "agent_code": updated.get("agent_code"),
            "failure_reason": updated.get("error_message"),
            "accepted_states": updated.get("accepted_states"),
            "rejected_states": updated.get("rejected_states"),
        }

    submission: Optional[CarrierSubmission] = None

    if req.submission_id:
        try:
            submission_uuid = uuid.UUID(req.submission_id)
        except ValueError:
            raise HTTPException(400, "submission_id must be a UUID")

        submission = db.query(CarrierSubmission).filter(CarrierSubmission.id == submission_uuid).first()

    if not submission:
        if not req.advisor_id:
            raise HTTPException(400, "advisor_id is required when submission_id is not provided")

        try:
            advisor_uuid = uuid.UUID(req.advisor_id)
        except ValueError:
            raise HTTPException(400, "advisor_id must be a UUID")

        submission = (
            db.query(CarrierSubmission)
            .filter(CarrierSubmission.advisor_id == advisor_uuid)
            .filter(CarrierSubmission.carrier_name == req.carrier_id)
            .order_by(CarrierSubmission.created_at.desc())
            .first()
        )

    if not submission:
        raise HTTPException(404, "Carrier submission not found")

    submission.status = req.status
    if req.agent_code is not None:
        submission.agent_code = req.agent_code
    if req.failure_reason is not None:
        submission.error_message = req.failure_reason
    if req.accepted_states is not None:
        submission.approved_states = req.accepted_states
    if req.rejected_states is not None:
        submission.rejected_states = req.rejected_states

    request_data = submission.request_data or {}
    request_data["submitted_states"] = req.submitted_states
    submission.request_data = request_data

    response_data = submission.response_data or {}
    response_data["status_update"] = req.model_dump()
    response_data["state_decision"] = {
        "submitted_states": req.submitted_states,
        "accepted_states": req.accepted_states,
        "rejected_states": req.rejected_states,
    }
    submission.response_data = response_data

    if req.status.lower() in {"completed", "finished", "done"}:
        submission.completed_at = datetime.utcnow()

        advisor = db.query(Advisor).filter(Advisor.id == submission.advisor_id).first()
        if advisor:
            advisor.status = "completed"

    db.add(submission)
    db.commit()
    db.refresh(submission)

    return {
        "success": True,
        "submission_id": str(submission.id),
        "advisor_id": str(submission.advisor_id),
        "carrier_id": submission.carrier_name,
        "status": submission.status,
        "agent_code": submission.agent_code,
        "failure_reason": submission.error_message,
        "accepted_states": submission.approved_states,
        "rejected_states": submission.rejected_states,
    }
