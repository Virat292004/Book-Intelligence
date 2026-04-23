# Book Intelligence Platform

Book Intelligence Platform is a full-stack AI web application for collecting book data, storing it in a searchable database, generating AI insights, and answering questions over the book collection using RAG (Retrieval-Augmented Generation).

The project uses a React + Vite frontend, a FastAPI backend, MongoDB for book metadata, ChromaDB for vector search, SentenceTransformers for embeddings, and Gemini/Groq through LangChain for AI answers and recommendations.

## Features

- Scrape book data from `books.toscrape.com`
- Store book details such as title, author, genre, rating, price, cover image, URL, and description
- Generate AI insights for each book, including summary, genre classification, sentiment, and key themes
- Store semantic embeddings in ChromaDB for vector search
- Ask natural-language questions about the book collection
- Show answer sources with relevance scores and excerpts
- Recommend similar books using vector similarity with genre fallback
- Search and filter books from the dashboard
- View book details, recommendations, and Q&A in a React UI

## Tech Stack

### Frontend

- React 18
- Vite
- Tailwind CSS
- React Router
- TanStack React Query
- Axios
- Lucide React icons

### Backend

- FastAPI
- Pydantic
- Motor async MongoDB driver
- MongoDB
- ChromaDB
- SentenceTransformers
- LangChain
- Gemini or Groq LLM
- BeautifulSoup and Requests for scraping

## Project Structure

```text
book-intelligence/
|-- backend/
|   |-- main.py
|   |-- requirements.txt
|   |-- app/
|   |   |-- config.py
|   |   |-- models/
|   |   |   `-- schemas.py
|   |   |-- routers/
|   |   |   `-- books.py
|   |   |-- services/
|   |   |   |-- scraper.py
|   |   |   |-- llm_service.py
|   |   |   `-- rag_service.py
|   |   `-- utils/
|   |       `-- database.py
|   `-- chroma_db/
|-- frontend/
|   |-- package.json
|   |-- vite.config.js
|   |-- src/
|   |   |-- App.jsx
|   |   |-- main.jsx
|   |   |-- components/
|   |   |-- pages/
|   |   `-- utils/api.js
|-- assets/
|   |-- dashboard.png
|   |-- details.png
|   `-- qna.png
|-- ARCHITECTURE.md
|-- TODO.md
`-- README.md
```

## Prerequisites

Install these before running the project:

- Python 3.10 or higher
- Node.js 18 or higher
- MongoDB local server or MongoDB Atlas connection string
- Gemini API key or Groq API key

## Environment Variables

Create `backend/.env`:

```env
MONGODB_URL=mongodb://localhost:27017
DATABASE_NAME=book_intelligence
GEMINI_API_KEY=your_gemini_api_key
GROQ_API_KEY=
LLM_PROVIDER=gemini
CHROMA_DB_PATH=./chroma_db
ALLOWED_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
```

Create `frontend/.env`:

```env
VITE_API_URL=http://localhost:8000
```

If you want to use Groq instead of Gemini, set:

```env
LLM_PROVIDER=groq
GROQ_API_KEY=your_groq_api_key
```

## How to Run

### 1. Start MongoDB

If MongoDB is installed locally, start the MongoDB service. The backend expects MongoDB at:

```text
mongodb://localhost:27017
```

You can also use MongoDB Atlas by replacing `MONGODB_URL` in `backend/.env`.

### 2. Run the Backend

```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

Backend runs at:

```text
http://localhost:8000
```

API documentation:

```text
http://localhost:8000/docs
```

Health check:

```text
http://localhost:8000/health
```

### 3. Run the Frontend

Open a second terminal:

```bash
cd frontend
npm install
npm run dev
```

Frontend runs at:

```text
http://localhost:5173
```

## How the Project Works Step by Step

### Step 1: User opens the frontend

The React app starts from `frontend/src/main.jsx` and loads routes from `frontend/src/App.jsx`.

Routes:

- `/` opens the dashboard
- `/books/:id` opens a book detail page
- `/ask` opens the Q&A page

The dashboard calls backend APIs through `frontend/src/utils/api.js`.

### Step 2: User imports books

On the dashboard, the user clicks `Import Books`. This opens `ScrapeModal.jsx`.

The frontend sends a POST request:

```text
POST /api/books/scrape
```

Example request body:

```json
{
  "max_pages": 3,
  "genre_filter": "Travel"
}
```

### Step 3: FastAPI starts the scraping pipeline

The route is handled in:

```text
backend/app/routers/books.py
```

The backend starts `_scrape_pipeline()` as a background task, so the API responds quickly while scraping continues in the background.

### Step 4: Scraper collects book data

Scraping logic is inside:

```text
backend/app/services/scraper.py
```

The scraper visits `books.toscrape.com`, reads category pages, extracts book cards, and collects:

- title
- rating
- price
- cover image
- book detail URL
- genre
- description from the detail page

Because the source website does not provide author names on listing pages, author is stored as `Unknown`.

### Step 5: Backend avoids duplicate books

