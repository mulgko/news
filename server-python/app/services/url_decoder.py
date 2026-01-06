"""
Google News URL decoding service.
"""
from googlenewsdecoder import new_decoderv1


def decode_google_news_url(url: str, session=None) -> str:
    """
    Decode Google News URL using googlenewsdecoder library.
    This is the simplest and most effective method.

    Args:
        url: Google News URL to decode
        session: Optional requests session (unused, kept for compatibility)

    Returns:
        Decoded URL or original URL if decoding fails
    """
    if not url or "google.com" not in url:
        return url

    try:
        decoded = new_decoderv1(url)
        # Handle case where new_decoderv1 returns a dictionary
        if isinstance(decoded, dict):
            if decoded.get("status") == True and decoded.get("decoded_url"):
                print(f"✅ 디코딩 성공: {decoded['decoded_url']}")
                return decoded["decoded_url"]
            else:
                print(f"❌ 디코딩 실패: {decoded.get('message', 'Unknown error')}")
        # Handle case where new_decoderv1 returns a string
        elif isinstance(decoded, str) and decoded and decoded != url:
            print(f"✅ 디코딩 성공: {decoded}")
            return decoded
        else:
            print("❌ 디코딩 결과가 유효하지 않음")
    except Exception as e:
        print(f"💥 디코딩 실패: {e}")

    return url
