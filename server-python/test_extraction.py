#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from main import extract_news_content

from googlenewsdecoder import new_decoderv1

def decode_google_news_url_simple(url: str) -> str:
    """가장 간단하고 효과적인 방법"""
    try:
        decoded = new_decoderv1(url)
        if decoded and decoded != url:
            print(f"✅ 디코딩 성공: {decoded}")
            return decoded
        else:
            print("❌ 디코딩 결과가 유효하지 않음")
    except Exception as e:
        print(f"💥 디코딩 실패: {e}")
    return url

# 테스트
google_news_url = 'https://news.google.com/rss/articles/CBMiZEFVX3lxTE1ZQWRTR3JmZ2thcW1tczcyMU5PUEFvT1NZdWVyLTN3RFdoZXNBT0g2eWpGc0IzOUx2Q2dmemVUd0N2V2FzX0pQZTFPN3VseTFqSlNnbDY0ZTJSRXhNSWhjM2ZjUFY?oc=5'

print('googlenewsdecoder 테스트')
result = decode_google_news_url_simple(google_news_url)
print(f'최종 결과: {result}')




