"""
AI-powered news summarization service using Google Gemini.
"""
import google.generativeai as genai
from app.core.config import settings


def generate_ai_summary_google(content: str, title: str = "") -> str:
    """
    Generate news article summary using Google Gemini AI.

    Args:
        content: Article content to summarize
        title: Article title (optional)

    Returns:
        Summary text or empty string if generation fails
    """
    if not content or len(content.strip()) < 50:
        print("⚠️ 요약할 콘텐츠가 부족하거나 비어있음")
        return ""

    try:
        # Check if Google AI API key is configured
        if not settings.is_google_ai_configured:
            print(
                "⚠️ Google AI API 키가 설정되지 않았습니다. "
                "Google AI Studio에서 API 키를 생성하여 .env 파일에 GOOGLE_AI_API_KEY를 설정해주세요."
            )
            print("   설정하지 않으면 AI 요약이 생성되지 않습니다.")
            return ""

        # Configure API key
        genai.configure(api_key=settings.GOOGLE_AI_API_KEY)

        # Initialize Gemini model
        model = genai.GenerativeModel("gemini-2.5-flash-lite")

        prompt = f"""
다음 뉴스 기사를 3-4줄로 간결하게 요약해주세요.
핵심 내용과 중요한 사실만 포함하세요.

제목: {title}

본문:
{content[:3000]}

요약:
"""

        print(f"🤖 Google AI로 요약 생성 시도: {title[:50]}...")
        response = model.generate_content(prompt)
        summary = response.text.strip()

        # Truncate if summary is too long
        if len(summary) > 500:
            summary = summary[:500] + "..."

        print(f"✅ Google AI 요약 생성 성공: {len(summary)}자")
        return summary

    except Exception as e:
        print(f"💥 Google AI 요약 생성 실패: {e}")
        return ""
