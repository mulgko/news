"""
News router - handles news fetching and storing endpoints.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from bs4 import BeautifulSoup

from app.core.database import get_db
from app.models.post import Post
from app.services.news_crawler import GoogleNewsRSSClient
from app.services.url_decoder import decode_google_news_url
from app.services.content_extractor import extract_news_content, clean_news_content
from app.services.ai_summarizer import generate_ai_summary_google
from app.utils.helpers import get_sort_key

router = APIRouter()


# News fetch, save Func
async def fetch_and_store_news(db: Session):
    """Google News RSS에서 뉴스를 가져와서 Python 서버의 자체 DB에 저장"""

    # 기존 데이터에 region 필드 기본값 설정 (마이그레이션)
    try:
        existing_posts = db.query(Post).filter(Post.region.is_(None)).all()
        if existing_posts:
            print(f"🔄 기존 {len(existing_posts)}개 뉴스에 region='korea' 설정 중...")
            for post in existing_posts:
                post.region = "korea"
            db.commit()
            print("✅ 기존 데이터 region 설정 완료")
    except Exception as e:
        print(f"⚠️ 기존 데이터 마이그레이션 실패: {e}")
        db.rollback()

    client = GoogleNewsRSSClient()

    total_processed = 0
    total_saved = 0

    # 한국 뉴스 가져오기
    print("🇰🇷 Fetching Korea news...")
    korea_articles = client.get_korea_news()
    print(f"📊 Found {len(korea_articles)} Korea articles")

    # 세계 뉴스 가져오기
    print("🌍 Fetching World news...")
    world_articles = client.get_world_news()
    print(f"📊 Found {len(world_articles)} World articles")

    # 뉴스 처리 (한국 뉴스 5개, 세계 뉴스 5개로 제한)
    for articles, region in [(korea_articles, "korea"), (world_articles, "world")]:
        # 지역별 뉴스 개수 제한
        limit = 5 if region == "korea" else 5  # 한국 5개, 세계 5개

        try:
            articles = sorted(articles, key=get_sort_key, reverse=True)[:limit]
            print(f"✅ Processing {len(articles)} {region} articles")
        except Exception as sort_err:
            print(f"❌ Sorting failed for {region}: {sort_err}")
            articles = articles[:limit]

        try:

            for i, article in enumerate(articles):
                title = article.get("title", "").strip()
                description = article.get("description", "").strip()
                category = article.get("category", "general").lower().strip()  # 카테고리 정보 가져오기

                # HTML 태그 제거만 하고 끝
                if description:
                    soup = BeautifulSoup(description, 'html.parser')
                    description = soup.get_text().strip()
                    description = ' '.join(description.split())

                total_processed += 1
                print(f"📰 Processing article {i+1}: {title[:50]}...")

                # 본문 추출 시도
                google_news_url = article.get("url", "")
                content = description  # 기본값으로 RSS 요약 사용

                # 실제 본문 추출 시도 (디코딩된 URL 사용)
                news_url = ""  # 디코딩된 URL 초기화
                if google_news_url:
                    try:
                        # 1. 먼저 Google News URL 디코딩
                        decoded_url = decode_google_news_url(google_news_url)
                        if decoded_url and isinstance(decoded_url, str):
                            news_url = decoded_url
                            print(f"✅ URL 디코딩 성공: {decoded_url}")

                            # 2. 디코딩된 URL에서 본문 추출 (test_extraction.py 방식)
                            extracted_content = extract_news_content(decoded_url)
                            if extracted_content and len(extracted_content.strip()) > 50:
                                # 3. 불필요한 내용만 제거 (전체 본문 유지)
                                filtered_content = clean_news_content(extracted_content)
                                if filtered_content and len(filtered_content.strip()) > 50:
                                    content = filtered_content
                                    print(f"✅ 본문 추출 및 정리 성공: {len(content)}자")
                                    print(f"📄 정리된 본문 미리보기: {content[:100]}...")

                                    # AI 요약 생성
                                    ai_summary = generate_ai_summary_google(content, title)
                                else:
                                    print("⚠️ 정리 결과가 너무 짧음, RSS 요약 사용")
                            else:
                                print("⚠️ 본문 추출 실패, RSS 요약 사용")
                        else:
                            print("❌ URL 디코딩 실패")
                    except Exception as e:
                        print(f"💥 본문 추출 오류: {e}, RSS 요약 사용")

                # Python DB에서 중복 체크 (제목 또는 URL 기준)
                existing_post = None

                # 1. 제목으로 먼저 체크
                existing_post = db.query(Post).filter(Post.title == title).first()

                # 2. URL로도 체크 (news_url이 있는 경우)
                if not existing_post and news_url:
                    existing_post = db.query(Post).filter(Post.url == news_url).first()

                if existing_post:
                    # 이미 존재하는 뉴스라면 업데이트
                    print(f"🔄 Updating existing post: {title[:30]}... (ID: {existing_post.id})")

                    # Region별 카테고리 매핑 (업데이트 시)
                    if region == "korea":
                        category_mapping = {
                            "business": "비즈니스",
                            "technology": "기술",
                            "science": "과학",
                            "health": "건강",
                            "entertainment": "엔터테인먼트",
                            "general": "일반"
                        }
                        update_category = category_mapping.get(category, "일반")
                    else:
                        category_mapping = {
                            "business": "Business",
                            "technology": "Technology",
                            "science": "Science",
                            "health": "Health",
                            "entertainment": "Entertainment",
                            "general": "General"
                        }
                        update_category = category_mapping.get(category, "General")

                    # AI 요약 생성 (콘텐츠가 업데이트될 때마다)
                    update_ai_summary = ""
                    if content and len(content.strip()) > 50:
                        update_ai_summary = generate_ai_summary_google(content, title)

                    # 업데이트할 필드들
                    update_data = {
                        'summary': description[:300],
                        'content': content,
                        'category': update_category,
                        'ai_summary': update_ai_summary if update_ai_summary else None,
                    }

                    # 이미지 URL이 있으면 업데이트
                    image_url = article.get("urlToImage", "")
                    if image_url:
                        update_data['image_url'] = image_url

                    # URL이 있으면 업데이트
                    if news_url:
                        update_data['url'] = news_url

                    try:
                        for key, value in update_data.items():
                            setattr(existing_post, key, value)

                        # content에 링크 추가 (이미 존재하는 경우에도 업데이트)
                        if news_url and "🔗 전체 기사 보기:" not in existing_post.content:
                            existing_post.content += f"\n\n🔗 전체 기사 보기: {news_url}"
                            existing_post.content += "\n\n© 모든 권리는 원본 저작권자와 출처에 있습니다."

                        db.commit()
                        print(f"✅ Updated existing post: {title[:30]}...")
                        continue  # 저장하지 않고 다음으로 진행
                    except Exception as update_error:
                        db.rollback()
                        print(f"💥 Error updating existing post: {update_error}")
                        continue

                # 새로운 뉴스인 경우 저장
                full_content = content
                if news_url:
                    full_content += f"\n\n🔗 전체 기사 보기: {news_url}"
                    full_content += "\n\n© 모든 권리는 원본 저작권자와 출처에 있습니다."
                    print(f"📎 링크 추가됨: {news_url}")
                else:
                    print("⚠️ news_url이 비어있음")

                image_url = article.get("urlToImage", "")
                if not image_url:
                    image_url = "https://images.unsplash.com/photo-1504711434969-e33886168f5c?auto=format&fit=crop&q=80&w=800"

                # Region별 카테고리 매핑 (한국어 vs 영어)
                if region == "korea":
                    # 한국 뉴스: 한국어 카테고리
                    category_mapping = {
                        "business": "비즈니스",
                        "technology": "기술",
                        "science": "과학",
                        "health": "건강",
                        "entertainment": "엔터테인먼트",
                        "sports": "스포츠",
                        "politics": "정치",
                        "world": "국제",
                        "nation": "국내",
                        "general": "일반",
                        "tech": "기술",
                        "medical": "건강",
                        "economy": "비즈니스",
                        "finance": "비즈니스",
                        "showbiz": "엔터테인먼트",
                        "celebrity": "엔터테인먼트",
                        "research": "과학",
                        "environment": "과학",
                    }
                    final_category = category_mapping.get(category, "일반")
                else:
                    # 세계 뉴스: 영어 카테고리
                    category_mapping = {
                        "business": "Business",
                        "technology": "Technology",
                        "science": "Science",
                        "health": "Health",
                        "entertainment": "Entertainment",
                        "sports": "Sports",
                        "politics": "Politics",
                        "world": "World",
                        "nation": "Nation",
                        "general": "General",
                        "tech": "Technology",
                        "medical": "Health",
                        "economy": "Business",
                        "finance": "Business",
                        "showbiz": "Entertainment",
                        "celebrity": "Entertainment",
                        "research": "Science",
                        "environment": "Science",
                    }
                    final_category = category_mapping.get(category, "General")

                # 제목/내용으로 키워드 분석 (항상 수행하여 더 정확한 분류)
                if title or description:
                    text_to_analyze = (title + " " + description).lower()

                    # 키워드 기반 카테고리 분류 (한국어 + 영어)
                    # 새로운 카테고리에 맞는 간단한 키워드 매핑
                    if region == "korea":
                        keyword_mapping = {
                            "정치": ["대통령", "정부", "국회", "정치", "선거", "장관", "국회의원", "총리", "의원", "민주", "국힘", "김병기", "강선우", "이혜훈", "내란", "공천", "의혹", "사퇴", "원내대표"],
                            "경제": ["경제", "금융", "기업", "시장", "주식", "사업", "회사", "산업", "은행", "투자", "무역", "환율", "부동산", "코스피", "코스닥"],
                            "과학": ["연구", "발견", "과학", "우주", "환경", "기후", "연구원", "과학자", "반도체", "기술", "AI", "인공지능"],
                            "연예": ["영화", "드라마", "연예인", "가수", "콘서트", "배우", "예술", "넷플릭스", "게임", "포트나이트", "스타", "주식시세"],
                        }
                    else:
                        keyword_mapping = {
                            "Politics": ["president", "government", "politics", "election", "minister", "congress", "political", "policy", "diplomatic", "trump", "china", "taiwan"],
                            "Business": ["economy", "finance", "company", "market", "stock", "business", "industry", "bank", "investment", "trading"],
                            "Science": ["research", "discovery", "science", "space", "environment", "climate", "scientist", "laboratory"],
                            "Entertainment": ["movie", "drama", "celebrity", "singer", "concert", "entertainment", "netflix", "actor", "artist"],
                        }

                    for cat, keywords in keyword_mapping.items():
                        if any(keyword in text_to_analyze for keyword in keywords):
                            final_category = cat
                            print(f"🎯 키워드 분석으로 카테고리 결정: {cat} (region: {region})")
                            break

                print(f"📂 최종 카테고리: {final_category} (원본: {category}, region: {region})")

                # Python Post 모델 생성 및 저장 (region 정보 추가)
                new_post = Post(
                    title=title[:200],
                    summary=description[:300],
                    content=full_content,
                    category=final_category,
                    region=region,  # region 정보 추가
                    image_url=image_url,
                    url=news_url if news_url else None,
                    ai_summary=ai_summary if ai_summary else None
                )

                print(f"📤 DB 저장 시도: {title[:30]}...")
                try:
                    db.add(new_post)
                    db.commit()
                    db.refresh(new_post)
                    total_saved += 1
                    print(f"✅ Saved to Python DB: {title[:30]}... (ID: {new_post.id})")
                except Exception as save_error:
                    db.rollback()
                    print(f"💥 Error saving to Python DB: {save_error}")

        except Exception as e:
            print(f"💥 Error fetching {region} news: {e}")
            continue

    print(f"🎉 Total processed: {total_processed}, Total saved to Python DB: {total_saved}")  # 최종 결과 로그
    print("News fetched and stored in Python database successfully")


@router.post("/api/news/fetch")
async def fetch_latest_news(db: Session = Depends(get_db)):
    """최신 뉴스를 가져와서 저장"""
    await fetch_and_store_news(db)
    return {"message": "Latest news fetched and stored successfully"}
