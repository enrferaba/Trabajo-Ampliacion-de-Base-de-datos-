from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional

from bson import ObjectId
from bson.errors import InvalidId
from django.conf import settings
from pymongo import ASCENDING, DESCENDING, MongoClient, ReturnDocument
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

    def list_books(
        self, filters: Dict[str, Any], sort: str, order: str, skip: int, limit: int
    ) -> List[Dict[str, Any]]:
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
        return self._serialize_many(cursor)

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
        data_copy = dict(data)
        data_copy["_id"] = str(inserted.inserted_id)
        return data_copy

    def get_book(self, book_id: str) -> Optional[Dict[str, Any]]:
        database = self.db()
        if database is None:
            for book in self._memory_books:
                if str(book.get("_id")) == str(book_id):
                    return book
            return None
        result = database.books.find_one({"_id": self._object_id(book_id)})
        return self._serialize(result)

    def update_book(self, book_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        database = self.db()
        if database is None:
            for book in self._memory_books:
                if str(book.get("_id")) == str(book_id):
                    book.update(updates)
                    return book
            return None
        result = database.books.find_one_and_update(
            {"_id": self._object_id(book_id)},
            {"$set": updates},
            return_document=ReturnDocument.AFTER,
        )
        return self._serialize(result)

    def list_authors(self, filters: Dict[str, Any], skip: int, limit: int) -> List[Dict[str, Any]]:
        database = self.db()
        if database is None:
            data = self._memory_authors
            if "name" in filters:
                term = filters["name"].lower()
                data = [item for item in data if term in item.get("name", "").lower()]
            return data[skip : skip + limit]
        cursor = database.authors.find(filters).skip(skip).limit(limit)
        return self._serialize_many(cursor)

    def create_author(self, data: Dict[str, Any]) -> Dict[str, Any]:
        database = self.db()
        if database is None:
            data.setdefault("_id", f"auth-{len(self._memory_authors) + 1}")
            self._memory_authors.append(data)
            return data
        inserted = database.authors.insert_one(data)
        data_copy = dict(data)
        data_copy["_id"] = str(inserted.inserted_id)
        return data_copy

    def _serialize_many(self, documents: Iterable[Dict[str, Any]] | None) -> List[Dict[str, Any]]:
        if not documents:
            return []
        return [self._serialize(document) for document in documents if document is not None]

    def _serialize(self, document: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        if document is None:
            return None
        serialized = dict(document)
        if "_id" in serialized:
            serialized["_id"] = str(serialized["_id"])
        return serialized

    def _object_id(self, value: Any) -> Any:
        if isinstance(value, ObjectId):
            return value
        try:
            return ObjectId(str(value))
        except (InvalidId, TypeError):
            return value
mongo_service = MongoCatalogService()
