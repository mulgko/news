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
import httpx
import feedparser
import requests
from bs4 import BeautifulSoup
import time
import re
import base64
import urllib.parse
from newspaper import Article, Config
import ssl
import urllib3
import certifi

# SSL 환경 설정 개선
os.environ['SSL_CERT_FILE'] = certifi.where()
ssl._create_default_https_context = ssl._create_unverified_context
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

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


def decode_google_news_url(source_url: str) -> str:
    """Google News의 CBMi... 형태의 URL을 디코딩하여 실제 URL을 추출합니다."""
    try:
        if not source_url.startswith("https://news.google.com/rss/articles/"):
            return source_url

        prefix = "https://news.google.com/rss/articles/"
        base64_str = source_url[len(prefix):].split('?')[0]

        # Base64 패딩 보정 및 디코딩
        padding = '=' * (4 - len(base64_str) % 4)
        decoded_bytes = base64.b64decode(base64_str + padding)

        # 디코딩된 바이트에서 URL 패턴 추출 (보통 4번째 바이트 이후에 URL이 위치함)
        # 프로토콜(http) 위치를 찾아 그 지점부터 추출하는 것이 가장 안정적입니다.
        decoded_str = decoded_bytes.decode('utf-8', errors='ignore')
        if "http" in decoded_str:
            start_idx = decoded_str.find("http")
            # URL 끝부분의 불필요한 바이너리 문자 제거
            actual_url = ""
            for char in decoded_str[start_idx:]:
                if ord(char) < 32 or ord(char) > 126: # 제어 문자나 비 ASCII 문자에서 중단
                    break
                actual_url += char
            return actual_url
    except Exception as e:
        print(f"⚠️ URL Decoding failed: {e}")
    return source_url


