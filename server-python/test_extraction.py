# #!/usr/bin/env python3
# # -*- coding: utf-8 -*-

# from main import extract_news_content

# from googlenewsdecoder import new_decoderv1

# def decode_google_news_url_simple(url: str) -> str:
#     """가장 간단하고 효과적인 방법"""
#     try:
#         decoded = new_decoderv1(url)
#         if decoded and decoded != url:
#             print(f"✅ 디코딩 성공: {decoded}")
#             return decoded
#         else:
#             print("❌ 디코딩 결과가 유효하지 않음")
#     except Exception as e:
#         print(f"💥 디코딩 실패: {e}")
#     return url

# # 테스트
# google_news_url = 'https://news.google.com/rss/articles/CBMiZEFVX3lxTE1ZQWRTR3JmZ2thcW1tczcyMU5PUEFvT1NZdWVyLTN3RFdoZXNBT0g2eWpGc0IzOUx2Q2dmemVUd0N2V2FzX0pQZTFPN3VseTFqSlNnbDY0ZTJSRXhNSWhjM2ZjUFY?oc=5'

# print('googlenewsdecoder 테스트')
# result = decode_google_news_url_simple(google_news_url)
# print(f'최종 결과: {result}')





#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests
import urllib3
import base64
import re

# SSL 경고 비활성화
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def decode_google_news_url(url: str) -> str:
    """
    Google News URL 디코딩 (googlenewsdecoder 없이)
    HTTP 리다이렉트 + Base64 디코딩 조합
    """
    if not url or "google.com" not in url:
        return url
    
    print(f"🔍 원본 URL: {url[:80]}...")
    
    # 방법 1: HTTP 리다이렉트 추적
    try:
        session = requests.Session()
        session.verify = False  # SSL 검증 비활성화
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7',
            'Accept-Encoding': 'gzip, deflate, br',
            'Referer': 'https://news.google.com/',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Cache-Control': 'max-age=0',
        }
        
        print("🌐 HTTP GET 요청 중...")
        response = session.get(
            url, 
            headers=headers, 
            allow_redirects=True, 
            timeout=15,
            verify=False
        )
        
        final_url = response.url
        print(f"📍 리다이렉트 결과: {final_url[:80]}...")
        
        # 유효한 뉴스 URL인지 확인
        if (final_url != url and 
            "google.com" not in final_url and 
            final_url.startswith('http') and
            len(final_url) > 30):
            print(f"✅ HTTP 리다이렉트 성공!")
            return final_url
        else:
            print(f"⚠️ 리다이렉트가 유효한 뉴스 URL로 이동하지 않음")
            
    except requests.exceptions.SSLError as ssl_err:
        print(f"🔐 SSL 오류 발생: {str(ssl_err)[:100]}...")
    except requests.exceptions.Timeout:
        print(f"⏱️ 타임아웃 발생")
    except Exception as e:
        print(f"⚠️ HTTP 요청 실패: {str(e)[:100]}...")
    
    # 방법 2: Base64 디코딩
    print("\n🔐 Base64 디코딩 시도...")
    try:
        match = re.search(r'/articles/(CBMi[^?]+)', url)
        if match:
            encoded_part = match.group(1)
            print(f"   인코딩된 부분 발견: {encoded_part[:50]}...")
            
            # 패딩 추가
            missing_padding = len(encoded_part) % 4
            if missing_padding:
                encoded_part += '=' * (4 - missing_padding)
            
            decoded_bytes = base64.urlsafe_b64decode(encoded_part)
            print(f"   디코딩된 바이트 수: {len(decoded_bytes)}")
            
            # 여러 인코딩으로 시도
            for encoding in ['utf-8', 'iso-8859-1', 'cp949', 'latin-1']:
                try:
                    decoded_text = decoded_bytes.decode(encoding, errors='ignore')
                    
                    # URL 패턴 찾기 (더 엄격한 패턴)
                    url_patterns = [
                        r'https?://(?:www\.)?[a-zA-Z0-9-]+\.[a-zA-Z]{2,}(?:/[^\s<>"{}|\\^`\[\]]*)?',
                        r'https?://[^\s<>"{}|\\^`\[\]]+',
                    ]
                    
                    for pattern in url_patterns:
                        urls = re.findall(pattern, decoded_text)
                        
                        for found_url in urls:
                            # URL 정리
                            clean_url = re.sub(r'[<>,"\'\s\x00-\x1f]+$', '', found_url)
                            
                            # 유효성 검사
                            if (len(clean_url) > 30 and 
                                "google.com" not in clean_url and
                                clean_url.startswith('http')):
                                print(f"✅ Base64에서 URL 추출 성공 ({encoding})!")
                                print(f"   추출된 URL: {clean_url}")
                                return clean_url
                                
                except UnicodeDecodeError:
                    continue
                except Exception as decode_err:
                    print(f"   {encoding} 디코딩 실패: {decode_err}")
                    
            print(f"⚠️ Base64 디코딩에서 유효한 URL을 찾지 못함")
                    
    except Exception as e:
        print(f"💥 Base64 디코딩 오류: {e}")
    
    print(f"\n❌ 모든 디코딩 방법 실패")
    return url


# 테스트
if __name__ == "__main__":
    google_news_url = 'https://news.google.com/rss/articles/CBMiZEFVX3lxTE1ZQWRTR3JmZ2thcW1tczcyMU5PUEFvT1NZdWVyLTN3RFdoZXNBT0g2eWpGc0IzOUx2Q2dmemVUd0N2V2FzX0pQZTFPN3VseTFqSlNnbDY0ZTJSRXhNSWhjM2ZjUFY?oc=5'
    
    print('=' * 100)
    print('Google News URL 디코딩 테스트 (직접 구현)')
    print('=' * 100)
    print()
    
    result = decode_google_news_url(google_news_url)
    
    print()
    print('=' * 100)
    print(f'최종 결과:')
    print(f'{result}')
    print('=' * 100)
    
    # 성공 여부 확인
    if result != google_news_url:
        print("\n🎉 디코딩 성공!")
    else:
        print("\n😔 디코딩 실패 - RSS description 사용 권장")