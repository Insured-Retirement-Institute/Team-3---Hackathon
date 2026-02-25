"""
SNS Integration Examples

This file demonstrates how to use the SNS service in your code.
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.services.sns_service import sns_service


async def example_1_simple_notification():
    """Example 1: Send a simple notification"""
    print("Example 1: Simple Notification")
    print("-" * 60)
    
    result = await sns_service.send_notification(
        subject="Hello from SNS",
        message="This is a simple notification message"
    )
    
    if result.get("success"):
        print(f"✅ Notification sent! Message ID: {result['message_id']}")
    else:
        print(f"❌ Failed: {result.get('error')}")
    print()


async def example_2_notification_with_attributes():
    """Example 2: Send notification with message attributes"""
    print("Example 2: Notification with Message Attributes")
    print("-" * 60)
    
    result = await sns_service.send_notification(
        subject="Important Alert",
        message="This notification has attributes for filtering",
        message_attributes={
            "Priority": "high",
            "Category": "alert",
            "Source": "backend-api"
        }
    )
    
    if result.get("success"):
        print(f"✅ Notification sent with attributes!")
    else:
        print(f"❌ Failed: {result.get('error')}")
    print()


async def example_3_document_processed():
    """Example 3: Notify when a document is processed"""
    print("Example 3: Document Processed Notification")
    print("-" * 60)
    
    result = await sns_service.send_document_processed_notification(
        filename="john_doe_application.pdf",
        advisor_name="John Doe",
        form_fields_count=28,
        highlighted_items_count=6,
        status="processed"
    )
    
    if result.get("success"):
        print(f"✅ Document notification sent!")
    else:
        print(f"❌ Failed: {result.get('error')}")
    print()


async def example_4_carrier_submission():
    """Example 4: Notify when data is submitted to a carrier"""
    print("Example 4: Carrier Submission Notification")
    print("-" * 60)
    
    result = await sns_service.send_carrier_submission_notification(
        advisor_name="Jane Smith",
        carrier_name="MetLife",
        status="submitted"
    )
    
    if result.get("success"):
        print(f"✅ Carrier submission notification sent!")
    else:
        print(f"❌ Failed: {result.get('error')}")
    print()


async def example_5_custom_json():
    """Example 5: Send custom JSON data"""
    print("Example 5: Custom JSON Notification")
    print("-" * 60)
    
    result = await sns_service.send_custom_notification(
        subject="Application Status Update",
        message_data={
            "application_id": "APP-2024-0001",
            "advisor_name": "Mike Johnson",
            "previous_status": "pending",
            "new_status": "approved",
            "approved_by": "admin@example.com",
            "timestamp": "2024-02-25T14:30:00Z",
            "notes": "All documents verified"
        },
        notification_type="StatusUpdate"
    )
    
    if result.get("success"):
        print(f"✅ Custom notification sent!")
    else:
        print(f"❌ Failed: {result.get('error')}")
    print()


async def example_6_workflow_integration():
    """Example 6: Integration in a workflow"""
    print("Example 6: Workflow Integration")
    print("-" * 60)
    
    print("Simulating advisor onboarding workflow...")
    
    advisor = {
        "name": "Sarah Williams",
        "email": "sarah@example.com",
        "document": "sarah_application.pdf"
    }
    
    carriers = ["AIG", "Prudential", "New York Life"]
    
    print(f"\n1. Processing document for {advisor['name']}...")
    result = await sns_service.send_document_processed_notification(
        filename=advisor['document'],
        advisor_name=advisor['name'],
        form_fields_count=30,
        highlighted_items_count=4,
        status="processed"
    )
    print(f"   {'✅' if result.get('success') else '❌'} Document notification sent")
    
    print(f"\n2. Submitting to carriers...")
    for carrier in carriers:
        result = await sns_service.send_carrier_submission_notification(
            advisor_name=advisor['name'],
            carrier_name=carrier,
            status="submitted"
        )
        print(f"   {'✅' if result.get('success') else '❌'} {carrier} notification sent")
    
    print(f"\n3. Workflow complete notification...")
    result = await sns_service.send_custom_notification(
        subject=f"Onboarding Complete - {advisor['name']}",
        message_data={
            "advisor_name": advisor['name'],
            "advisor_email": advisor['email'],
            "carriers_submitted": len(carriers),
            "carrier_names": carriers,
            "status": "completed",
            "completion_time": "2024-02-25T15:00:00Z"
        },
        notification_type="OnboardingComplete"
    )
    print(f"   {'✅' if result.get('success') else '❌'} Completion notification sent")
    print()


async def example_7_error_handling():
    """Example 7: Proper error handling"""
    print("Example 7: Error Handling")
    print("-" * 60)
    
    try:
        if not sns_service.enabled:
            print("⚠️  SNS is not enabled - notifications will be skipped")
            return
        
        result = await sns_service.send_notification(
            subject="Test with Error Handling",
            message="This demonstrates proper error handling"
        )
        
        if result.get("success"):
            message_id = result.get("message_id")
            print(f"✅ Success! Message ID: {message_id}")
        else:
            error = result.get("error")
            print(f"❌ Failed to send notification: {error}")
            
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
    print()


async def example_8_conditional_notifications():
    """Example 8: Send notifications based on conditions"""
    print("Example 8: Conditional Notifications")
    print("-" * 60)
    
    extraction_results = [
        {"file": "complete_form.pdf", "fields": 30, "confidence": 0.95},
        {"file": "partial_form.pdf", "fields": 15, "confidence": 0.60},
        {"file": "poor_quality.pdf", "fields": 5, "confidence": 0.30}
    ]
    
    for result_data in extraction_results:
        confidence = result_data["confidence"]
        
        if confidence >= 0.80:
            status = "processed"
            message = f"High confidence extraction"
        elif confidence >= 0.50:
            status = "review_required"
            message = f"Medium confidence - manual review recommended"
        else:
            status = "failed"
            message = f"Low confidence - manual intervention required"
        
        print(f"\n{result_data['file']} (confidence: {confidence:.0%})")
        
        result = await sns_service.send_custom_notification(
            subject=f"Document Extraction: {status.upper()}",
            message_data={
                "filename": result_data["file"],
                "fields_extracted": result_data["fields"],
                "confidence_score": confidence,
                "status": status,
                "message": message
            },
            notification_type="ExtractionResult"
        )
        
        print(f"{'✅' if result.get('success') else '❌'} Notification sent: {message}")
    print()


async def main():
    """Run all examples"""
    print("=" * 60)
    print("SNS Integration Examples")
    print("=" * 60)
    print()
    
    if not sns_service.enabled:
        print("⚠️  SNS is not enabled!")
        print("\nTo run these examples:")
        print("1. Configure AWS credentials in .env")
        print("2. Set SNS_TOPIC_ARN in .env")
        print("3. Set SNS_ENABLED=true in .env")
        print("\nSee SNS_SETUP.md for detailed instructions.")
        return
    
    print(f"✅ SNS is enabled")
    print(f"📍 Topic: {sns_service.topic_arn}")
    print()
    
    await example_1_simple_notification()
    await example_2_notification_with_attributes()
    await example_3_document_processed()
    await example_4_carrier_submission()
    await example_5_custom_json()
    await example_6_workflow_integration()
    await example_7_error_handling()
    await example_8_conditional_notifications()
    
    print("=" * 60)
    print("All examples completed!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
