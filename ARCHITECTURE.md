# Book Intelligence Platform: Implementation and Architecture

## Overview
The Book Intelligence Platform is a full-stack web application designed for AI-powered book discovery, scraping, storage, and interactive Q&A using Retrieval-Augmented Generation (RAG). It combines modern web technologies with AI/ML services to enable users to scrape book data from websites, store embeddings for semantic search, and query their library intelligently.

## Architecture

### High-Level Design
- **Client Layer**: React 18 + Vite + Tailwind CSS (responsive UI).
- **API Layer**: FastAPI (async Python backend) with automatic OpenAPI docs at `/docs`.
- **Data Layer**: MongoDB (metadata, full-text search), ChromaDB (vector embeddings).
- **AI Layer**: LLM integration (Gemini 1.5/Groq) for insights, summaries, recommendations.
- **Processing Layer**: Background scraping with Selenium/BeautifulSoup.

**Data Flow**:
1. User triggers scrape → `scraper.py` fetches book details → Store in MongoDB → Embed text → Persist in ChromaDB.
2. Q&A query → RAG pipeline retrieves relevant chunks → LLM generates answer with citations.
3. Recommendations → Vector similarity search in ChromaDB + genre fallback.

### Backend Implementation (FastAPI)
- **Routers** (`app/routers/books.py`): CRUD for books, `/scrape`, `/ask`, `/recommendations`.
- **Services**:
  - `llm_service.py`: Abstracts Gemini/Groq API calls.
  - `rag_service.py`: Retrieval from Chroma + prompt engineering.
  - `scraper.py`: Genre-based web scraping (e.g., sci-fi books).
- **Utils**: `database.py` (Motor async Mongo client), config via Pydantic.
- **Health Checks**: `/health` verifies Mongo, Chroma, LLM.

**Key Features Implemented**:
- **RAG Q&A**: Query Chroma for top-k chunks, feed to LLM with context.
- **Embeddings**: Sentence transformers or LLM embeddings stored persistently.
- **Scalability**: Async endpoints, background Celery tasks for scraping.

### Frontend Implementation (React)
- **Pages**: Dashboard (stats/search), BookDetail (insights/recs), QnA (chat interface), ScrapeModal.
- **Components**: BookCard, Skeletons (loading).
- **API Utils**: `api.js` fetches with auth/token handling.
- **State**: React hooks + TanStack Query for caching.

### Deployment & Extensibility
- Local: `uvicorn` backend, `npm run dev` frontend.
- Env vars: API keys, DB URLs configurable.
- Future: Docker, user auth (JWT), multi-LLM, advanced analytics.

**Word Count**: 278

*Optimized for performance, modularity, and developer experience.*

