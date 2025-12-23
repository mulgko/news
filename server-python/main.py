from fastapi import FastAPI, HTTPException, Query, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, field_serializer
from datetime import datetime
from typing import Optional, List, AsyncGenerator, Dict
from contextlib import asynccontextmanager
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, Column, Integer, String, Text, TIMESTAMP, func
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker, Session
import uvicorn
import feedparser
import requests
from bs4 import BeautifulSoup
import time
import re
import trafilatura

# 간단 버전에서는 기본 세션만 사용
session = requests.Session()

def get_sort_key(article):
    """기사 정렬을 위한 키 함수 - 최신순 정렬"""
    published_date = article.get("publishedAt", "")
    if published_date:
        try:
            # 이미 ISO format이므로 바로 파싱
            if published_date.endswith('Z'):
                published_date = published_date.replace('Z', '+00:00')
            return datetime.fromisoformat(published_date)
        except Exception as e:
            print(f"⚠️ Date parsing error for article: {article.get('title', '')[:30]}... - {e}")
            return datetime.min
    return datetime.min


def decode_google_news_url(url: str, session=None) -> str:
    """
    Google News URL 디코딩 (googlenewsdecoder 우선 + 기존 방법들)
    """
    if not url or "google.com" not in url:
        return url

    try:
        # 0. googlenewsdecoder 우선 시도 (가장 효과적!)
        try:
            from googlenewsdecoder import new_decoderv1
            decoded = new_decoderv1(url)
            if decoded and decoded != url and "google.com" not in decoded:
                print(f"✅ googlenewsdecoder 성공: {decoded[:80]}...")
                return decoded
        except ImportError:
            print("⚠️ googlenewsdecoder 미설치")
        except Exception as decoder_error:
            print(f"⚠️ googlenewsdecoder 실패: {decoder_error}")

        # 1. HTTP 리다이렉트 시도
        if session is None:
            session = requests.Session()
            session.verify = False

        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7',
                'Referer': 'https://news.google.com/',
            }

            print(f"🔗 HTTP 리다이렉트 시도...")
            response = session.get(url, headers=headers, allow_redirects=True, timeout=15, verify=False)

            final_url = response.url
            if final_url != url and "google.com" not in final_url and final_url.startswith('http'):
                print(f"✅ HTTP 리다이렉트 성공: {final_url[:80]}...")
                return final_url
            else:
                print(f"⚠️ 리다이렉트 결과가 유효하지 않음: {final_url[:60]}...")

        except Exception as redirect_error:
            print(f"⚠️ HTTP 리다이렉트 실패: {redirect_error}")

        # 2. Base64 디코딩 시도 (보조 수단)
        import base64
        import re

        match = re.search(r'/rss/articles/(CBMi[^?]+)', url)
        if match:
            encoded_part = match.group(1)
            print(f"🔍 Base64 디코딩 시도...")

            try:
                # 패딩 추가
                missing_padding = len(encoded_part) % 4
                if missing_padding:
                    encoded_part += '=' * (4 - missing_padding)

                decoded_bytes = base64.urlsafe_b64decode(encoded_part)
                decoded_text = decoded_bytes.decode('utf-8', errors='ignore')

                # URL 패턴 찾기
                url_patterns = [
                    r'https?://[^\s\'"<>(){}\[\]]+',
                    r'https?://[^\s\'"<>\s]+',
                ]

                for pattern in url_patterns:
                    matches = re.findall(pattern, decoded_text)
                    for match in matches:
                        real_url = re.sub(r'[<>,"\'\s]+$', '', match)
                        if len(real_url) > 20 and "google.com" not in real_url and real_url.startswith('http'):
                            print(f"✅ Base64에서 URL 발견: {real_url[:80]}...")
                            return real_url

            except Exception as b64_error:
                print(f"⚠️ Base64 디코딩 실패: {b64_error}")

        # 3. 최후의 수단: URL 파라미터 방식
        from urllib.parse import urlparse, parse_qs
        parsed = urlparse(url)
        if 'url' in parse_qs(parsed.query):
            direct_url = parse_qs(parsed.query)['url'][0]
            if "google.com" not in direct_url and direct_url.startswith('http'):
                print(f"✅ URL 파라미터에서 추출: {direct_url[:80]}...")
                return direct_url

        print(f"⚠️ 모든 디코딩 방법 실패, 원본 URL 사용")
        return url

    except Exception as e:
        print(f"💥 URL 디코딩 오류: {e}, 원본 사용")
        return url

