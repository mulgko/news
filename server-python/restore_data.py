#!/usr/bin/env python3
import sqlite3
import os

def restore_data():
    # 백업 DB에서 데이터 읽기
    backup_conn = sqlite3.connect('backup.db')
    backup_cursor = backup_conn.cursor()

    # 새 DB 연결
    new_conn = sqlite3.connect('news.db')
    new_cursor = new_conn.cursor()

    # 백업 데이터 조회
    backup_cursor.execute("""
        SELECT id, title, summary, content, category, image_url, url, created_at, likes, dislikes, views, region
        FROM posts
        ORDER BY created_at DESC
    """)

    rows = backup_cursor.fetchall()

    print(f"백업에서 {len(rows)}개의 레코드를 발견했습니다.")

    # 새 DB에 데이터 삽입 (칼럼 순서 재배열)
    for row in rows:
        try:
            # 백업 DB 순서: id, title, summary, content, category, image_url, url, created_at, likes, dislikes, views, region
            # 새 DB 순서:  id, title, summary, content, category, region, image_url, url, created_at, likes, dislikes, views
            id, title, summary, content, category, image_url, url, created_at, likes, dislikes, views, region = row

            new_cursor.execute("""
                INSERT INTO posts (id, title, summary, content, category, region, image_url, url, created_at, likes, dislikes, views)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (id, title, summary, content, category, region, image_url, url, created_at, likes, dislikes, views))
        except sqlite3.IntegrityError as e:
            print(f"ID {row[0]} 삽입 실패 (이미 존재): {e}")
            continue

    new_conn.commit()

    # 확인
    new_cursor.execute("SELECT COUNT(*) FROM posts")
    count = new_cursor.fetchone()[0]
    print(f"복원 완료: {count}개의 레코드가 새 데이터베이스에 있습니다.")

    backup_conn.close()
    new_conn.close()

if __name__ == "__main__":
    restore_data()
