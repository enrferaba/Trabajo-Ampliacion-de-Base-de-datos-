from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List

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
            return [item for item in self._memory_graph["similar"] if item["book_id"] == book_id][:top_k]
        query = (
            "MATCH (b:Book {id: $book_id})-[:SIMILAR_TO]-(other:Book) "
            "RETURN other.id as id, other.title as title, other.cover_url as cover_url ORDER BY other.avg_rating DESC LIMIT $top_k"
        )
        try:
            with driver.session() as session:
                result = session.run(query, book_id=book_id, top_k=top_k)
                return [record.data() for record in result]
        except Neo4jError:
            return []

    def personalized_for_user(self, user_id: str, top_k: int = 10) -> List[Dict[str, Any]]:
        driver = self.driver()
        if driver is None:
            return [item for item in self._memory_graph["user"] if item["user_id"] == user_id][:top_k]
        query = (
            "MATCH (u:User {id: $user_id})-[:REVIEWED]->(:Book)-[:HAS_GENRE]->(g:Genre)<-[:HAS_GENRE]-(rec:Book) "
            "RETURN rec.id as id, rec.title as title LIMIT $top_k"
        )
        try:
            with driver.session() as session:
                result = session.run(query, user_id=user_id, top_k=top_k)
                return [record.data() for record in result]
        except Neo4jError:
            return []

    def upsert_similarity(self, book_id: str, similar_books: List[Dict[str, Any]]) -> None:
        driver = self.driver()
        if driver is None:
            self._memory_graph["similar"].extend(similar_books)
            return
        query = (
            "UNWIND $similar AS sim "
            "MATCH (b:Book {id: $book_id}) "
            "MERGE (other:Book {id: sim.id}) "
            "MERGE (b)-[r:SIMILAR_TO]-(other) "
            "SET r.score = sim.score"
        )
        try:
            with driver.session() as session:
                session.run(query, book_id=book_id, similar=similar_books)
        except Neo4jError:
            pass


neo4j_service = Neo4jService()
