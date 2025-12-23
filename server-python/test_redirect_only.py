#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests
import re
import base64

def decode_google_news_url(url: str, session=None) -> str:
    """
    Google News URL 디코딩 (HTTP 리다이렉트 우선 방식)
    실제 뉴스 URL로 리다이렉트되는 특성을 활용
    """
    if not url or "google.com" not in url:
        return url

    try:
        # 1. HTTP 리다이렉트를 우선적으로 시도 (가장 효과적)
        if session is None:
            session = requests.Session()
            session.verify = False

        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7',
                'Referer': 'https://news.google.com/',
            }

            print(f"Google News URL 리다이렉트 추적 시작...")
            response = session.get(url, headers=headers, allow_redirects=True, timeout=15, verify=False)

            final_url = response.url
            if final_url != url and "google.com" not in final_url and final_url.startswith('http'):
                print(f"HTTP 리다이렉트 성공! 실제 뉴스 URL: {final_url[:80]}...")
                return final_url
            else:
                print(f"리다이렉트 결과가 유효하지 않음: {final_url[:60]}...")

        except Exception as redirect_error:
            print(f"HTTP 리다이렉트 실패: {redirect_error}")

        # 2. Base64 디코딩 시도 (보조 수단)
        match = re.search(r'/rss/articles/(CBMi[^?]+)', url)
        if match:
            encoded_part = match.group(1)
            print(f"Base64 디코딩 시도...")

            try:
                # 패딩 추가
                missing_padding = len(encoded_part) % 4
                if missing_padding:
                    encoded_part += '=' * (4 - missing_padding)

                decoded_bytes = base64.urlsafe_b64decode(encoded_part)
                decoded_text = decoded_bytes.decode('utf-8', errors='ignore')

                # URL 패턴 찾기
                url_patterns = [
                    r'https?://[^\s\'"<>(){}\[\]]+',
                    r'https?://[^\s\'"<>\s]+',
                ]

                for pattern in url_patterns:
                    matches = re.findall(pattern, decoded_text)
                    for match in matches:
                        real_url = re.sub(r'[<>,"\'\s]+$', '', match)
                        if len(real_url) > 20 and "google.com" not in real_url and real_url.startswith('http'):
                            print(f"Base64에서 URL 발견: {real_url[:80]}...")
                            return real_url

            except Exception as b64_error:
                print(f"Base64 디코딩 실패: {b64_error}")

        print(f"모든 디코딩 방법 실패, 원본 URL 사용")
        return url

    except Exception as e:
        print(f"URL 디코딩 오류: {e}, 원본 사용")
        return url

# 테스트
google_news_url = 'https://news.google.com/rss/articles/CBMiZEFVX3lxTE1ZQWRTR3JmZ2thcW1tczcyMU5PUEFvT1NZdWVyLTN3RFdoZXNBT0g2eWpGc0IzOUx2Q2dmemVUd0N2V2FzX0pQZTFPN3VseTFqSlNnbDY0ZTJSRXhNSWhjM2ZjUFY?oc=5'

session = requests.Session()
session.verify = False

print('Google News RSS URL 디코딩 테스트')
print(f'원본 URL: {google_news_url[:60]}...')

decoded_url = decode_google_news_url(google_news_url, session)
print(f'디코딩된 URL: {decoded_url[:60]}...')
print(f'성공 여부: {decoded_url != google_news_url}')

if decoded_url != google_news_url:
    print('성공! 실제 뉴스 URL을 찾았습니다.')
else:
    print('실패! 원본 URL과 동일합니다.')
