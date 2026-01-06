"""
News App - Main FastAPI Application
A news aggregation and AI summarization service powered by FastAPI.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from contextlib import asynccontextmanager
from typing import AsyncGenerator
import os

# Import database initialization
from app.core.database import init_db
from app.core.config import settings

# Import routers
from app.routers import posts, news


# Lifespan event handler
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Initialize database on startup"""
    print("🚀 Starting News App...")
    init_db()
    print("✅ Database initialized")
    yield
    # Cleanup on shutdown (if needed)
    print("👋 Shutting down News App...")


# Create FastAPI app
app = FastAPI(
    title="News API",
    version="1.0.0",
    description="Google News RSS aggregation with AI-powered summarization",
    lifespan=lifespan,
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(posts.router)
app.include_router(news.router)

# Static file serving (production)
# Current file location: server-python/main.py
# Frontend build location: dist/public
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(BASE_DIR)
DIST_DIR = os.path.join(ROOT_DIR, "dist", "public")
ASSETS_DIR = os.path.join(DIST_DIR, "assets")

# Mount assets directory
if os.path.exists(ASSETS_DIR):
    app.mount("/assets", StaticFiles(directory=ASSETS_DIR), name="assets")
else:
    print(f"⚠️  Assets directory not found at {ASSETS_DIR}. Frontend might not be built.")


# Root path - serve SPA
@app.get("/")
async def serve_spa_root():
    """Serve the frontend SPA index.html"""
    index_file = os.path.join(DIST_DIR, "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file)
    return {
        "message": "Welcome to News App API",
        "status": "Frontend not found. Please build the frontend.",
        "path_checked": index_file,
    }


# Health check endpoint
@app.get("/api/health")
async def health_check():
    """API health check"""
    return {"status": "running", "version": "1.0.0"}


# SPA routing catch-all (for frontend routes)
# This should be defined last to avoid catching API routes
@app.get("/{full_path:path}")
async def serve_spa(full_path: str):
    """Catch-all route for SPA (handles frontend routing)"""
    # Only serve SPA for non-API routes
    if not full_path.startswith("api/"):
        index_file = os.path.join(DIST_DIR, "index.html")
        if os.path.exists(index_file):
            return FileResponse(index_file)

    return {"detail": "Not Found"}


# Run with uvicorn
if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", "8000"))
    print(f"🌐 Starting server on port {port}")

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        reload=True,
    )
