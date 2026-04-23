"""
Books API Router
Endpoints:
  GET  /api/books/          - list all books (paginated)
  GET  /api/books/{id}      - book detail
  GET  /api/books/{id}/recommendations - related books
  GET  /api/books/genres    - list distinct genres
  POST /api/books/scrape    - trigger scraping pipeline
  POST /api/books/ask       - RAG Q&A
"""

import logging
from typing import Optional
from fastapi import APIRouter, HTTPException, Query, BackgroundTasks

from app.models.schemas import (
    BookListResponse,
    BookResponse,
    ScrapeRequest,
    ScrapeResponse,
    QuestionRequest,
    QuestionResponse,
    RecommendationResponse,
    SourceCitation,
)
from app.utils.database import (
    get_all_books,
    get_book_by_id,
    create_book,
    update_book,
    get_book_by_url,
    get_books_by_genre,
    get_genres,
    get_book_count,
)
from app.services.scraper import scrape_books
from app.services.llm_service import (
    generate_book_insights,
    answer_question_with_context,
    get_recommendation_reason,
    get_llm_model_name,
)
from app.services.rag_service import (
    store_book_embeddings,
    search_similar_chunks,
    find_similar_books,
)

router = APIRouter(prefix="/api/books", tags=["Books"])
logger = logging.getLogger(__name__)


# ── GET /api/books/ ──────────────────────────────────────────────────────────

@router.get("/", response_model=BookListResponse)
async def list_books(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    genre: Optional[str] = Query(default=None),
    search: Optional[str] = Query(default=None),
):
    """List all books with optional filtering and pagination."""
    result = await get_all_books(page=page, page_size=page_size, genre=genre, search=search)
    return result


# ── GET /api/books/genres ────────────────────────────────────────────────────

@router.get("/genres")
async def list_genres():
    """Return all distinct genres in the database."""
    genres = await get_genres()
    return {"genres": sorted([g for g in genres if g])}


# ── GET /api/books/stats ─────────────────────────────────────────────────────

@router.get("/stats")
async def get_stats():
    """Return high-level stats about the book database."""
    from app.services.rag_service import get_collection_stats
    total = await get_book_count()
    genres = await get_genres()
    rag_stats = get_collection_stats()
    return {
        "total_books": total,
        "total_genres": len([g for g in genres if g]),
        "rag_chunks": rag_stats.get("total_chunks", 0),
        "llm_model": get_llm_model_name(),
    }


# ── GET /api/books/{id} ───────────────────────────────────────────────────────

