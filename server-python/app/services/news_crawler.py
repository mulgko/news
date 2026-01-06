"""
Google News RSS Crawler Service

This module handles crawling news from Google News RSS feeds.
It includes the GoogleNewsRSSClient class which:
- Fetches news from Korea and World RSS feeds
- Extracts real article URLs from Google News URLs
- Extracts article content from news sites
- Handles SSL verification and network requests
"""

import requests
import feedparser
from typing import List, Dict
from datetime import datetime
from email.utils import parsedate_to_datetime

from app.services.content_extractor import extract_news_content
from app.services.url_decoder import decode_google_news_url
from app.services.ai_summarizer import generate_ai_summary_google
from app.utils.helpers import get_sort_key

# Global session for network requests
session = requests.Session()


class GoogleNewsRSSClient:
    def __init__(self):
        # 한국 뉴스 RSS 피드
        self.base_url = "https://news.google.com/rss"
        # 간단 버전에서는 기본 세션 사용
        self.session = session

    def extract_article_content(self, url: str) -> str:
        """Trafilatura를 사용한 뉴스 본문 추출"""
        return extract_news_content(url, self.session)

    def _extract_real_url(self, google_news_url: str) -> str:
        """Google News URL에서 실제 뉴스 URL 추출 (간소화된 버전)"""
        # 새로 만든 전문 디코더 사용 - self.session 전달!
        return decode_google_news_url(google_news_url, self.session)

    def get_korea_news(self) -> List[Dict]:
        """한국 주요 뉴스 가져오기"""
        rss_url = "https://news.google.com/rss?hl=ko&gl=KR&ceid=KR:ko"
        return self._fetch_news_from_rss(rss_url)

    def get_world_news(self) -> List[Dict]:
        """세계 주요 뉴스 가져오기"""
        rss_url = "https://news.google.com/rss?hl=en-US&gl=US&ceid=US:en"
        return self._fetch_news_from_rss(rss_url)

    def _fetch_news_from_rss(self, rss_url: str) -> List[Dict]:
        """RSS URL에서 뉴스 가져오기"""

        try:
            # RSS 피드 파싱
            print(f"🌐 Fetching RSS from: {rss_url}")  # 디버깅 로그

            # SSL 검증 없이 RSS 가져오기 (requests 사용) - 강화된 SSL 우회
            try:
                # 첫 번째 시도: 일반적인 SSL 우회
                response = self.session.get(rss_url, verify=False, timeout=30)
                response.raise_for_status()
                rss_content = response.text
            except Exception as ssl_error:
                print(f"⚠️ SSL 오류 발생, 인증서 검증 완전 우회 시도: {ssl_error}")
                try:
                    # 두 번째 시도: 더 강력한 SSL 우회
                    import ssl
                    from urllib3.util import ssl_

                    # SSL 컨텍스트 생성 (인증서 검증 완전 비활성화)
                    ssl_context = ssl.create_default_context()
                    ssl_context.check_hostname = False
                    ssl_context.verify_mode = ssl.CERT_NONE

                    response = self.session.get(
                        rss_url,
                        verify=False,
                        timeout=30,
                        cert_reqs=ssl.CERT_NONE
                    )
                    response.raise_for_status()
                    rss_content = response.text
                except Exception as fallback_error:
                    print(f"💥 SSL 우회 실패, 마지막 시도: {fallback_error}")
                    # 세 번째 시도: urllib 사용
                    try:
                        import urllib.request
                        import urllib.error

                        req = urllib.request.Request(rss_url)
                        req.add_header('User-Agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
                        with urllib.request.urlopen(req, timeout=30) as response:
                            rss_content = response.read().decode('utf-8')
                    except Exception as urllib_error:
                        print(f"💥 모든 SSL 우회 방법 실패: {urllib_error}")
                        return []

            # 가져온 RSS 텍스트를 feedparser로 파싱
            feed = feedparser.parse(rss_content)

            # 상세한 디버깅 정보
            print(f"📡 Feed status: {feed.status if hasattr(feed, 'status') else 'unknown'}")
            print(f"📰 Feed entries count: {len(feed.entries)}")
            print(f"📝 Feed title: {getattr(feed.feed, 'title', 'No title')}")
            print(f"🔍 Feed keys: {list(feed.keys())}")
            print(f"📄 Raw feed data (first 500 chars): {str(feed)[:500]}")

            if hasattr(feed, 'bozo') and feed.bozo:
                print(f"⚠️ Feed parsing error: {feed.bozo_exception}")

            # entries 상세 정보
            if feed.entries:
                print(f"✅ First entry keys: {list(feed.entries[0].keys()) if feed.entries else 'No entries'}")
                print(f"✅ First entry title: {getattr(feed.entries[0], 'title', 'No title') if feed.entries else 'No entries'}")
            else:
                print(f"❌ No entries found in feed")

            articles = []
            for entry in feed.entries[:20]:  # 최대 20개 뉴스
                # 이미지 URL 추출 개선
                image_url = ""
                if hasattr(entry, 'media_thumbnail') and entry.media_thumbnail:
                    image_url = entry.media_thumbnail[0].get('url', '')
                elif hasattr(entry, 'media_content') and entry.media_content:
                    image_url = entry.media_content[0].get('url', '')
                elif hasattr(entry, 'enclosures') and entry.enclosures:
                    for enclosure in entry.enclosures:
                        if enclosure.get('type', '').startswith('image/'):
                            image_url = enclosure.get('url', '')
                            break

                # 날짜 처리 개선
                published_at = getattr(entry, 'published', '')
                if published_at:
                    try:
                        from email.utils import parsedate_to_datetime
                        published_at = parsedate_to_datetime(published_at).isoformat()
                    except:
                        published_at = datetime.now().isoformat()

                # Google News 링크에서 실제 뉴스 URL 추출 시도
                actual_url = self._extract_real_url(entry.link)

                article = {
                    "title": entry.title,
                    "description": getattr(entry, 'summary', ''),
                    "content": getattr(entry, 'summary', ''),  # RSS에서는 콘텐츠가 제한적
                    "url": actual_url,  # 실제 뉴스 URL 사용
                    "urlToImage": image_url,
                    "publishedAt": published_at
                }
                articles.append(article)

            print(f"✅ Returning {len(articles)} articles")
            return articles

        except Exception as e:
            print(f"💥 Error parsing RSS feed for {topic}: {e}")
            import traceback
            print(f"💥 Full traceback: {traceback.format_exc()}")
            return []
