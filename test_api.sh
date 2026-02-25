#!/bin/bash

# Test script for Document Extraction API

echo "🧪 Testing Document Extraction API..."
echo ""

# Test health endpoint
echo "1. Testing health endpoint..."
curl -s http://localhost:8001/health | python -m json.tool
echo ""
echo ""

# Check if a test file was provided
if [ -z "$1" ]; then
    echo "📄 To test file extraction, provide a PDF or Excel file:"
    echo "   ./test_api.sh /path/to/document.pdf"
    exit 0
fi

# Test extraction with provided file
echo "2. Testing extraction with file: $1"
echo ""

curl -X POST http://localhost:8001/api/extract \
  -F "file=@$1" \
  -s | python -m json.tool

echo ""
echo "✅ Test complete!"
