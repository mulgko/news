"""
Configuration management for the application.
Handles environment variables and application settings.
"""
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class Settings:
    """Application settings"""

    # Google AI API Key
    GOOGLE_AI_API_KEY: str = os.getenv("GOOGLE_AI_API_KEY", "")

    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./news.db")

    # CORS Settings
    CORS_ORIGINS: list = [
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
    ]

    # API Settings
    API_V1_PREFIX: str = "/api"

    @property
    def is_google_ai_configured(self) -> bool:
        """Check if Google AI API key is properly configured"""
        return (
            self.GOOGLE_AI_API_KEY
            and self.GOOGLE_AI_API_KEY not in ["your_google_ai_api_key_here", "test_key"]
        )


# Create global settings instance
settings = Settings()
