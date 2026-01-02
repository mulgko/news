# 뉴스 앱 배포 가이드

## 준비 사항

### 1. 필수 파일 확인
- ✅ `Dockerfile` - 생성 완료
- ✅ `.dockerignore` - 생성 완료
- ✅ `railway.toml` - 수정 완료

### 2. 환경 변수 설정 필요
Railway 대시보드에서 다음 환경 변수를 설정하세요:

```
GOOGLE_AI_API_KEY=your_actual_api_key_here
```

**Google AI API 키 발급 방법:**
1. https://ai.google.dev/ 접속
2. "Get API key in Google AI Studio" 클릭
3. API 키 생성 후 복사

---

## Railway 배포 방법

### 방법 1: GitHub 연동 (권장)

1. **GitHub 저장소에 푸시**
   ```bash
   cd /Users/gimdogyeong/mulgko/news
   git init  # 아직 git 초기화를 안 했다면
   git add .
   git commit -m "Add Docker configuration for Railway deployment"
   git remote add origin <your-github-repo-url>
   git push -u origin main
   ```

2. **Railway에서 프로젝트 생성**
   - https://railway.app 로그인
   - "New Project" 클릭
   - "Deploy from GitHub repo" 선택
   - 저장소 선택

3. **환경 변수 설정**
   - Railway 프로젝트 대시보드에서 "Variables" 탭 클릭
   - `GOOGLE_AI_API_KEY` 추가

4. **배포 시작**
   - Railway가 자동으로 Dockerfile을 감지하고 빌드 시작
   - 빌드 로그 확인

### 방법 2: Railway CLI 사용

1. **Railway CLI 설치**
   ```bash
   npm install -g @railway/cli
   ```

2. **로그인**
   ```bash
   railway login
   ```

3. **프로젝트 초기화**
   ```bash
   cd /Users/gimdogyeong/mulgko/news
   railway init
   ```

4. **환경 변수 설정**
   ```bash
   railway variables set GOOGLE_AI_API_KEY=your_actual_api_key_here
   ```

5. **배포**
   ```bash
   railway up
   ```

---

## 배포 후 확인 사항

### 1. 헬스체크 확인
배포된 URL에 `/api/health` 접속하여 다음 응답이 오는지 확인:
```json
{
  "status": "running",
  "version": "1.0.0"
}
```

### 2. 프론트엔드 확인
- 루트 URL(`/`)에 접속하여 React 앱이 정상적으로 로드되는지 확인
- 만약 API 메시지만 보인다면, 빌드가 제대로 안 된 것

### 3. 뉴스 데이터 가져오기
배포된 URL에서 다음 API 호출:
```bash
curl -X POST https://your-app.railway.app/api/news/fetch
```

---

## 트러블슈팅

### 문제 1: 빌드가 실패함
**확인 사항:**
- Railway 빌드 로그에서 에러 메시지 확인
- `Dockerfile`이 프로젝트 루트에 있는지 확인
- `railway.toml`에서 `builder = "DOCKERFILE"` 설정 확인

### 문제 2: 프론트엔드가 안 보임
**원인:** 프론트엔드 빌드가 실패했거나 경로 설정이 잘못됨

**해결:**
1. Railway 빌드 로그에서 "npm run build" 단계 확인
2. 에러가 있다면 로컬에서 `npm run build` 테스트
3. `dist/public` 폴더가 생성되는지 확인

### 문제 3: API는 작동하지만 CORS 에러
**해결:** `main.py`의 CORS 설정에 Railway URL 추가
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "https://your-app.railway.app",  # Railway URL 추가
        "*"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### 문제 4: 데이터베이스 연결 오류
**원인:** 현재 SQLite를 사용 중인데, Railway는 임시 스토리지 사용

**해결 방법 (선택):**
1. **PostgreSQL 사용 (권장):**
   - Railway에서 PostgreSQL 플러그인 추가
   - `main.py`의 `DATABASE_URL` 수정
   - 환경 변수 `DATABASE_URL` 설정

2. **SQLite 유지:**
   - 데이터가 재배포 시 초기화됨을 감안
   - 개발/테스트용으로만 사용

---

## 로컬 테스트 (선택 사항)

Docker를 사용하여 로컬에서 배포 환경과 동일하게 테스트:

```bash
# Docker 이미지 빌드
docker build -t news-app .

# 컨테이너 실행
docker run -p 8080:8080 \
  -e GOOGLE_AI_API_KEY=your_api_key \
  news-app

# 브라우저에서 http://localhost:8080 접속
```

---

## 다음 단계

### 1. 도메인 연결
Railway 대시보드에서 "Settings" > "Domains"에서 커스텀 도메인 추가

### 2. PostgreSQL 데이터베이스 추가
- Railway 프로젝트에서 "New" > "Database" > "PostgreSQL" 선택
- 자동으로 `DATABASE_URL` 환경 변수가 설정됨
- `main.py`에서 SQLite 대신 PostgreSQL 사용하도록 수정

### 3. 자동 뉴스 업데이트 설정
- Railway Cron Jobs 또는 외부 스케줄러 사용
- 주기적으로 `/api/news/fetch` 엔드포인트 호출

---

## 유용한 명령어

```bash
# Railway 로그 확인
railway logs

# 환경 변수 확인
railway variables

# 프로젝트 상태 확인
railway status

# 로컬 Railway 환경에서 실행
railway run npm run dev
```

---

## 참고 자료

- [Railway 공식 문서](https://docs.railway.app/)
- [Dockerfile 레퍼런스](https://docs.docker.com/engine/reference/builder/)
- [FastAPI 배포 가이드](https://fastapi.tiangolo.com/deployment/)
