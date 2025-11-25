from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct, VectorParams, Distance
from typing import List, Dict, Optional
import uuid
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct, VectorParams, Distance
from typing import List, Dict, Optional
import uuid

class QdrantDB:
    """
    Quản lý kết nối và thao tác với Qdrant vector database.
    Hỗ trợ tạo collection riêng cho từng user.
    """

    def __init__(self,
                 host: str = "localhost",
                 port: int = 6333,
                 base_collection: str = "user_",
                 vector_size: int = 768,
                 distance: Distance = Distance.COSINE):
        self.base_collection = base_collection
        self.vector_size = vector_size
        self.distance = distance
        self.client = QdrantClient(host=host, port=port)

    # --------------------------
    # Helper: Tạo hoặc lấy collection riêng của user
    # --------------------------
    def _get_collection_name(self, user_id: str) -> str:
        return f"{self.base_collection}{user_id}"

    def _ensure_collection(self, user_id: str):
        """Tạo collection cho user nếu chưa có."""
        collection_name = self._get_collection_name(user_id)
        collections = [c.name for c in self.client.get_collections().collections]
        if collection_name not in collections:
            print(f"🟢 Tạo collection mới cho user: {collection_name}")
            self.client.recreate_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(
                    size=self.vector_size,
                    distance=self.distance
                )
            )
        return collection_name

    # --------------------------
    # Upsert 1 vector
    # --------------------------
    def upsert_one(self, user_id: str, vector: List[float], payload: Dict):
        """
        Thêm 1 vector duy nhất vào collection của user.
        """
        collection_name = self._ensure_collection(user_id)
        point = PointStruct(
            id=str(uuid.uuid4()),
            vector=vector,
            payload=payload
        )
        self.client.upsert(collection_name=collection_name, points=[point])
        print(f"💾 Đã thêm 1 vector vào collection '{collection_name}'")

    # --------------------------
    # Tìm kiếm
    # --------------------------
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

    # --------------------------
    # Liệt kê dữ liệu
    # --------------------------
    def list_points(self, user_id: str, limit: int = 10):
        collection_name = self._get_collection_name(user_id)
        points, _ = self.client.scroll(
            collection_name=collection_name,
            limit=limit,
            with_payload=True,
            with_vectors=False
        )
        print(f"📄 Dữ liệu trong collection '{collection_name}':")
        for p in points:
            print(f" - ID: {p.id}, payload: {p.payload}")
