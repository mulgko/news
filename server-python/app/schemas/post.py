"""
Pydantic schemas for request/response validation.
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, field_serializer


class PostBase(BaseModel):
    """Base schema for Post"""

    title: str
    summary: str
    content: str
    category: str
    region: str
    image_url: str
    url: Optional[str] = None
    ai_summary: Optional[str] = None


class PostCreate(PostBase):
    """Schema for creating a new post"""

    pass


class PostResponse(PostBase):
    """Schema for post response"""

    id: int
    created_at: Optional[datetime] = None
    likes: int = 0
    dislikes: int = 0
    views: int = 0
    ai_summary: Optional[str] = None

    @field_serializer("created_at")
    def serialize_created_at(self, value: Optional[datetime]) -> Optional[str]:
        """Serialize datetime to ISO format string"""
        if value is None:
            return None
        return value.isoformat()

    model_config = {"from_attributes": True, "populate_by_name": True}
