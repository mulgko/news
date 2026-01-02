# 배포 문제 해결 과정 기록

## 문제 증상

### 초기 증상
- Railway에 배포 후 웹사이트 접속 시 **"404 Page Not Found"** 메시지만 표시됨
- 백엔드 API는 정상 작동 (직접 접속 시 데이터 반환)
- 프론트엔드는 로드되지만 뉴스 목록이 표시되지 않음

### 구체적인 증상
```
증상 1: https://news-production-917c.up.railway.app/ 접속 시 "404 Page Not Found"
증상 2: 브라우저 네트워크 탭에 API 요청 (/api/posts) 없음
증상 3: 콘솔에 에러 메시지 없음
증상 4: HTML과 JS 파일은 정상적으로 로드됨
```

---

## 문제 원인 분석

### 1차 분석: 라우팅 문제인가?
처음에는 React Router (wouter) 설정 문제로 의심했습니다.

**확인 결과:**
- `App.tsx`에서 라우트 설정은 정상
- `<Route path="/" component={Home} />` 올바르게 설정됨
- 진짜 문제는 다른 곳에 있었음

### 2차 분석: 상태 초기화 문제
`Home.tsx`에서 `selectedCategory` 상태가 빈 문자열로 초기화되어 있었습니다.

**발견한 문제:**
```typescript
// 문제 코드 (Home.tsx:142)
const [selectedCategory, setSelectedCategory] = useState<string>("");
```

**수정:**
```typescript
const [selectedCategory, setSelectedCategory] = useState<string>(() => {
  return selectedRegion === "korea" ? "전체" : "all";
});
```

하지만 이것도 근본 원인은 아니었습니다.

### 3차 분석 (진짜 원인): new URL() 사용 오류

**핵심 문제를 발견했습니다!**

`use-posts.ts`에서 모든 API 호출 시 다음과 같이 URL을 생성하고 있었습니다:

```typescript
// 문제 코드
const API_BASE_URL = import.meta.env.MODE === "development"
  ? "http://127.0.0.1:8000"
  : "";

const url = new URL(API_BASE_URL + api.posts.list.path);
```

**프로덕션 환경에서:**
- `API_BASE_URL`이 빈 문자열 `""`
- `new URL("" + "/api/posts")` → `new URL("/api/posts")`
- **JavaScript의 `new URL()`은 상대 경로만 전달하면 에러 발생!**
- 결과: 모든 API 호출이 실패하고, React Query가 데이터를 가져오지 못함

**왜 에러가 보이지 않았나?**
- React Query가 조용히 실패 (silent fail)
- 네트워크 요청 자체가 발생하지 않음
- `isLoading`이 끝나고 `posts`가 빈 배열/undefined
- 따라서 "404 Page Not Found" fallback 메시지 표시

---

## 해결 방법

### 수정 1: URL 생성 방식 개선

모든 API 호출 함수에서 URL 생성 로직을 수정했습니다.

**수정 파일:** `client/src/hooks/use-posts.ts`

#### Before (잘못된 코드):
```typescript
const url = new URL(API_BASE_URL + api.posts.list.path);
```

#### After (올바른 코드):
```typescript
const url = new URL(
  api.posts.list.path,
  API_BASE_URL || window.location.origin
);
```

**핵심 개념:**
```typescript
new URL(path, base)
```
- `path`: 상대 경로 또는 절대 경로
- `base`: 기준이 되는 URL (옵션이지만 상대 경로 사용 시 필수)

**프로덕션에서:**
- `API_BASE_URL`이 빈 문자열이면 `window.location.origin` 사용
- 예: `new URL("/api/posts", "https://news-production-917c.up.railway.app")`
- 결과: `"https://news-production-917c.up.railway.app/api/posts"`

**개발 환경에서:**
- `API_BASE_URL`이 `"http://127.0.0.1:8000"`
- 예: `new URL("/api/posts", "http://127.0.0.1:8000")`
- 결과: `"http://127.0.0.1:8000/api/posts"`

### 수정 2: Fallback 메시지 개선

```typescript
// Before (혼란스러운 메시지)
<p>404 Page Not Found</p>

// After (명확한 메시지)
<p>게시물이 없습니다</p>
```

---

## 적용된 모든 수정 사항

### 1. `client/src/hooks/use-posts.ts`
다음 함수들의 URL 생성 로직 수정:
- `usePosts()` - 게시물 목록 조회
- `usePost()` - 개별 게시물 조회
- `useCreatePost()` - 게시물 생성
- `useLikePost()` - 좋아요
- `useViewPost()` - 조회수 증가
- `useDislikePost()` - 싫어요

### 2. `client/src/pages/Home.tsx`
- `selectedCategory` 초기값 수정
- Fallback 메시지 개선

---

## 기술적 배경 지식

### JavaScript의 new URL() API

```javascript
// 1. 절대 URL - 정상 작동
new URL("https://example.com/api/posts")
// → "https://example.com/api/posts"

// 2. 상대 경로 + base URL - 정상 작동
new URL("/api/posts", "https://example.com")
// → "https://example.com/api/posts"

// 3. 상대 경로만 - 에러 발생!
new URL("/api/posts")
// → TypeError: Failed to construct 'URL': Invalid URL

// 4. 빈 문자열 + 경로 - 에러 발생!
new URL("" + "/api/posts")
// → TypeError: Failed to construct 'URL': Invalid URL
```

### Vite 환경 변수

```typescript
import.meta.env.MODE
```
- **개발 환경**: `"development"` (vite dev server)
- **프로덕션 빌드**: `"production"` (vite build)

---

## 교훈 및 체크리스트

### 배포 전 체크리스트
- [ ] 프로덕션 환경에서 API Base URL이 올바르게 설정되는가?
- [ ] `new URL()` 사용 시 base URL이 제공되는가?
- [ ] 네트워크 탭에서 API 요청이 발생하는가?
- [ ] 브라우저 콘솔에 에러가 없는가?
- [ ] 로컬에서 `npm run build && npm run preview` 테스트 완료했는가?

### 디버깅 팁
1. **증상**: "데이터가 안 보여요"
   - 네트워크 탭 확인 → API 요청이 있는가?
   - 콘솔 확인 → JavaScript 에러가 있는가?
   - API 직접 호출 → 백엔드가 정상인가?

2. **증상**: "API 요청이 안 보내져요"
   - URL 생성 로직 확인
   - React Query 설정 확인
   - 환경 변수 확인

3. **증상**: "로컬에서는 되는데 배포하면 안 돼요"
   - 환경 변수 차이 확인 (`import.meta.env.MODE`)
   - 빌드된 파일 확인 (`dist/` 폴더)
   - Railway 로그 확인

---

## 타임라인

```
문제 발견: Railway 배포 후 "404 Page Not Found"
  ↓
1차 시도: React Router 설정 확인 → 문제 없음
  ↓
2차 시도: selectedCategory 초기값 수정 → 여전히 안 됨
  ↓
3차 분석: 네트워크 탭 확인 → API 요청 없음!
  ↓
근본 원인 발견: new URL() 사용 오류
  ↓
수정: URL 생성 로직 개선
  ↓
✅ 해결: 프로덕션에서 정상 작동
```

---

## 참고 자료

- [MDN - URL() constructor](https://developer.mozilla.org/en-US/docs/Web/API/URL/URL)
- [Vite - Env Variables and Modes](https://vitejs.dev/guide/env-and-mode.html)
- [React Query - Query Functions](https://tanstack.com/query/latest/docs/react/guides/query-functions)
