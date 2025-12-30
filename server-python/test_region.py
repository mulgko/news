#!/usr/bin/env python3
import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# 환경 변수 로드 시도
try:
    from dotenv import load_dotenv
    load_dotenv()
except:
    pass

# 데이터베이스 설정
DATABASE_URL = os.getenv("DATABASE_URL") or "sqlite:///./news.db"
engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def test_region_query():
    db = SessionLocal()
    try:
        # region='korea'인 포스트 조회
        result = db.execute(text("SELECT COUNT(*) FROM posts WHERE region = 'korea'"))
        count = result.fetchone()[0]
        print(f"region='korea'인 포스트 수: {count}")

        # 모든 포스트의 region 값 확인
        result = db.execute(text("SELECT DISTINCT region FROM posts"))
        regions = [row[0] for row in result.fetchall()]
        print(f"존재하는 region 값들: {regions}")

        print("✅ region 칼럼이 정상 작동합니다!")

    except Exception as e:
        print(f"❌ 오류 발생: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    test_region_query()