Before saving a scraped book, the backend checks MongoDB using the book URL.

If the same URL already exists, the book is skipped.

### Step 6: LLM generates AI insights

For each new book, `llm_service.py` sends the book title, genre, description, and rating to Gemini or Groq.

The LLM returns structured JSON:

- summary
- genre classification
- sentiment
- sentiment score
- key themes

If the LLM fails, the app uses fallback insights so the scrape does not stop.

### Step 7: Book is saved in MongoDB

MongoDB logic is inside:

```text
backend/app/utils/database.py
```

The book is inserted into the `books` collection. MongoDB stores normal book metadata and AI insights.

Indexes are created on:

- title
- author
- genre
- created_at

These help search, filtering, and sorting.

### Step 8: Text is converted into embeddings

RAG logic is inside:

```text
backend/app/services/rag_service.py
```

The app combines important book fields into one text document:

- title
- author
- genre
- description
- AI summary
- key themes
- sentiment

Then the text is split into overlapping chunks.

Each chunk is converted into an embedding using:

```text
sentence-transformers/all-MiniLM-L6-v2
```

### Step 9: Embeddings are stored in ChromaDB

The embeddings are stored in a persistent ChromaDB collection called:

```text
book_chunks
```

Each chunk stores metadata:

- book ID
- title
- author
- genre
- chunk index

MongoDB stores book records. ChromaDB stores searchable semantic vectors.

### Step 10: Dashboard displays books

The dashboard calls:

```text
GET /api/books/
GET /api/books/genres
GET /api/books/stats
```

Users can:

- search by title or author
- filter by genre
- paginate books
- open a book detail page
- import more books

### Step 11: User asks a question

The Q&A page sends:

```text
POST /api/books/ask
```

Example:

```json
{
  "question": "Which books are good for beginners?"
}
```

The request can also include a `book_id` to ask about one specific book.

### Step 12: RAG retrieves relevant chunks

The backend embeds the user's question and searches ChromaDB for the most similar chunks.

This is semantic search, so the question does not need to use the exact same words as the book description.

### Step 13: LLM creates the final answer

The top matching chunks are sent to the LLM as background information.

The LLM writes a natural answer based on the retrieved book data.

The API returns:

- answer
- source books
- relevance score
- excerpt
- model used

### Step 14: Frontend shows answer with sources

`QnA.jsx` displays the assistant answer and lets the user expand sources.

This makes the system explainable because the user can see which books were used to answer.

### Step 15: Recommendations

For a book detail page, the frontend calls:

```text
GET /api/books/{book_id}/recommendations
```

The backend first tries vector similarity. If that fails or returns too few books, it falls back to same-genre recommendations.

The LLM can also generate a short reason explaining why the recommendation is relevant.

## Main API Endpoints

| Method | Endpoint | Purpose |
| --- | --- | --- |
| GET | `/` | Basic API info |
| GET | `/health` | Check MongoDB, ChromaDB, and LLM status |
| GET | `/api/books/` | List books with pagination, search, and genre filters |
| GET | `/api/books/genres` | Get all available genres |
| GET | `/api/books/stats` | Get total books, genres, chunks, and LLM model |
| GET | `/api/books/{book_id}` | Get one book's details |
| GET | `/api/books/{book_id}/recommendations` | Get similar books |
| POST | `/api/books/scrape` | Start book scraping in the background |
| POST | `/api/books/ask` | Ask a RAG-based question |

## Important Files Explained

### `backend/main.py`

Creates the FastAPI app, configures CORS, connects to MongoDB on startup, disconnects on shutdown, registers routers, and exposes health endpoints.

### `backend/app/config.py`

Loads environment variables such as MongoDB URL, database name, LLM keys, provider choice, ChromaDB path, and allowed frontend origins.

### `backend/app/models/schemas.py`

Defines Pydantic models for request and response validation. This keeps API data structured and prevents invalid input.

### `backend/app/routers/books.py`

Contains the main API endpoints for listing books, scraping, Q&A, recommendations, genres, and stats.

### `backend/app/services/scraper.py`

Scrapes books from `books.toscrape.com` using Requests and BeautifulSoup.

### `backend/app/services/llm_service.py`

Connects to Gemini or Groq using LangChain. It generates book insights, answers questions, and creates recommendation reasons.

### `backend/app/services/rag_service.py`

Builds book text, chunks it, creates embeddings, stores them in ChromaDB, performs semantic search, and finds similar books.

### `backend/app/utils/database.py`

Handles MongoDB connection and CRUD functions for books.

### `frontend/src/utils/api.js`

Creates the Axios client and defines frontend functions for calling backend APIs.

### `frontend/src/pages/Dashboard.jsx`

Shows the book library, search, filters, pagination, refresh, and import action.

### `frontend/src/pages/QnA.jsx`

Implements the chat-style RAG Q&A interface.

### `frontend/src/pages/BookDetail.jsx`

Shows a selected book with details, AI insights, and recommendations.

## Data Flow Diagram

