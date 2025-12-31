# Railway 배포 가이드

이 프로젝트는 Python FastAPI 백엔드와 React 프론트엔드로 구성되어 있습니다. Railway에서 두 개의 서비스로 분리하여 배포하는 방법을 설명합니다.

## 🚂 Railway 설정 방법

### 1. Railway 프로젝트 생성

1. [Railway](https://railway.app)에서 계정 생성/로그인
2. "New Project" → "Deploy from GitHub repo" 선택
3. 이 리포지토리를 연결

### 2. 백엔드 (Python FastAPI) 배포

Railway는 자동으로 `server-python/` 폴더를 Python 서비스로 인식합니다.

**환경 변수 설정:**
Railway 대시보드에서 다음 환경 변수를 설정하세요:

```bash
# 필수: 데이터베이스 연결 (Railway PostgreSQL 사용 권장)
DATABASE_URL=postgresql://postgres:password@containers-us-west-xxx.railway.app:xxxx/railway

# 필수: Google AI API 키 (Google AI Studio에서 발급)
GOOGLE_AI_API_KEY=your_google_ai_api_key_here

# 선택: OpenAI API 키 (AI 기능 확장 시)
OPENAI_API_KEY=your_openai_api_key_here

# 자동 설정됨: Railway에서 제공하는 포트
PORT=8080
```

**배포 확인:**

- Railway에서 자동으로 `requirements.txt`를 읽어 의존성 설치
- `Procfile`의 명령어로 서버 실행: `uvicorn main:app --host 0.0.0.0 --port $PORT`

### 3. 프론트엔드 (React) 배포

루트 디렉토리의 `package.json`을 사용해 React 앱을 배포합니다.

**Railway 서비스 설정:**

1. 프로젝트 대시보드에서 "New Service" → "GitHub" 선택
2. 같은 리포지토리를 다시 연결
3. 서비스 이름을 "frontend" 또는 "client"로 설정

**빌드 설정:**
Railway에서 다음 설정을 추가하세요:

```bash
# Build Command
npm run build:client

# Start Command
npm run start:client
```

### 4. 서비스 연결

프론트엔드가 백엔드 API를 호출할 수 있도록 Railway에서 제공하는 내부 도메인을 사용하세요.

**프론트엔드 환경 변수:**

```bash
# Railway에서 백엔드 서비스의 내부 URL
VITE_API_URL=https://your-backend-service.up.railway.app
```

## 🔧 로컬에서 Railway 시뮬레이션

로컬에서 Railway 환경을 시뮬레이션하려면:

```bash
# 백엔드 (Python)
cd server-python
PORT=8000 uvicorn main:app --host 0.0.0.0 --port 8000

# 프론트엔드 (React)
PORT=3000 npm run start:client
```

## 📁 프로젝트 구조

```
news/
├── server-python/        # FastAPI 백엔드
│   ├── main.py          # 메인 서버 파일
│   ├── requirements.txt # Python 의존성
│   ├── Procfile         # Railway 시작 명령
│   └── runtime.txt      # Python 버전
├── client/              # React 프론트엔드
│   └── src/
├── package.json         # Node.js 설정 및 스크립트
└── railway.toml         # Railway 설정 (선택사항)
```

## 🚀 배포 후 확인사항

1. 백엔드 API 엔드포인트가 정상 작동하는지 확인
2. 프론트엔드가 백엔드와 정상 통신하는지 확인
3. 데이터베이스 연결이 정상인지 확인
4. 정적 파일들이 올바르게 서빙되는지 확인

## 💡 팁

- Railway의 환경 변수는 대시보드에서 안전하게 관리됩니다
- 각 서비스의 로그는 Railway 대시보드에서 실시간으로 확인 가능
- 무료 플랜에서는 일정 시간 후 서비스가 슬립될 수 있습니다
