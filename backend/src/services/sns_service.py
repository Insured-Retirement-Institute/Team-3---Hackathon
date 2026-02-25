"""
AWS SNS Service for sending notifications
"""
import boto3
import json
import logging
from typing import Optional, Dict, Any, List
from botocore.exceptions import ClientError
from src import config

logger = logging.getLogger(__name__)


class SNSService:
    """Service for sending notifications via AWS SNS"""
    
    def __init__(self):
        """Initialize SNS client"""
        self.enabled = config.SNS_ENABLED
        
        if not self.enabled:
            logger.warning("SNS is disabled. Set SNS_ENABLED=true in .env to enable.")
            self.client = None
            return
        
        if not config.SNS_TOPIC_ARN:
            logger.error("SNS_TOPIC_ARN not configured in .env")
            self.enabled = False
            self.client = None
            return
        
        try:
            session_kwargs = {
                'region_name': config.AWS_REGION
            }
            
            if config.AWS_ACCESS_KEY_ID and config.AWS_SECRET_ACCESS_KEY:
                session_kwargs['aws_access_key_id'] = config.AWS_ACCESS_KEY_ID
                session_kwargs['aws_secret_access_key'] = config.AWS_SECRET_ACCESS_KEY
                
                if config.AWS_SESSION_TOKEN:
                    session_kwargs['aws_session_token'] = config.AWS_SESSION_TOKEN
            
            self.client = boto3.client('sns', **session_kwargs)
            self.topic_arn = config.SNS_TOPIC_ARN
            logger.info(f"✅ SNS Service initialized with topic: {self.topic_arn}")
            
        except Exception as e:
            logger.error(f"Failed to initialize SNS client: {e}")
            self.enabled = False
            self.client = None
    
    async def send_notification(
        self,
        subject: str,
        message: str,
        message_attributes: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Send a notification to SNS topic
        
        Args:
            subject: Email subject line
            message: Message body (plain text or JSON string)
            message_attributes: Optional message attributes for filtering
            
        Returns:
            Dict with success status and message_id or error
        """
        if not self.enabled or not self.client:
            logger.warning("SNS is not enabled or configured")
            return {
                "success": False,
                "error": "SNS is not enabled or configured"
            }
        
        try:
            publish_kwargs = {
                'TopicArn': self.topic_arn,
                'Subject': subject,
                'Message': message
            }
            
            if message_attributes:
                formatted_attributes = {}
                for key, value in message_attributes.items():
                    if isinstance(value, str):
                        formatted_attributes[key] = {
                            'DataType': 'String',
                            'StringValue': value
                        }
                    elif isinstance(value, (int, float)):
                        formatted_attributes[key] = {
                            'DataType': 'Number',
                            'StringValue': str(value)
                        }
                publish_kwargs['MessageAttributes'] = formatted_attributes
            
            response = self.client.publish(**publish_kwargs)
            
            message_id = response.get('MessageId')
            logger.info(f"✅ SNS notification sent successfully. MessageId: {message_id}")
            
            return {
                "success": True,
                "message_id": message_id,
                "subject": subject
            }
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_message = e.response['Error']['Message']
            logger.error(f"❌ SNS ClientError: {error_code} - {error_message}")
            return {
                "success": False,
                "error": f"{error_code}: {error_message}"
            }
        except Exception as e:
            logger.error(f"❌ Failed to send SNS notification: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }
    
    async def send_document_processed_notification(
        self,
        filename: str,
        advisor_name: Optional[str] = None,
        form_fields_count: int = 0,
        highlighted_items_count: int = 0,
        status: str = "processed"
    ) -> Dict[str, Any]:
        """
        Send notification when a document is processed
        
        Args:
            filename: Name of the processed file
            advisor_name: Name of the advisor (if available)
            form_fields_count: Number of form fields extracted
            highlighted_items_count: Number of highlighted items found
            status: Processing status (processed, failed, etc.)
            
        Returns:
            Dict with success status
        """
        subject = f"Document Processing: {filename}"
        
        message_parts = [
            f"Document: {filename}",
            f"Status: {status.upper()}"
        ]
        
        if advisor_name:
            message_parts.append(f"Advisor: {advisor_name}")
        
        if status == "processed":
            message_parts.append(f"Form Fields Extracted: {form_fields_count}")
            message_parts.append(f"Highlighted Items: {highlighted_items_count}")
        
        message = "\n".join(message_parts)
        
        message_attributes = {
            "DocumentType": "AdvisorOnboarding",
            "Status": status,
            "FileName": filename
        }
        
        return await self.send_notification(
            subject=subject,
            message=message,
            message_attributes=message_attributes
        )
    
    async def send_carrier_submission_notification(
        self,
        advisor_name: str,
        carrier_name: str,
        status: str = "submitted"
    ) -> Dict[str, Any]:
        """
        Send notification when advisor data is submitted to a carrier
        
        Args:
            advisor_name: Name of the advisor
            carrier_name: Name of the carrier
            status: Submission status (submitted, failed, etc.)
            
        Returns:
            Dict with success status
        """
        subject = f"Carrier Submission: {carrier_name} - {advisor_name}"
        
        message = f"""
Advisor: {advisor_name}
Carrier: {carrier_name}
Status: {status.upper()}
        """.strip()
        
        message_attributes = {
            "NotificationType": "CarrierSubmission",
            "CarrierName": carrier_name,
            "Status": status
        }
        
        return await self.send_notification(
            subject=subject,
            message=message,
            message_attributes=message_attributes
        )
    
    async def send_custom_notification(
        self,
        subject: str,
        message_data: Dict[str, Any],
        notification_type: str = "Custom"
    ) -> Dict[str, Any]:
        """
        Send a custom JSON notification
        
        Args:
            subject: Notification subject
            message_data: Dictionary to be sent as JSON
            notification_type: Type of notification for filtering
            
        Returns:
            Dict with success status
        """
        message = json.dumps(message_data, indent=2)
        
        message_attributes = {
            "NotificationType": notification_type
        }
        
        return await self.send_notification(
            subject=subject,
            message=message,
            message_attributes=message_attributes
        )
    
    def get_topic_attributes(self) -> Optional[Dict[str, Any]]:
        """Get SNS topic attributes"""
        if not self.enabled or not self.client:
            return None
        
        try:
            response = self.client.get_topic_attributes(TopicArn=self.topic_arn)
            return response.get('Attributes', {})
        except Exception as e:
            logger.error(f"Failed to get topic attributes: {e}")
            return None
    
    def list_subscriptions(self) -> List[Dict[str, Any]]:
        """List all subscriptions for the topic"""
        if not self.enabled or not self.client:
            return []
        
        try:
            response = self.client.list_subscriptions_by_topic(TopicArn=self.topic_arn)
            return response.get('Subscriptions', [])
        except Exception as e:
            logger.error(f"Failed to list subscriptions: {e}")
            return []


sns_service = SNSService()
