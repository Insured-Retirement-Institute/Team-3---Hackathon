"""
Configuration settings for Document Extraction API
Loads from environment variables or provides defaults
"""

import os
from typing import Optional

# Load .env file if it exists
try:
    from dotenv import load_dotenv
    # Load from backend directory
    env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
    load_dotenv(env_path)
except ImportError:
    pass

# OCR Service Configuration
OCR_SERVICE_URL: str = os.getenv('OCR_SERVICE_URL', 'http://localhost:8000')

# Application Configuration
APP_HOST: str = os.getenv('APP_HOST', '0.0.0.0')
APP_PORT: int = int(os.getenv('APP_PORT', '8001'))
DEBUG: bool = os.getenv('DEBUG', 'False').lower() == 'true'

# Logging Configuration
LOG_LEVEL: str = os.getenv('LOG_LEVEL', 'INFO')

# File Upload Configuration
MAX_FILE_SIZE: int = int(os.getenv('MAX_FILE_SIZE', '52428800'))  # 50MB default
