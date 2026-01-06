# 뉴스 앱 빌드 및 배포 가이드

이 문서는 개발부터 프로덕션 배포까지 전체 과정을 다룹니다.

---

## 목차
1. [개발 환경 설정](#개발-환경-설정)
2. [로컬 개발](#로컬-개발)
3. [빌드 전 체크리스트](#빌드-전-체크리스트)
4. [프로덕션 빌드](#프로덕션-빌드)
5. [Railway 배포](#railway-배포)
6. [배포 후 확인](#배포-후-확인)
7. [주의사항](#주의사항)
8. [자주 발생하는 문제](#자주-발생하는-문제)

---

## 개발 환경 설정

### 필수 요구사항
- Node.js 18 이상
- Python 3.12 이상
- Git

### 초기 설정

```bash
# 1. 저장소 클론
git clone <your-repo-url>
cd news

# 2. Node.js 패키지 설치
npm install

# 3. Python 가상환경 생성 및 패키지 설치
cd server-python
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cd ..
```

### 환경 변수 설정

**로컬 개발용 `.env` 파일 생성** (선택사항)
```bash
# server-python/.env
GOOGLE_AI_API_KEY=your_google_ai_api_key_here
DATABASE_URL=sqlite:///./news.db
```

**중요:** `.env` 파일은 절대 Git에 커밋하지 마세요!

---

## 로컬 개발

### 1. 백엔드 서버 실행

```bash
# Terminal 1
cd server-python
python main.py
```

서버가 `http://127.0.0.1:8000`에서 실행됩니다.

**확인:**
```bash
curl http://127.0.0.1:8000/api/health
# 출력: {"status":"running","version":"1.0.0"}
```

### 2. 프론트엔드 개발 서버 실행

```bash
# Terminal 2 (프로젝트 루트에서)
npm run dev
```

프론트엔드가 `http://localhost:5173`에서 실행됩니다.

### 3. 뉴스 데이터 가져오기 (최초 1회)

```bash
curl -X POST http://127.0.0.1:8000/api/news/fetch
```

---

## 빌드 전 체크리스트

### 필수 확인 사항

- [ ] **코드 변경사항 확인**
  ```bash
  git status
  git diff
  ```

- [ ] **API 호출 로직 확인**
  - `client/src/hooks/use-posts.ts`에서 `new URL()` 사용이 올바른가?
  - 모든 API 함수가 `new URL(path, API_BASE_URL || window.location.origin)` 형식인가?

- [ ] **환경 변수 확인**
  ```typescript
  // client/src/hooks/use-posts.ts
  const API_BASE_URL = import.meta.env.MODE === "development"
    ? "http://127.0.0.1:8000"
    : "";
  ```

- [ ] **TypeScript 에러 없음**
  ```bash
  npx tsc --noEmit
  ```

- [ ] **린트 에러 없음**
  ```bash
  npm run lint
  ```

---

## 프로덕션 빌드

### 1. 프론트엔드 빌드

```bash
# 프로젝트 루트에서
npm run build
```

**성공 출력 예시:**
```
✓ 2090 modules transformed.
../dist/public/index.html                   2.01 kB │ gzip:   0.77 kB
../dist/public/assets/index-JlWaqlOH.css   76.27 kB │ gzip:  12.54 kB
../dist/public/assets/index-nDlhFBoK.js   420.80 kB │ gzip: 127.17 kB
✓ built in 2.51s
```

**빌드 결과 확인:**
```bash
ls -la dist/public
# index.html, assets/ 폴더가 있어야 함
```

### 2. 빌드 결과 로컬 테스트 (선택사항)

Vite의 preview 서버로 빌드 결과를 테스트할 수 있습니다:

```bash
# Terminal 1: 백엔드 서버 실행
cd server-python
python main.py

# Terminal 2: 프론트엔드 preview 서버
npm run preview
```

`http://localhost:4173`에서 프로덕션 빌드를 확인할 수 있습니다.

### 3. Docker 로컬 테스트 (선택사항)

배포 전에 Docker로 전체 환경을 테스트할 수 있습니다:

```bash
# Docker 이미지 빌드
docker build -t news-app .

# 컨테이너 실행
docker run -p 8080:8080 \
  -e GOOGLE_AI_API_KEY=your_api_key \
  -e DATABASE_URL=sqlite:///./news.db \
  news-app

# 브라우저에서 http://localhost:8080 접속
```

---

## Railway 배포

### 배포 전 준비

#### 1. Git 커밋

```bash
# 변경사항 확인
git status

# 스테이징
git add .

# 커밋
git commit -m "Fix: API URL construction for production"

# GitHub에 푸시
git push origin main
```

#### 2. Railway 환경 변수 확인

Railway 대시보드에서 다음 환경 변수가 설정되어 있는지 확인:

```
GOOGLE_AI_API_KEY=your_actual_google_ai_api_key
DATABASE_URL=postgresql://... (Railway에서 자동 설정)
```

**환경 변수 추가/수정 방법:**
1. Railway 프로젝트 대시보드 접속
2. "Variables" 탭 클릭
3. 환경 변수 추가 또는 수정
4. 저장 (자동으로 재배포됨)

### 배포 방법

#### 방법 1: GitHub 자동 배포 (권장)

```bash
git push origin main
```

Railway가 자동으로:
1. 새 커밋 감지
2. Dockerfile 빌드
3. 컨테이너 배포
4. 헬스체크 확인

**배포 상태 확인:**
- Railway 대시보드에서 "Deployments" 탭 확인
- 빌드 로그 실시간 확인 가능

#### 방법 2: Railway CLI 사용

```bash
# Railway CLI 설치 (최초 1회)
npm install -g @railway/cli

# 로그인
railway login

# 배포
railway up
```

### 배포 과정 모니터링

```bash
# Railway CLI로 로그 확인
railway logs

# 또는 Railway 대시보드에서 실시간 로그 확인
```

**정상 배포 로그 예시:**
```
Building with Dockerfile...
Step 1/12 : FROM node:18-alpine AS frontend-builder
...
Step 12/12 : CMD cd server-python && python main.py
Successfully built abc123def456
Deploying...
Deployment successful!
```

---

## 배포 후 확인

### 1. 헬스체크 확인

```bash
curl https://your-app.railway.app/api/health
```

**예상 응답:**
```json
{"status":"running","version":"1.0.0"}
```

### 2. 프론트엔드 확인

브라우저에서 `https://your-app.railway.app` 접속

**확인 사항:**
- [ ] 페이지가 로드되는가?
- [ ] 뉴스 목록이 보이는가?
- [ ] 브라우저 콘솔에 에러가 없는가?
- [ ] 네트워크 탭에서 `/api/posts` 요청이 성공하는가?

### 3. API 엔드포인트 확인

```bash
# 게시물 목록 조회
curl "https://your-app.railway.app/api/posts?region=korea"

# 뉴스 데이터 가져오기 (최초 1회)
curl -X POST https://your-app.railway.app/api/news/fetch
```

### 4. 데이터베이스 확인

Railway 대시보드에서:
1. PostgreSQL 서비스 클릭
2. "Data" 탭에서 테이블 확인
3. `posts` 테이블에 데이터가 있는지 확인

---

## 주의사항

### ⚠️ 절대 하지 말아야 할 것

1. **`new URL()` 사용 시 base URL 생략**
   ```typescript
   // ❌ 잘못된 코드
   const url = new URL(API_BASE_URL + path);

   // ✅ 올바른 코드
   const url = new URL(path, API_BASE_URL || window.location.origin);
   ```

2. **프로덕션에서 localhost API 호출**
   ```typescript
   // ❌ 하드코딩된 localhost
   const API_BASE_URL = "http://127.0.0.1:8000";

   // ✅ 환경별 설정
   const API_BASE_URL = import.meta.env.MODE === "development"
     ? "http://127.0.0.1:8000"
     : "";
   ```

3. **`.env` 파일 Git에 커밋**
   ```bash
   # .gitignore에 반드시 포함되어야 함
   .env
   .env.local
   .env.production
   ```

4. **빌드 없이 배포**
   - 항상 `npm run build`로 빌드 성공 확인 후 배포
   - Dockerfile이 자동으로 빌드하지만, 로컬에서 미리 확인

5. **Railway 환경 변수 누락**
   - `GOOGLE_AI_API_KEY` 없으면 AI 요약 기능 안 됨
   - `DATABASE_URL` 없으면 SQLite 사용 (데이터 유실 가능)

### 💡 권장 사항

1. **빌드 전 항상 로컬 테스트**
   ```bash
   npm run build
   npm run preview  # 빌드 결과 확인
   ```

2. **단계별 커밋**
   ```bash
   # 기능별로 커밋을 나누세요
   git commit -m "feat: Add user authentication"
   git commit -m "fix: Fix API URL construction"
   git commit -m "docs: Update README"
   ```

3. **배포 전 브랜치 전략**
   ```bash
   # main 브랜치에 직접 푸시하지 말고
   git checkout -b feature/new-feature
   # 작업 후
   git push origin feature/new-feature
   # PR 생성 → 리뷰 → main에 병합
   ```

4. **Railway 로그 모니터링**
   - 배포 후 최소 5분간 로그 확인
   - 에러가 있으면 즉시 롤백

---

## 자주 발생하는 문제

### 문제 1: "게시물이 없습니다" 표시

**원인:**
- API 호출 실패
- 데이터베이스에 데이터 없음

**해결:**
1. 네트워크 탭에서 API 요청 확인
2. 요청이 없으면 → URL 생성 로직 확인
3. 요청은 있지만 빈 배열 반환 → 뉴스 데이터 가져오기
   ```bash
   curl -X POST https://your-app.railway.app/api/news/fetch
   ```

### 문제 2: 빌드 실패

**원인:**
- TypeScript 에러
- 패키지 버전 충돌

**해결:**
```bash
# 에러 로그 확인
npm run build

# node_modules 재설치
rm -rf node_modules package-lock.json
npm install

# TypeScript 에러 확인
npx tsc --noEmit
```

### 문제 3: Railway 배포 실패

**원인:**
- Dockerfile 오류
- 환경 변수 누락
- 빌드 타임아웃

**해결:**
1. Railway 빌드 로그 확인
2. 로컬에서 Docker 빌드 테스트
   ```bash
   docker build -t news-app .
   ```
3. 환경 변수 확인

### 문제 4: CORS 에러

**원인:**
- 백엔드 CORS 설정 누락

**해결:**
`server-python/main.py`에서 CORS 설정 확인:
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### 문제 5: 데이터베이스 연결 실패

**원인:**
- `DATABASE_URL` 환경 변수 누락
- PostgreSQL 서비스 중지

**해결:**
1. Railway 대시보드에서 PostgreSQL 상태 확인
2. `DATABASE_URL` 환경 변수 확인
3. Railway 로그에서 데이터베이스 연결 로그 확인

---

## 빠른 참조 명령어

### 개발
```bash
# 백엔드 실행
cd server-python && python main.py

# 프론트엔드 실행
npm run dev

# 뉴스 데이터 가져오기
curl -X POST http://127.0.0.1:8000/api/news/fetch
```

### 빌드
```bash
# TypeScript 체크
npx tsc --noEmit

# 린트
npm run lint

# 빌드
npm run build

# 빌드 결과 테스트
npm run preview
```

### 배포
```bash
# Git 커밋 & 푸시
git add .
git commit -m "Your commit message"
git push origin main

# Railway CLI 배포
railway up

# Railway 로그 확인
railway logs
```

### 확인
```bash
# 헬스체크
curl https://your-app.railway.app/api/health

# 게시물 조회
curl https://your-app.railway.app/api/posts?region=korea

# 뉴스 가져오기
curl -X POST https://your-app.railway.app/api/news/fetch
```

---

## 배포 체크리스트 (출력용)

배포 전에 이 체크리스트를 사용하세요:

```
□ 코드 변경사항 확인 (git status)
□ TypeScript 에러 없음 (npx tsc --noEmit)
□ 린트 에러 없음 (npm run lint)
□ 로컬 빌드 성공 (npm run build)
□ API URL 생성 로직 확인 (new URL 사용법)
□ 환경 변수 확인 (Railway Variables 탭)
□ Git 커밋 & 푸시
□ Railway 배포 로그 확인
□ 헬스체크 확인 (/api/health)
□ 프론트엔드 접속 확인
□ 네트워크 탭에서 API 요청 확인
□ 브라우저 콘솔 에러 없음 확인
□ 뉴스 목록 정상 표시 확인
```

---

## 참고 문서

- [TROUBLESHOOTING_HISTORY.md](./TROUBLESHOOTING_HISTORY.md) - 문제 해결 과정 기록
- [DEPLOYMENT_GUIDE.md](./DEPLOYMENT_GUIDE.md) - Railway 배포 상세 가이드
- [Railway 공식 문서](https://docs.railway.app/)
- [Vite 공식 문서](https://vitejs.dev/)
- [FastAPI 공식 문서](https://fastapi.tiangolo.com/)

---

## 프로젝트 구조 (2026-01-06 업데이트)

### 백엔드 구조 (리팩토링 완료)

```
server-python/
├── main.py                    # FastAPI 앱 초기화 (116줄)
├── requirements.txt           # Python 의존성
├── news.db                    # SQLite 데이터베이스 (로컬)
└── app/                       # 애플리케이션 모듈
    ├── core/                  # 핵심 설정
    │   ├── config.py         # 환경변수 및 설정
    │   └── database.py       # DB 연결 관리
    ├── models/               # 데이터베이스 모델
    │   └── post.py           # Post SQLAlchemy 모델
    ├── schemas/              # API 스키마
    │   └── post.py           # Pydantic 검증 스키마
    ├── services/             # 비즈니스 로직
    │   ├── ai_summarizer.py      # Google Gemini AI 통합
    │   ├── content_extractor.py  # 뉴스 콘텐츠 추출
    │   ├── news_crawler.py       # Google News RSS 크롤러
    │   └── url_decoder.py        # URL 디코딩
    ├── routers/              # API 엔드포인트
    │   ├── posts.py          # 게시물 CRUD
    │   └── news.py           # 뉴스 가져오기
    └── utils/                # 유틸리티 함수
        └── helpers.py        # 헬퍼 함수
```

### 프론트엔드 구조

```
client/
├── src/
│   ├── components/          # React 컴포넌트
│   │   └── ui/             # shadcn/ui 컴포넌트
│   ├── hooks/              # 커스텀 훅
│   ├── lib/                # 유틸리티
│   ├── pages/              # 페이지 컴포넌트
│   └── App.tsx             # 루트 컴포넌트
└── public/                 # 정적 파일
```

### 주요 변경사항 (리팩토링)

**이전 구조:**
- `server-python/main.py`: 1,660줄의 단일 파일

**현재 구조:**
- `server-python/main.py`: 116줄 (FastAPI 초기화만)
- `server-python/app/`: 18개 모듈로 체계적 분리

**이점:**
- ✅ 코드 가독성 및 유지보수성 향상
- ✅ 모듈별 독립적 테스트 가능
- ✅ 팀 협업 시 파일 충돌 최소화
- ✅ 새 기능 추가 시 적절한 위치에 배치 용이

### 개발 워크플로우 변경사항

**이전:**
- 모든 코드가 `main.py`에 집중
- 수정 시 전체 파일 탐색 필요

**현재:**
- 기능별로 모듈 분리
- 수정할 기능에 해당하는 모듈만 열면 됨

**예시:**
- AI 요약 수정 → `app/services/ai_summarizer.py`
- API 엔드포인트 추가 → `app/routers/posts.py` 또는 `news.py`
- 데이터베이스 설정 변경 → `app/core/database.py`

---

**문서 업데이트**: 2026-01-06  
**관련 문서**: [ARCHITECTURE.md](./ARCHITECTURE.md) - 상세 아키텍처 설명
