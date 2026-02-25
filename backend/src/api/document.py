"""
Document Extraction API - Pass-through to python-ocr-demo
"""
from fastapi import APIRouter, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse
import httpx
import os
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

# OCR Service URL (python-ocr-demo)
OCR_SERVICE_URL = os.getenv("OCR_SERVICE_URL", "http://localhost:8000")


@router.post("/extract")
async def extract_document(file: UploadFile = File(...)):
    """
    Extract structured JSON from PDF, Excel, and Image files.
    Pass-through endpoint to python-ocr-demo API.
    """
    try:
        logger.info(f"📤 Processing file: {file.filename}")
        
        # Read file content
        file_content = await file.read()
        
        if len(file_content) == 0:
            raise HTTPException(status_code=400, detail="Empty file uploaded")
        
        # Validate file type and determine endpoint
        file_ext = os.path.splitext(file.filename)[1].lower()
        
        # Supported file types (all use vision-extract)
        pdf_types = ['.pdf']
        excel_types = ['.xlsx', '.xls', '.xlsm', '.xlsb']
        image_types = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp']
        
        if file_ext in pdf_types:
            endpoint = f"{OCR_SERVICE_URL}/api/vision-extract"
            logger.info(f"📄 Using vision-extract for PDF")
        elif file_ext in excel_types:
            endpoint = f"{OCR_SERVICE_URL}/api/vision-extract"
            logger.info(f"📊 Using vision-extract for Excel")
        elif file_ext in image_types:
            endpoint = f"{OCR_SERVICE_URL}/api/vision-extract"
            logger.info(f"🖼️ Using vision-extract for Image")
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file type: {file_ext}. Supported types: PDF (.pdf), Excel (.xlsx, .xls), Images (.jpg, .png, etc.)"
            )
        
        files = {'file': (file.filename, file_content, file.content_type)}
        
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(
                    endpoint,
                    files=files
                )
            
            if response.status_code != 200:
                error_detail = response.json() if 'application/json' in response.headers.get('content-type', '') else response.text
                logger.error(f"❌ OCR service error: {error_detail}")
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"OCR service error: {error_detail}"
                )
            
            result = response.json()
            
        except httpx.ConnectError:
            logger.error(f"❌ Cannot connect to OCR service at {OCR_SERVICE_URL}")
            raise HTTPException(
                status_code=503,
                detail=f"Cannot connect to OCR service. Please ensure python-ocr-demo is running on port 8000."
            )
        except httpx.TimeoutException:
            logger.error("❌ OCR service timeout")
            raise HTTPException(
                status_code=504,
                detail="OCR service timeout. The document may be too large or complex."
            )
        
        if not result.get('success'):
            logger.error(f"❌ Extraction failed: {result.get('error')}")
            raise HTTPException(
                status_code=500,
                detail=result.get('error', 'Extraction failed')
            )
        
        # Get highlighted items - python-ocr-demo returns 'agent_carrier_list'
        highlighted_items = result.get('agent_carrier_list', result.get('highlighted_carriers', []))
        
        logger.info(f"✅ Extraction completed successfully")
        logger.info(f"   - Form fields: {len(result.get('form_data', {}))}")
        logger.info(f"   - Highlighted items: {len(highlighted_items)}")
        
        # Transform response to match frontend expectations
        response_data = {
            "success": True,
            "filename": file.filename,
            "data": {
                "form_fields": result.get('form_data', {}),
                "highlighted_items": highlighted_items,
                "background_info": result.get('background_info', {}),
                "signatures": result.get('signatures', {})
            },
            "confidence": result.get('confidence', 0.0),
            "pages_analyzed": result.get('pages_analyzed', 0),
            "notes": result.get('notes', '')
        }
        
        return JSONResponse(response_data)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Extraction failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )
