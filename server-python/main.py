from fastapi import FastAPI, HTTPException, Query, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, field_serializer
from datetime import datetime
from typing import Optional, List, AsyncGenerator, Dict
from contextlib import asynccontextmanager
import os
import sys  # 추가
from dotenv import load_dotenv
from googlenewsdecoder import new_decoderv1
from sqlalchemy import create_engine, Column, Integer, String, Text, TIMESTAMP, func
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker, Session
import uvicorn
import feedparser
import requests
from bs4 import BeautifulSoup
import time
import re
import trafilatura

# 간단 버전에서는 기본 세션만 사용
session = requests.Session()

def get_sort_key(article):
    """기사 정렬을 위한 키 함수 - 최신순 정렬"""
    published_date = article.get("publishedAt", "")
    if published_date:
        try:
            # 이미 ISO format이므로 바로 파싱
            if published_date.endswith('Z'):
                published_date = published_date.replace('Z', '+00:00')
            return datetime.fromisoformat(published_date)
        except Exception as e:
            print(f"⚠️ Date parsing error for article: {article.get('title', '')[:30]}... - {e}")
            return datetime.min
    return datetime.min


def decode_google_news_url(url: str, session=None) -> str:
    """
    Google News URL 디코딩 (googlenewsdecoder 라이브러리 사용)
    가장 간단하고 효과적인 방법
    """
    if not url or "google.com" not in url:
        return url

    try:
        decoded = new_decoderv1(url)
        # new_decoderv1이 딕셔너리를 반환하는 경우 처리
        if isinstance(decoded, dict):
            if decoded.get('status') == True and decoded.get('decoded_url'):
                print(f"✅ 디코딩 성공: {decoded['decoded_url']}")
                return decoded['decoded_url']
            else:
                print(f"❌ 디코딩 실패: {decoded.get('message', 'Unknown error')}")
        # 문자열을 반환하는 경우 처리
        elif isinstance(decoded, str) and decoded and decoded != url:
            print(f"✅ 디코딩 성공: {decoded}")
            return decoded
        else:
            print("❌ 디코딩 결과가 유효하지 않음")
    except Exception as e:
        print(f"💥 디코딩 실패: {e}")

    return url

