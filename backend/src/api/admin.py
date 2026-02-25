from __future__ import annotations

import json
import logging
import os
import uuid
from typing import Any, List, Optional

logger = logging.getLogger(__name__)

from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from src.utils.database import get_db
from src.models.advisor import Advisor
from src.models.advisor import CarrierSubmission
from src.services.ai_service import AIService
from src.services.carrier_dispatcher import dispatch_carrier_submissions, build_flat_payload, build_nested_payload
from src.services.carrier_transform_service import (
    transform_to_carrier_format,
    get_bedrock_debug_info,
    get_last_transform_error,
    BUILTIN_NESTED_FORMAT_YAML,
)
from src.services.sns_service import sns_service

# Built-in flat format YAML so UI can display it for carriers without custom YAML
BUILTIN_FLAT_FORMAT_YAML = """# Standard carrier template (flat)
request:
  carrierId: string
  advisor:
    advisor_id: string
    npn: string
    first_name: string
    last_name: string
    email: string
    phone: string
    broker_dealer: string
    license_states: list of strings
  statesRequested: list of state codes
""".strip()
from src.utils import json_store
from src.utils import carrier_formats as carrier_formats_store
from src.utils.carrier_registry import (
    get_carrier_name,
    get_default_template,
    list_carriers as registry_list_carriers,
    STANDARD_TEMPLATE,
)
import boto3

router = APIRouter()
s3_client = boto3.client('s3')
ai_service = AIService()


class CarrierSubmissionCreateRequest(BaseModel):
    carrier_id: str
    integration_method: str = "api"
    submitted_states: List[str] = Field(default_factory=list)
    carrier_format: str = "flat"


class AdvisorCreateRequest(BaseModel):
    npn: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    broker_dealer: Optional[str] = None
    license_states: List[str] = Field(default_factory=list)
    status: str = "pending"
    document_url: Optional[str] = None
    transfer_date: Optional[str] = None


class CarrierDispatchTarget(BaseModel):
    carrier_id: str
    carrier_format: str = "flat"
    integration_method: str = "api"
    submitted_states: List[str] = Field(default_factory=list)


class DispatchAllCarriersRequest(BaseModel):
    carriers: List[CarrierDispatchTarget] = Field(default_factory=list)
    carrier_base_url: Optional[str] = None


class CreateAndTransferRequest(BaseModel):
    """One-shot: create agent and transfer to selected carriers and states. One submission per (carrier, state)."""
    agent: AdvisorCreateRequest
    carriers: List[str] = Field(default_factory=list, description="Carrier IDs e.g. ['1','2','3']")
    states: List[str] = Field(default_factory=list, description="State codes e.g. ['AL','CA']")
    carrier_base_url: Optional[str] = None


class TransferFromDocumentRequest(BaseModel):
    """Create agent from document extraction and optionally transfer to carriers."""
    form_fields: dict = Field(..., description="Extracted form fields from document")
    carriers: List[str] = Field(default_factory=list, description="Carrier IDs e.g. ['1','2','3']")
    states: List[str] = Field(default_factory=list, description="State codes e.g. ['AL','CA']")
    transfer_immediately: bool = Field(True, description="If true, transfer to carriers immediately")
    carrier_base_url: Optional[str] = None


class CarrierPayloadUploadRequest(BaseModel):
    advisor_id: str
    carrier_id: str
    carrier_format: str = "flat"
    integration_method: str = "api"
    submitted_states: List[str] = Field(default_factory=list)
    payload: dict
    dispatch_now: bool = True
    carrier_base_url: Optional[str] = None


def _carrier_payload_flat(advisor: Advisor, carrier_id: str, states: List[str]) -> dict:
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


def _carrier_payload_nested(advisor: Advisor, carrier_id: str, states: List[str]) -> dict:
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


def _advisor_to_dict(advisor: Any) -> dict:
    """Normalize Advisor ORM or dict to a plain dict for payload building."""
    if hasattr(advisor, "__dict__") and not isinstance(advisor, dict):
        return {
            "id": str(advisor.id),
            "advisor_id": str(advisor.id),
            "npn": getattr(advisor, "npn", None),
            "first_name": getattr(advisor, "first_name", None),
            "last_name": getattr(advisor, "last_name", None),
            "email": getattr(advisor, "email", None),
            "phone": getattr(advisor, "phone", None),
            "broker_dealer": getattr(advisor, "broker_dealer", None),
            "license_states": getattr(advisor, "license_states", None) or [],
        }
    d = dict(advisor) if hasattr(advisor, "keys") else advisor
    d.setdefault("advisor_id", d.get("id"))
    return d


