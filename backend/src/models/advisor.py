from sqlalchemy import Column, String, ARRAY, DateTime, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from src.utils.database import Base
import uuid
from datetime import datetime

class Advisor(Base):
    __tablename__ = "advisors"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    npn = Column(String(20), unique=True, nullable=False)
    first_name = Column(String(100))
    last_name = Column(String(100))
    email = Column(String(255))
    phone = Column(String(20))
    broker_dealer = Column(String(255))
    license_states = Column(ARRAY(String))
    status = Column(String(50), default="pending")
    document_url = Column(Text)
    transfer_date = Column(String(50))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class CarrierSubmission(Base):
    __tablename__ = "carrier_submissions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    advisor_id = Column(UUID(as_uuid=True), nullable=False)
    carrier_name = Column(String(100))
    integration_method = Column(String(20))  # 'api', 'pull', 'email'
    status = Column(String(50), default="pending")
    agent_code = Column(String(50))
    approved_states = Column(ARRAY(String))
    rejected_states = Column(ARRAY(String))
    request_data = Column(JSONB)
    response_data = Column(JSONB)
    error_message = Column(Text)
    submitted_at = Column(DateTime)
    completed_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)