def extract_news_content(article_url: str, session=None) -> str:
    """
    개선된 뉴스 본문 추출 (BeautifulSoup 우선)
    Google News URL 디코딩 후 본문 자동 추출
    """
    try:
        # 1. Google News URL 디코딩
        real_url = decode_google_news_url(article_url, session)

        if not real_url:
            print(f"URL 처리 실패: {article_url}")
            return None

        # Google News URL인 경우에도 시도 (리다이렉트될 것임)
        target_url = real_url if real_url != article_url else article_url

        # 2. BeautifulSoup로 우선 추출 시도 (더 안정적)
        print(f"BeautifulSoup로 본문 추출 시도: {target_url[:80]}...")
        result = _extract_with_beautifulsoup(target_url, session)
        if result:
            return result

        # 3. BeautifulSoup 실패시 Trafilatura 대안 시도
        print(f"BeautifulSoup 실패, Trafilatura 대안 시도")
        downloaded = trafilatura.fetch_url(target_url)

        if not downloaded:
            print(f"페이지 다운로드 실패: {target_url}")
            return None

        # 본문 텍스트 추출 (정밀 모드, 댓글 제외)
        text = trafilatura.extract(
            downloaded,
            output_format='txt',
            include_comments=False,
            favor_precision=True
        )

        if text and len(text.strip()) > 100:
            # 성공: 텍스트 정리
            cleaned_text = ' '.join(text.split())  # 연속 공백 제거
            print(f"Trafilatura 추출 성공: {len(cleaned_text)}자")
            return cleaned_text[:2000]  # 길이 제한
        else:
            print(f"Trafilatura 추출 실패")
            return None

    except Exception as e:
        print(f"본문 추출 오류: {e}")
        # 최종 Fallback: BeautifulSoup 재시도
        try:
            return _extract_with_beautifulsoup(target_url, session)
        except Exception as fallback_e:
            print(f"Fallback도 실패: {fallback_e}")
            return None


def _extract_with_beautifulsoup(url: str, session=None) -> str:
    """
    BeautifulSoup를 사용한 대안 본문 추출
    Trafilatura 실패시 사용
    """
    try:
        if session is None:
            session = requests.Session()
            session.verify = False

        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }

        # SSL 검증 완전 우회 및 타임아웃 증가 - 강화된 SSL 처리
        try:
            response = session.get(url, headers=headers, timeout=20, verify=False, allow_redirects=True)
            response.raise_for_status()
        except Exception as ssl_error:
            print(f"⚠️ SSL 오류 발생, 인증서 검증 완전 우회 시도: {ssl_error}")
            try:
                import ssl
                response = session.get(
                    url,
                    headers=headers,
                    timeout=20,
                    verify=False,
                    allow_redirects=True,
                    cert_reqs=ssl.CERT_NONE
                )
                response.raise_for_status()
            except Exception as fallback_error:
                print(f"💥 SSL 우회 실패: {fallback_error}")
                raise fallback_error

        soup = BeautifulSoup(response.content, 'html.parser')

        # 불필요한 요소 제거
        for element in soup.find_all(['script', 'style', 'nav', 'footer', 'header', 'aside']):
            element.decompose()

        # 한국 뉴스 사이트용 본문 선택자들
        content_selectors = [
            'article',
            '[id*="article"]',
            '[class*="article"]',
            '[id*="content"]',
            '[class*="content"]',
            '#articleBody',
            '#newsct_article',
            '.article_body',
            '.news_body',
            'div[itemprop="articleBody"]',
            '.article-content',
            'main'
        ]

        content_text = ""
        for selector in content_selectors:
            elements = soup.select(selector)
            if elements:
                texts = []
                for elem in elements:
                    paragraphs = elem.find_all(['p', 'div'])
                    for p in paragraphs:
                        text = p.get_text(strip=True)
                        if len(text) > 30:  # 의미있는 길이의 텍스트만
                            texts.append(text)

                if texts:
                    content_text = '\n\n'.join(texts)
                    break

        # 추가 정리
        if content_text:
            # 한국 뉴스 사이트 흔한 아티팩트 제거
            content_text = re.sub(r'▶.*?\n', '', content_text)
            content_text = re.sub(r'\[.*?\]', '', content_text)
            content_text = re.sub(r'사진.*?\n', '', content_text)
            content_text = re.sub(r'\s+', ' ', content_text)
            content_text = content_text.strip()

        if len(content_text) > 100:
            print(f"✅ BeautifulSoup 추출 성공: {len(content_text)}자")
            return content_text[:2000]
        else:
            print(f"❌ BeautifulSoup 추출 실패: 텍스트가 너무 짧음")
            return None

    except Exception as e:
        print(f"💥 BeautifulSoup 추출 오류: {e}")
        return None




