import uuid

from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from src.utils.database import get_db
from src.models.advisor import Advisor
from src.models.advisor import CarrierSubmission
from src.services.ai_service import AIService
from src.services.carrier_dispatcher import dispatch_carrier_submissions, build_carrier_a_payload, build_carrier_b_payload
from src.utils import json_store
import boto3
import os

router = APIRouter()
s3_client = boto3.client('s3')
ai_service = AIService()


class CarrierSubmissionCreateRequest(BaseModel):
    carrier_id: str
    integration_method: str = "api"
    submitted_states: list[str] = Field(default_factory=list)
    carrier_format: str = "carrier_a"


class AdvisorCreateRequest(BaseModel):
    npn: str
    first_name: str | None = None
    last_name: str | None = None
    email: str | None = None
    phone: str | None = None
    broker_dealer: str | None = None
    license_states: list[str] = Field(default_factory=list)
    status: str = "pending"
    document_url: str | None = None
    transfer_date: str | None = None


class CarrierDispatchTarget(BaseModel):
    carrier_id: str
    carrier_format: str = "carrier_a"
    integration_method: str = "api"
    submitted_states: list[str] = Field(default_factory=list)


class DispatchAllCarriersRequest(BaseModel):
    carriers: list[CarrierDispatchTarget] = Field(default_factory=list)
    carrier_base_url: str | None = None


class CarrierPayloadUploadRequest(BaseModel):
    advisor_id: str
    carrier_id: str
    carrier_format: str = "carrier_a"
    integration_method: str = "api"
    submitted_states: list[str] = Field(default_factory=list)
    payload: dict
    dispatch_now: bool = True
    carrier_base_url: str | None = None


def _carrier_payload_carrier_a(advisor: Advisor, carrier_id: str, states: list[str]) -> dict:
    return {
        "carrierId": carrier_id,
        "advisor": {
            "advisor_id": str(advisor.id),
            "npn": advisor.npn,
            "first_name": advisor.first_name,
            "last_name": advisor.last_name,
            "email": advisor.email,
            "phone": advisor.phone,
            "broker_dealer": advisor.broker_dealer,
            "license_states": advisor.license_states or [],
        },
        "statesRequested": states,
    }


def _carrier_payload_carrier_b(advisor: Advisor, carrier_id: str, states: list[str]) -> dict:
    return {
        "meta": {"carrier_id": carrier_id},
        "agent": {
            "advisor_id": str(advisor.id),
            "npn": advisor.npn,
            "name": {"first": advisor.first_name, "last": advisor.last_name},
            "contacts": [
                {"type": "email", "value": advisor.email},
                {"type": "phone", "value": advisor.phone},
            ],
            "broker_dealer": advisor.broker_dealer,
            "license_states": advisor.license_states or [],
        },
        "appointment": {"states": states},
    }

