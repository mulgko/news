#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Google News RSS URL 처리 테스트

결론:
- Google News RSS URL은 HTTP 리다이렉트로 실제 뉴스 URL로 변환되지 않음
- Base64 디코딩으로는 바이너리 데이터밖에 얻을 수 없음
- 가장 현실적인 해결책: RSS 피드의 description을 뉴스 본문으로 사용

테스트 결과:
- Google News URL: 리다이렉트 실패, 본문 추출 실패
- 직접 뉴스 URL: 성공적으로 본문 추출 가능
"""

import requests

def extract_news_content_simple(url: str, session=None) -> str:
    """간단한 뉴스 본문 추출 (BeautifulSoup만 사용)"""
    try:
        if session is None:
            session = requests.Session()
            session.verify = False

        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        }

        response = session.get(url, headers=headers, timeout=20, verify=False, allow_redirects=True)
        response.raise_for_status()

        try:
            from bs4 import BeautifulSoup
        except ImportError:
            return "BeautifulSoup 미설치"

        soup = BeautifulSoup(response.content, 'html.parser')

        # 불필요한 요소 제거
        for element in soup.find_all(['script', 'style', 'nav', 'footer', 'header', 'aside']):
            element.decompose()

        # 본문 선택자들
        content_selectors = [
            'article', '[id*="article"]', '[class*="article"]',
            '[id*="content"]', '[class*="content"]',
            '#articleBody', '#newsct_article', '.article_body',
            '.news_body', 'div[itemprop="articleBody"]',
            '.article-content', 'main'
        ]

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
                    # 정리
                    import re
                    content_text = re.sub(r'▶.*?\n', '', content_text)
                    content_text = re.sub(r'\[.*?\]', '', content_text)
                    content_text = re.sub(r'사진.*?\n', '', content_text)
                    content_text = re.sub(r'\s+', ' ', content_text)
                    content_text = content_text.strip()

                    if len(content_text) > 100:
                        return content_text[:2000]

        return None

    except Exception as e:
        return f"오류: {e}"

# 테스트 URL들
google_news_url = 'https://news.google.com/rss/articles/CBMiZEFVX3lxTE1ZQWRTR3JmZ2thcW1tczcyMU5PUEFvT1NZdWVyLTN3RFdoZXNBT0g2eWpGc0IzOUx2Q2dmemVUd0N2V2FzX0pQZTFPN3VseTFqSlNnbDY0ZTJSRXhNSWhjM2ZjUFY?oc=5'
direct_url = 'https://www.ddaily.co.kr/page/view/2025122314214291723'

session = requests.Session()
session.verify = False

print('Google News RSS URL vs 직접 뉴스 URL 비교 테스트')
print('=' * 80)

# 1. Google News URL 테스트
print('1. Google News RSS URL 테스트')
print(f'URL: {google_news_url[:70]}...')

# HTTP 리다이렉트 테스트
print('HTTP 리다이렉트 시도...')
try:
    response = session.get(google_news_url, allow_redirects=True, timeout=10, verify=False)
    final_url = response.url
    print(f'최종 URL: {final_url[:80]}...')
    is_redirected = final_url != google_news_url and "google.com" not in final_url
    print(f'리다이렉트 성공: {is_redirected}')
except Exception as e:
    print(f'리다이렉트 실패: {e}')

# 본문 추출 테스트
print('본문 추출 시도...')
result = extract_news_content_simple(google_news_url, session)
if result and not result.startswith("오류"):
    print(f'성공! 길이: {len(result)}')
    print(f'미리보기: {result[:150]}...')
elif result and result.startswith("오류"):
    print(f'실패: {result}')
else:
    print('실패: 본문 없음')

print('\n' + '=' * 80)

# 2. 직접 뉴스 URL 테스트
print('2. 직접 뉴스 URL 테스트')
print(f'URL: {direct_url}')

result = extract_news_content_simple(direct_url, session)
if result and not result.startswith("오류"):
    print(f'성공! 길이: {len(result)}')
    print(f'미리보기: {result[:150]}...')
elif result and result.startswith("오류"):
    print(f'실패: {result}')
else:
    print('실패: 본문 없음')

print('\n' + '=' * 80)
print('결론:')
print('- Google News RSS URL: 본문 추출 불가능 (리다이렉트 실패)')
print('- 직접 뉴스 URL: 본문 추출 가능')
print('- 해결책: RSS 피드의 description을 뉴스 본문으로 사용')
