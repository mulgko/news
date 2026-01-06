"""
SQLAlchemy database models.
"""
from sqlalchemy import Column, Integer, String, Text, TIMESTAMP, func
from app.core.database import Base


class Post(Base):
    """Post model representing a news article"""

    __tablename__ = "posts"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    summary = Column(Text, nullable=False)
    content = Column(Text, nullable=False)
    category = Column(String, nullable=False)
    region = Column(String, nullable=False)
    image_url = Column("image_url", String, nullable=False)
    url = Column(String, nullable=True)
    created_at = Column("created_at", TIMESTAMP, server_default=func.now())
    likes = Column(Integer, default=0)
    dislikes = Column(Integer, default=0)
    views = Column(Integer, default=0)
    ai_summary = Column(Text, nullable=True)
