# News App - Architecture Documentation

**Last Updated**: 2026-01-06
**Version**: 2.0.0 (Post-Refactoring)

---

## 📐 Architecture Overview

News App is a full-stack web application with a **Python FastAPI backend** and **React TypeScript frontend**, designed for news aggregation and AI-powered summarization.

### Tech Stack

**Backend**
- **Framework**: FastAPI (Python 3.12)
- **Database**: SQLAlchemy ORM (PostgreSQL/SQLite)
- **AI**: Google Gemini AI
- **Web Scraping**: BeautifulSoup4, Trafilatura
- **News Source**: Google News RSS

**Frontend**
- **Framework**: React 18 + TypeScript
- **Build Tool**: Vite 5
- **UI Library**: Radix UI + Tailwind CSS
- **State Management**: TanStack Query (React Query)
- **Routing**: Wouter

---

## 🏗️ Backend Architecture

### Directory Structure

```
server-python/
├── main.py                    # FastAPI app initialization (116 lines)
└── app/
    ├── core/                  # Configuration & database
    │   ├── config.py         # Environment variables, settings
    │   └── database.py       # SQLAlchemy setup, DB session
    ├── models/               # Database models
    │   └── post.py           # Post model (SQLAlchemy)
    ├── schemas/              # Request/Response schemas
    │   └── post.py           # Pydantic schemas
    ├── services/             # Business logic
    │   ├── ai_summarizer.py      # Google Gemini AI integration
    │   ├── content_extractor.py  # News content scraping
    │   ├── news_crawler.py       # Google News RSS crawler
    │   └── url_decoder.py        # Google News URL decoder
    ├── routers/              # API endpoints
    │   ├── posts.py          # Posts CRUD operations
    │   └── news.py           # News fetching endpoint
    └── utils/                # Utilities
        └── helpers.py        # Helper functions
```

### Module Responsibilities

#### **core/**
- `config.py`: Centralized configuration management
  - Environment variables (API keys, DB URLs)
  - CORS settings
  - Application settings class

- `database.py`: Database layer
  - SQLAlchemy engine and session creation
  - Database dependency injection (`get_db`)
  - Database initialization (`init_db`)

#### **models/**
- `post.py`: SQLAlchemy ORM model
  - Post table schema
  - Database columns and constraints

#### **schemas/**
- `post.py`: Pydantic validation schemas
  - `PostBase`: Base post fields
  - `PostCreate`: Create post request
  - `PostResponse`: API response format

#### **services/**
- `news_crawler.py`: Google News RSS integration
  - `GoogleNewsRSSClient` class
  - Fetches Korea and World news
  - Handles RSS parsing and article extraction

- `content_extractor.py`: Web scraping logic
  - Extracts article content from URLs
  - Site-specific extraction strategies
  - Content cleaning and filtering

- `ai_summarizer.py`: AI summarization
  - Google Gemini API integration
  - Generates 3-4 line summaries

- `url_decoder.py`: URL processing
  - Decodes Google News redirect URLs
  - Extracts original article URLs

#### **routers/**
- `posts.py`: Post management endpoints
  - GET `/api/posts` - List posts with filters
  - GET `/api/posts/{id}` - Get single post
  - POST `/api/posts` - Create post
  - POST `/api/posts/{id}/like` - Like post
  - POST `/api/posts/{id}/dislike` - Dislike post
  - POST `/api/posts/{id}/view` - Increment views

- `news.py`: News fetching endpoint
  - POST `/api/news/fetch` - Fetch latest news

---

## 🎨 Frontend Architecture

### Directory Structure

```
client/
├── src/
│   ├── components/          # Reusable UI components
│   │   └── ui/             # shadcn/ui components
│   ├── hooks/              # Custom React hooks
│   ├── lib/                # Utilities and helpers
│   ├── pages/              # Route components
│   └── App.tsx             # Root component
└── public/                 # Static assets
```

### Key Features

- **Responsive Design**: Mobile-first approach with Tailwind CSS
- **Component Library**: Radix UI primitives with custom styling
- **Type Safety**: Full TypeScript coverage
- **API Integration**: TanStack Query for data fetching and caching
- **Client-side Routing**: Wouter for lightweight routing

---

## 🔄 Data Flow

### News Fetching Process

```
1. User clicks "Fetch News" button
   ↓
2. Frontend sends POST /api/news/fetch
   ↓
3. Backend (news.py router)
   ├─→ GoogleNewsRSSClient.get_korea_news()
   ├─→ GoogleNewsRSSClient.get_world_news()
   ↓
4. For each article:
   ├─→ decode_google_news_url() - Get real URL
   ├─→ extract_news_content() - Scrape content
   ├─→ clean_news_content() - Clean text
   ├─→ generate_ai_summary_google() - AI summary
   ↓
5. Save to database (SQLAlchemy)
   ↓
6. Return success response
   ↓
7. Frontend refreshes post list
```