# 환경 변수 로드
load_dotenv()


# 데이터베이스 설정
DATABASE_URL = os.getenv("DATABASE_URL") or "sqlite:///./news.db"

engine = create_engine(DATABASE_URL, echo=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# 데이터베이스 모델
class Post(Base):
    __tablename__ = "posts"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    summary = Column(Text, nullable=False)
    content = Column(Text, nullable=False)
    category = Column(String, nullable=False)
    image_url = Column("image_url", String, nullable=False)
    created_at = Column("created_at", TIMESTAMP, server_default=func.now())

# Pydantic 스키마
class PostBase(BaseModel):
    title: str
    summary: str
    content: str
    category: str
    image_url: str

class PostCreate(PostBase):
    pass

class PostResponse(PostBase):
    id: int
    created_at: Optional[datetime] = None

    @field_serializer('created_at')
    def serialize_created_at(self, value: Optional[datetime]) -> Optional[str]:
        if value is None:
            return None
        return value.isoformat()

    model_config = {
        "from_attributes": True,
        "populate_by_name": True
    }


# lifespan 이벤트 핸들러
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    # startup
    Base.metadata.create_all(bind=engine)
    await seed_database()
    yield
    # shutdown (필요시 cleanup 코드 추가)


# FastAPI 앱 생성
app = FastAPI(title="News API", version="1.0.0", lifespan=lifespan)

# CORS 설정 (필요시)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],  # Vite 기본 포트
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 데이터베이스 세션 의존성
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# 데이터베이스 초기화 (테이블 생성)



async def seed_database():
    db = SessionLocal()
    try:
        # 기존 데이터 모두 삭제 (스키마 변경으로 인한 리셋)
        db.query(Post).delete()
        db.commit()
        print("Existing posts deleted for schema update")
        # 시드 데이터
        seed_posts = [
            {
                "title": "2025년 AI의 미래 전망",
                "summary": "인공지능이 빠르게 발전하고 있습니다. 내년에 어떤 변화가 예상되는지 알아보세요.",
                "content": "인공지능이 빠르게 발전하고 있습니다. 내년에 어떤 변화가 예상되는지 알아보세요. 전문가들은 생성형 모델과 자율 에이전트 분야에서 주요 돌파구를 예상하고 있습니다. AI의 일상생활 통합이 더욱 원활해지며 의료, 금융 등 다양한 산업에 영향을 미칠 것입니다.",
                "category": "기술",
                "image_url": "https://images.unsplash.com/photo-1677442136019-21780ecad995?auto=format&fit=crop&q=80&w=800",
            },
            {
                "title": "인플레이션 완화로 글로벌 증시 상승",
                "summary": "이번 주 경제 지표 호조로 주식 시장이 신고점을 기록했습니다.",
                "content": "이번 주 경제 지표 호조로 주식 시장이 신고점을 기록했습니다. 투자자들은 중앙은행의 다음 움직임에 대해 낙관적입니다. 기술주를 중심으로 주요 지수가 사상 최고치를 기록했습니다.",
                "category": "비즈니스",
                "image_url": "https://images.unsplash.com/photo-1611974765270-ca12586343bb?auto=format&fit=crop&q=80&w=800",
            },
            {
                "title": "생명존에 위치한 새로운 행성 발견",
                "summary": "천문학자들이 지구와 유사한 잠재적 행성을 40광년 거리에서 발견했습니다.",
                "content": "천문학자들이 지구와 유사한 잠재적 행성을 40광년 거리에서 발견했습니다. 글리제 12 b로 명명된 이 행성은 적색 왜성 주위를 공전하며 액체 물을 유지할 수 있는 온도를 가지고 있습니다. 제임스 웹 우주 망원경을 통한 추가 관측이 계획되어 있습니다.",
                "category": "과학",
                "image_url": "https://images.unsplash.com/photo-1451187580459-43490279c0fa?auto=format&fit=crop&q=80&w=800",
            },
            {
                "title": "오늘 밤 숙면을 위한 5가지 팁",
                "summary": "숙면을 취하기 어려우신가요? 과학적으로 검증된 팁을 확인하세요.",
                "content": "숙면을 취하기 어려우신가요? 과학적으로 검증된 팁을 확인하세요. 1. 규칙적인 일정 유지하기. 2. 편안한 환경 조성하기. 3. 취침 전 화면 시간 제한하기. 4. 먹는 음식과 마시는 음료 주의하기. 5. 일상 생활에 신체 활동 포함하기.",
                "category": "건강",
                "image_url": "https://images.unsplash.com/photo-1541781777621-794453259724?auto=format&fit=crop&q=80&w=800",
            },
            {
                "title": "올여름 볼만한 기대작 영화들",
                "summary": "팝콘 준비하세요! 이번 시즌 가장 기대되는 영화들을 소개합니다.",
                "content": "팝콘 준비하세요! 이번 시즌 가장 기대되는 영화들을 소개합니다. 슈퍼히어로 대작부터 따뜻한 감동 애니메이션까지 모두를 위한 작품이 준비되어 있습니다. 이번 여름 극장에서 볼 수 있는 필람 영화 목록을 확인해보세요.",
                "category": "엔터테인먼트",
                "image_url": "https://images.unsplash.com/photo-1536440136628-849c177e76a1?auto=format&fit=crop&q=80&w=800",
            },
        ]

        for post_data in seed_posts:
            post = Post(**post_data)
            db.add(post)
        db.commit()
        print("Database seeded with initial posts")
    except Exception as e: 
        db.rollback()
        print(f"Error seeding database: {e}")
    finally:
        db.close()



# Google News RSS Client
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

    def get_news_by_topic(self, topic: str = "general") -> List[Dict]:
        """Google News 검색 RSS에서 뉴스 가져오기"""
        # 토픽별 검색어 매핑 (더 안정적인 방식)
        topic_queries = {
            "business": "비즈니스 OR 경제 OR 기업 OR 금융",
            "technology": "기술 OR IT OR 인공지능 OR 스타트업",
            "science": "과학 OR 연구 OR 우주 OR 환경",
            "health": "건강 OR 의료 OR 병원 OR 코로나",
            "entertainment": "연예 OR 영화 OR 음악 OR 드라마",
            "general": ""
        }

        # Google News 검색 RSS URL 생성
        base_url = "https://news.google.com/rss/search?q="
        query = topic_queries.get(topic, "")
        if query:
            # 검색어를 URL 인코딩
            import urllib.parse
            encoded_query = urllib.parse.quote(query)
            rss_url = f"{base_url}{encoded_query}&hl=ko&gl=KR&ceid=KR:ko"
        else:
            rss_url = "https://news.google.com/rss?hl=ko&gl=KR&ceid=KR:ko"

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
        







# News fetch, save Func
async def fetch_and_store_news(db: Session):
    """Google News RSS에서 뉴스를 가져와서 데이터베이스에 저장"""
    client = GoogleNewsRSSClient()

    # 여러 카테고리의 뉴스 가져오기
    categories = ["business", "technology", "science", "health", "entertainment"]

    total_processed = 0
    total_saved = 0

    for category in categories:
        print(f"🔍 Fetching {category} news...")  # 디버깅 로그
        articles = client.get_news_by_topic(topic=category)
        print(f"📊 Found {len(articles)} articles for {category}")  # 디버깅 로그

        # 최신순으로 정렬하고 5개로 제한
        print(f"🔢 Before sorting: {len(articles)} articles")  # 디버깅 로그
        try:
            articles = sorted(articles, key=get_sort_key, reverse=True)[:5]
            print(f"✅ After sorting and limiting: {len(articles)} articles")  # 디버깅 로그
        except Exception as sort_err:
            print(f"❌ Sorting failed: {sort_err}")  # 디버깅 로그
            # 정렬 실패시 그냥 처음 5개 사용
            articles = articles[:5]
        print(f"📊 Processing {len(articles)} most recent articles for {category}")  # 디버깅 로그

        try:

            for i, article in enumerate(articles):
                title = article.get("title", "").strip()
                description = article.get("description", "").strip()

                # HTML 태그 제거만 하고 끝
                if description:
                    soup = BeautifulSoup(description, 'html.parser')
                    description = soup.get_text().strip()
                    description = ' '.join(description.split())

                total_processed += 1
                print(f"📰 Processing article {i+1}: {title[:50]}...")

                # 본문 추출 시도
                news_url = article.get("url", "")
                content = description  # 기본값으로 RSS 요약 사용

                # 실제 본문 추출 시도
                if news_url:
                    try:
                        extracted_content = client.extract_article_content(news_url)
                        if extracted_content and len(extracted_content.strip()) > 50:
                            content = extracted_content
                            print(f"✅ 본문 추출 성공: {len(content)}자")
                        else:
                            print("⚠️ 본문 추출 실패, RSS 요약 사용")
                    except Exception as e:
                        print(f"💥 본문 추출 오류: {e}, RSS 요약 사용")

                # 중복 체크 간단하게
                existing = db.query(Post).filter(Post.title == title).first()
                if existing:
                    print(f"🔄 Skipped: Already exists - {title[:30]}...")
                    continue

                # 저장
                full_content = content
                if news_url:
                    full_content += f"\n\n🔗 전체 기사 보기: {news_url}"

                image_url = article.get("urlToImage", "")
                if not image_url:
                    image_url = "https://images.unsplash.com/photo-1504711434969-e33886168f5c?auto=format&fit=crop&q=80&w=800"

                post_data = {
                    "title": title[:200],
                    "summary": description[:300],
                    "content": full_content,
                    "category": category.capitalize(),
                    "image_url": image_url
                }

                db_post = Post(**post_data)
                db.add(db_post)
                total_saved += 1
                print(f"✅ Saved article: {title[:30]}...")
                
        except Exception as e:
            print(f"💥 Error fetching {category} news: {e}")
            continue

    try:
        db.commit()
        print(f"🎉 Total processed: {total_processed}, Total saved: {total_saved}")  # 최종 결과 로그
        print("News fetched and stored successfully")
    except Exception as e:
        db.rollback()
        print(f"💥 Error saving news to database: {e}")

# API 앤드 포인트들
@app.get("/api/posts", response_model=List[PostResponse])
async def get_posts(
    category: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    query = db.query(Post)

    if category:
        query = query.filter(Post.category == category)

    if search:
        search_term = f"%{search.lower()}%"
        query = query.filter(
            (Post.title.ilike(search_term)) |
            (Post.content.ilike(search_term))
        )

    posts = query.order_by(Post.created_at.desc()).all()
    return posts

# FastAPI에서는 경로 파라미터를 중괄호로 선언해야 하며, f-string을 사용할 필요가 없다.
@app.api_route("/api/posts/{post_id}", methods=["GET"])  # api_route로 변경하여 validation 우회
async def get_post(post_id, db: Session = Depends(get_db)):  # 타입 힌트 제거
    print(f"DEBUG: Requesting post with ID: {post_id}, type: {type(post_id)}")

    try:
        post_id_int = int(post_id)
        print(f"DEBUG: Converted to int: {post_id_int}")
    except ValueError as e:
        print(f"DEBUG: Failed to convert ID to int: {e}")
        raise HTTPException(status_code=400, detail=f"Invalid ID format: {post_id}")

    # 데이터베이스에 해당 ID가 존재하는지 확인
    all_posts = db.query(Post).all()
    print(f"DEBUG: All post IDs in database: {[p.id for p in all_posts]}")

    post = db.query(Post).filter(Post.id == post_id_int).first()
    if not post:
        print(f"DEBUG: Post with ID {post_id_int} not found")
        raise HTTPException(status_code=404, detail="Post not found")

    print(f"DEBUG: Found post: {post.id}, {post.title}")
    return post


@app.post("/api/posts", response_model=PostResponse, status_code=201)
async def create_post(post: PostCreate, db: Session = Depends(get_db)):
    db_post = Post(**post.dict())
    db.add(db_post)
    db.commit()
    db.refresh(db_post)
    return db_post


@app.post("/api/news/fetch")
async def fetch_latest_news(db: Session = Depends(get_db)):
    """최신 뉴스를 가져와서 저장"""
    await fetch_and_store_news(db)
    return {"message": "Latest news fetched and stored successfully"}
    
        

# 간단한 서버 실행
if __name__ == "__main__":
    # 테스트 코드
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        print("🧪 본문 추출 테스트...")
        test_url = 'https://news.google.com/rss/articles/CBMiVkFVX3lxTE9WUjlNZ0psX0hZMW5mVlQyZFhRblQ4TVFaRVdUMmdIMXNKbXUzZ284MmVuWDhRcVV6eFBHdWWhmMkhON1lEMFRwWnMxNDdMMU1Qb3BsdEZB?oc=5'
        try:
            result = extract_news_content(test_url)
            if result:
                print(f'✅ 성공! 추출된 텍스트 길이: {len(result)}')
                print(f'📝 미리보기: {result[:200]}...')
            else:
                print('❌ 추출 실패')
        except Exception as e:
            print(f'💥 오류 발생: {e}')
            import traceback
            print(traceback.format_exc())
    else:
        port = int(os.getenv("PORT", 8000))
        uvicorn.run(app, host="127.0.0.1", port=port)



