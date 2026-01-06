"""
Posts router - handles all post-related endpoints.
"""
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query, Depends
from sqlalchemy.orm import Session

from app.models.post import Post
from app.schemas.post import PostResponse, PostCreate
from app.core.database import get_db

router = APIRouter()


@router.get("/api/posts", response_model=List[PostResponse])
async def get_posts(
    category: Optional[str] = Query(None),
    region: Optional[str] = Query("korea"),  # 기본값을 korea로 설정
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    query = db.query(Post)

    if category:
        query = query.filter(Post.category == category)

    if region:
        query = query.filter(Post.region == region)

    if search:
        search_term = f"%{search.lower()}%"
        query = query.filter(
            (Post.title.ilike(search_term)) |
            (Post.content.ilike(search_term))
        )

    posts = query.order_by(Post.created_at.desc(), Post.id.desc()).all()
    return posts


# FastAPI에서는 경로 파라미터를 중괄호로 선언해야 하며, f-string을 사용할 필요가 없다.
@router.api_route("/api/posts/{post_id}", methods=["GET"])  # api_route로 변경하여 validation 우회
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

    # GET 요청에서는 조회수 증가하지 않음 - 오직 POST /view에서만 증가
    print(f"DEBUG: Found post: {post.id}, {post.title} (views: {post.views})")
    return post


@router.post("/api/posts", response_model=PostResponse, status_code=201)
async def create_post(post: PostCreate, db: Session = Depends(get_db)):
    db_post = Post(**post.dict())
    db.add(db_post)
    db.commit()
    db.refresh(db_post)
    return db_post


@router.post("/api/posts/{post_id}/like")
async def like_post(post_id: int, db: Session = Depends(get_db)):
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    post.likes += 1
    db.commit()
    return {"success": True}


@router.post("/api/posts/{post_id}/view")
async def view_post(post_id: int, db: Session = Depends(get_db)):
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    post.views += 1
    db.commit()
    return {"success": True}


@router.post("/api/posts/{post_id}/dislike")
async def dislike_post(post_id: int, db: Session = Depends(get_db)):
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    post.dislikes += 1
    db.commit()
    return {"success": True}
