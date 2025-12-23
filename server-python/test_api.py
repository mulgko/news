#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests
import time

# 서버가 시작될 때까지 잠시 대기
time.sleep(3)

try:
    print("디코딩 API 서버 테스트 중...")

    # 헬스체크
    response = requests.get('http://127.0.0.1:5000/health', timeout=5)
    print('헬스체크 성공:', response.json())

    # 디코딩 테스트
    payload = {
        'source_url': 'https://news.google.com/rss/articles/CBMiZEFVX3lxTE1ZQWRTR3JmZ2thcW1tczcyMU5PUEFvT1NZdWVyLTN3RFdoZXNBT0g2eWpGc0IzOUx2Q2dmemVUd0N2V2FzX0pQZTFPN3VseTFqSlNnbDY0ZTJSRXhNSWhjM2ZjUFY?oc=5',
        'interval_time': 3
    }

    print("Google News URL 디코딩 요청...")
    response = requests.post('http://127.0.0.1:5000/decode/', json=payload, timeout=20)
    result = response.json()
    print('디코딩 결과:')
    print(f'   성공: {result.get("success", False)}')

    if result.get("success"):
        print(f'   원본 URL: {result.get("original_url", "")[:60]}...')
        print(f'   디코딩 URL: {result.get("decoded_url", "")[:60]}...')
    else:
        print(f'   오류: {result.get("error", "알 수 없는 오류")}')
        print(f'   폴백 URL: {result.get("fallback_url", "")[:60]}...')

except requests.exceptions.RequestException as e:
    print(f'서버 연결 실패: {e}')
    print('서버가 실행 중인지 확인하세요 (python google_decoder.py)')
except Exception as e:
    print(f'기타 오류: {e}')
    import traceback
    traceback.print_exc()
