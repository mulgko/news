#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import base64
import re

# Google News RSS URL
google_news_url = 'https://news.google.com/rss/articles/CBMiZEFVX3lxTE1ZQWRTR3JmZ2thcW1tczcyMU5PUEFvT1NZdWVyLTN3RFdoZXNBT0g2eWpGc0IzOUx2Q2dmemVUd0N2V2FzX0pQZTFPN3VseTFqSlNnbDY0ZTJSRXhNSWhjM2ZjUFY?oc=5'

print('Google News RSS URL Base64 디코딩 분석')
print(f'원본 URL: {google_news_url}')

# Base64 부분 추출
match = re.search(r'/rss/articles/(CBMi[^?]+)', google_news_url)
if match:
    encoded_part = match.group(1)
    print(f'Base64 인코딩 부분: {encoded_part}')

    try:
        # 패딩 추가
        missing_padding = len(encoded_part) % 4
        if missing_padding:
            encoded_part += '=' * (4 - missing_padding)

        print(f'패딩 적용 후 길이: {len(encoded_part)} (원본: {len(match.group(1))})')

        # Base64 디코딩
        decoded_bytes = base64.urlsafe_b64decode(encoded_part)
        decoded_text = decoded_bytes.decode('utf-8', errors='replace')

        print(f'디코딩된 텍스트 길이: {len(decoded_text)}')
        print(f'디코딩된 텍스트 (전체):\n{decoded_text}')

        # 16진수 분석
        print(f'\n16진수 분석 (처음 100바이트):')
        hex_data = decoded_bytes[:100].hex()
        for i in range(0, len(hex_data), 32):
            print(f'  {i//2:04x}: {hex_data[i:i+32]}')

        # 바이너리 데이터 분석
        binary_count = sum(1 for b in decoded_bytes if b < 32 and b not in [9, 10, 13])
        print(f'바이너리/제어 문자: {binary_count}개 (총 {len(decoded_bytes)}바이트 중)')

        # URL 패턴 찾기 시도
        print('\nURL 패턴 검색...')

        url_patterns = [
            r'https?://[^\s\'"<>(){}\[\]]+',
            r'https?://[^\s\'"<>\s]+',
            r'https?://[^\s]+',
        ]

        found_urls = []
        for i, pattern in enumerate(url_patterns, 1):
            matches = re.findall(pattern, decoded_text)
            if matches:
                print(f'패턴 {i}: {len(matches)}개 URL 발견')
                for match in matches:
                    clean_url = re.sub(r'[<>,"\'\s]+$', '', match)
                    if clean_url not in found_urls:
                        found_urls.append(clean_url)
                        print(f'   -> {clean_url}')
            else:
                print(f'패턴 {i}: URL 없음')

        print(f'\n최종 결과: {len(found_urls)}개의 URL 후보 발견')

        # 각 URL의 유효성 검사
        for i, url in enumerate(found_urls, 1):
            is_valid = len(url) > 20 and 'google.com' not in url and url.startswith('http')
            status = 'VALID' if is_valid else 'INVALID'
            print(f'{i}. [{status}] {url[:80]}...')

    except Exception as e:
        print(f'Base64 디코딩 오류: {e}')
        import traceback
        print(traceback.format_exc())
else:
    print('CBMi 패턴을 찾을 수 없음')

print('\n' + '='*80)
print('분석 완료')
print('Google News RSS URL의 구조:')
print('1. /rss/articles/CBMi[base64_data]?oc=5&hl=ko&gl=KR&ceid=KR:ko')
print('2. CBMi 다음 부분이 Base64 인코딩된 데이터')
print('3. 디코딩 결과가 바이너리 데이터 + URL 정보')
print('4. 실제 뉴스 URL을 찾으려면 다른 디코딩 방식 필요')