def extract_news_content(article_url):
    """실제 뉴스 페이지에서 본문을 추출합니다."""
    try:
        # 1. Google News URL인 경우 실제 언론사 URL로 먼저 변환
        real_url = decode_google_news_url(article_url)

        if real_url == article_url:
            # 디코딩 실패 시 requests를 이용한 최종 리다이렉트 추적 시도
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
            with requests.Session() as s:
                s.verify = False
                resp = s.get(article_url, headers=headers, timeout=5, allow_redirects=True)
                real_url = resp.url

        print(f"🔗 Attempting extraction from: {real_url}")

        # 2. newspaper3k 설정 (SSL 검증 우회 설정은 없으므로 URL 자체가 중요함)
        config = Config()
        config.browser_user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        config.request_timeout = 15

        article = Article(real_url, config=config, language='ko')
        article.download()
        article.parse()

        if len(article.text) > 100:
            content = article.text.strip()
            print(f"✅ Newspaper3k extracted content: {len(content)} characters")
            return content
        else:
            print(f"❌ Newspaper3k failed to extract meaningful content")
            return None

    except Exception as e:
        print(f"❌ Newspaper3k error: {e}")
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
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })

            # SSL 인증서 검증 비활성화 추가
        self.session.verify = False

    def extract_article_content(self, url: str) -> str:
        """뉴스 기사 URL에서 전체 내용을 추출"""
        try:
            # 요청 간 딜레이 추가 (크롤링 예의)
            time.sleep(1)

            response = self.session.get(url, timeout=10)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')

            # 다양한 뉴스 사이트의 본문 추출 시도
            content_selectors = [
                'article',  # 일반적인 article 태그
                '[class*="content"]',  # content 클래스가 포함된 요소
                '[class*="article"]',  # article 클래스가 포함된 요소
                '[class*="story"]',  # story 클래스가 포함된 요소
                'div[itemprop="articleBody"]',  # schema.org 마크업
                '.news-content',  # 네이버 뉴스
                '#articleBodyContents',  # 다음 뉴스
                '.article-body',  # 일반적인 본문 클래스
                'p'  # 모든 p 태그 (fallback)
            ]

            for selector in content_selectors:
                content_elements = soup.select(selector)
                if content_elements:
                    # 텍스트 추출 및 정리
                    content_text = ' '.join([elem.get_text().strip() for elem in content_elements if elem.get_text().strip()])

                    # 불필요한 텍스트 제거 (광고, 관련 기사 등)
                    content_text = re.sub(r'▶.*?\n', '', content_text)  # 네이버 뉴스 화살표 제거
                    content_text = re.sub(r'\[.*?\]', '', content_text)  # 대괄호 안 텍스트 제거
                    content_text = re.sub(r'사진.*?\n', '', content_text)  # 사진 설명 제거
                    content_text = re.sub(r'\s+', ' ', content_text)  # 연속된 공백 제거

                    if len(content_text) > 100:  # 충분한 길이의 내용인지 확인
                        return content_text[:2000]  # 길이 제한

            return ""  # 내용 추출 실패

        except Exception as e:
            print(f"Error extracting content from {url}: {e}")
            return ""

    def _extract_real_url(self, google_news_url: str) -> str:
        """Google News URL에서 실제 뉴스 URL 추출 (간소화된 버전)"""
        # 새로 만든 전문 디코더 사용
        return decode_google_news_url(google_news_url)

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

            # SSL 검증 없이 RSS 가져오기 (requests 사용)
            response = self.session.get(rss_url, verify=False)
            response.raise_for_status()
            rss_content = response.text

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

        # 최신순으로 정렬하고 20개로 제한
        print(f"🔢 Before sorting: {len(articles)} articles")  # 디버깅 로그
        try:
            articles = sorted(articles, key=get_sort_key, reverse=True)[:20]
            print(f"✅ After sorting and limiting: {len(articles)} articles")  # 디버깅 로그
        except Exception as sort_err:
            print(f"❌ Sorting failed: {sort_err}")  # 디버깅 로그
            # 정렬 실패시 그냥 처음 20개 사용
            articles = articles[:20]
        print(f"📊 Processing {len(articles)} most recent articles for {category}")  # 디버깅 로그

        try:

            for i, article in enumerate(articles):
                title = article.get("title", "").strip()
                description = article.get("description", "").strip()

                # HTML 태그 제거 (Google News RSS는 HTML 형식의 description을 제공)
                if description:
                    soup = BeautifulSoup(description, 'html.parser')
                    # 텍스트만 추출하고 불필요한 공백 제거
                    description = soup.get_text().strip()
                    # 여러 공백을 하나로 통합
                    description = ' '.join(description.split())

                total_processed += 1
                print(f"📰 Processing article {i+1}: {title[:50]}...")  # 디버깅 로그
                print(f"📝 Description after cleaning: {description[:100]}...")  # 디버깅 로그

                # 실제 뉴스 본문 추출 시도
                news_url = ""
                full_content = None

                # Google News에서 실제 뉴스 URL 추출 (GoogleNewsRSSClient에서 "url" 필드에 저장됨)
                news_url = article.get("url", "")
                print(f"🔗 News URL: {news_url}")  # 디버깅 로그

                # 실제 뉴스 페이지에서 본문 추출
                if news_url:
                    full_content = extract_news_content(news_url)

                # content 설정 (실제 본문 우선, 없으면 description 사용)
                if full_content:
                    content = full_content
                    print(f"📄 Using full article content ({len(content)} chars)")  # 디버깅 로그
                else:
                    content = description
                    print(f"📄 Using RSS description ({len(content)} chars)")  # 디버깅 로그

                # 유효성 검증
                if not title or not content:
                    print(f"❌ Skipped: Empty title or content")  # 디버깅 로그
                    continue
                
                # 중복 체크
                published_date = article.get("publishedAt", "")
                existing = None
                
                if published_date:
                    try:
                        from datetime import datetime
                        pub_dt = datetime.fromisoformat(published_date.replace('Z', '+00:00'))
                        date_str = pub_dt.date().isoformat()
                        existing = db.query(Post).filter(
                            Post.title == title,
                            func.date(Post.created_at) == date_str
                        ).first()
                    except Exception as date_err:
                        print(f"⚠️ Date parsing error: {date_err}")  # 디버깅 로그
                        existing = db.query(Post).filter(Post.title == title).first()
                else:
                    existing = db.query(Post).filter(Post.title == title).first()
                
                if existing:
                    print(f"🔄 Skipped: Already exists - {title[:30]}...")  # 디버깅 로그
                    continue
                
                # 저장할 데이터 준비
                # news_url은 위에서 이미 추출됨

                print(f"📝 Original content length: {len(content)}")  # 디버깅 로그
                print(f"🔗 News URL: {news_url}")  # 디버깅 로그

                # RSS 내용이 부족하거나 링크만 있으면 실제 기사에서 전체 내용 추출 시도
                should_extract = (
                    len(content) < 200 or      # 내용이 너무 짧거나
                    "http" in content or        # 링크가 포함되어 있거나
                    "..." in content or         # 생략 기호가 있거나
                    content.strip() == "" or    # 내용이 비어있거나
                    len(content.split()) < 10   # 단어가 10개 미만
                )

                if should_extract and news_url:
                    print(f"🛠️ Extracting full content from: {news_url}")  # 디버깅 로그
                    try:
                        full_article_content = client.extract_article_content(news_url)
                        if full_article_content and len(full_article_content) > len(content):
                            content = full_article_content
                            print(f"✅ Successfully extracted content ({len(content)} chars)")  # 디버깅 로그
                        else:
                            print(f"❌ Failed to extract content or content too short")  # 디버깅 로그
                            # 추출 실패 시 원본 content라도 사용 (링크 제거)
                            if "http" in content:
                                content = content.split("http")[0].strip()
                                print(f"🔧 Cleaned content: {content[:100]}...")  # 디버깅 로그
                    except Exception as extract_err:
                        print(f"⚠️ Content extraction failed: {extract_err}")  # 디버깅 로그
                        # 에러 시에도 링크 제거된 content 사용
                        if "http" in content:
                            content = content.split("http")[0].strip()
                
                if not content:
                    print(f"❌ Skipped: No content available")  # 디버깅 로그
                    continue
                
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
                
                try:
                    db_post = Post(**post_data)
                    db.add(db_post)
                    total_saved += 1
                    print(f"✅ Saved article: {title[:30]}...")  # 디버깅 로그
                except Exception as save_err:
                    print(f"❌ Save failed: {save_err}")  # 디버깅 로그
                    continue
                
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
    
        

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))  # 5000 대신 8000 사용
    uvicorn.run(app, host="127.0.0.1", port=port)



