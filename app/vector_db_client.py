from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct, VectorParams, Distance
from typing import List, Dict
import uuid
import os

class QdrantDB:
    def __init__(self,
                 host: str = None,
                 port: int = None,
                 base_collection: str = "user_",
                 vector_size: int = 768,
                 distance: Distance = Distance.COSINE):
        self.base_collection = base_collection
        self.vector_size = vector_size
        self.distance = distance
        
        # Use environment variables if not provided
        host = host or os.getenv("QDRANT_HOST", "localhost")
        port = port or int(os.getenv("QDRANT_PORT", "6333"))
        
        self.client = QdrantClient(host=host, port=port)

    def _get_collection_name(self, user_id: str) -> str:
        return f"{self.base_collection}{user_id}"

    def _ensure_collection(self, user_id: str):
        collection_name = self._get_collection_name(user_id)
        collections = [c.name for c in self.client.get_collections().collections]
        if collection_name not in collections:
            print(f"Create new collection for user: {collection_name}")
            self.client.recreate_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(
                    size=self.vector_size,
                    distance=self.distance
                )
            )
        return collection_name

    def upsert_one(self, user_id: str, vector: List[float], payload: Dict):
        collection_name = self._ensure_collection(user_id)
        point = PointStruct(
            id=str(uuid.uuid4()),
            vector=vector,
            payload=payload
        )
        self.client.upsert(collection_name=collection_name, points=[point])
        print(f"Add vector to collection '{collection_name}'")

    def search_one(self, user_id: str, query_vector: List[float], limit: int = 5):
        collection_name = self._ensure_collection(user_id)
        collection_name = self._get_collection_name(user_id)
        results = self.client.search(
            collection_name=collection_name,
            query_vector=query_vector,
            limit=limit
        )
        return [
            {"id": r.id, "score": r.score, "payload": r.payload}
            for r in results
        ]

    def list_points(self, user_id: str, limit: int = 10):
        collection_name = self._get_collection_name(user_id)
        points, _ = self.client.scroll(
            collection_name=collection_name,
            limit=limit,
            with_payload=True,
            with_vectors=False
        )
        print(f"Data in collection '{collection_name}':")
        for p in points:
            print(f" - ID: {p.id}, payload: {p.payload}")
