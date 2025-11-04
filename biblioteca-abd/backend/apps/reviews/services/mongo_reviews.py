from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from django.conf import settings
from pymongo import MongoClient
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
        data["_id"] = str(inserted.inserted_id)
        return data

    def list_reviews_for_book(self, book_id: str) -> List[Dict[str, Any]]:
        database = self.db()
        if database is None:
            return [review for review in self._memory_reviews if review.get("book_id") == book_id and not review.get("deleted_at")]
        return list(database.reviews.find({"book_id": book_id, "deleted_at": {"$exists": False}}))

    def update_review(self, review_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        database = self.db()
        if database is None:
            for review in self._memory_reviews:
                if str(review.get("_id")) == str(review_id):
                    review.update(updates)
                    return review
            return None
        return database.reviews.find_one_and_update({"_id": review_id}, {"$set": updates}, return_document=True)

    def delete_review(self, review_id: str) -> bool:
        database = self.db()
        if database is None:
            for review in self._memory_reviews:
                if str(review.get("_id")) == str(review_id):
                    review["deleted_at"] = datetime.utcnow().isoformat()
                    return True
            return False
        result = database.reviews.update_one({"_id": review_id}, {"$set": {"deleted_at": datetime.utcnow().isoformat()}})
        return result.modified_count > 0


mongo_reviews = MongoReviewService()
