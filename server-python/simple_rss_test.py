#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests
import re

# Google News RSS URL 생성 (비즈니스 뉴스)
import urllib.parse
query = urllib.parse.quote("비즈니스 OR 경제 OR 기업 OR 금융")
rss_url = f"https://news.google.com/rss/search?q={query}&hl=ko&gl=KR&ceid=KR:ko"

print('Google News RSS 피드 분석')
print(f'RSS URL: {rss_url}')

try:
    # RSS 피드 가져오기
    session = requests.Session()
    session.verify = False

    response = session.get(rss_url, timeout=10, verify=False)
    response.raise_for_status()

    rss_content = response.text
    print(f'RSS 내용 길이: {len(rss_content)}')

    # XML에서 item 태그 찾기
    item_pattern = r'<item>(.*?)</item>'
    items = re.findall(item_pattern, rss_content, re.DOTALL)

    print(f'발견된 기사 수: {len(items)}')

    # 첫 번째 기사 분석
    if items:
        first_item = items[0]
        print(f'\n첫 번째 기사 XML:\n{first_item[:500]}...')

        # link 태그 찾기
        link_match = re.search(r'<link>(.*?)</link>', first_item)
        if link_match:
            link = link_match.group(1).strip()
            print(f'\n추출된 링크: {link}')
            print(f'Google News URL 여부: {"news.google.com" in link}')

            if 'news.google.com' in link:
                print('Google News URL 구조 분석:')
                print(f'전체 URL: {link}')

                # URL 파라미터 분석
                from urllib.parse import urlparse, parse_qs
                parsed = urlparse(link)
                params = parse_qs(parsed.query)
                print(f'쿼리 파라미터: {params}')

                # 실제 리다이렉트 테스트
                print('\n실제 리다이렉트 테스트...')
                try:
                    redirect_response = session.get(link, allow_redirects=True, timeout=10, verify=False)
                    final_url = redirect_response.url
                    print(f'최종 URL: {final_url}')
                    print(f'리다이렉트 성공: {final_url != link and "google.com" not in final_url}')
                except Exception as e:
                    print(f'리다이렉트 실패: {e}')

except Exception as e:
    print(f'오류 발생: {e}')
    import traceback
    traceback.print_exc()
