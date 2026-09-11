"""
Application Configuration
=========================
Loads environment variables using python-dotenv and sets global Flask config settings,
including upload payload size limits (default 500MB).
"""

import os
from dotenv import load_dotenv

# Load environment variables from .env file if present
load_dotenv()


class Config:
    """Base application configuration class for Flask."""
    PROJECT_NAME: str = os.getenv("PROJECT_NAME", "KPI Backend Service")
    VERSION: str = os.getenv("VERSION", "1.0.0")
    SECRET_KEY: str = os.getenv("SECRET_KEY", "dev-secret-change-me")
    
    # Maximum allowed payload size for uploaded Excel files (Default: 500MB)
    MAX_CONTENT_LENGTH: int = int(os.getenv("MAX_CONTENT_LENGTH_MB", "500")) * 1024 * 1024

