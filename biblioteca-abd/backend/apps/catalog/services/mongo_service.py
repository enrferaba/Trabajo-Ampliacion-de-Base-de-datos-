from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from django.conf import settings
from pymongo import MongoClient, ASCENDING, DESCENDING
from pymongo.errors import PyMongoError


@dataclass
class MongoCatalogService:
    url: str = settings.MONGO_URL
    db_name: str = settings.MONGO_DB
    _memory_books: List[Dict[str, Any]] = field(default_factory=list)
    _memory_authors: List[Dict[str, Any]] = field(default_factory=list)

    @property
    def client(self) -> Optional[MongoClient]:
        try:
            return MongoClient(self.url, serverSelectionTimeoutMS=500)
        except PyMongoError:
            return None

    def db(self):
        client = self.client
        if client is None:
            return None
        try:
            client.admin.command("ping")
            return client[self.db_name]
        except PyMongoError:
            return None

    # Persistence helpers
    def ensure_indexes(self) -> None:
        database = self.db()
        if database is None:
            return
        books = database.books
        authors = database.authors
        try:
            books.create_index([("title", "text"), ("synopsis", "text")])
            books.create_index([("genres", ASCENDING), ("year", DESCENDING)])
            books.create_index([("avg_rating", DESCENDING), ("rating_count", DESCENDING)])
            authors.create_index("name", unique=True)
        except PyMongoError:
            pass

    def list_books(self, filters: Dict[str, Any], sort: str, order: str, skip: int, limit: int) -> List[Dict[str, Any]]:
        database = self.db()
        sort_key = "avg_rating" if sort == "rating" else "rating_count"
        sort_direction = DESCENDING if order == "desc" else ASCENDING
        if database is None:
            data = self._apply_filters(self._memory_books, filters)
            return sorted(data, key=lambda x: x.get(sort_key, 0), reverse=sort_direction == DESCENDING)[
                skip : skip + limit
            ]
        cursor = (
            database.books.find(filters)
            .sort([(sort_key, sort_direction)])
            .skip(skip)
            .limit(limit)
        )
        return list(cursor)

    def _apply_filters(self, data: List[Dict[str, Any]], filters: Dict[str, Any]) -> List[Dict[str, Any]]:
        result = data
        if "title" in filters:
            term = filters["title"].lower()
            result = [item for item in result if term in item.get("title", "").lower()]
        if "authors.id" in filters:
            author_id = filters["authors.id"]
            result = [item for item in result if any(a.get("id") == author_id for a in item.get("authors", []))]
        if "genres" in filters:
            genres = set(filters["genres"]) if isinstance(filters["genres"], list) else {filters["genres"]}
            result = [item for item in result if genres.intersection(set(item.get("genres", [])))]
        return result

    def create_book(self, data: Dict[str, Any]) -> Dict[str, Any]:
        database = self.db()
        if database is None:
            data.setdefault("_id", f"mem-{len(self._memory_books) + 1}")
            self._memory_books.append(data)
            return data
        inserted = database.books.insert_one(data)
        data["_id"] = str(inserted.inserted_id)
        return data

    def get_book(self, book_id: str) -> Optional[Dict[str, Any]]:
        database = self.db()
        if database is None:
            for book in self._memory_books:
                if str(book.get("_id")) == str(book_id):
                    return book
            return None
        return database.books.find_one({"_id": book_id})

    def update_book(self, book_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        database = self.db()
        if database is None:
            for book in self._memory_books:
                if str(book.get("_id")) == str(book_id):
                    book.update(updates)
                    return book
            return None
        result = database.books.find_one_and_update({"_id": book_id}, {"$set": updates}, return_document=True)
        return result

    def list_authors(self, filters: Dict[str, Any], skip: int, limit: int) -> List[Dict[str, Any]]:
        database = self.db()
        if database is None:
            data = self._memory_authors
            if "name" in filters:
                term = filters["name"].lower()
                data = [item for item in data if term in item.get("name", "").lower()]
            return data[skip : skip + limit]
        cursor = database.authors.find(filters).skip(skip).limit(limit)
        return list(cursor)

    def create_author(self, data: Dict[str, Any]) -> Dict[str, Any]:
        database = self.db()
        if database is None:
            data.setdefault("_id", f"auth-{len(self._memory_authors) + 1}")
            self._memory_authors.append(data)
            return data
        inserted = database.authors.insert_one(data)
        data["_id"] = str(inserted.inserted_id)
        return data


mongo_service = MongoCatalogService()
