#!/usr/bin/env python3
import os
import sys
sys.path.insert(0, '.')

from main import SessionLocal, Post

def update_existing_categories():
    """기존 뉴스들의 카테고리를 업데이트"""
    db = SessionLocal()
    try:
        # 현재 "일반" 카테고리인 뉴스들을 찾아서 제목이나 내용으로 카테고리 재분류
        posts_to_update = db.query(Post).filter(Post.category == "일반").all()

        print(f"📊 '일반' 카테고리의 뉴스 {len(posts_to_update)}개를 발견했습니다.")

        # 간단한 키워드 기반 카테고리 분류
        category_keywords = {
            "비즈니스": ["경제", "금융", "기업", "시장", "주식", "사업", "회사", "산업"],
            "기술": ["AI", "인공지능", "반도체", "소프트웨어", "앱", "디지털", "기술", "IT", "컴퓨터", "인터넷"],
            "과학": ["연구", "발견", "과학", "우주", "환경", "기후", "연구원", "과학자"],
            "건강": ["의료", "병원", "질병", "치료", "건강", "의사", "약", "바이러스", "백신"],
            "엔터테인먼트": ["영화", "드라마", "연예인", "가수", "콘서트", "예능", "OTT", "넷플릭스"]
        }

        updated_count = 0

        for post in posts_to_update:
            # 제목과 요약을 합쳐서 키워드 검색
            text_to_check = (post.title + " " + post.summary).lower()

            new_category = "일반"  # 기본값

            for category, keywords in category_keywords.items():
                if any(keyword.lower() in text_to_check for keyword in keywords):
                    new_category = category
                    break

            if new_category != "일반":
                post.category = new_category
                updated_count += 1
                print(f"✅ 업데이트: '{post.title[:30]}...' → {new_category}")

        db.commit()
        print(f"🎉 총 {updated_count}개의 뉴스 카테고리가 업데이트되었습니다!")

    except Exception as e:
        db.rollback()
        print(f"❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    update_existing_categories()
