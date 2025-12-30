#!/usr/bin/env python3
import os
import sys
sys.path.insert(0, '.')

from main import SessionLocal, Post

def update_to_final_categories():
    """최종 카테고리로 뉴스 재분류"""
    db = SessionLocal()
    try:
        # 기존 뉴스들 가져오기
        posts = db.query(Post).all()

        print(f"📊 총 {len(posts)}개의 뉴스를 최종 카테고리로 재분류합니다.")

        # 카테고리 매핑
        korea_mapping = {
            "일반": "전체",
            "비즈니스": "전체",
            "기술": "전체",
            "과학": "과학",
            "건강": "전체",
            "엔터테인먼트": "연예",
            "스포츠": "전체",
            "정치": "정치",
        }

        world_mapping = {
            "Politics": "Politics",
            "Business": "all",
            "Technology": "all",
            "Science": "Science",
            "Health": "all",
            "Entertainment": "Entertainment",
            "Sports": "all",
            "General": "all",
        }

        updated_count = 0

        for post in posts:
            if post.region == "korea":
                new_category = korea_mapping.get(post.category, "전체")
            else:  # world
                new_category = world_mapping.get(post.category, "all")

            if new_category != post.category:
                print(f"✅ 업데이트: '{post.title[:30]}...' → {new_category}")
                post.category = new_category
                updated_count += 1

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
    update_to_final_categories()
