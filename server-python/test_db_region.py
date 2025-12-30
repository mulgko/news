#!/usr/bin/env python3
import os
import sys
sys.path.insert(0, '.')

# Import the database setup from main.py
from main import SessionLocal, Post

def test_database_region():
    db = SessionLocal()
    try:
        # Test region='korea' query
        print("Testing region='korea' query...")
        posts = db.query(Post).filter(Post.region == 'korea').limit(5).all()
        print(f"Found {len(posts)} korea posts")

        # Test region='world' query
        print("Testing region='world' query...")
        posts = db.query(Post).filter(Post.region == 'world').limit(5).all()
        print(f"Found {len(posts)} world posts")

        # Test general query
        print("Testing general posts query...")
        posts = db.query(Post).order_by(Post.created_at.desc()).limit(5).all()
        print(f"Found {len(posts)} total posts")

        print("✅ All database queries working correctly!")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    test_database_region()