def _log_carrier_request_body(carrier_id: str, format_used: str, payload: dict, prefix: str = "BEDROCK") -> None:
    """Log the carrier API request body for demo (Bedrock or direct builder). Truncate if very long."""
    try:
        body_str = json.dumps(payload, indent=2, default=str)
    except (TypeError, ValueError):
        body_str = str(payload)
    max_len = 4000
    if len(body_str) > max_len:
        body_str = body_str[:max_len] + "\n... (truncated)"
    logger.info(
        "[%s] Carrier request body (carrier_id=%s, format=%s):\n%s",
        prefix,
        carrier_id,
        format_used,
        body_str,
    )


async def _build_payload_for_carrier(
    advisor: Any,
    carrier_id: str,
    carrier_format: str,
    submitted_states: List[str],
) -> tuple[dict, str, bool]:
    """
    Build carrier request payload. Returns (payload, format_used, bedrock_used).
    format_used is 'custom_yaml' | 'flat' | 'nested'. Use Bedrock when custom YAML exists
    or when default template is nested (built-in nested YAML). Fall back to code builders otherwise.

    Data sources (for demo / debugging):
    - advisor: from json_store.get_advisor(advisor_id) or request body (create-and-transfer agent,
      dispatch-all/submit advisor). Contains npn, first_name, last_name, email, phone, broker_dealer, license_states.
    - submitted_states: from request (body.states in create-and-transfer, or per-carrier states in dispatch-all).
    - YAML format: loaded at request time from carrier_formats_store.load_carrier_format(carrier_id),
      which reads backend/local_data/carrier_formats/{carrier_id}.yaml. When a carrier format is added
      or updated via POST /api/admin/carrier-formats/{carrier_id}, the next transfer request uses that YAML.
    """
    advisor_dict = _advisor_to_dict(advisor)
    default_tpl = get_default_template(carrier_id)
    format_yaml = carrier_formats_store.load_carrier_format(carrier_id)

    if format_yaml:
        logger.info(
            "[BEDROCK] Using Bedrock to build carrier request for carrier_id=%s (custom YAML from carrier format upload)",
            carrier_id,
        )
        transformed = await transform_to_carrier_format(
            carrier_id, format_yaml, advisor_dict, submitted_states
        )
        if transformed is not None:
            logger.info(
                "[BEDROCK] Bedrock transform succeeded for carrier_id=%s (custom_yaml), payload keys: %s",
                carrier_id,
                list(transformed.keys())[:10],
            )
            _log_carrier_request_body(carrier_id, "custom_yaml", transformed)
            return transformed, "custom_yaml", True

    if default_tpl == "nested":
        logger.info(
            "[BEDROCK] Using Bedrock to build carrier request for carrier_id=%s (built-in nested YAML)",
            carrier_id,
        )
        nested_payload = await transform_to_carrier_format(
            carrier_id, BUILTIN_NESTED_FORMAT_YAML, advisor_dict, submitted_states
        )
        if nested_payload is not None:
            logger.info(
                "[BEDROCK] Bedrock transform succeeded for carrier_id=%s (nested), payload keys: %s",
                carrier_id,
                list(nested_payload.keys())[:10],
            )
            _log_carrier_request_body(carrier_id, "nested", nested_payload)
            return nested_payload, "nested", True
        logger.info("[CARRIER] Framing request for carrier_id=%s as format=nested (direct builder, Bedrock unavailable)", carrier_id)
        nested_direct = build_nested_payload(advisor_dict, carrier_id, submitted_states)
        _log_carrier_request_body(carrier_id, "nested", nested_direct, prefix="CARRIER")
        return nested_direct, "nested", False

    logger.info("[CARRIER] Framing request for carrier_id=%s as format=flat (direct builder, no Bedrock)", carrier_id)
    flat_payload = build_flat_payload(advisor_dict, carrier_id, submitted_states)
    _log_carrier_request_body(carrier_id, "flat", flat_payload, prefix="CARRIER")
    return flat_payload, "flat", False

