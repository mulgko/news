#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import feedparser
import requests

# Google News RSS URL 생성 (비즈니스 뉴스)
import urllib.parse
query = urllib.parse.quote("비즈니스 OR 경제 OR 기업 OR 금융")
rss_url = f"https://news.google.com/rss/search?q={query}&hl=ko&gl=KR&ceid=KR:ko"

print('Google News RSS 피드 파싱 테스트')
print(f'RSS URL: {rss_url}')

try:
    # RSS 피드 가져오기
    session = requests.Session()
    session.verify = False

    response = session.get(rss_url, timeout=10, verify=False)
    response.raise_for_status()

    # RSS 파싱
    feed = feedparser.parse(response.text)

    print(f'피드 제목: {getattr(feed.feed, "title", "No title")}')
    print(f'기사 개수: {len(feed.entries)}')

    # 첫 번째 기사 3개 분석
    for i, entry in enumerate(feed.entries[:3]):
        print(f'\n=== 기사 {i+1} ===')
        print(f'제목: {entry.title}')

        # 다양한 링크 정보 출력
        print(f'link: {getattr(entry, "link", "N/A")}')
        if hasattr(entry, 'links'):
            print(f'links: {[link.get("href", link.get("url", "N/A")) for link in entry.links]}')

        # URL이 Google News URL인지 확인
        link = getattr(entry, 'link', '')
        is_google_news = 'news.google.com' in link
        print(f'Google News URL 여부: {is_google_news}')

        if is_google_news:
            print(f'Google News URL 구조: {link[:80]}...')

            # 실제로 이 URL에 접근해보기
            try:
                print('실제 URL 접근 테스트...')
                test_response = session.get(link, allow_redirects=True, timeout=10, verify=False)
                final_url = test_response.url
                print(f'최종 리다이렉트 URL: {final_url[:100]}...')
                print(f'리다이렉트 성공: {final_url != link and "google.com" not in final_url}')
            except Exception as e:
                print(f'접근 실패: {e}')

except Exception as e:
    print(f'RSS 파싱 오류: {e}')
    import traceback
    traceback.print_exc()
