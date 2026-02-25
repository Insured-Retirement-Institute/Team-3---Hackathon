"""
SNS Notifications API
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
import logging
from src.services.sns_service import sns_service

logger = logging.getLogger(__name__)

router = APIRouter()


class NotificationRequest(BaseModel):
    """Request model for sending notifications"""
    subject: str = Field(..., description="Email subject line", min_length=1, max_length=100)
    message: str = Field(..., description="Message body", min_length=1)
    message_attributes: Optional[Dict[str, str]] = Field(
        default=None,
        description="Optional message attributes for filtering"
    )


class DocumentProcessedNotification(BaseModel):
    """Request model for document processed notification"""
    filename: str = Field(..., description="Name of the processed file")
    advisor_name: Optional[str] = Field(None, description="Name of the advisor")
    form_fields_count: int = Field(0, description="Number of form fields extracted")
    highlighted_items_count: int = Field(0, description="Number of highlighted items found")
    status: str = Field("processed", description="Processing status")


class CarrierSubmissionNotification(BaseModel):
    """Request model for carrier submission notification"""
    advisor_name: str = Field(..., description="Name of the advisor")
    carrier_name: str = Field(..., description="Name of the carrier")
    status: str = Field("submitted", description="Submission status")


class CustomNotification(BaseModel):
    """Request model for custom notification"""
    subject: str = Field(..., description="Notification subject")
    message_data: Dict[str, Any] = Field(..., description="Data to be sent as JSON")
    notification_type: str = Field("Custom", description="Type of notification")


@router.get("/status")
async def get_sns_status():
    """Get SNS service status and configuration"""
    if not sns_service.enabled:
        return {
            "enabled": False,
            "message": "SNS service is not enabled or configured"
        }
    
    attributes = sns_service.get_topic_attributes()
    subscriptions = sns_service.list_subscriptions()
    
    return {
        "enabled": True,
        "topic_arn": sns_service.topic_arn,
        "region": sns_service.client.meta.region_name,
        "subscriptions_count": len(subscriptions),
        "subscriptions": [
            {
                "endpoint": sub.get('Endpoint'),
                "protocol": sub.get('Protocol'),
                "status": sub.get('SubscriptionArn') != 'PendingConfirmation'
            }
            for sub in subscriptions
        ]
    }


@router.post("/send")
async def send_notification(request: NotificationRequest):
    """
    Send a custom notification to SNS topic
    
    Example:
    ```json
    {
        "subject": "Test Notification",
        "message": "This is a test message",
        "message_attributes": {
            "priority": "high",
            "source": "api"
        }
    }
    ```
    """
    if not sns_service.enabled:
        raise HTTPException(
            status_code=503,
            detail="SNS service is not enabled or configured"
        )
    
    result = await sns_service.send_notification(
        subject=request.subject,
        message=request.message,
        message_attributes=request.message_attributes
    )
    
    if not result.get("success"):
        raise HTTPException(
            status_code=500,
            detail=result.get("error", "Failed to send notification")
        )
    
    return result


@router.post("/document-processed")
async def send_document_processed_notification(request: DocumentProcessedNotification):
    """
    Send notification when a document is processed
    
    Example:
    ```json
    {
        "filename": "advisor_form.pdf",
        "advisor_name": "John Doe",
        "form_fields_count": 25,
        "highlighted_items_count": 5,
        "status": "processed"
    }
    ```
    """
    if not sns_service.enabled:
        raise HTTPException(
            status_code=503,
            detail="SNS service is not enabled or configured"
        )
    
    result = await sns_service.send_document_processed_notification(
        filename=request.filename,
        advisor_name=request.advisor_name,
        form_fields_count=request.form_fields_count,
        highlighted_items_count=request.highlighted_items_count,
        status=request.status
    )
    
    if not result.get("success"):
        raise HTTPException(
            status_code=500,
            detail=result.get("error", "Failed to send notification")
        )
    
    return result


@router.post("/carrier-submission")
async def send_carrier_submission_notification(request: CarrierSubmissionNotification):
    """
    Send notification when advisor data is submitted to a carrier
    
    Example:
    ```json
    {
        "advisor_name": "John Doe",
        "carrier_name": "AIG",
        "status": "submitted"
    }
    ```
    """
    if not sns_service.enabled:
        raise HTTPException(
            status_code=503,
            detail="SNS service is not enabled or configured"
        )
    
    result = await sns_service.send_carrier_submission_notification(
        advisor_name=request.advisor_name,
        carrier_name=request.carrier_name,
        status=request.status
    )
    
    if not result.get("success"):
        raise HTTPException(
            status_code=500,
            detail=result.get("error", "Failed to send notification")
        )
    
    return result


@router.post("/custom")
async def send_custom_notification(request: CustomNotification):
    """
    Send a custom JSON notification
    
    Example:
    ```json
    {
        "subject": "Application Status Update",
        "message_data": {
            "application_id": "12345",
            "status": "approved",
            "timestamp": "2024-02-25T10:30:00Z"
        },
        "notification_type": "StatusUpdate"
    }
    ```
    """
    if not sns_service.enabled:
        raise HTTPException(
            status_code=503,
            detail="SNS service is not enabled or configured"
        )
    
    result = await sns_service.send_custom_notification(
        subject=request.subject,
        message_data=request.message_data,
        notification_type=request.notification_type
    )
    
    if not result.get("success"):
        raise HTTPException(
            status_code=500,
            detail=result.get("error", "Failed to send notification")
        )
    
    return result