@router.post("/advisors/upload")
async def upload_advisor(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """Upload advisor data (PDF/Excel) and extract information using AI"""
    bucket = os.getenv("S3_BUCKET")
    file_key = f"uploads/{file.filename}"

    if bucket:
        # 1a. Upload file to S3
        s3_client.upload_fileobj(
            file.file,
            bucket,
            file_key
        )
    else:
        # 1b. Local dev: save to local_data/uploads/
        from pathlib import Path
        local_dir = Path(__file__).resolve().parents[2] / "local_data" / "uploads"
        local_dir.mkdir(parents=True, exist_ok=True)
        local_path = local_dir / (file.filename or "upload")
        content = await file.read()
        local_path.write_bytes(content)
        file_key = str(local_path)
        bucket = "local"

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


@router.post("/create-and-transfer")
async def create_agent_and_transfer(body: CreateAndTransferRequest, background_tasks: BackgroundTasks):
    """
    Create a new agent and immediately submit transfer requests: one per (carrier, state).
    Requires USE_JSON_STORE=true. Agent details + carriers + states in one request.
    """
    use_json = os.getenv("USE_JSON_STORE", "true").lower() in {"1", "true", "yes"}
    if not use_json:
        raise HTTPException(400, "create-and-transfer is only supported when USE_JSON_STORE=true")
    try:
        advisor_id = json_store.create_advisor(body.agent.model_dump())
    except ValueError as e:
        raise HTTPException(409, str(e))
    advisor = json_store.get_advisor(advisor_id)
    if not advisor:
        raise HTTPException(500, "Advisor created but not found")

    carrier_ids = body.carriers or ["1", "2"]
    states_list = body.states or ["CA", "TX"]
    carrier_base_url = body.carrier_base_url or os.getenv("CARRIER_BASE_URL", "http://localhost:8000")

    submission_ids: List[str] = []
    for carrier_id in carrier_ids:
        carrier_format = get_default_template(carrier_id)
        if carrier_format == "nested":
            carrier_format = "nested"
        else:
            carrier_format = "flat"
        for one_state in states_list:
            submitted_states_single = [one_state]
            payload, format_used, _ = await _build_payload_for_carrier(
                advisor, carrier_id, carrier_format, submitted_states_single
            )
            submission_id = json_store.create_submission(
                {
                    "advisor_id": str(advisor.get("id")),
                    "carrier_id": carrier_id,
                    "integration_method": "api",
                    "status": "queued",
                    "request_data": {
                        "carrier_format": format_used,
                        "payload": payload,
                        "submitted_states": submitted_states_single,
                    },
                }
            )
            submission_ids.append(submission_id)

    background_tasks.add_task(dispatch_carrier_submissions, submission_ids, carrier_base_url)

    # Send SNS notification for agent transfer
    if sns_service.enabled:
        try:
            advisor_name = f"{advisor.get('first_name', '')} {advisor.get('last_name', '')}".strip() or "Unknown Advisor"
            carrier_names = [get_carrier_name(cid) for cid in carrier_ids]
            carriers_str = ", ".join(carrier_names)
            states_str = ", ".join(states_list)
            
            await sns_service.send_custom_notification(
                subject=f"Agent Transfer Created - {advisor_name}",
                message_data={
                    "event": "agent_transfer_created",
                    "advisor_id": advisor_id,
                    "advisor_name": advisor_name,
                    "carriers": carrier_names,
                    "states": states_list,
                    "submission_count": len(submission_ids),
                    "status": "sent_to_carrier"
                },
                notification_type="AgentTransfer"
            )
            logger.info(f"✅ SNS notification sent for agent transfer: {advisor_name} to {carriers_str}")
        except Exception as e:
            logger.warning(f"Failed to send SNS notification for agent transfer: {e}")

    return {
        "success": True,
        "advisor_id": advisor_id,
        "submission_ids": submission_ids,
        "status": "queued",
    }


@router.post("/transfer-from-document")
async def transfer_agent_from_document(body: TransferFromDocumentRequest):
    """
    Create agent from extracted document data and optionally transfer to carriers.
    Maps extracted form fields to agent structure and creates/transfers in one call.
    """
    use_json = os.getenv("USE_JSON_STORE", "true").lower() in {"1", "true", "yes"}
    if not use_json:
        raise HTTPException(400, "transfer-from-document is only supported when USE_JSON_STORE=true")
    
    # Map extracted form fields to agent structure
    form_fields = body.form_fields
    
    # Log received fields for debugging
    logger.info(f"📋 Received form fields: {list(form_fields.keys())}")
    
    # Common field mappings from various document types
    def get_field(keys: List[str], default: str = "") -> str:
        """Try multiple field name variations (case-insensitive)"""
        # Try exact matches first
        for key in keys:
            value = form_fields.get(key)
            if value and value not in ["(empty)", "(not specified)", "", None]:
                logger.info(f"✓ Found field '{key}' = '{value}'")
                return str(value).strip()
        
        # Try case-insensitive matches
        form_fields_lower = {k.lower(): v for k, v in form_fields.items()}
        for key in keys:
            value = form_fields_lower.get(key.lower())
            if value and value not in ["(empty)", "(not specified)", "", None]:
                logger.info(f"✓ Found field '{key}' (case-insensitive) = '{value}'")
                return str(value).strip()
        
        return default
    
    # Extract agent data from form fields with extensive variations
    agent_data = {
        "npn": get_field([
            "npn", "NPN", "National Producer Number", "producer_number", "license_number",
            "Producer Number", "License Number", "Agent Number", "agent_number"
        ]),
        "first_name": get_field([
            "first_name", "First Name", "given_name", "fname", "FirstName",
            "Given Name", "first", "First", "name_first"
        ]),
        "last_name": get_field([
            "last_name", "Last Name", "surname", "family_name", "lname", "LastName",
            "Family Name", "last", "Last", "name_last"
        ]),
        "email": get_field([
            "email", "Email", "email_address", "Email Address", "e-mail", "E-Mail",
            "EmailAddress", "contact_email"
        ]),
        "phone": get_field([
            "phone", "Phone", "phone_number", "Phone Number", "telephone", "Telephone",
            "PhoneNumber", "contact_phone", "mobile", "Mobile"
        ]),
        "broker_dealer": get_field([
            "broker_dealer", "Broker Dealer", "broker/dealer", "firm_name", "Firm Name",
            "BrokerDealer", "firm", "Firm", "company", "Company", "Company Name"
        ]),
        "license_states": [],
        "status": "pending",
    }
    
    # Handle full name if first/last not separate - try many variations
    full_name = get_field([
        "full_name", "name", "Name", "Full Name", "FullName",
        "agent_name", "Agent Name", "advisor_name", "Advisor Name",
        "applicant_name", "Applicant Name"
    ])
    if full_name and not (agent_data["first_name"] and agent_data["last_name"]):
        # Try to split name intelligently
        parts = full_name.split(maxsplit=1)
        if len(parts) >= 2:
            agent_data["first_name"] = parts[0]
            agent_data["last_name"] = parts[1]
            logger.info(f"✓ Split full name: '{full_name}' → first='{parts[0]}', last='{parts[1]}'")
        elif len(parts) == 1:
            agent_data["last_name"] = parts[0]
            logger.info(f"✓ Using single name as last name: '{parts[0]}'")
    
    # Extract license states from form fields
    license_states_str = get_field([
        "license_states", "License States", "licensed_states", 
        "states_licensed", "state_licenses", "State Licenses"
    ])
    if license_states_str:
        # Split by common delimiters and clean
        import re
        states = re.split(r'[,;\s]+', license_states_str)
        agent_data["license_states"] = [s.strip().upper() for s in states if s.strip()]
    
    # Log what we extracted
    logger.info(f"📊 Extracted agent data: first_name='{agent_data['first_name']}', last_name='{agent_data['last_name']}', npn='{agent_data['npn']}'")
    
    # Validate required fields
    if not agent_data["npn"]:
        available_fields = ", ".join(list(form_fields.keys())[:10])
        raise HTTPException(
            400, 
            f"NPN is required. Could not extract from form fields. Available fields: {available_fields}"
        )
    
    if not (agent_data["first_name"] or agent_data["last_name"]):
        # Show what fields we received to help debug
        available_fields = ", ".join(list(form_fields.keys())[:10])
        raise HTTPException(
            400, 
            f"Name is required. Could not extract from form fields. Available fields: {available_fields}"
        )
    
    # If we only have last name, use it as both
    if agent_data["last_name"] and not agent_data["first_name"]:
        agent_data["first_name"] = agent_data["last_name"]
        logger.info(f"⚠️ Only last name found, using as both first and last: '{agent_data['last_name']}'")
    
    # Check if advisor already exists (by NPN)
    existing_advisors = json_store.list_advisors()
    existing_advisor = None
    for adv in existing_advisors:
        if adv.get("npn") == agent_data["npn"]:
            existing_advisor = adv
            break
    
    # Create or use existing advisor
    if existing_advisor:
        advisor_id = str(existing_advisor.get("id"))
        advisor = existing_advisor
        logger.info(f"✓ Found existing advisor with NPN {agent_data['npn']}: {advisor_id}")
        # Note: We could update the existing advisor here if needed
    else:
        try:
            advisor_id = json_store.create_advisor(agent_data)
            advisor = json_store.get_advisor(advisor_id)
            logger.info(f"✓ Created new advisor: {advisor_id}")
        except ValueError as e:
            raise HTTPException(409, str(e))
    
    if not advisor:
        raise HTTPException(500, "Advisor created but not found")
    
    # If transfer requested, submit to carriers
    submission_ids: List[str] = []
    if body.transfer_immediately and body.carriers:
        carrier_ids = body.carriers
        states_list = body.states or agent_data["license_states"] or ["CA", "TX"]
        carrier_base_url = body.carrier_base_url or os.getenv("CARRIER_BASE_URL", "http://localhost:8000")
        
        for carrier_id in carrier_ids:
            carrier_format = get_default_template(carrier_id)
            if carrier_format == "nested":
                carrier_format = "nested"
            else:
                carrier_format = "flat"
            
            for one_state in states_list:
                submitted_states_single = [one_state]
                payload, format_used, _ = await _build_payload_for_carrier(
                    advisor, carrier_id, carrier_format, submitted_states_single
                )
                submission_id = json_store.create_submission(
                    {
                        "advisor_id": str(advisor.get("id")),
                        "carrier_id": carrier_id,
                        "integration_method": "api",
                        "status": "queued",
                        "request_data": {
                            "carrier_format": format_used,
                            "payload": payload,
                            "submitted_states": submitted_states_single,
                        },
                    }
                )
                submission_ids.append(submission_id)
        
        # Dispatch submissions
        await dispatch_carrier_submissions(submission_ids, carrier_base_url)
        
        # Send SNS notification
        if sns_service.enabled:
            try:
                advisor_name = f"{advisor.get('first_name', '')} {advisor.get('last_name', '')}".strip() or "Unknown Advisor"
                carrier_names = [get_carrier_name(cid) for cid in carrier_ids]
                
                await sns_service.send_custom_notification(
                    subject=f"Agent Transfer from Document - {advisor_name}",
                    message_data={
                        "event": "agent_transfer_from_document",
                        "advisor_id": advisor_id,
                        "advisor_name": advisor_name,
                        "carriers": carrier_names,
                        "states": states_list,
                        "submission_count": len(submission_ids),
                        "source": "document_upload",
                        "status": "sent_to_carrier"
                    },
                    notification_type="AgentTransferFromDocument"
                )
                logger.info(f"✅ SNS notification sent for document transfer: {advisor_name}")
            except Exception as e:
                logger.warning(f"Failed to send SNS notification for document transfer: {e}")
    
    return {
        "success": True,
        "advisor_id": advisor_id,
        "agent_data": agent_data,
        "submission_ids": submission_ids if body.transfer_immediately else [],
        "status": "sent_to_carrier" if body.transfer_immediately else "created",
        "extracted_fields": list(form_fields.keys())
    }


@router.get("/advisors")
async def list_advisors(
    status: Optional[str] = None,
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


@router.post("/seed")
async def seed_advisors(db: Session = Depends(get_db)):
    """Create sample advisors in local JSON store (USE_JSON_STORE=true only). For UI integration."""
    if db is not None:
        raise HTTPException(400, "Seed is only supported when USE_JSON_STORE=true")
    seed_data = [
        {"npn": "12345678", "first_name": "Jane", "last_name": "Smith", "email": "jane.smith@example.com", "phone": "555-0101", "broker_dealer": "Example BD", "license_states": ["CA", "TX", "NY"], "status": "pending"},
        {"npn": "87654321", "first_name": "John", "last_name": "Doe", "email": "john.doe@example.com", "phone": "555-0102", "broker_dealer": "Example BD", "license_states": ["CA", "FL"], "status": "pending"},
        {"npn": "11223344", "first_name": "Maria", "last_name": "Garcia", "email": "maria.garcia@example.com", "phone": "555-0103", "broker_dealer": "Another BD", "license_states": ["TX", "AZ", "NM"], "status": "completed"},
    ]
    created = []
    for data in seed_data:
        try:
            advisor_id = json_store.create_advisor(data)
            created.append({"id": advisor_id, "npn": data["npn"], "name": f"{data['first_name']} {data['last_name']}"})
        except ValueError as e:
            if "NPN already exists" not in str(e):
                raise
    return {"success": True, "created": len(created), "advisors": created}


@router.get("/debug/bedrock")
async def debug_bedrock():
    """Check why Bedrock might not be running: env vars (set/not set), region, and last error from boto3. No secrets returned."""
    return get_bedrock_debug_info()


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
            CarrierDispatchTarget(carrier_id="1", carrier_format="flat"),
            CarrierDispatchTarget(carrier_id="2", carrier_format="nested"),
        ]

    submission_ids: List[str] = []
    states_per_carrier = [c.submitted_states or [] for c in carriers]
    if not any(states_per_carrier):
        states_per_carrier = [["CA", "TX"]] * len(carriers)  # default

    for c, states_list in zip(carriers, states_per_carrier):
        carrier_format = (c.carrier_format or "").lower()
        if carrier_format not in {"flat", "nested"}:
            raise HTTPException(400, "carrier_format must be flat or nested")
        states_to_use = states_list if states_list else ["CA", "TX"]

        for one_state in states_to_use:
            submitted_states_single = [one_state]
            if db is None:
                payload, format_used, _ = await _build_payload_for_carrier(
                    advisor, c.carrier_id, carrier_format, submitted_states_single
                )
                submission_id = json_store.create_submission(
                    {
                        "advisor_id": str(advisor.get("id")),
                        "carrier_id": c.carrier_id,
                        "integration_method": c.integration_method,
                        "status": "queued",
                        "request_data": {
                            "carrier_format": format_used,
                            "payload": payload,
                            "submitted_states": submitted_states_single,
                        },
                    }
                )
                submission_ids.append(submission_id)
            else:
                payload, format_used, _ = await _build_payload_for_carrier(
                    advisor, c.carrier_id, carrier_format, submitted_states_single
                )
                submission = CarrierSubmission(
                    advisor_id=advisor.id,
                    carrier_name=c.carrier_id,
                    integration_method=c.integration_method,
                    status="queued",
                    request_data={
                        "carrier_format": format_used,
                        "payload": payload,
                        "submitted_states": submitted_states_single,
                    },
                )
                db.add(submission)
                db.commit()
                db.refresh(submission)
                submission_ids.append(str(submission.id))

    carrier_base_url = body.carrier_base_url or os.getenv("CARRIER_BASE_URL", "http://localhost:8000")
    background_tasks.add_task(dispatch_carrier_submissions, submission_ids, carrier_base_url)

    # Send SNS notification for dispatch-all
    if sns_service.enabled:
        try:
            if db is None:
                advisor_name = f"{advisor.get('first_name', '')} {advisor.get('last_name', '')}".strip() or "Unknown Advisor"
            else:
                advisor_name = f"{advisor.first_name or ''} {advisor.last_name or ''}".strip() or "Unknown Advisor"
            
            carrier_ids = [c.carrier_id for c in carriers]
            carrier_names = [get_carrier_name(cid) for cid in carrier_ids]
            carriers_str = ", ".join(carrier_names)
            
            await sns_service.send_custom_notification(
                subject=f"Agent Dispatched to Multiple Carriers - {advisor_name}",
                message_data={
                    "event": "agent_dispatch_all",
                    "advisor_id": str(advisor.get("id")) if db is None else str(advisor.id),
                    "advisor_name": advisor_name,
                    "carriers": carrier_names,
                    "submission_count": len(submission_ids),
                    "status": "sent_to_carrier"
                },
                notification_type="AgentDispatchAll"
            )
            logger.info(f"✅ SNS notification sent for dispatch-all: {advisor_name} to {carriers_str}")
        except Exception as e:
            logger.warning(f"Failed to send SNS notification for dispatch-all: {e}")

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
    if carrier_format not in {"flat", "nested"}:
        raise HTTPException(400, "carrier_format must be flat or nested")

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

    carrier_format = (body.carrier_format or "").lower()
    if carrier_format not in {"flat", "nested"}:
        raise HTTPException(400, "carrier_format must be flat or nested")

    states_to_use = body.submitted_states or ["CA", "TX"]
    submission_ids: List[str] = []

    for one_state in states_to_use:
        submitted_states_single = [one_state]
        if db is None:
            payload, format_used, _ = await _build_payload_for_carrier(
                advisor, body.carrier_id, carrier_format, submitted_states_single
            )
            submission_id = json_store.create_submission(
                {
                    "advisor_id": str(advisor.get("id")),
                    "carrier_id": body.carrier_id,
                    "integration_method": body.integration_method,
                    "status": "queued",
                    "request_data": {
                        "carrier_format": format_used,
                        "payload": payload,
                        "submitted_states": submitted_states_single,
                    },
                }
            )
            submission_ids.append(submission_id)
        else:
            payload, format_used, _ = await _build_payload_for_carrier(
                advisor, body.carrier_id, carrier_format, submitted_states_single
            )
            submission = CarrierSubmission(
                advisor_id=advisor.id,
                carrier_name=body.carrier_id,
                integration_method=body.integration_method,
                status="queued",
                request_data={
                    "carrier_format": format_used,
                    "payload": payload,
                    "submitted_states": submitted_states_single,
                },
                submitted_at=None,
            )
            db.add(submission)
            db.commit()
            db.refresh(submission)
            submission_ids.append(str(submission.id))

    carrier_base_url = os.getenv("CARRIER_BASE_URL", "http://localhost:8000")
    background_tasks.add_task(dispatch_carrier_submissions, submission_ids, carrier_base_url)

    # Send SNS notification for carrier submission
    if sns_service.enabled:
        try:
            if db is None:
                advisor_name = f"{advisor.get('first_name', '')} {advisor.get('last_name', '')}".strip() or "Unknown Advisor"
            else:
                advisor_name = f"{advisor.first_name or ''} {advisor.last_name or ''}".strip() or "Unknown Advisor"
            
            # Get carrier name from registry
            carrier_name = get_carrier_name(body.carrier_id)
            states_str = ", ".join(body.submitted_states or [])
            
            await sns_service.send_carrier_submission_notification(
                advisor_name=advisor_name,
                carrier_name=carrier_name,
                status="submitted"
            )
            logger.info(f"✅ SNS notification sent for carrier submission: {advisor_name} to {carrier_name} ({states_str})")
        except Exception as e:
            logger.warning(f"Failed to send SNS notification for carrier submission: {e}")

    return {
        "success": True,
        "submission_ids": submission_ids,
        "advisor_id": str(advisor.get("id")) if db is None else str(advisor.id),
        "carrier_id": body.carrier_id,
        "status": "queued",
    }


@router.get("/carrier-submissions")
@router.get("/carrier-submissions/")
async def list_all_carrier_submissions(db: Session = Depends(get_db)):
    """List all carrier submissions (JSON store only). For pending-transfers UI."""
    if db is not None:
        raise HTTPException(400, "List all submissions is only supported when USE_JSON_STORE=true")
    submissions = json_store.list_submissions()
    return {"success": True, "data": submissions}


@router.get("/carrier-submissions/{submission_id}")
async def get_carrier_submission(submission_id: str, db: Session = Depends(get_db)):
    if not (submission_id and submission_id.strip()):
        raise HTTPException(400, "submission_id is required")
    submission_id = submission_id.strip()
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
    carrier_id: Optional[str] = None,
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


# ---------- Carriers (id -> name registry for UI) ----------

@router.get("/carriers")
async def list_carriers_endpoint():
    """List carriers with id, display name, and default template (flat/nested) for UI."""
    carriers_raw = registry_list_carriers()
    format_ids = set(carrier_formats_store.list_carrier_format_ids())
    data = [
        {
            "id": c["id"],
            "name": c["name"],
            "default_template": get_default_template(c["id"]),
            "has_custom_yaml": c["id"] in format_ids,
        }
        for c in carriers_raw
    ]
    return {"success": True, "data": data}


@router.get("/carriers/with-formats")
async def list_carriers_with_formats():
    """
    List all carriers with id, name, format used (flat | nested | custom_yaml), and YAML content.
    Always includes yaml: built-in flat/nested YAML when no custom YAML is uploaded, else the custom YAML.
    """
    carriers_raw = registry_list_carriers()
    data = []
    for c in carriers_raw:
        cid = c["id"]
        name = c["name"]
        default_tpl = get_default_template(cid)
        yaml_content = carrier_formats_store.load_carrier_format(cid)
        if yaml_content:
            format_used = "custom_yaml"
            yaml_to_return = yaml_content
        else:
            format_used = default_tpl
            yaml_to_return = BUILTIN_NESTED_FORMAT_YAML if default_tpl == "nested" else BUILTIN_FLAT_FORMAT_YAML
        data.append({
            "carrier_id": cid,
            "name": name,
            "format_used": format_used,
            "yaml": yaml_to_return,
        })
    return {"success": True, "data": data}


# ---------- Carrier format YAML (request/response schema); used by Bedrock to transform payloads ----------

@router.get("/carrier-formats/sample")
async def get_sample_carrier_format_yaml():
    """Return the standard carrier template (flat) YAML as reference."""
    sample = """# Standard carrier template (flat)
# This is the default request shape. Carriers can upload different YAMLs; Bedrock will map agent data to the uploaded shape.

request:
  carrierId: string
  advisor:
    advisor_id: string
    npn: string
    first_name: string
    last_name: string
    email: string
    phone: string
    broker_dealer: string
    license_states: list of strings
  statesRequested: list of state codes
"""
    return {
        "success": True,
        "yaml": sample,
        "template_name": "standard (flat)",
        "description": "Reference shape. Upload carrier-specific YAMLs for different formats; use carrier ID when uploading.",
    }


class TestTransformRequest(BaseModel):
    carrier_id: str
    advisor_id: str
    states: List[str] = Field(default_factory=list)


@router.post("/carrier-formats/test-transform")
async def test_transform_payload(body: TestTransformRequest, db: Session = Depends(get_db)):
    """
    Run the payload build synchronously (no submit). Returns the JSON that would be sent to the carrier.
    Uses the same logic as submit/dispatch: custom YAML + Bedrock, or built-in nested via Bedrock, or flat/nested code builders.
    """
    if db is None:
        advisor = json_store.get_advisor(body.advisor_id)
    else:
        try:
            advisor_uuid = uuid.UUID(body.advisor_id)
        except ValueError:
            raise HTTPException(400, "advisor_id must be a UUID")
        adv = db.query(Advisor).filter(Advisor.id == advisor_uuid).first()
        if not adv:
            raise HTTPException(404, "Advisor not found")
        advisor = {
            "id": str(adv.id),
            "npn": adv.npn,
            "first_name": adv.first_name,
            "last_name": adv.last_name,
            "email": adv.email,
            "phone": adv.phone,
            "broker_dealer": adv.broker_dealer,
            "license_states": adv.license_states or [],
        }
    if not advisor:
        raise HTTPException(404, "Advisor not found")
    states = body.states or []
    carrier_id = body.carrier_id.strip() or "1"
    default_tpl = get_default_template(carrier_id)
    payload, format_used, bedrock_used = await _build_payload_for_carrier(
        advisor, carrier_id, default_tpl, states
    )
    custom_yaml_uploaded = bool(carrier_formats_store.load_carrier_format(carrier_id))
    bedrock_error = get_last_transform_error() if (custom_yaml_uploaded and not bedrock_used) else None
    return {
        "success": True,
        "payload": payload,
        "format_used": format_used,
        "carrier_id": carrier_id,
        "custom_yaml_uploaded": custom_yaml_uploaded,
        "bedrock_used": bedrock_used,
        "message": "Custom YAML is configured for this carrier but Bedrock did not run (check AWS credentials and region). Showing default payload."
        if (custom_yaml_uploaded and not bedrock_used)
        else None,
        "bedrock_error": bedrock_error,
    }


@router.post("/carrier-formats/{carrier_id}")
async def upload_carrier_format_yaml(carrier_id: str, file: UploadFile = File(...)):
    """
    Upload a YAML file that describes the carrier API request (and optionally response) format.
    Stored locally under local_data/carrier_formats/{carrier_id}.yaml. When present, Bedrock
    Claude is used to transform advisor data into this format before calling the carrier.
    """
    if not carrier_id or not carrier_id.strip():
        raise HTTPException(400, "carrier_id is required")
    content = (await file.read()).decode("utf-8", errors="replace")
    path = carrier_formats_store.save_carrier_format(carrier_id.strip(), content)
    return {"success": True, "carrier_id": carrier_id.strip(), "saved_as": path}


@router.get("/carrier-formats/{carrier_id}")
async def get_carrier_format_yaml(carrier_id: str):
    """Get the stored YAML format for a carrier, if any."""
    content = carrier_formats_store.load_carrier_format(carrier_id)
    if content is None:
        raise HTTPException(404, f"No format YAML found for carrier {carrier_id}")
    return {"success": True, "carrier_id": carrier_id, "yaml": content}


@router.get("/carrier-formats")
async def list_carrier_formats():
    """List carriers that have a format YAML stored. Includes template used (custom_yaml vs default)."""
    ids = carrier_formats_store.list_carrier_format_ids()
    items = [
        {
            "carrier_id": cid,
            "name": get_carrier_name(cid),
            "template_used": "custom_yaml",
            "default_template": get_default_template(cid),
        }
        for cid in ids
    ]
    return {"success": True, "carrier_ids": ids, "carriers": items}