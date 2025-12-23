#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

# 필요한 모듈들만 import
import requests
from bs4 import BeautifulSoup
import trafilatura
import re

def decode_google_news_url(url: str, session=None) -> str:
    """간소화된 URL 디코딩"""
    if not url or "google.com" not in url:
        return url

    try:
        from urllib.parse import urlparse, parse_qs
        parsed = urlparse(url)
        if 'url' in parse_qs(parsed.query):
            direct_url = parse_qs(parsed.query)['url'][0]
            if "google.com" not in direct_url and direct_url.startswith('http'):
                print(f"URL 파라미터에서 추출: {direct_url[:80]}...")
                return direct_url
        print(f"URL 디코딩 생략, 원본 사용: {url[:80]}...")
        return url
    except Exception as e:
        print(f"URL 파싱 오류: {e}, 원본 사용")
        return url

def extract_news_content(article_url: str, session=None) -> str:
    """본문 추출 테스트"""
    try:
        real_url = decode_google_news_url(article_url, session)
        if not real_url:
            print(f"URL 처리 실패: {article_url}")
            return None

        # Google News URL인 경우에도 시도 (리다이렉트될 것임)
        target_url = real_url if real_url != article_url else article_url

        # BeautifulSoup부터 시도
        print(f"BeautifulSoup로 본문 추출 시도: {target_url[:80]}...")
        result = _extract_with_beautifulsoup(target_url, session)
        if result:
            return result

        # BeautifulSoup 실패시 Trafilatura 시도
        print(f"BeautifulSoup 실패, Trafilatura 대안 시도")
        downloaded = trafilatura.fetch_url(target_url)
        if not downloaded:
            print(f"페이지 다운로드 실패: {target_url}")
            return None

        text = trafilatura.extract(
            downloaded,
            output_format='txt',
            include_comments=False,
            favor_precision=True
        )

        if text and len(text.strip()) > 100:
            cleaned_text = ' '.join(text.split())
            print(f"Trafilatura 추출 성공: {len(cleaned_text)}자")
            return cleaned_text[:2000]
        else:
            print(f"Trafilatura 추출 실패")
            return None

    except Exception as e:
        print(f"Trafilatura 추출 오류: {e}, BeautifulSoup 대안 시도")
        try:
            return _extract_with_beautifulsoup(real_url, session)
        except Exception as fallback_e:
            print(f"Fallback도 실패: {fallback_e}")
            return None

def _extract_with_beautifulsoup(url: str, session=None) -> str:
    """BeautifulSoup 대안 추출"""
    try:
        if session is None:
            session = requests.Session()
            session.verify = False

        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }

        response = session.get(url, headers=headers, timeout=20, verify=False, allow_redirects=True)
        response.raise_for_status()

        soup = BeautifulSoup(response.content, 'html.parser')

        for element in soup.find_all(['script', 'style', 'nav', 'footer', 'header', 'aside']):
            element.decompose()

        content_selectors = [
            'article', '[id*="article"]', '[class*="article"]',
            '[id*="content"]', '[class*="content"]',
            '#articleBody', '#newsct_article', '.article_body',
            '.news_body', 'div[itemprop="articleBody"]',
            '.article-content', 'main'
        ]

        content_text = ""
        for selector in content_selectors:
            elements = soup.select(selector)
            if elements:
                texts = []
                for elem in elements:
                    paragraphs = elem.find_all(['p', 'div'])
                    for p in paragraphs:
                        text = p.get_text(strip=True)
                        if len(text) > 30:
                            texts.append(text)
                if texts:
                    content_text = '\n\n'.join(texts)
                    break

        if content_text:
            content_text = re.sub(r'▶.*?\n', '', content_text)
            content_text = re.sub(r'\[.*?\]', '', content_text)
            content_text = re.sub(r'사진.*?\n', '', content_text)
            content_text = re.sub(r'\s+', ' ', content_text)
            content_text = content_text.strip()

        if len(content_text) > 100:
            print(f"BeautifulSoup 추출 성공: {len(content_text)}자")
            return content_text[:2000]
        else:
            print(f"BeautifulSoup 추출 실패: 텍스트가 너무 짧음")
            return None

    except Exception as e:
        print(f"BeautifulSoup 추출 오류: {e}")
        return None

# 테스트
if __name__ == "__main__":
    print("본문 추출 테스트...")

    # 실제 뉴스 사이트 URL로 테스트 (연합뉴스)
    test_url = "https://www.yna.co.kr/view/AKR20251223042400004?section=society/all&site=hot_news_view_swipe01"

    try:
        result = extract_news_content(test_url)
        if result:
            print(f"성공! 추출된 텍스트 길이: {len(result)}")
            print(f"미리보기: {result[:200]}...")
        else:
            print("추출 실패")
    except Exception as e:
        print(f"오류 발생: {e}")
        import traceback
        print(traceback.format_exc())
