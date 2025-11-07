from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Iterable, List, Optional

from bson import ObjectId
from bson.errors import InvalidId
from django.conf import settings
from pymongo import MongoClient, ReturnDocument
from pymongo.errors import PyMongoError


@dataclass
class MongoReviewService:
    url: str = settings.MONGO_URL
    db_name: str = settings.MONGO_DB
    _memory_reviews: List[Dict[str, Any]] = field(default_factory=list)

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

    def create_review(self, data: Dict[str, Any]) -> Dict[str, Any]:
        data.setdefault("created_at", datetime.utcnow().isoformat())
        database = self.db()
        if database is None:
            data.setdefault("_id", f"rev-{len(self._memory_reviews) + 1}")
            self._memory_reviews.append(data)
            return data
        inserted = database.reviews.insert_one(data)
        document = dict(data)
        document["_id"] = str(inserted.inserted_id)
        return document

    def list_reviews_for_book(self, book_id: str) -> List[Dict[str, Any]]:
        database = self.db()
        if database is None:
            return [
                review
                for review in self._memory_reviews
                if review.get("book_id") == book_id and not review.get("deleted_at")
            ]
        cursor = database.reviews.find({"book_id": book_id, "deleted_at": {"$exists": False}})
        return self._serialize_many(cursor)

    def update_review(self, review_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        database = self.db()
        if database is None:
            for review in self._memory_reviews:
                if str(review.get("_id")) == str(review_id):
                    review.update(updates)
                    return review
            return None
        document = database.reviews.find_one_and_update(
            {"_id": self._object_id(review_id)},
            {"$set": updates},
            return_document=ReturnDocument.AFTER,
        )
        return self._serialize(document)

    def delete_review(self, review_id: str) -> bool:
        database = self.db()
        if database is None:
            for review in self._memory_reviews:
                if str(review.get("_id")) == str(review_id):
                    review["deleted_at"] = datetime.utcnow().isoformat()
                    return True
            return False
        result = database.reviews.update_one(
            {"_id": self._object_id(review_id)},
            {"$set": {"deleted_at": datetime.utcnow().isoformat()}},
        )
        return result.modified_count > 0

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
mongo_reviews = MongoReviewService()