```text
React UI
  |
  | Axios API calls
  v
FastAPI backend
  |
  | scrape request
  v
books.toscrape.com
  |
  | parsed book data
  v
LLM insights generation
  |
  | book metadata
  v
MongoDB
  |
  | book text
  v
SentenceTransformer embeddings
  |
  | vectors + chunk metadata
  v
ChromaDB
  |
  | semantic search
  v
LLM answer generation
  |
  | answer + sources
  v
React Q&A page
```

## Example User Flow

1. Start MongoDB.
2. Run the backend at `http://localhost:8000`.
3. Run the frontend at `http://localhost:5173`.
4. Open the dashboard.
5. Click `Import Books`.
6. Select a genre or scrape default categories.
7. Wait while books are scraped, analyzed, saved, and embedded.
8. Browse the library.
9. Open a book detail page.
10. Ask questions from the `Ask the Library` page.
11. Read answers with source citations.
12. Use recommendations to discover similar books.

## Troubleshooting

### Backend cannot connect to MongoDB

Make sure MongoDB is running or update `MONGODB_URL` in `backend/.env`.

### Q&A says there is not enough indexed data

Scrape books first. The app needs ChromaDB embeddings before RAG answers can work.

### LLM model says "Not configured"

Add `GEMINI_API_KEY` or `GROQ_API_KEY` to `backend/.env`.

### Frontend cannot call backend

Check `frontend/.env`:

```env
VITE_API_URL=http://localhost:8000
```

Also confirm the backend is running.

### `/api/health` fails from frontend

The backend health route is `/health`, not `/api/health`. Use `http://localhost:8000/health` directly for checking backend status.

## Resume Points for Overleaf

You can add this project to your Overleaf resume under `PROJECTS`.

### Short Version

```latex
\resumeProjectHeading
{\textbf{Book Intelligence Platform} $|$ \emph{React, FastAPI, MongoDB, ChromaDB, LangChain, Gemini/Groq, RAG}}{2026}
\resumeItemListStart
  \resumeItem{Built a full-stack AI book discovery platform with scraping, semantic search, RAG-based Q\&A, and source-backed answers.}
  \resumeItem{Implemented a FastAPI backend with MongoDB for metadata storage and ChromaDB vector embeddings for similarity search.}
  \resumeItem{Integrated Gemini/Groq through LangChain to generate summaries, sentiment, key themes, and recommendation reasons.}
  \resumeItem{Developed a React + Tailwind dashboard for importing books, filtering genres, viewing details, and chatting with the library.}
\resumeItemListEnd
```

### Stronger Version With Metrics

Use this if you can honestly verify the numbers after testing:

```latex
\resumeProjectHeading
{\textbf{Book Intelligence Platform} $|$ \emph{React, FastAPI, MongoDB, ChromaDB, LangChain, Gemini/Groq, RAG}}{2026}
\resumeItemListStart
  \resumeItem{Developed an AI-powered book intelligence system that scrapes book data, stores metadata, generates embeddings, and enables RAG-based Q\&A.}
  \resumeItem{Designed FastAPI APIs for scraping, search, recommendations, health checks, and question answering with source citations.}
  \resumeItem{Used ChromaDB and SentenceTransformers to retrieve top relevant book chunks for semantic search and LLM-grounded answers.}
  \resumeItem{Built a responsive React + Tailwind interface with dashboard search, genre filters, book detail pages, and chat-style Q\&A.}
\resumeItemListEnd
```

### One-Line Project Description

```latex
\textbf{Book Intelligence Platform}: Full-stack RAG application that scrapes books, stores metadata in MongoDB, indexes embeddings in ChromaDB, and answers natural-language questions with source citations.
```

### Skills to Add

Add these only if they fit your resume layout:

```text
FastAPI, React, MongoDB, ChromaDB, LangChain, Gemini API, Groq API, RAG, Vector Search, Web Scraping, BeautifulSoup, SentenceTransformers, Tailwind CSS
```

### Better Resume Wording

Instead of writing:

```text
Made book website using AI
```

Write:

```text
Built a full-stack RAG-based book intelligence platform with semantic search, AI-generated insights, and source-backed Q&A.
```

## Interview Explanation

If an interviewer asks how this project works, answer like this:

```text
This is a full-stack AI project. The React frontend lets users import books, browse the library, and ask questions. The FastAPI backend scrapes book data from books.toscrape.com, stores metadata in MongoDB, generates AI insights using Gemini or Groq, and creates embeddings using SentenceTransformers. These embeddings are stored in ChromaDB. When a user asks a question, the backend retrieves the most relevant book chunks from ChromaDB and sends them with the question to the LLM. The final answer is returned with source citations, so the user can see which books supported the response.
```

## Future Improvements

- Add authentication and saved user libraries
- Add Docker setup for easier deployment
- Add support for more book sources
- Improve scraping to collect author names from richer sources
- Add tests for backend APIs
- Add deployment configuration for Render, Railway, Vercel, or Docker Compose
- Add conversation history for Q&A
- Add admin controls for re-indexing embeddings

