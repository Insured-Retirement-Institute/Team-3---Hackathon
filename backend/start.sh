#!/bin/bash

# Start script for Document Extraction API

echo "🚀 Starting Document Extraction API..."
echo ""

# Check if python-ocr-demo is running
if ! curl -s http://localhost:8000/api/health > /dev/null 2>&1; then
    echo "⚠️  Warning: python-ocr-demo service not detected on port 8000"
    echo "   Please start python-ocr-demo first:"
    echo "   cd /Users/sandeepnair/dev/python-ocr-demo && python app.py"
    echo ""
fi

# Change to src directory
cd "$(dirname "$0")/src"

# Start the API
echo "✅ Starting API on http://localhost:8001"
python main.py