@router.get("/{book_id}", response_model=BookResponse)
async def get_book(book_id: str):
    """Get full details of a single book by ID."""
    book = await get_book_by_id(book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    return book


# ── GET /api/books/{id}/recommendations ──────────────────────────────────────

@router.get("/{book_id}/recommendations", response_model=list[RecommendationResponse])
async def get_recommendations(book_id: str, limit: int = Query(default=5, ge=1, le=10)):
    """
    Get book recommendations.
    Strategy:
      1. Try vector-based similarity search first.
      2. Fall back to genre-based matching.
    """
    book = await get_book_by_id(book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")

    recommendations = []

    # Attempt vector similarity
    try:
        all_books_data = await get_all_books(page=1, page_size=200)
        all_ids = [b["id"] for b in all_books_data["books"] if b["id"] != book_id]

        similar = find_similar_books(book_id, all_ids, n=limit)

        for sim_id, score in similar:
            sim_book = await get_book_by_id(sim_id)
            if not sim_book:
                continue
            reason = get_recommendation_reason(book, sim_book)
            recommendations.append(
                RecommendationResponse(
                    book_id=sim_id,
                    title=sim_book.get("title", ""),
                    author=sim_book.get("author", ""),
                    genre=sim_book.get("genre"),
                    rating=sim_book.get("rating"),
                    cover_image=sim_book.get("cover_image"),
                    reason=reason,
                    similarity_score=score,
                )
            )
    except Exception as e:
        logger.warning(f"Vector rec failed, falling back to genre: {e}")

    # Fill remaining with genre-based if needed
    if len(recommendations) < limit and book.get("genre"):
        genre_books = await get_books_by_genre(
            book["genre"], book_id, limit=limit - len(recommendations)
        )
        existing_ids = {r.book_id for r in recommendations}
        for gb in genre_books:
            if gb["id"] not in existing_ids:
                reason = get_recommendation_reason(book, gb)
                recommendations.append(
                    RecommendationResponse(
                        book_id=gb["id"],
                        title=gb.get("title", ""),
                        author=gb.get("author", ""),
                        genre=gb.get("genre"),
                        rating=gb.get("rating"),
                        cover_image=gb.get("cover_image"),
                        reason=reason,
                        similarity_score=0.5,
                    )
                )

    return recommendations[:limit]


# ── POST /api/books/scrape ────────────────────────────────────────────────────

@router.post("/scrape", response_model=ScrapeResponse)
async def scrape_and_store(request: ScrapeRequest, background_tasks: BackgroundTasks):
    """
    Trigger scraping in background (non-blocking)
    """
    logger.info(f"Scrape triggered: max_pages={request.max_pages}")

    background_tasks.add_task(
        _scrape_pipeline,
        request.max_pages,
        request.genre_filter
    )

    return ScrapeResponse(
        message="Scraping started in background",
        books_scraped=0,
        books_added=0,
    )

async def _scrape_pipeline(max_pages: int, genre_filter: str | None):
    """
    Full scraping pipeline (runs in background)
    """
    try:
        scraped_books = scrape_books(
            max_pages=max_pages,
            genre_filter=genre_filter,
        )

        added = 0

        for raw_book in scraped_books:

            # Deduplicate
            existing = await get_book_by_url(raw_book.get("book_url", ""))
            if existing:
                continue

            # Generate AI insights (slow but OK in background)
            try:
                insights = generate_book_insights(raw_book)
                raw_book["ai_insights"] = insights
            except Exception as e:
                logger.warning(f"Insight failed: {e}")
                raw_book["ai_insights"] = {}

            # Save to DB
            created = await create_book(raw_book)
            added += 1

            # Store embeddings (also async)
            await _store_embeddings_task(created)

        logger.info(f"✅ Scraping finished. Added {added} books")

    except Exception as e:
        logger.error(f"❌ Scraping pipeline failed: {e}")
        
async def _store_embeddings_task(book: dict):
    """Background task: store book embeddings in ChromaDB."""
    try:
        success = store_book_embeddings(book)
        if success:
            await update_book(book["id"], {"embedding_stored": True})
    except Exception as e:
        logger.error(f"Background embedding task failed for {book.get('id')}: {e}")


# ── POST /api/books/ask ───────────────────────────────────────────────────────

@router.post("/ask", response_model=QuestionResponse)
async def ask_question(request: QuestionRequest):
    """
    RAG Q&A endpoint.
    1. Embed the user's question
    2. Retrieve similar book chunks from ChromaDB
    3. Send context + question to LLM
    4. Return answer with source citations
    """
    logger.info(f"Q&A request: {request.question[:80]}")

    # Retrieve similar chunks
    chunks = search_similar_chunks(
        query=request.question,
        n_results=5,
        book_id_filter=request.book_id,
    )

    if not chunks:
        # No embeddings yet - try with all books as context
        return QuestionResponse(
            question=request.question,
            answer=(
                "I don't have enough indexed book data to answer that question yet. "
                "Please scrape some books first using the /api/books/scrape endpoint, "
                "then try again after embeddings are generated."
            ),
            sources=[],
            model_used=get_llm_model_name(),
        )

    # Generate answer via LLM
    answer = answer_question_with_context(request.question, chunks)

    # Build source citations (deduplicate by book)
    seen_books = set()
    sources = []
    for chunk in chunks:
        bid = chunk["book_id"]
        if bid not in seen_books:
            seen_books.add(bid)
            sources.append(
                SourceCitation(
                    book_id=bid,
                    title=chunk["title"],
                    author=chunk["author"],
                    relevance_score=chunk["score"],
                    excerpt=chunk["text"][:200] + "..." if len(chunk["text"]) > 200 else chunk["text"],
                )
            )

    return QuestionResponse(
        question=request.question,
        answer=answer,
        sources=sources,
        model_used=get_llm_model_name(),
    )
