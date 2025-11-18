from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional

from django.conf import settings
from neo4j import GraphDatabase
from neo4j.exceptions import Neo4jError


@dataclass
class Neo4jService:
    uri: str = settings.NEO4J_URI
    user: str = settings.NEO4J_USER
    password: str = settings.NEO4J_PASSWORD
    _memory_graph: Dict[str, List[Dict[str, Any]]] = field(default_factory=lambda: {"similar": [], "user": []})

    def driver(self):
        try:
            return GraphDatabase.driver(self.uri, auth=(self.user, self.password))
        except Neo4jError:
            return None

    def similar_books(self, book_id: str, top_k: int = 10) -> List[Dict[str, Any]]:
        driver = self.driver()
        if driver is None:
            return self._memory_similar(book_id, top_k)
        query = (
            "MATCH (b:Book {id: $book_id})-[:SIMILAR_TO]-(other:Book) "
            "RETURN other.id as id, other.title as title, other.cover_url as cover_url ORDER BY other.avg_rating DESC LIMIT $top_k"
        )
        result = self._run(driver, query, book_id=book_id, top_k=top_k)
        if result is None:
            return []
        return [record.data() for record in result]

    def personalized_for_user(self, user_id: str, top_k: int = 10) -> List[Dict[str, Any]]:
        driver = self.driver()
        if driver is None:
            return self._memory_personalized(user_id, top_k)
        query = (
            "MATCH (u:User {id: $user_id})-[:REVIEWED]->(:Book)-[:HAS_GENRE]->(g:Genre)<-[:HAS_GENRE]-(rec:Book) "
            "RETURN rec.id as id, rec.title as title LIMIT $top_k"
        )
        result = self._run(driver, query, user_id=user_id, top_k=top_k)
        if result is None:
            return []
        return [record.data() for record in result]

    def upsert_similarity(self, book_id: str, similar_books: List[Dict[str, Any]]) -> None:
        driver = self.driver()
        if driver is None:
            self._memory_graph["similar"].extend(
                [dict(item, book_id=book_id) for item in similar_books]
            )
            return
        query = (
            "UNWIND $similar AS sim "
            "MATCH (b:Book {id: $book_id}) "
            "MERGE (other:Book {id: sim.id}) "
            "MERGE (b)-[r:SIMILAR_TO]-(other) "
            "SET r.score = sim.score"
        )
        self._run(driver, query, book_id=book_id, similar=similar_books)


    def _run(
        self,
        driver,
        query: str,
        **parameters: Any,
    ) -> Optional[Iterable[Any]]:
        if driver is None:
            return None
        try:
            with driver.session() as session:
                return session.run(query, **parameters)
        except (Neo4jError, OSError, ValueError):
            return None
        finally:
            driver.close()

    def _memory_similar(self, book_id: str, top_k: int) -> List[Dict[str, Any]]:
        return [
            {key: value for key, value in item.items() if key != "book_id"}
            for item in self._memory_graph["similar"]
            if item.get("book_id") == book_id
        ][:top_k]

    def _memory_personalized(self, user_id: str, top_k: int) -> List[Dict[str, Any]]:
        return [
            {key: value for key, value in item.items() if key != "user_id"}
            for item in self._memory_graph["user"]
            if item.get("user_id") == user_id
        ][:top_k]


neo4j_service = Neo4jService()
