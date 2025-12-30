#!/usr/bin/env python3
import os
import sys
sys.path.insert(0, '.')

from main import SessionLocal, Post

def reclassify_korea_news():
    """한국 뉴스들을 새로운 키워드로 재분류"""
    db = SessionLocal()
    try:
        # 한국 뉴스들 가져오기
        korea_posts = db.query(Post).filter(Post.region == "korea").all()

        print(f"📊 한국 뉴스 {len(korea_posts)}개를 재분류합니다.")

        # 새로운 키워드 매핑
        keyword_mapping = {
            "정치": ["대통령", "정부", "국회", "정치", "선거", "장관", "국회의원", "총리", "의원", "민주", "국힘", "김병기", "강선우", "이혜훈", "내란", "공천", "의혹", "사퇴", "원내대표"],
            "과학": ["연구", "발견", "과학", "우주", "환경", "기후", "연구원", "과학자", "반도체", "기술", "AI", "인공지능"],
            "연예": ["영화", "드라마", "연예인", "가수", "콘서트", "배우", "예술", "넷플릭스", "게임", "포트나이트", "스타", "주식시세"],
        }

        updated_count = 0

        for post in korea_posts:
            # 이미 정치 카테고리가 아닌 뉴스들만 재분류
            if post.category != "정치":
                text_to_analyze = (post.title + " " + post.summary).lower()

                new_category = "전체"  # 기본값

                for cat, keywords in keyword_mapping.items():
                    if any(keyword.lower() in text_to_analyze for keyword in keywords):
                        new_category = cat
                        print(f"✅ 재분류: '{post.title[:30]}...' → {cat}")
                        break

                if new_category != post.category:
                    post.category = new_category
                    updated_count += 1

        db.commit()
        print(f"🎉 총 {updated_count}개의 한국 뉴스가 재분류되었습니다!")

    except Exception as e:
        db.rollback()
        print(f"❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    reclassify_korea_news()
