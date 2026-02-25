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

# AWS Configuration
AWS_REGION: str = os.getenv('AWS_REGION', 'us-east-1')
AWS_ACCESS_KEY_ID: Optional[str] = os.getenv('AWS_ACCESS_KEY_ID')
AWS_SECRET_ACCESS_KEY: Optional[str] = os.getenv('AWS_SECRET_ACCESS_KEY')
AWS_SESSION_TOKEN: Optional[str] = os.getenv('AWS_SESSION_TOKEN')

# SNS Configuration
SNS_TOPIC_ARN: Optional[str] = os.getenv('SNS_TOPIC_ARN')
SNS_ENABLED: bool = os.getenv('SNS_ENABLED', 'false').lower() == 'true'
