"""
Utility helper functions.
"""
from datetime import datetime


def get_sort_key(article: dict) -> datetime:
    """
    Get sorting key for article - sorts by newest first.

    Args:
        article: Article dictionary with publishedAt field

    Returns:
        datetime object for sorting, or datetime.min if parsing fails
    """
    published_date = article.get("publishedAt", "")
    if published_date:
        try:
            # Already in ISO format, parse directly
            if published_date.endswith("Z"):
                published_date = published_date.replace("Z", "+00:00")
            return datetime.fromisoformat(published_date)
        except Exception as e:
            print(
                f"⚠️ Date parsing error for article: {article.get('title', '')[:30]}... - {e}"
            )
            return datetime.min
    return datetime.min
