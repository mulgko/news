#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import base64
import re
import requests
from main import extract_news_content

# Google News RSS URL
google_news_url = 'https://news.google.com/rss/articles/CBMiZEFVX3lxTE1ZQWRTR3JmZ2thcW1tczcyMU5PUEFvT1NZdWVyLTN3RFdoZXNBT0g2eWpGc0IzOUx2Q2dmemVUd0N2V2FzX0pQZTFPN3VseTFqSlNnbDY0ZTJSRXhNSWhjM2ZjUFY?oc=5'

direct_url = 'https://www.ddaily.co.kr/page/view/2025122314214291723'

print('🔬 Google News RSS URL Base64 디코딩 심층 분석')
print(f'📝 원본 URL: {google_news_url}')

# Base64 부분 추출
match = re.search(r'/rss/articles/(CBMi[^?]+)', google_news_url)
if match:
    encoded_part = match.group(1)
    print(f'🔍 Base64 인코딩 부분: {encoded_part}')

    try:
        # 패딩 추가
        missing_padding = len(encoded_part) % 4
        if missing_padding:
            encoded_part += '=' * (4 - missing_padding)

        print(f'📊 패딩 적용 후 길이: {len(encoded_part)} (원본: {len(match.group(1))})')

        # Base64 디코딩
        decoded_bytes = base64.urlsafe_b64decode(encoded_part)
        decoded_text = decoded_bytes.decode('utf-8', errors='replace')  # ignore 대신 replace로 변경

        print(f'📄 디코딩된 텍스트 길이: {len(decoded_text)}')
        print(f'📄 디코딩된 텍스트 (처음 300자):\n{decoded_text[:300]}')

        # 16진수 분석
        print(f'\n🔢 16진수 분석 (처음 50바이트):')
        hex_data = decoded_bytes[:50].hex()
        print(f'Hex: {hex_data}')

        # 바이너리 데이터 확인
        binary_chars = [b for b in decoded_bytes[:100] if b < 32 and b not in [9, 10, 13]]
        print(f'🔍 바이너리/특수 문자 포함: {len(binary_chars)}개 (총 {len(decoded_bytes[:100])}바이트 중)')

        # 다양한 URL 패턴 찾기
        print('\n🔍 URL 패턴 검색 시도...')

        # 더 넓은 패턴들
        patterns = [
            r'https?://[^\s\'"<>(){}\[\]]+',  # 더 엄격한 패턴
            r'https?://[^\s\'"<>\s]+',        # 중간 패턴
            r'https?://[^\s]+',               # 기본 패턴
            r'http://[^\s]+',                 # HTTP만
            r'https://[^\s]+',                # HTTPS만
        ]

        all_matches = []
        for i, pattern in enumerate(patterns, 1):
            matches = re.findall(pattern, decoded_text)
            if matches:
                print(f'✅ 패턴 {i} ({pattern[:30]}...): {len(matches)}개 발견')
                for j, match in enumerate(matches[:5]):  # 처음 5개
                    clean_match = re.sub(r'[<>,"\'\s]+$', '', match)  # 끝부분 정리
                    print(f'   {j+1}: {clean_match[:100]}...')
                    if clean_match not in all_matches:
                        all_matches.append(clean_match)
            else:
                print(f'❌ 패턴 {i}: 없음')

        print(f'\n🎯 총 {len(all_matches)}개의 고유 URL 후보')

        # 각 URL 테스트
        session = requests.Session()
        session.verify = False

        for i, candidate_url in enumerate(all_matches[:3], 1):  # 처음 3개만 테스트
            print(f'\n🧪 URL 후보 {i} 테스트: {candidate_url[:60]}...')
            try:
                result = extract_news_content(candidate_url, session)
                if result and len(result) > 100:
                    print(f'✅ 성공! 텍스트 길이: {len(result)}')
                    print(f'📝 미리보기: {result[:150]}...')
                    break  # 성공하면 중단
                else:
                    print('❌ 빈 결과 또는 너무 짧음')
            except Exception as e:
                print(f'💥 테스트 실패: {str(e)[:100]}...')

    except Exception as e:
        print(f'💥 Base64 디코딩 오류: {e}')
        import traceback
        print(traceback.format_exc())
else:
    print('❌ CBMi 패턴을 찾을 수 없음')

print('\n' + '='*80 + '\n')

# 직접 URL 비교 테스트
print('🧪 직접 뉴스 URL 테스트 (비교용)...')
try:
    session = requests.Session()
    session.verify = False
    result = extract_news_content(direct_url, session)
    if result:
        print(f'✅ 직접 URL 성공! 추출된 텍스트 길이: {len(result)}')
        print(f'📝 미리보기: {result[:200]}...')
    else:
        print('❌ 직접 URL 추출 실패')
except Exception as e:
    print(f'💥 직접 URL 오류 발생: {e}')
