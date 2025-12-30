#!/usr/bin/env python3
import os
import sys
sys.path.insert(0, '.')

from main import SessionLocal, Post

def update_world_categories():
    """세계 뉴스들의 카테고리를 영어로 변환"""
    db = SessionLocal()
    try:
        # 세계 뉴스들만 선택
        world_posts = db.query(Post).filter(Post.region == "world").all()

        print(f"🌍 세계 뉴스 {len(world_posts)}개를 발견했습니다.")

        # 한국어 → 영어 카테고리 매핑
        category_mapping = {
            "비즈니스": "Business",
            "기술": "Technology",
            "과학": "Science",
            "건강": "Health",
            "엔터테인먼트": "Entertainment",
            "스포츠": "Sports",
            "정치": "Politics",
            "국제": "World",
            "국내": "Nation",
            "일반": "General"
        }

        updated_count = 0

        for post in world_posts:
            new_category = category_mapping.get(post.category, post.category)
            if new_category != post.category:
                print(f"✅ 업데이트: '{post.title[:30]}...' → {new_category}")
                post.category = new_category
                updated_count += 1

        db.commit()
        print(f"🎉 총 {updated_count}개의 세계 뉴스 카테고리가 영어로 업데이트되었습니다!")

    except Exception as e:
        db.rollback()
        print(f"❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    update_world_categories()
