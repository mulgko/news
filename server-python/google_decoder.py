#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Google News URL 디코딩 API 서버
googlenewsdecoder 라이브러리를 사용하여 Google News RSS URL을 실제 뉴스 URL로 변환
"""

from fastapi import FastAPI, Request, HTTPException
from pydantic import BaseModel
from typing import Optional
import ssl
import logging

# SSL 인증서 검증 우회 (googlenewsdecoder가 SSL 검증을 하기 때문)
ssl._create_default_https_context = ssl._create_unverified_context

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DecodeRequest(BaseModel):
    source_url: str
    interval_time: int = 5

class BatchDecodeRequest(BaseModel):
    urls: list[str]
    interval_time: int = 5

app = FastAPI(
    title="Google News URL Decoder API",
    description="Google News RSS URL을 실제 뉴스 URL로 디코딩하는 API",
    version="1.0.0"
)

# IP 기반 인증 (보안)
ALLOWED_IPS = {
    "127.0.0.1",
    "localhost",
    "::1"  # IPv6 localhost
}

@app.middleware("http")
async def ip_filter_middleware(request: Request, call_next):
    client_ip = request.client.host
    if client_ip not in ALLOWED_IPS:
        logger.warning(f"Access denied for IP: {client_ip}")
        raise HTTPException(status_code=403, detail="Access forbidden: Your IP address is not allowed.")
    response = await call_next(request)
    return response

@app.get("/health")
async def health_check():
    """헬스체크 엔드포인트"""
    return {"status": "healthy", "service": "google_news_decoder"}

@app.post("/decode/")
async def decode_url(request: DecodeRequest):
    """단일 URL 디코딩"""
    try:
        logger.info(f"Decoding URL: {request.source_url}, Interval: {request.interval_time}")

        # googlenewsdecoder 임포트 (런타임에)
        try:
            from googlenewsdecoder import new_decoderv1
        except ImportError as e:
            logger.error(f"googlenewsdecoder not installed: {e}")
            raise HTTPException(status_code=500, detail="googlenewsdecoder library not installed")

        # URL 디코딩
        decoded_result = new_decoderv1(request.source_url, interval=request.interval_time)

        if decoded_result.get("status"):
            logger.info(f"Successfully decoded: {decoded_result['decoded_url'][:80]}...")
            return {
                "success": True,
                "decoded_url": decoded_result["decoded_url"],
                "original_url": request.source_url
            }
        else:
            error_msg = decoded_result.get("message", "Unknown error")
            logger.warning(f"Decoding failed: {error_msg}")
            return {
                "success": False,
                "error": error_msg,
                "original_url": request.source_url,
                "fallback_url": request.source_url  # 실패시 원본 URL 반환
            }

    except Exception as e:
        error_msg = str(e)
        logger.error(f"Unexpected error: {error_msg}")
        return {
            "success": False,
            "error": error_msg,
            "original_url": request.source_url,
            "fallback_url": request.source_url
        }

@app.post("/decode_batch/")
async def decode_batch(request: BatchDecodeRequest):
    """여러 URL 일괄 디코딩"""
    try:
        logger.info(f"Batch decoding {len(request.urls)} URLs")

        try:
            from googlenewsdecoder import new_decoderv1
        except ImportError as e:
            raise HTTPException(status_code=500, detail="googlenewsdecoder library not installed")

        results = []
        for url in request.urls:
            try:
                decoded_result = new_decoderv1(url, interval=request.interval_time)
                if decoded_result.get("status"):
                    results.append({
                        "original_url": url,
                        "decoded_url": decoded_result["decoded_url"],
                        "success": True
                    })
                else:
                    results.append({
                        "original_url": url,
                        "decoded_url": url,  # 실패시 원본 사용
                        "success": False,
                        "error": decoded_result.get("message", "Decoding failed")
                    })
            except Exception as e:
                results.append({
                    "original_url": url,
                    "decoded_url": url,
                    "success": False,
                    "error": str(e)
                })

        return {"results": results}

    except Exception as e:
        logger.error(f"Batch decoding error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    print("🚀 Starting Google News URL Decoder API Server...")
    print("📍 Server will be available at: http://127.0.0.1:5000")
    print("🔒 Access restricted to localhost only")
    uvicorn.run(app, host="127.0.0.1", port=5000)