### Post Display Process

```
1. User navigates to homepage
   ↓
2. Frontend sends GET /api/posts?region=korea
   ↓
3. Backend (posts.py router)
   ├─→ Query database with filters
   ├─→ Order by created_at DESC
   ├─→ Convert to Pydantic schemas
   ↓
4. Return JSON array of posts
   ↓
5. Frontend displays in grid/list
```

---

## 🗄️ Database Schema

### Posts Table

| Column      | Type      | Constraints          | Description                |
|-------------|-----------|----------------------|----------------------------|
| id          | INTEGER   | PRIMARY KEY          | Auto-increment ID          |
| title       | TEXT      | NOT NULL             | Article title              |
| summary     | TEXT      | NOT NULL             | RSS description            |
| content     | TEXT      | NOT NULL             | Full article content       |
| category    | TEXT      | NOT NULL             | Category (정치, 경제, etc.) |
| region      | TEXT      | NOT NULL             | Region (korea, world)      |
| image_url   | TEXT      | NOT NULL             | Article image URL          |
| url         | TEXT      | NULLABLE             | Original article URL       |
| created_at  | TIMESTAMP | DEFAULT NOW()        | Creation timestamp         |
| likes       | INTEGER   | DEFAULT 0            | Like count                 |
| dislikes    | INTEGER   | DEFAULT 0            | Dislike count              |
| views       | INTEGER   | DEFAULT 0            | View count                 |
| ai_summary  | TEXT      | NULLABLE             | AI-generated summary       |

---

## 🔐 Security Considerations

1. **API Key Protection**: Google AI API key stored in `.env`
2. **CORS**: Configured for specific origins only
3. **SQL Injection**: SQLAlchemy ORM prevents injection
4. **Input Validation**: Pydantic schemas validate all inputs
5. **SSL Verification**: Disabled for news scraping (with warnings)

---

## 🚀 Deployment

### Production Setup

1. **Backend**: Deploy to Railway/Heroku with PostgreSQL
2. **Frontend**: Build static files with `npm run build`
3. **Static Serving**: FastAPI serves built frontend from `/dist/public`
4. **Environment Variables**:
   - `DATABASE_URL`: PostgreSQL connection string
   - `GOOGLE_AI_API_KEY`: Gemini API key
   - `PORT`: Server port (default: 8000)

### Build Commands


```bash
# Backend
cd server-python
pip install -r requirements.txt
python main.py

# Frontend
npm install
npm run build

# Combined
npm run dev  # Runs both concurrently
```

---

## 📊 Performance Optimizations

1. **Database Indexing**: Primary key on `id`, server default on `created_at`
2. **Query Filtering**: Database-level filtering for category/region
3. **Content Caching**: TanStack Query caches API responses
4. **Lazy Loading**: Dynamic imports for route components
5. **Build Optimization**: Vite's production build with tree-shaking

---

## 🧪 Testing Strategy

### Backend Testing
- **Unit Tests**: Test individual services (crawler, extractor, summarizer)
- **Integration Tests**: Test API endpoints with test database
- **Manual Testing**: Server startup, health check, API calls

### Frontend Testing
- **Type Checking**: `npm run check` for TypeScript validation
- **Build Verification**: `npm run build` success check
- **Manual Testing**: Browser testing on different screen sizes

---

## 🔮 Future Improvements

1. **Database Migrations**: Add Alembic for schema versioning
2. **Caching Layer**: Redis for frequently accessed data
3. **API Rate Limiting**: Prevent abuse of news fetching
4. **User Authentication**: Add login/registration system
5. **Real-time Updates**: WebSocket for live news updates
6. **Search Optimization**: Full-text search with PostgreSQL
7. **Image Optimization**: CDN integration for faster loading
8. **Monitoring**: Add logging and error tracking (Sentry)

---

## 📚 Related Documentation

- [BUILD_GUIDE.md](./BUILD_GUIDE.md) - Setup and build instructions
- [CLAUDE_OPTIMIZATION_REPORT.md](./CLAUDE_OPTIMIZATION_REPORT.md) - Optimization details
- [TROUBLESHOOTING_HISTORY.md](./TROUBLESHOOTING_HISTORY.md) - Common issues

---

**Note**: This architecture reflects the post-refactoring state (Phase 1 & 2 complete). The modular structure significantly improves maintainability compared to the original monolithic `main.py`.