def extract_news_content(article_url: str, session=None) -> str:
    """
    개선된 뉴스 본문 추출 (BeautifulSoup 우선)
    Google News URL 디코딩 후 본문 자동 추출
    """
    try:
        # 법률신문 특화 처리 (CSS 클래스명에 의존하지 않는 안정적인 방법)
        if 'lawtimes' in article_url.lower():
            response = session.get(article_url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10, verify=False)
            soup = BeautifulSoup(response.content, 'html.parser')

            # 방법 1: Next.js __next 컨테이너 안에서 뉴스 콘텐츠 패턴 찾기
            next_container = soup.select('#__next')
            if next_container:
                next_div = next_container[0]

                # 뉴스 콘텐츠 특징: 긴 텍스트 + 뉴스 키워드 + 짧은 형제 요소들
                all_child_divs = next_div.find_all('div', recursive=False)

                for child_div in all_child_divs:
                    child_text = child_div.get_text(strip=True)

                    # 뉴스 콘텐츠 감지 조건
                    if (200 <= len(child_text) <= 400 and  # 적절한 길이
                        any(keyword in child_text for keyword in ['기업', '인공지능', 'AI', '교육']) and  # 뉴스 키워드
                        '2025-' in child_text and  # 날짜 패턴
                        '댓글' in child_text):  # 댓글 섹션

                        print(f"✅ 법률신문 구조 기반 추출 성공: {len(child_text)}자")
                        return child_text[:8000]  # 최대 길이 제한 늘림

            # 방법 2: 큰 뉴스 콘텐츠 우선 찾기 (수정됨)
            all_divs = soup.find_all('div')

            # 1단계: 큰 콘텐츠(800자 이상) 우선 찾기 (키워드 검사 완화)
            large_content_candidates = []
            for div in all_divs:
                text = div.get_text(strip=True)
                text_len = len(text)

                if text_len >= 800:  # 큰 콘텐츠 우선 (기준 낮춤)
                    # 뉴스 콘텐츠 가능성 평가 (키워드 필수 아님, 콘텐츠 품질로 판단)
                    has_news_keywords = any(keyword in text for keyword in ['더존비즈온', 'AI', '연말정산', '기업', '인공지능', '기술', '사업', '시장', '개발'])
                    has_news_indicators = (
                        has_news_keywords or  # 뉴스 키워드 포함
                        ('2025' in text or '2024' in text) or  # 날짜 포함
                        ('기자' in text and '@' in text) or  # 기자 정보
                        len([s for s in text.split('.') if len(s.strip()) > 10]) >= 3  # 3문장 이상
                    )

                    if has_news_indicators:
                        # 뉴스 콘텐츠 일반 품질 점수 계산 (범용적)
                        # 문장 수, 단어 다양성, 기본 뉴스 키워드 등으로 평가
                        sentences = [s.strip() for s in text.replace('。', '.').replace('！', '!').replace('？', '?').split('.') if s.strip()]
                        sentence_count = len(sentences)

                        words = text.split()
                        unique_words = len(set(words))

                        content_score = 0
                        content_length = len(text)

                        # 대용량 콘텐츠(1000자 이상)의 경우 다른 평가 기준
                        if content_length >= 1000:
                            # 대용량 콘텐츠: 길이 기반으로 높은 점수 부여
                            content_score += 70  # 기본 70점 (대용량 자체로 높은 점수)

                            # 뉴스 기사 일반 패턴으로 추가 점수
                            # 날짜 패턴 포함
                            if '2025-' in text or '2024-' in text:
                                content_score += 10  # 날짜 포함시 +10점

                            # 뉴스 관련 일반 단어 포함 (기업, 기술, 사업 등)
                            general_news_words = ['기업', '기술', '시장', '사업', '개발', '서비스', '데이터', '시스템']
                            general_word_count = sum(1 for word in general_news_words if word in text)
                            content_score += min(general_word_count * 2, 10)  # 최대 +10점

                            # 문장 구조 점수 (대용량인데도 적절한 문장 수)
                            if sentence_count >= 8:
                                content_score += 10
                            elif sentence_count >= 5:
                                content_score += 5

                        else:
                            # 일반 콘텐츠: 기존 평가 방식
                            # 문장 수 점수
                            if sentence_count >= 8:
                                content_score += 40
                            elif sentence_count >= 5:
                                content_score += 20
                            elif sentence_count >= 3:
                                content_score += 10

                            # 단어 다양성 점수
                            if unique_words >= 150:
                                content_score += 30
                            elif unique_words >= 100:
                                content_score += 15
                            elif unique_words >= 50:
                                content_score += 5


                        # 길이 보너스 (더 긴 콘텐츠일수록 우선)
                        length_bonus = min(text_len // 500, 10)  # 최대 10점 보너스

                        total_score = content_score + length_bonus
                        large_content_candidates.append((div, text, total_score, content_score))

            if large_content_candidates:
                # 가장 긴 콘텐츠를 우선 선택 (점수도 고려)
                best_large = max(large_content_candidates, key=lambda x: (len(x[1]), x[2]))  # 길이 우선, 그 다음 점수
                div, text, score, content_score = best_large

                print(f"✅ 법률신문 대용량 뉴스 콘텐츠 추출 성공: {len(text)}자 (내용점수: {content_score})")
                return text[:8000]  # 최대 길이 제한 늘림

            # 2단계: 큰 콘텐츠가 없으면 작은 콘텐츠 찾기 (fallback)
            print("⚠️ 큰 뉴스 콘텐츠를 찾지 못해 작은 콘텐츠로 fallback")
            small_candidates = []
            for div in all_divs:
                text = div.get_text(strip=True)
                text_len = len(text)

                has_essential_keywords = any(keyword in text for keyword in ['더존비즈온', 'AI', '연말정산'])

                if has_essential_keywords and 200 <= text_len <= 500:  # 중간 크기
                    small_candidates.append((div, text))

            if small_candidates:
                # 가장 긴 중간 크기 콘텐츠 선택
                best_small = max(small_candidates, key=lambda x: len(x[1]))
                div, text = best_small

                print(f"✅ 법률신문 중간 크기 뉴스 콘텐츠 추출 성공: {len(text)}자")
                return text[:8000]  # 최대 길이 제한 늘림

            # 방법 3: 기존 CSS 선택자들 시도 (fallback)
            fallback_selectors = [
                '.css-1t61h32',
                '[class*="e4yx7rl4"]',
                '[class*="css-"]'
            ]

            for selector in fallback_selectors:
                elements = soup.select(selector)
                if elements:
                    for elem in elements:
                        text = elem.get_text(strip=True)
                        if (200 <= len(text) <= 400 and
                            any(keyword in text for keyword in ['기업', '인공지능', 'AI'])):
                            print(f"✅ 법률신문 fallback 추출 성공: {len(text)}자")
                            return text[:8000]  # 최대 길이 제한 늘림

        # 1. Google News URL 디코딩
        real_url = decode_google_news_url(article_url, session)

        if not real_url:
            print(f"URL 처리 실패: {article_url}")
            return None

        # Google News URL인 경우에도 시도 (리다이렉트될 것임)
        target_url = real_url if real_url != article_url else article_url

        # 2. BeautifulSoup로 우선 추출 시도 (더 안정적)
        print(f"BeautifulSoup로 본문 추출 시도: {target_url[:80]}...")
        result = _extract_with_beautifulsoup(target_url, session)
        if result:
            # 뉴시스 스타일 콘텐츠 자동 감지 및 필터링 적용
            result = clean_news_content(result)
            # summary 기반 필터링은 fetch_and_store_news에서 수행
            return result

        # 3. BeautifulSoup 실패시 Trafilatura 대안 시도
        print(f"BeautifulSoup 실패, Trafilatura 대안 시도")
        downloaded = trafilatura.fetch_url(target_url)

        if not downloaded:
            print(f"페이지 다운로드 실패: {target_url}")
            return None

        # 본문 텍스트 추출 (정밀 모드, 댓글 제외)
        text = trafilatura.extract(
            downloaded,
            output_format='txt',
            include_comments=False,
            favor_precision=True
        )

        if text and len(text.strip()) > 100:
            # 뉴시스 스타일 콘텐츠 자동 감지 및 필터링 적용
            cleaned_text = clean_news_content(text)
            if cleaned_text and len(cleaned_text) > 100:
                print(f"Trafilatura 추출 성공: {len(cleaned_text)}자")
                return cleaned_text[:4000]  # 길이 제한
        else:
            print(f"Trafilatura 추출 실패")
            return None

    except Exception as e:
        print(f"본문 추출 오류: {e}")
        # 최종 Fallback: BeautifulSoup 재시도
        try:
            return _extract_with_beautifulsoup(target_url, session)
        except Exception as fallback_e:
            print(f"Fallback도 실패: {fallback_e}")
            return None


def _is_newsis_style_content(content: str) -> bool:
    """
    콘텐츠가 뉴시스 스타일인지 자동 감지
    (메인 기사 + 다른 뉴스 헤드라인이 섞인 형태)
    """
    import re

    # 뉴시스 스타일의 특징적인 패턴들
    unwanted_patterns = [
        r'박나래.*매니저',
        r'입짧은햇님.*다이어트약',
        r'이지훈.*유산',
        r'배우 박정수.*갑상선암',
        r'삼성전자.*화재',
        r'정청래.*통일교',
        r'김계리.*내란 특검',
        r'국힘.*내란재판부법',
        r'뉴욕증시.*GDP',
        r'트럼프.*관세.*연준',
        r'술 마신 다음 날.*국밥',
        r'서학개미.*양도세',
        r'돌반지.*금값',
        r'산타랠리.*비트코인',
        r'이재용.*주식 가치',
        r'박나래.*매니저',
        r'이지훈.*유산',
        r'입짧은햇님.*다이어트약',
        r'베일 벗는.*보스턴',
        r'기부하러 가다 참변',
        r'마약 혐의.*남양유업',
        r'근로감독관',
        r'희토류.*배터리',
        r'K-소비재.*수출동력',
        r'허위정보근절법',
        r'중국산 반도체.*관세',
        r'인생샷.*중국 여성',
        r'유류세.*인하',
        r'치솟는 환율',
        r'외환당국.*구두개입',
        r'엔켐.*CATL',
        r'성과급도 경쟁',
        r'구윤철.*할인',
        r'입주.*반토막',
        r'CES.*K뷰티테크',
        r'중국.*인도.*헬스케어',
        r'지젤 번천.*불륜',
        r'류석문.*현대오토에버',
        r'주사 대신.*비만치료제',
        r'검찰.*조두순',
        r'법원.*김용현',
        r'경찰청.*신한카드',
        r'새벽.*올림픽선수촌아파트',
        r'서울 시내버스.*파업',
        r'4인 가족.*무주택',
        r'서울시.*국가유산청',
        r'직구.*초저가',
        r'KTX.*논산훈련소',
        r'청주서.*시내버스',
        r'경찰.*수의계약',
        r'김해가야테마파크',
        r'제주.*흐리고',
        r'김해공항.*승객',
        r'케데헌.*이건희',
        r'줄 서는 미술관',
        r'워커힐.*관광진흥',
        r'원불교.*기록유산',
        r'작가 몰리나르',
        r'퇴계 이황.*과거',
        r'간판 송성문',
        r'복근.*호날두',
        r'홍명보호.*남아공',
        r'오타니.*돈치치',
        r'프로축구 제주',
        r'MLB.*하퍼',
        r'EPL.*아스널',
        r'한예슬.*미모',
        r'이상민.*결혼',
        r'최태웅.*학폭',
        r'손태진.*가짜뉴스',
        r'이경실.*조혜련'
    ]

    # 불필요한 패턴들의 출현 빈도 계산
    short_headlines = 0
    for pattern in unwanted_patterns:
        matches = len(re.findall(pattern, content, re.IGNORECASE))
        short_headlines += matches

    # 뉴시스 스타일 판단: 불필요한 패턴이 3개 이상이면 뉴시스 스타일
    # (임계값을 낮춰서 뉴시스와 비슷한 구조의 다른 사이트들도 감지)
    return short_headlines >= 3


def _filter_newsis_content(content: str) -> str:
    """
    뉴시스 기사에서 메인 콘텐츠와 다른 뉴스 헤드라인 분리 (뉴시스 전용)
    더 안전하고 구조적인 접근법 사용
    """
    import re

    # 뉴시스 기사에서 다른 뉴스 헤드라인을 식별하는 패턴
    # 뉴시스 기사에서는 다른 뉴스들이 큰따옴표로 시작하는 짧은 텍스트로 나타남
    # 예: "박나래, 매니저에 샤넬백·시계 선물"…인증샷 있었다

    # 1. 큰따옴표로 둘러싸인 짧은 헤드라인 패턴 찾기 및 제거
    # 이 패턴은 뉴시스 기사에서만 나타나는 구조적 특징
    headline_pattern = r'"[^"]{10,80}"[^"]{0,50}(?:있었다|못 들어|사례도|관심↑|했다|조사|출동|갔나|차|매달려|발표도|-NYT|목표|통과|경신|뒤|해야|법|뻔|지원|까지|운영|경신|될 것|계약|머물러|하나|확대|직격탄|1위|관심|도래|축하|전무|돌입|구형|우려|착수|이송|결렬|구멍|수도|품|고시|부상|의혹|이벤트|16도|선물은|차|최다|표창|권|이다|확인|먹구름|비결은|령|우승|선임|구축|진출|있었다|활짝|아냐|응|없어|겨웠다)'
    content = re.sub(headline_pattern, '', content, flags=re.MULTILINE)

    # 2. 남은 다른 짧은 뉴스 패턴들 정리 (더 일반적인 패턴)
    # 하지만 뉴시스 기사 맥락에서만 나타나는 패턴들만
    additional_patterns = [
        r'베일 벗는 보스턴 다이내믹스[^\\n]{0,50}',
        r'마약 혐의 남양유업[^\\n]{0,50}',
        r'삼성전자 화성캠퍼스[^\\n]{0,50}',
        r'대통령실 공식명칭[^\\n]{0,50}',
    ]

    for pattern in additional_patterns:
        content = re.sub(pattern, '', content, flags=re.MULTILINE | re.IGNORECASE)

    # 3. 정리: 연속된 공백과 빈 줄 정리
    content = re.sub(r'\n{3,}', '\n\n', content)
    content = re.sub(r'[ \t]+', ' ', content)
    content = content.strip()

    return content


def filter_content_by_summary(content: str, summary: str) -> str:
    """
    summary와 관련된 내용을 우선적으로 포함하되, 적절한 길이 유지
    """
    if not content or not summary:
        return content

    # summary의 핵심 키워드 추출
    summary_words = set(word for word in re.findall(r'\w+', summary.lower()) if len(word) > 1)

    # content를 문장 단위로 분리
    sentences = re.split(r'[.!?]\s+', content)

    # 각 문장과 summary의 유사도 계산
    scored_sentences = []
    for sentence in sentences:
        sentence = sentence.strip()
        if len(sentence) < 10:
            continue

        sentence_words = set(word for word in re.findall(r'\w+', sentence.lower()) if len(word) > 1)
        common_words = summary_words.intersection(sentence_words)

        # 유사도 점수 계산 (Jaccard 유사도)
        if len(sentence_words.union(summary_words)) > 0:
            similarity = len(common_words) / len(sentence_words.union(summary_words))
            scored_sentences.append((sentence, similarity))

    # 유사도 순으로 정렬
    scored_sentences.sort(key=lambda x: x[1], reverse=True)

    # 전략적 선택:
    # 1. 유사도가 높은 문장들 (summary 확장)
    # 2. 중간 유사도의 문장들 (맥락 제공)
    # 3. 낮은 유사도라도 뉴스 콘텐츠로 보이는 문장들 (길이 확보)

    selected_sentences = []
    high_similarity = [s for s, sim in scored_sentences if sim >= 0.2]  # 매우 관련된 내용
    medium_similarity = [s for s, sim in scored_sentences if 0.1 <= sim < 0.2]  # 어느 정도 관련된 내용
    low_similarity = [s for s, sim in scored_sentences if sim < 0.1]  # 덜 관련된 내용

    # 우선순위에 따라 선택
    selected_sentences.extend(high_similarity[:3])  # 최대 3개 고유사도 문장
    selected_sentences.extend(medium_similarity[:2])  # 최대 2개 중간 유사도 문장

    # 길이가 너무 짧으면 저유사도 문장도 추가 (최대 300자 목표)
    current_length = len('. '.join(selected_sentences))
    if current_length < 200 and low_similarity:
        for sentence in low_similarity[:3]:  # 최대 3개 저유사도 문장
            if current_length + len(sentence) < 400:  # 총 길이 제한
                selected_sentences.append(sentence)
                current_length += len(sentence) + 2

    # 중복 제거
    unique_sentences = []
    seen = set()
    for sentence in selected_sentences:
        if sentence not in seen:
            unique_sentences.append(sentence)
            seen.add(sentence)

    # 결과 조합
    if unique_sentences:
        result = '. '.join(unique_sentences)
        if not result.endswith('.'):
            result += '.'
        return result
    else:
        return summary


def clean_news_content(content: str, summary: str = None) -> str:
    """
    뉴스 본문에서 불필요한 요소만 제거하고 원본 콘텐츠 유지
    뉴시스 스타일 콘텐츠(메인 기사 + 다른 뉴스 헤드라인 섞임) 자동 감지
    """
    if not content:
        return ""

    # HTML 태그가 포함된 경우 텍스트만 추출
    try:
        from bs4 import BeautifulSoup
        if '<' in content and '>' in content:
            soup = BeautifulSoup(content, 'html.parser')
            content = soup.get_text()
    except ImportError:
        pass

    # 뉴시스 스타일 콘텐츠인지 자동 감지
    if _is_newsis_style_content(content):
        content = _filter_newsis_content(content)

    # DAILY NEWS 처리 (기존 로직 유지)
    content = re.sub(r'DAILY NEWS', '\nDAILY NEWS', content)
    content = re.sub(r'\n+', '\n', content)

    lines = content.split('\n')
    cleaned_lines = []
    seen_daily_news = set()

    for line in lines:
        line = line.strip()
        if not line:
            cleaned_lines.append('')
            continue

        if line.startswith('DAILY NEWS'):
            headline_content = line.replace('DAILY NEWS', '').strip()
            if headline_content and headline_content not in seen_daily_news:
                seen_daily_news.add(headline_content)
                cleaned_lines.append(line)
        else:
            cleaned_lines.append(line)

    content = '\n'.join(cleaned_lines)

    # 1. 불필요한 패턴 제거 (더 정확한 패턴)
    remove_patterns = [
        # 광고 관련
        r'▶[^\n]*?(?:광고|배너|팝업|프로모션)[^\n]*?\n',
        r'\[광고\][^\n]*?\n',
        r'ADVERTISEMENT[^\n]*?\n',
        r'모바일\s+앱에서\s+더\s+많은\s+혜택을\s+누리세요[^\n]*?\n',

        # 소셜 공유 버튼
        r'공유하기\s+페이스북\s+트위터\s+카카오톡[^\n]*?\n',
        r'페이스북\s+공유\s+트위터\s+공유\s+카카오톡\s+공유[^\n]*?\n',

        # 추천/반대 버튼
        r'추천\d+\s+반대\d+[^\n]*?\n',

        # 저작권 표시
        r'저작권자.*?(?:무단|©|ⓒ)[^\n]*?\n',
        r'Copyright[^\n]*?\n',

        # 기자 정보 (더 정확하게)
        r'기자\s+[^\n]*?@[^\n]*?\.[^\n]*?\n',

        # 모바일 앱/다운로드 유도
        r'모바일\s+앱.*다운로드[^\n]*?\n',
        r'앱\s+다운로드[^\n]*?\n',

        # 로그인/회원가입 유도
        r'로그인\s+후.*보세요[^\n]*?\n',
        r'회원가입.*혜택[^\n]*?\n',

        # 관련 상품/이벤트
        r'관련\s+상품[^\n]*?\n',
        r'이벤트\s+참여[^\n]*?\n',

        # 추가 불필요 패턴들
        r'사진\s*=\s*[^\n]*?\n',
        r'영상\s*=\s*[^\n]*?\n',
        r'사진\s*\([^\)]*\)\s*=\s*[^\n]*?\n',
    ]

    for pattern in remove_patterns:
        content = re.sub(pattern, '', content, flags=re.IGNORECASE | re.MULTILINE)

    # 2. 기본 정리
    content = re.sub(r'[ \t]+', ' ', content)  # 연속 공백 정리
    content = re.sub(r'\n{3,}', '\n\n', content)  # 연속 개행 정리
    content = content.strip()

    # 3. 최소 길이 확인
    if len(content) < 20:
        return ""

    return content


def _extract_with_beautifulsoup(url: str, session=None) -> str:
    """
    BeautifulSoup를 사용한 대안 본문 추출
    Trafilatura 실패시 사용
    """
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

        # SSL 검증 완전 우회 및 타임아웃 증가 - 강화된 SSL 처리
        try:
            response = session.get(url, headers=headers, timeout=20, verify=False, allow_redirects=True)
            response.raise_for_status()
        except Exception as ssl_error:
            print(f"⚠️ SSL 오류 발생, 인증서 검증 완전 우회 시도: {ssl_error}")
            try:
                import ssl
                response = session.get(
                    url,
                    headers=headers,
                    timeout=20,
                    verify=False,
                    allow_redirects=True,
                    cert_reqs=ssl.CERT_NONE
                )
                response.raise_for_status()
            except Exception as fallback_error:
                print(f"💥 SSL 우회 실패: {fallback_error}")
                raise fallback_error

        soup = BeautifulSoup(response.content, 'html.parser')

        # 불필요한 요소 제거 (더 엄격하게)
        for element in soup.find_all(['script', 'style', 'nav', 'footer', 'header', 'aside', 'sidebar', 'related', 'recommend']):
            element.decompose()

        # 추가로 클래스/아이디 기반 제거
        for element in soup.find_all(attrs={'class': lambda x: x and any(term in x.lower() for term in ['sidebar', 'related', 'recommend', 'ad', 'banner', 'popup'])}):
            element.decompose()
        for element in soup.find_all(attrs={'id': lambda x: x and any(term in x.lower() for term in ['sidebar', 'related', 'recommend', 'ad', 'banner', 'popup'])}):
            element.decompose()

        # 한국 뉴스/매거진 사이트용 본문 선택자들 (확장)
        content_selectors = [
            # 법률신문 등 React/Next.js 기반 사이트 (최우선! - 가장 구체적 선택자 먼저)
            '.css-1t61h32',  # 법률신문 뉴스 콘텐츠 (가장 정확함!)
            '[class*="css-1t61h32"]',  # 법률신문 뉴스 콘텐츠 (패턴)
            '[class*="css-"][class*="e4yx7rl4"]',  # 법률신문 뉴스 콘텐츠 패턴

            # 뉴스 사이트 (우선순위 높음)
            'article',
            '[id*="article"]',
            '[class*="article"]',
            '#articleBody',
            '#newsct_article',
            '.article_body',
            '.news_body',
            'div[itemprop="articleBody"]',
            '.article-content',

            # 뉴시스 등 특정 사이트용
            '.news_article',
            '.news_content',
            '.article_view',
            '.content_view',

            # 딜사이트 같은 사이트용 (중요!)
            '.read-news-main-contents',
            '.contents.small-top',
            '.content-main',

            # 일반 React/Next.js 기반 사이트 (더 일반적인 패턴은 뒤로)
            '[class*="css-"][class*="e1bre4in1"]',  # 법률신문 메인 콘텐츠
            '.css-1spzpv0',  # 법률신문 특정 클래스
            '[class*="css-"]',  # React/Next.js CSS 모듈 패턴

            # 일반 뉴스 콘텐츠
            '[id*="content"]',
            '[class*="content"]',

            # 매거진/블로그 사이트
            '.post-content',
            '.entry-content',
            '.content-area',
            '.article-body',
            '.article__content',
            '.post-body',
            '.entry-body',
            '.content-body',
            '.main-content',
            '.article-main',
            '.post-main',

            # 일반적인 콘텐츠 영역
            'main',
            '.main',
            '[role="main"]',
            '.content',
            '.post',
            '.entry',
            '.article-wrapper',
            '.content-wrapper',

            # 추가 선택자들
            '[data-content]',
            '.story-content',
            '.article-text',
            '.post-text',
            '.entry-text',
            '.article-detail',
            '.news-content',
            '.magazine-content'
        ]

        content_text = ""
        best_content = ""
        best_score = 0

        # 조선일보 특화 처리
        if 'chosun.com' in url.lower():
            print("📰 조선일보 사이트 감지 - 특화 추출 시도")

            # 조선일보 전용 선택자들
            chosun_selectors = [
                '.article-body',
                '.news_body',
                '.news-article',
                '[class*="article-body"]',
                '[class*="news_body"]',
                '.content',
                '.article-content',
                '.news-content'
            ]

            for selector in chosun_selectors:
                elements = soup.select(selector)
                if elements:
                    for elem in elements:
                        # 불필요한 요소 제거
                        for sub_elem in elem.find_all(['script', 'style', 'aside', 'nav', 'footer']):
                            sub_elem.decompose()

                        text = elem.get_text(strip=True)
                        if len(text) > 200:  # 적절한 길이의 콘텐츠
                            print(f"✅ 조선일보 특화 추출 성공: {len(text)}자")
                            content_text = clean_news_content(text)
                            if len(content_text) > 100:
                                return content_text[:4000]
            print("⚠️ 조선일보 특화 선택자 모두 실패")

        # 뉴시스 특화 로직은 extract_news_content 함수에서 처리하므로 여기서는 제거

        # 뉴시스 스타일 사이트 감지 및 특화 처리
        # 뉴시스뿐만 아니라 비슷한 구조의 사이트에서도 적용
        articles = soup.find_all('article')
        if len(articles) > 10:  # 많은 article 요소가 있는 사이트
            # 각 article의 텍스트를 분석해서 뉴시스 스타일인지 확인
            article_texts = [art.get_text(strip=True) for art in articles]

            # 뉴시스 스타일 감지 (여러 짧은 헤드라인 + 긴 메인 콘텐츠)
            short_headlines = len([text for text in article_texts if len(text) < 50])
            long_content = len([text for text in article_texts if len(text) > 200])

            if short_headlines > 5 and long_content >= 1:  # 뉴시스 스타일 패턴
                # 뉴시스 키워드가 포함된 가장 긴 콘텐츠 선택
                main_content = ""
                for text in article_texts:
                    if len(text) > len(main_content) and len(text) > 200:  # 긴 콘텐츠 우선
                        main_content = text

                if main_content:
                    # 뉴시스 스타일 필터링 적용
                    content_text = clean_news_content(main_content)
                    if len(content_text) > 100:
                        print(f"✅ 뉴시스 스타일 사이트 감지 및 추출 성공: {len(content_text)}자")
                        return content_text[:4000]

        # 일반적인 선택자 시도
        selectors_to_try = [
            '.css-1t61h32',  # 법률신문 뉴스 콘텐츠 (최우선!)
            '.articleView',  # 뉴시스 메인 콘텐츠
            '[class*="articleView"]',  # articleView 클래스 포함
            '[class*="article"]',  # article 클래스 포함
            'article',  # 일반 article 태그
            '.contents',  # 뉴시스 콘텐츠 영역
            '.news_content',  # 뉴시스 전용
            '.article_body',  # 뉴시스 본문
            # 조선일보 추가 선택자들
            '.article-body',  # 조선일보 본문
            '.news_body',  # 조선일보 뉴스 본문
            '.news-article',  # 조선일보 뉴스 기사
        ] + content_selectors

        for selector in selectors_to_try:
            if content_text:  # 이미 콘텐츠를 찾았으면 중단
                break

            elements = soup.select(selector)
            if elements:
                texts = []
                seen_texts = set()  # 중복 제거를 위한 집합

                for elem in elements:
                    # article 태그의 경우 추가 정제
                    if selector == 'article':
                        # article 안에서 사이드바, 관련 뉴스 등 제거
                        for sub_elem in elem.find_all(['aside', 'div']):
                            if (sub_elem.get('class') and any(term in ' '.join(sub_elem.get('class')).lower()
                                                             for term in ['sidebar', 'related', 'recommend', 'ad', 'banner', 'widget'])) or \
                               (sub_elem.get('id') and any(term in sub_elem.get('id').lower()
                                                          for term in ['sidebar', 'related', 'recommend', 'ad', 'banner'])):
                                sub_elem.decompose()

                    # 1. p 태그 우선 추출 (뉴스 본문의 핵심)
                    p_tags = elem.find_all('p')
                    for p in p_tags:
                        text = p.get_text(strip=True)
                        if len(text) > 15:  # p 태그는 더 짧은 텍스트도 허용
                            text_hash = hash(text.strip())
                            if text_hash not in seen_texts:
                                seen_texts.add(text_hash)
                                texts.append(text)

                    # 2. p 태그가 부족하면 다른 태그들도 추출 (보충)
                    if len(texts) < 3:  # p 태그로 충분한 콘텐츠를 확보하지 못한 경우
                        other_tags = elem.find_all(['div', 'span', 'li', 'h2', 'h3', 'h4'])
                        for tag in other_tags:
                            text = tag.get_text(strip=True)
                            # 더 엄격한 필터링 (광고성 텍스트 제외)
                            if (len(text) > 25 and
                                not any(skip_word in text.lower() for skip_word in
                                       ['광고', '배너', '팝업', '공유', '추천', '저작권', 'copyright', '로그인', '회원가입'])):
                                text_hash = hash(text.strip())
                                if text_hash not in seen_texts:
                                    seen_texts.add(text_hash)
                                    texts.append(text)

                if texts:
                    current_content = '\n\n'.join(texts)
                    current_length = len(current_content)

                    # p 태그 비율로 품질 평가 (p 태그가 많을수록 뉴스 콘텐츠일 가능성 높음)
                    p_tag_count = len([t for t in texts if len(t.split()) > 10])  # 긴 문장 수
                    p_ratio = p_tag_count / max(1, len(texts))

                    # 콘텐츠 품질 평가 (길이 + p 태그 비율 + 텍스트 밀도)
                    text_density = current_length / max(1, len(texts))
                    score = current_length * 0.5 + p_ratio * 100 + text_density * 0.2

                    # 긴 콘텐츠를 우선시하되, 품질도 고려
                    if current_length > 150 and score > best_score:
                        best_content = current_content
                        best_score = score

        content_text = best_content if best_content else content_text

        # 강력한 콘텐츠 필터링 적용
        if content_text:
            content_text = clean_news_content(content_text)

        if len(content_text) > 100:
            print(f"✅ BeautifulSoup 추출 성공: {len(content_text)}자")
            return content_text[:4000]
        else:
            print(f"❌ BeautifulSoup 추출 실패: 텍스트가 너무 짧음")
            return None

    except Exception as e:
        print(f"💥 BeautifulSoup 추출 오류: {e}")
        return None




# 환경 변수 로드 (파일이 없어도 실행 가능)
try:
    load_dotenv()
except Exception as e:
    print(f"⚠️ .env 파일 로드 실패 (무시 가능): {e}")


# 데이터베이스 설정 - SQLite를 강제로 사용
DATABASE_URL = "sqlite:///./news.db"

engine = create_engine(DATABASE_URL, echo=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# 데이터베이스 모델
class Post(Base):
    __tablename__ = "posts"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    summary = Column(Text, nullable=False)
    content = Column(Text, nullable=False)
    category = Column(String, nullable=False)
    region = Column(String, nullable=False)
    image_url = Column("image_url", String, nullable=False)
    url = Column(String, nullable=True)
    created_at = Column("created_at", TIMESTAMP, server_default=func.now())
    likes = Column(Integer, default=0)
    dislikes = Column(Integer, default=0)
    views = Column(Integer, default=0)

# Pydantic 스키마
class PostBase(BaseModel):
    title: str
    summary: str
    content: str
    category: str
    region: str
    image_url: str
    url: Optional[str] = None

class PostCreate(PostBase):
    pass

class PostResponse(PostBase):
    id: int
    created_at: Optional[datetime] = None
    likes: int = 0
    dislikes: int = 0
    views: int = 0

    @field_serializer('created_at')
    def serialize_created_at(self, value: Optional[datetime]) -> Optional[str]:
        if value is None:
            return None
        return value.isoformat()

    model_config = {
        "from_attributes": True,
        "populate_by_name": True
    }


# lifespan 이벤트 핸들러
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    # startup
    Base.metadata.create_all(bind=engine)
    await seed_database()
    yield
    # shutdown (필요시 cleanup 코드 추가)


# FastAPI 앱 생성
app = FastAPI(title="News API", version="1.0.0", lifespan=lifespan)

# CORS 설정 (필요시)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],  # Vite 기본 포트
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 데이터베이스 세션 의존성
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# 데이터베이스 초기화 (테이블 생성)



async def seed_database():
    # 시드 데이터는 더 이상 사용하지 않음
    pass



# Google News RSS Client
class GoogleNewsRSSClient:
    def __init__(self):
        # 한국 뉴스 RSS 피드
        self.base_url = "https://news.google.com/rss"
        # 간단 버전에서는 기본 세션 사용
        self.session = session

    def extract_article_content(self, url: str) -> str:
        """Trafilatura를 사용한 뉴스 본문 추출"""
        return extract_news_content(url, self.session)

    def _extract_real_url(self, google_news_url: str) -> str:
        """Google News URL에서 실제 뉴스 URL 추출 (간소화된 버전)"""
        # 새로 만든 전문 디코더 사용 - self.session 전달!
        return decode_google_news_url(google_news_url, self.session)

    def get_korea_news(self) -> List[Dict]:
        """한국 주요 뉴스 가져오기"""
        rss_url = "https://news.google.com/rss?hl=ko&gl=KR&ceid=KR:ko"
        return self._fetch_news_from_rss(rss_url)

    def get_world_news(self) -> List[Dict]:
        """세계 주요 뉴스 가져오기"""
        rss_url = "https://news.google.com/rss?hl=en-US&gl=US&ceid=US:en"
        return self._fetch_news_from_rss(rss_url)

    def _fetch_news_from_rss(self, rss_url: str) -> List[Dict]:
        """RSS URL에서 뉴스 가져오기"""

        try:
            # RSS 피드 파싱
            print(f"🌐 Fetching RSS from: {rss_url}")  # 디버깅 로그

            # SSL 검증 없이 RSS 가져오기 (requests 사용) - 강화된 SSL 우회
            try:
                # 첫 번째 시도: 일반적인 SSL 우회
                response = self.session.get(rss_url, verify=False, timeout=30)
                response.raise_for_status()
                rss_content = response.text
            except Exception as ssl_error:
                print(f"⚠️ SSL 오류 발생, 인증서 검증 완전 우회 시도: {ssl_error}")
                try:
                    # 두 번째 시도: 더 강력한 SSL 우회
                    import ssl
                    from urllib3.util import ssl_

                    # SSL 컨텍스트 생성 (인증서 검증 완전 비활성화)
                    ssl_context = ssl.create_default_context()
                    ssl_context.check_hostname = False
                    ssl_context.verify_mode = ssl.CERT_NONE

                    response = self.session.get(
                        rss_url,
                        verify=False,
                        timeout=30,
                        cert_reqs=ssl.CERT_NONE
                    )
                    response.raise_for_status()
                    rss_content = response.text
                except Exception as fallback_error:
                    print(f"💥 SSL 우회 실패, 마지막 시도: {fallback_error}")
                    # 세 번째 시도: urllib 사용
                    try:
                        import urllib.request
                        import urllib.error

                        req = urllib.request.Request(rss_url)
                        req.add_header('User-Agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
                        with urllib.request.urlopen(req, timeout=30) as response:
                            rss_content = response.read().decode('utf-8')
                    except Exception as urllib_error:
                        print(f"💥 모든 SSL 우회 방법 실패: {urllib_error}")
                        return []

            # 가져온 RSS 텍스트를 feedparser로 파싱
            feed = feedparser.parse(rss_content)

            # 상세한 디버깅 정보
            print(f"📡 Feed status: {feed.status if hasattr(feed, 'status') else 'unknown'}")
            print(f"📰 Feed entries count: {len(feed.entries)}")
            print(f"📝 Feed title: {getattr(feed.feed, 'title', 'No title')}")
            print(f"🔍 Feed keys: {list(feed.keys())}")
            print(f"📄 Raw feed data (first 500 chars): {str(feed)[:500]}")

            if hasattr(feed, 'bozo') and feed.bozo:
                print(f"⚠️ Feed parsing error: {feed.bozo_exception}")

            # entries 상세 정보
            if feed.entries:
                print(f"✅ First entry keys: {list(feed.entries[0].keys()) if feed.entries else 'No entries'}")
                print(f"✅ First entry title: {getattr(feed.entries[0], 'title', 'No title') if feed.entries else 'No entries'}")
            else:
                print(f"❌ No entries found in feed")

            articles = []
            for entry in feed.entries[:20]:  # 최대 20개 뉴스
                # 이미지 URL 추출 개선
                image_url = ""
                if hasattr(entry, 'media_thumbnail') and entry.media_thumbnail:
                    image_url = entry.media_thumbnail[0].get('url', '')
                elif hasattr(entry, 'media_content') and entry.media_content:
                    image_url = entry.media_content[0].get('url', '')
                elif hasattr(entry, 'enclosures') and entry.enclosures:
                    for enclosure in entry.enclosures:
                        if enclosure.get('type', '').startswith('image/'):
                            image_url = enclosure.get('url', '')
                            break

                # 날짜 처리 개선
                published_at = getattr(entry, 'published', '')
                if published_at:
                    try:
                        from email.utils import parsedate_to_datetime
                        published_at = parsedate_to_datetime(published_at).isoformat()
                    except:
                        published_at = datetime.now().isoformat()

                # Google News 링크에서 실제 뉴스 URL 추출 시도
                actual_url = self._extract_real_url(entry.link)

                article = {
                    "title": entry.title,
                    "description": getattr(entry, 'summary', ''),
                    "content": getattr(entry, 'summary', ''),  # RSS에서는 콘텐츠가 제한적
                    "url": actual_url,  # 실제 뉴스 URL 사용
                    "urlToImage": image_url,
                    "publishedAt": published_at
                }
                articles.append(article)

            print(f"✅ Returning {len(articles)} articles")
            return articles

        except Exception as e:
            print(f"💥 Error parsing RSS feed for {topic}: {e}")
            import traceback
            print(f"💥 Full traceback: {traceback.format_exc()}")
            return []
        







# News fetch, save Func
async def fetch_and_store_news(db: Session):
    """Google News RSS에서 뉴스를 가져와서 Python 서버의 자체 DB에 저장"""

    # 기존 데이터에 region 필드 기본값 설정 (마이그레이션)
    try:
        existing_posts = db.query(Post).filter(Post.region.is_(None)).all()
        if existing_posts:
            print(f"🔄 기존 {len(existing_posts)}개 뉴스에 region='korea' 설정 중...")
            for post in existing_posts:
                post.region = "korea"
            db.commit()
            print("✅ 기존 데이터 region 설정 완료")
    except Exception as e:
        print(f"⚠️ 기존 데이터 마이그레이션 실패: {e}")
        db.rollback()

    client = GoogleNewsRSSClient()

    total_processed = 0
    total_saved = 0

    # 한국 뉴스 가져오기
    print("🇰🇷 Fetching Korea news...")
    korea_articles = client.get_korea_news()
    print(f"📊 Found {len(korea_articles)} Korea articles")

    # 세계 뉴스 가져오기
    print("🌍 Fetching World news...")
    world_articles = client.get_world_news()
    print(f"📊 Found {len(world_articles)} World articles")

    # 뉴스 처리
    for articles, region in [(korea_articles, "korea"), (world_articles, "world")]:
        # 최신순으로 정렬하고 10개로 제한
        try:
            articles = sorted(articles, key=get_sort_key, reverse=True)[:10]
            print(f"✅ Processing {len(articles)} {region} articles")
        except Exception as sort_err:
            print(f"❌ Sorting failed for {region}: {sort_err}")
            articles = articles[:10]

        try:

            for i, article in enumerate(articles):
                title = article.get("title", "").strip()
                description = article.get("description", "").strip()
                category = article.get("category", "general").lower().strip()  # 카테고리 정보 가져오기

                # HTML 태그 제거만 하고 끝
                if description:
                    soup = BeautifulSoup(description, 'html.parser')
                    description = soup.get_text().strip()
                    description = ' '.join(description.split())

                total_processed += 1
                print(f"📰 Processing article {i+1}: {title[:50]}...")

                # 본문 추출 시도
                google_news_url = article.get("url", "")
                content = description  # 기본값으로 RSS 요약 사용

                # 실제 본문 추출 시도 (디코딩된 URL 사용)
                news_url = ""  # 디코딩된 URL 초기화
                if google_news_url:
                    try:
                        # 1. 먼저 Google News URL 디코딩
                        decoded_url = decode_google_news_url(google_news_url)
                        if decoded_url and isinstance(decoded_url, str):
                            news_url = decoded_url
                            print(f"✅ URL 디코딩 성공: {decoded_url}")

                            # 2. 디코딩된 URL에서 본문 추출 (test_extraction.py 방식)
                            extracted_content = extract_news_content(decoded_url)
                            if extracted_content and len(extracted_content.strip()) > 50:
                                # 3. 불필요한 내용만 제거 (전체 본문 유지)
                                filtered_content = clean_news_content(extracted_content)
                                if filtered_content and len(filtered_content.strip()) > 50:
                                    content = filtered_content
                                    print(f"✅ 본문 추출 및 정리 성공: {len(content)}자")
                                    print(f"📄 정리된 본문 미리보기: {content[:100]}...")
                                else:
                                    print("⚠️ 정리 결과가 너무 짧음, RSS 요약 사용")
                            else:
                                print("⚠️ 본문 추출 실패, RSS 요약 사용")
                        else:
                            print("❌ URL 디코딩 실패")
                    except Exception as e:
                        print(f"💥 본문 추출 오류: {e}, RSS 요약 사용")

                # Python DB에서 중복 체크 (제목 또는 URL 기준)
                existing_post = None

                # 1. 제목으로 먼저 체크
                existing_post = db.query(Post).filter(Post.title == title).first()

                # 2. URL로도 체크 (news_url이 있는 경우)
                if not existing_post and news_url:
                    existing_post = db.query(Post).filter(Post.url == news_url).first()

                if existing_post:
                    # 이미 존재하는 뉴스라면 업데이트
                    print(f"🔄 Updating existing post: {title[:30]}... (ID: {existing_post.id})")

                    # Region별 카테고리 매핑 (업데이트 시)
                    if region == "korea":
                        category_mapping = {
                            "business": "비즈니스",
                            "technology": "기술",
                            "science": "과학",
                            "health": "건강",
                            "entertainment": "엔터테인먼트",
                            "general": "일반"
                        }
                        update_category = category_mapping.get(category, "일반")
                    else:
                        category_mapping = {
                            "business": "Business",
                            "technology": "Technology",
                            "science": "Science",
                            "health": "Health",
                            "entertainment": "Entertainment",
                            "general": "General"
                        }
                        update_category = category_mapping.get(category, "General")

                    # 업데이트할 필드들
                    update_data = {
                        'summary': description[:300],
                        'content': content,
                        'category': update_category,
                    }

                    # 이미지 URL이 있으면 업데이트
                    image_url = article.get("urlToImage", "")
                    if image_url:
                        update_data['image_url'] = image_url

                    # URL이 있으면 업데이트
                    if news_url:
                        update_data['url'] = news_url

                    try:
                        for key, value in update_data.items():
                            setattr(existing_post, key, value)

                        # content에 링크 추가 (이미 존재하는 경우에도 업데이트)
                        if news_url and "🔗 전체 기사 보기:" not in existing_post.content:
                            existing_post.content += f"\n\n🔗 전체 기사 보기: {news_url}"

                        db.commit()
                        print(f"✅ Updated existing post: {title[:30]}...")
                        continue  # 저장하지 않고 다음으로 진행
                    except Exception as update_error:
                        db.rollback()
                        print(f"💥 Error updating existing post: {update_error}")
                        continue

                # 새로운 뉴스인 경우 저장
                full_content = content
                if news_url:
                    full_content += f"\n\n🔗 전체 기사 보기: {news_url}"
                    print(f"📎 링크 추가됨: {news_url}")
                else:
                    print("⚠️ news_url이 비어있음")

                image_url = article.get("urlToImage", "")
                if not image_url:
                    image_url = "https://images.unsplash.com/photo-1504711434969-e33886168f5c?auto=format&fit=crop&q=80&w=800"

                # Region별 카테고리 매핑 (한국어 vs 영어)
                if region == "korea":
                    # 한국 뉴스: 한국어 카테고리
                    category_mapping = {
                        "business": "비즈니스",
                        "technology": "기술",
                        "science": "과학",
                        "health": "건강",
                        "entertainment": "엔터테인먼트",
                        "sports": "스포츠",
                        "politics": "정치",
                        "world": "국제",
                        "nation": "국내",
                        "general": "일반",
                        "tech": "기술",
                        "medical": "건강",
                        "economy": "비즈니스",
                        "finance": "비즈니스",
                        "showbiz": "엔터테인먼트",
                        "celebrity": "엔터테인먼트",
                        "research": "과학",
                        "environment": "과학",
                    }
                    final_category = category_mapping.get(category, "일반")
                else:
                    # 세계 뉴스: 영어 카테고리
                    category_mapping = {
                        "business": "Business",
                        "technology": "Technology",
                        "science": "Science",
                        "health": "Health",
                        "entertainment": "Entertainment",
                        "sports": "Sports",
                        "politics": "Politics",
                        "world": "World",
                        "nation": "Nation",
                        "general": "General",
                        "tech": "Technology",
                        "medical": "Health",
                        "economy": "Business",
                        "finance": "Business",
                        "showbiz": "Entertainment",
                        "celebrity": "Entertainment",
                        "research": "Science",
                        "environment": "Science",
                    }
                    final_category = category_mapping.get(category, "General")

                # 제목/내용으로 키워드 분석 (항상 수행하여 더 정확한 분류)
                if title or description:
                    text_to_analyze = (title + " " + description).lower()

                    # 키워드 기반 카테고리 분류 (한국어 + 영어)
                    # 새로운 카테고리에 맞는 간단한 키워드 매핑
                    if region == "korea":
                        keyword_mapping = {
                            "정치": ["대통령", "정부", "국회", "정치", "선거", "장관", "국회의원", "총리", "의원", "민주", "국힘", "김병기", "강선우", "이혜훈", "내란", "공천", "의혹", "사퇴", "원내대표"],
                            "경제": ["경제", "금융", "기업", "시장", "주식", "사업", "회사", "산업", "은행", "투자", "무역", "환율", "부동산", "코스피", "코스닥"],
                            "과학": ["연구", "발견", "과학", "우주", "환경", "기후", "연구원", "과학자", "반도체", "기술", "AI", "인공지능"],
                            "연예": ["영화", "드라마", "연예인", "가수", "콘서트", "배우", "예술", "넷플릭스", "게임", "포트나이트", "스타", "주식시세"],
                        }
                    else:
                        keyword_mapping = {
                            "Politics": ["president", "government", "politics", "election", "minister", "congress", "political", "policy", "diplomatic", "trump", "china", "taiwan"],
                            "Business": ["economy", "finance", "company", "market", "stock", "business", "industry", "bank", "investment", "trading"],
                            "Science": ["research", "discovery", "science", "space", "environment", "climate", "scientist", "laboratory"],
                            "Entertainment": ["movie", "drama", "celebrity", "singer", "concert", "entertainment", "netflix", "actor", "artist"],
                        }

                    for cat, keywords in keyword_mapping.items():
                        if any(keyword in text_to_analyze for keyword in keywords):
                            final_category = cat
                            print(f"🎯 키워드 분석으로 카테고리 결정: {cat} (region: {region})")
                            break

                print(f"📂 최종 카테고리: {final_category} (원본: {category}, region: {region})")

                # Python Post 모델 생성 및 저장 (region 정보 추가)
                new_post = Post(
                    title=title[:200],
                    summary=description[:300],
                    content=full_content,
                    category=final_category,
                    region=region,  # region 정보 추가
                    image_url=image_url,
                    url=news_url if news_url else None
                )

                print(f"📤 DB 저장 시도: {title[:30]}...")
                try:
                    db.add(new_post)
                    db.commit()
                    db.refresh(new_post)
                    total_saved += 1
                    print(f"✅ Saved to Python DB: {title[:30]}... (ID: {new_post.id})")
                except Exception as save_error:
                    db.rollback()
                    print(f"💥 Error saving to Python DB: {save_error}")

        except Exception as e:
            print(f"💥 Error fetching {region} news: {e}")
            continue

    print(f"🎉 Total processed: {total_processed}, Total saved to Python DB: {total_saved}")  # 최종 결과 로그
    print("News fetched and stored in Python database successfully")

# API 앤드 포인트들
@app.get("/api/posts", response_model=List[PostResponse])
async def get_posts(
    category: Optional[str] = Query(None),
    region: Optional[str] = Query("korea"),  # 기본값을 korea로 설정
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    query = db.query(Post)

    if category:
        query = query.filter(Post.category == category)

    if region:
        query = query.filter(Post.region == region)

    if search:
        search_term = f"%{search.lower()}%"
        query = query.filter(
            (Post.title.ilike(search_term)) |
            (Post.content.ilike(search_term))
        )

    posts = query.order_by(Post.created_at.desc(), Post.id.desc()).all()
    return posts

# FastAPI에서는 경로 파라미터를 중괄호로 선언해야 하며, f-string을 사용할 필요가 없다.
@app.api_route("/api/posts/{post_id}", methods=["GET"])  # api_route로 변경하여 validation 우회
async def get_post(post_id, db: Session = Depends(get_db)):  # 타입 힌트 제거
    print(f"DEBUG: Requesting post with ID: {post_id}, type: {type(post_id)}")

    try:
        post_id_int = int(post_id)
        print(f"DEBUG: Converted to int: {post_id_int}")
    except ValueError as e:
        print(f"DEBUG: Failed to convert ID to int: {e}")
        raise HTTPException(status_code=400, detail=f"Invalid ID format: {post_id}")

    # 데이터베이스에 해당 ID가 존재하는지 확인
    all_posts = db.query(Post).all()
    print(f"DEBUG: All post IDs in database: {[p.id for p in all_posts]}")

    post = db.query(Post).filter(Post.id == post_id_int).first()
    if not post:
        print(f"DEBUG: Post with ID {post_id_int} not found")
        raise HTTPException(status_code=404, detail="Post not found")

    # GET 요청에서는 조회수 증가하지 않음 - 오직 POST /view에서만 증가
    print(f"DEBUG: Found post: {post.id}, {post.title} (views: {post.views})")
    return post


@app.post("/api/posts", response_model=PostResponse, status_code=201)
async def create_post(post: PostCreate, db: Session = Depends(get_db)):
    db_post = Post(**post.dict())
    db.add(db_post)
    db.commit()
    db.refresh(db_post)
    return db_post


@app.post("/api/posts/{post_id}/like")
async def like_post(post_id: int, db: Session = Depends(get_db)):
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    post.likes += 1
    db.commit()
    return {"success": True}


@app.post("/api/posts/{post_id}/view")
async def view_post(post_id: int, db: Session = Depends(get_db)):
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    post.views += 1
    db.commit()
    return {"success": True}


@app.post("/api/posts/{post_id}/dislike")
async def dislike_post(post_id: int, db: Session = Depends(get_db)):
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    post.dislikes += 1
    db.commit()
    return {"success": True}


@app.post("/api/news/fetch")
async def fetch_latest_news(db: Session = Depends(get_db)):
    """최신 뉴스를 가져와서 저장"""
    await fetch_and_store_news(db)
    return {"message": "Latest news fetched and stored successfully"}
    
        

# 간단한 서버 실행
if __name__ == "__main__":
    # 테스트 코드
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        print("🧪 본문 추출 테스트...")
        test_url = 'https://news.google.com/rss/articles/CBMiVkFVX3lxTE9WUjlNZ0psX0hZMW5mVlQyZFhRblQ4TVFaRVdUMmdIMXNKbXUzZ284MmVuWDhRcVV6eFBHdWWhmMkhON1lEMFRwWnMxNDdMMU1Qb3BsdEZB?oc=5'
        try:
            result = extract_news_content(test_url)
            if result:
                print(f'✅ 성공! 추출된 텍스트 길이: {len(result)}')
                print(f'📝 미리보기: {result[:200]}...')
            else:
                print('❌ 추출 실패')
        except Exception as e:
            print(f'💥 오류 발생: {e}')
            import traceback
            print(traceback.format_exc())
    else:
        port = int(os.getenv("PORT", 8000))
        uvicorn.run(app, host="127.0.0.1", port=port)