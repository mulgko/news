"""
News Content Extraction Module

This module handles the extraction and cleaning of news content from various sources.
It provides functions to:
- Extract news content from URLs (including Google News URLs)
- Detect and filter Newsis-style content
- Clean news content by removing ads and unwanted elements
- Extract content using BeautifulSoup and Trafilatura

All extraction logic is centralized here for better maintainability.
"""

import re
import requests
from bs4 import BeautifulSoup
import trafilatura

from app.services.url_decoder import decode_google_news_url


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
