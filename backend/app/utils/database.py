"""
MongoDB connection and CRUD helpers using Motor (async).
"""

import motor.motor_asyncio
from bson import ObjectId
from typing import Optional, List, Dict, Any
from datetime import datetime

from app.config import settings

# Global client
client: Optional[motor.motor_asyncio.AsyncIOMotorClient] = None
db = None


async def connect_db():
    """Create MongoDB connection on startup."""
    global client, db
    try:
        client = motor.motor_asyncio.AsyncIOMotorClient(
            settings.MONGODB_URL,
            serverSelectionTimeoutMS=5000  # fail fast
        )
        db = client[settings.DATABASE_NAME]

        # 🔥 VERY IMPORTANT: force connection check
        await client.admin.command("ping")

        # Create indexes
        await db.books.create_index("title")
        await db.books.create_index("author")
        await db.books.create_index("genre")
        await db.books.create_index("created_at")

        print(f"✅ Connected to MongoDB: {settings.DATABASE_NAME}")

    except Exception as e:
        print("❌ MongoDB Connection Failed:", e)
        raise e   # stop app if DB fails

async def disconnect_db():
    """Close MongoDB connection on shutdown."""
    global client
    if client:
        client.close()
        print("MongoDB connection closed.")


def get_db():
    """Return the database instance."""
    if db is None:
        raise Exception("Database not initialized. Did you call connect_db()?")

    return db


def doc_to_dict(doc: Dict) -> Dict:
    """Convert MongoDB document to JSON-serializable dict."""
    if doc is None:
        return None
    doc["id"] = str(doc.pop("_id"))
    return doc


# ── Books CRUD ──────────────────────────────────────────────────────────────

async def create_book(book_data: Dict) -> Dict:
    """Insert a new book document."""
    book_data["created_at"] = datetime.utcnow()
    book_data["embedding_stored"] = False
    result = await db.books.insert_one(book_data)
    created = await db.books.find_one({"_id": result.inserted_id})
    return doc_to_dict(created)


async def get_book_by_id(book_id: str) -> Optional[Dict]:
    """Fetch a single book by its ID."""
    try:
        doc = await db.books.find_one({"_id": ObjectId(book_id)})
        return doc_to_dict(doc) if doc else None
    except Exception:
        return None


async def get_book_by_url(url: str) -> Optional[Dict]:
    """Fetch a book by its source URL (deduplication)."""
    doc = await db.books.find_one({"book_url": url})
    return doc_to_dict(doc) if doc else None


async def get_all_books(
    page: int = 1,
    page_size: int = 20,
    genre: Optional[str] = None,
    search: Optional[str] = None,
) -> Dict:
    """List books with pagination, optional genre/search filter."""
    query: Dict[str, Any] = {}

    if genre:
        query["genre"] = {"$regex": genre, "$options": "i"}

    if search:
        query["$or"] = [
            {"title": {"$regex": search, "$options": "i"}},
            {"author": {"$regex": search, "$options": "i"}},
        ]

    total = await db.books.count_documents(query)
    skip = (page - 1) * page_size

    cursor = db.books.find(query).sort("created_at", -1).skip(skip).limit(page_size)
    books = [doc_to_dict(doc) async for doc in cursor]

    return {"books": books, "total": total, "page": page, "page_size": page_size}


async def update_book(book_id: str, update_data: Dict) -> Optional[Dict]:
    """Partially update a book document."""
    try:
        await db.books.update_one(
            {"_id": ObjectId(book_id)}, {"$set": update_data}
        )
        return await get_book_by_id(book_id)
    except Exception:
        return None


async def get_books_by_genre(genre: str, exclude_id: str, limit: int = 5) -> List[Dict]:
    """Get books in the same genre, excluding a given book."""
    try:
        cursor = db.books.find(
            {
                "genre": {"$regex": genre, "$options": "i"},
                "_id": {"$ne": ObjectId(exclude_id)},
            }
        ).limit(limit)
        return [doc_to_dict(doc) async for doc in cursor]
    except Exception:
        return []


async def get_genres() -> List[str]:
    """Return distinct genre values."""
    return await db.books.distinct("genre")


async def get_book_count() -> int:
    """Return total number of books."""
    return await db.books.count_documents({})