@router.post("/advisors/upload")
async def upload_advisor(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """Upload advisor data (PDF/Excel) and extract information using AI"""
    
    # 1. Upload file to S3
    bucket = os.getenv("S3_BUCKET")
    file_key = f"uploads/{file.filename}"
    
    s3_client.upload_fileobj(
        file.file,
        bucket,
        file_key
    )
    
    # 2. Extract data using AI
    advisor_data = await ai_service.extract_from_file(bucket, file_key)
    
    if db is None:
        advisor_id = json_store.create_advisor(advisor_data)
    else:
        advisor = Advisor(**advisor_data)
        db.add(advisor)
        db.commit()
        db.refresh(advisor)
        advisor_id = str(advisor.id)
    
    # 4. Process carriers (background task)
    # TODO: Implement carrier processing
    
    return {
        "success": True,
        "advisor_id": advisor_id,
        "status": "processing"
    }


@router.post("/advisors")
async def create_advisor(body: AdvisorCreateRequest, db: Session = Depends(get_db)):
    if db is None:
        try:
            advisor_id = json_store.create_advisor(body.model_dump())
        except ValueError as e:
            raise HTTPException(409, str(e))
        return {"success": True, "advisor_id": advisor_id}

    existing = db.query(Advisor).filter(Advisor.npn == body.npn).first()
    if existing:
        raise HTTPException(409, "Advisor with this NPN already exists")

    advisor = Advisor(
        npn=body.npn,
        first_name=body.first_name,
        last_name=body.last_name,
        email=body.email,
        phone=body.phone,
        broker_dealer=body.broker_dealer,
        license_states=body.license_states,
        status=body.status,
        document_url=body.document_url,
        transfer_date=body.transfer_date,
    )
    db.add(advisor)
    db.commit()
    db.refresh(advisor)

    return {"success": True, "advisor_id": str(advisor.id)}


@router.get("/advisors")
async def list_advisors(
    status: str = None,
    db: Session = Depends(get_db)
):
    """List all advisors"""
    if db is None:
        advisors = json_store.list_advisors(status=status)
        return {
            "success": True,
            "data": [
                {
                    "id": str(a.get("id")),
                    "npn": a.get("npn"),
                    "name": f"{a.get('first_name') or ''} {a.get('last_name') or ''}".strip(),
                    "status": a.get("status"),
                    "created_at": a.get("created_at"),
                }
                for a in advisors
            ],
        }

    query = db.query(Advisor)

    if status:
        query = query.filter(Advisor.status == status)

    advisors = query.all()

    return {
        "success": True,
        "data": [
            {
                "id": str(a.id),
                "npn": a.npn,
                "name": f"{a.first_name} {a.last_name}",
                "status": a.status,
                "created_at": a.created_at.isoformat(),
            }
            for a in advisors
        ],
    }


@router.get("/advisors/{advisor_id}")
async def get_advisor(
    advisor_id: str,
    db: Session = Depends(get_db)
):
    """Get advisor details"""
    if db is None:
        advisor = json_store.get_advisor(advisor_id)
        if not advisor:
            raise HTTPException(404, "Advisor not found")

        return {
            "success": True,
            "data": {
                "id": str(advisor.get("id")),
                "npn": advisor.get("npn"),
                "first_name": advisor.get("first_name"),
                "last_name": advisor.get("last_name"),
                "email": advisor.get("email"),
                "phone": advisor.get("phone"),
                "broker_dealer": advisor.get("broker_dealer"),
                "license_states": advisor.get("license_states") or [],
                "status": advisor.get("status"),
                "transfer_date": advisor.get("transfer_date"),
            },
        }

    try:
        advisor_uuid = uuid.UUID(advisor_id)
    except ValueError:
        raise HTTPException(400, "advisor_id must be a UUID")

    advisor = db.query(Advisor).filter(Advisor.id == advisor_uuid).first()
    
    if not advisor:
        raise HTTPException(404, "Advisor not found")
    
    return {
        "success": True,
        "data": {
            "id": str(advisor.id),
            "npn": advisor.npn,
            "first_name": advisor.first_name,
            "last_name": advisor.last_name,
            "email": advisor.email,
            "phone": advisor.phone,
            "broker_dealer": advisor.broker_dealer,
            "license_states": advisor.license_states,
            "status": advisor.status,
            "transfer_date": advisor.transfer_date,
        }
    }


@router.post("/advisors/{advisor_id}/carriers/dispatch-all")
async def dispatch_advisor_to_all_carriers(
    advisor_id: str,
    body: DispatchAllCarriersRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    if db is None:
        advisor = json_store.get_advisor(advisor_id)
        if not advisor:
            raise HTTPException(404, "Advisor not found")
    else:
        try:
            advisor_uuid = uuid.UUID(advisor_id)
        except ValueError:
            raise HTTPException(400, "advisor_id must be a UUID")

        advisor = db.query(Advisor).filter(Advisor.id == advisor_uuid).first()
        if not advisor:
            raise HTTPException(404, "Advisor not found")

    carriers = body.carriers
    if not carriers:
        carriers = [
            CarrierDispatchTarget(carrier_id="carrier-a", carrier_format="carrier_a"),
            CarrierDispatchTarget(carrier_id="carrier-b", carrier_format="carrier_b"),
        ]

    submission_ids: list[str] = []
    for c in carriers:
        carrier_format = (c.carrier_format or "").lower()
        if carrier_format not in {"carrier_a", "carrier_b"}:
            raise HTTPException(400, "carrier_format must be carrier_a or carrier_b")

        if db is None:
            if carrier_format == "carrier_a":
                payload = build_carrier_a_payload(advisor, c.carrier_id, c.submitted_states)
            else:
                payload = build_carrier_b_payload(advisor, c.carrier_id, c.submitted_states)

            submission_id = json_store.create_submission(
                {
                    "advisor_id": str(advisor.get("id")),
                    "carrier_id": c.carrier_id,
                    "integration_method": c.integration_method,
                    "status": "queued",
                    "request_data": {
                        "carrier_format": carrier_format,
                        "payload": payload,
                        "submitted_states": c.submitted_states,
                    },
                }
            )
            submission_ids.append(submission_id)
        else:
            if carrier_format == "carrier_a":
                payload = _carrier_payload_carrier_a(advisor, c.carrier_id, c.submitted_states)
            else:
                payload = _carrier_payload_carrier_b(advisor, c.carrier_id, c.submitted_states)

            submission = CarrierSubmission(
                advisor_id=advisor.id,
                carrier_name=c.carrier_id,
                integration_method=c.integration_method,
                status="queued",
                request_data={
                    "carrier_format": carrier_format,
                    "payload": payload,
                    "submitted_states": c.submitted_states,
                },
            )
            db.add(submission)
            db.commit()
            db.refresh(submission)
            submission_ids.append(str(submission.id))

    carrier_base_url = body.carrier_base_url or os.getenv("CARRIER_BASE_URL", "http://localhost:8000")
    background_tasks.add_task(dispatch_carrier_submissions, submission_ids, carrier_base_url)

    return {
        "success": True,
        "advisor_id": str(advisor.get("id")) if db is None else str(advisor.id),
        "carrier_base_url": carrier_base_url,
        "submission_ids": submission_ids,
        "status": "queued",
    }


@router.post("/carriers/payloads")
async def upload_carrier_payload(
    body: CarrierPayloadUploadRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    if db is not None:
        raise HTTPException(400, "This endpoint is only supported when USE_JSON_STORE=true")

    advisor = json_store.get_advisor(body.advisor_id)
    if not advisor:
        raise HTTPException(404, "Advisor not found")

    carrier_format = (body.carrier_format or "").lower()
    if carrier_format not in {"carrier_a", "carrier_b"}:
        raise HTTPException(400, "carrier_format must be carrier_a or carrier_b")

    payload_file = json_store.save_carrier_payload(body.payload)

    submission_id = json_store.create_submission(
        {
            "advisor_id": body.advisor_id,
            "carrier_id": body.carrier_id,
            "integration_method": body.integration_method,
            "status": "queued" if body.dispatch_now else "submitted",
            "request_data": {
                "carrier_format": carrier_format,
                "payload_file": payload_file,
                "submitted_states": body.submitted_states,
            },
        }
    )

    if body.dispatch_now:
        carrier_base_url = body.carrier_base_url or os.getenv("CARRIER_BASE_URL", "http://localhost:8000")
        background_tasks.add_task(dispatch_carrier_submissions, [submission_id], carrier_base_url)

    return {
        "success": True,
        "submission_id": submission_id,
        "advisor_id": body.advisor_id,
        "carrier_id": body.carrier_id,
        "payload_file": payload_file,
        "status": "queued" if body.dispatch_now else "submitted",
    }


@router.post("/advisors/{advisor_id}/carriers/submit")
async def submit_advisor_to_carrier(
    advisor_id: str,
    body: CarrierSubmissionCreateRequest,
    db: Session = Depends(get_db),
):
    if db is None:
        advisor = json_store.get_advisor(advisor_id)
        if not advisor:
            raise HTTPException(404, "Advisor not found")
    else:
        try:
            advisor_uuid = uuid.UUID(advisor_id)
        except ValueError:
            raise HTTPException(400, "advisor_id must be a UUID")

        advisor = db.query(Advisor).filter(Advisor.id == advisor_uuid).first()
        if not advisor:
            raise HTTPException(404, "Advisor not found")

    carrier_format = (body.carrier_format or "").lower()
    if carrier_format not in {"carrier_a", "carrier_b"}:
        raise HTTPException(400, "carrier_format must be carrier_a or carrier_b")

    if db is None:
        if carrier_format == "carrier_a":
            payload = build_carrier_a_payload(advisor, body.carrier_id, body.submitted_states)
        else:
            payload = build_carrier_b_payload(advisor, body.carrier_id, body.submitted_states)

        submission_id = json_store.create_submission(
            {
                "advisor_id": str(advisor.get("id")),
                "carrier_id": body.carrier_id,
                "integration_method": body.integration_method,
                "status": "submitted",
                "request_data": {
                    "carrier_format": carrier_format,
                    "payload": payload,
                    "submitted_states": body.submitted_states,
                },
            }
        )

        return {
            "success": True,
            "submission_id": submission_id,
            "advisor_id": str(advisor.get("id")),
            "carrier_id": body.carrier_id,
            "status": "submitted",
            "payload": payload,
        }

    if carrier_format == "carrier_a":
        payload = _carrier_payload_carrier_a(advisor, body.carrier_id, body.submitted_states)
    else:
        payload = _carrier_payload_carrier_b(advisor, body.carrier_id, body.submitted_states)

    submission = CarrierSubmission(
        advisor_id=advisor.id,
        carrier_name=body.carrier_id,
        integration_method=body.integration_method,
        status="submitted",
        request_data={
            "carrier_format": carrier_format,
            "payload": payload,
            "submitted_states": body.submitted_states,
        },
        submitted_at=None,
    )
    db.add(submission)
    db.commit()
    db.refresh(submission)

    return {
        "success": True,
        "submission_id": str(submission.id),
        "advisor_id": str(submission.advisor_id),
        "carrier_id": submission.carrier_name,
        "status": submission.status,
        "payload": payload,
    }


@router.get("/carrier-submissions/{submission_id}")
async def get_carrier_submission(submission_id: str, db: Session = Depends(get_db)):
    if db is None:
        submission = json_store.get_submission(submission_id)
        if not submission:
            raise HTTPException(404, "Carrier submission not found")

        return {"success": True, "data": submission}

    try:
        submission_uuid = uuid.UUID(submission_id)
    except ValueError:
        raise HTTPException(400, "submission_id must be a UUID")

    submission = db.query(CarrierSubmission).filter(CarrierSubmission.id == submission_uuid).first()
    if not submission:
        raise HTTPException(404, "Carrier submission not found")

    return {
        "success": True,
        "data": {
            "id": str(submission.id),
            "advisor_id": str(submission.advisor_id),
            "carrier_id": submission.carrier_name,
            "integration_method": submission.integration_method,
            "status": submission.status,
            "agent_code": submission.agent_code,
            "accepted_states": submission.approved_states,
            "rejected_states": submission.rejected_states,
            "request_data": submission.request_data,
            "response_data": submission.response_data,
            "error_message": submission.error_message,
            "submitted_at": submission.submitted_at.isoformat() if submission.submitted_at else None,
            "completed_at": submission.completed_at.isoformat() if submission.completed_at else None,
            "created_at": submission.created_at.isoformat() if submission.created_at else None,
        },
    }


@router.get("/advisors/{advisor_id}/carrier-submissions")
async def list_advisor_carrier_submissions(
    advisor_id: str,
    carrier_id: str | None = None,
    db: Session = Depends(get_db),
):
    if db is None:
        submissions = json_store.list_submissions(advisor_id=advisor_id, carrier_id=carrier_id)
        return {"success": True, "data": submissions}

    try:
        advisor_uuid = uuid.UUID(advisor_id)
    except ValueError:
        raise HTTPException(400, "advisor_id must be a UUID")

    query = db.query(CarrierSubmission).filter(CarrierSubmission.advisor_id == advisor_uuid)
    if carrier_id:
        query = query.filter(CarrierSubmission.carrier_name == carrier_id)

    submissions = query.order_by(CarrierSubmission.created_at.desc()).all()

    return {
        "success": True,
        "data": [
            {
                "id": str(s.id),
                "carrier_id": s.carrier_name,
                "status": s.status,
                "agent_code": s.agent_code,
                "accepted_states": s.approved_states,
                "rejected_states": s.rejected_states,
                "created_at": s.created_at.isoformat() if s.created_at else None,
            }
            for s in submissions
        ],
    }