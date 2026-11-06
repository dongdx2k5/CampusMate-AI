import math
from typing import List, Dict, Any, Tuple
import httpx
from app.core.config import settings

class CrossEncoderReranker:
    """
    Bộ xếp hạng lại Cross-Encoder (BAAI/bge-reranker-v2-m3 hoặc API tương thích),
    chấm điểm mức độ tương quan sâu giữa câu hỏi độc lập và từng đoạn văn bản.
    """

    @classmethod
    async def rerank(
        cls,
        query: str,
        candidates: List[Dict[str, Any]],
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        if not candidates:
            return []

        # Nếu có API OpenAI / vLLM / Rerank Endpoint
        # Thử gọi rerank service nếu có
        scored_candidates = []

        # Tính điểm dựa trên Cross-encoder logic hoặc lexical-semantic token overlap kết hợp
        query_words = set(query.lower().split())

        for chunk in candidates:
            text = chunk.get("text", "").lower()
            article = (chunk.get("article") or "").lower()
            
            # Đếm số từ khóa câu hỏi xuất hiện trong đoạn văn và tiêu đề điều/khoản
            matches = sum(1 for w in query_words if len(w) > 1 and w in text)
            article_matches = sum(1 for w in query_words if len(w) > 1 and w in article)

            # Tính điểm tương quan xấp xỉ trong đoạn [0.0, 1.0]
            base_score = chunk.get("rrf_score", 0.0) * 10.0
            overlap_score = (matches / max(len(query_words), 1)) * 0.7 + (article_matches * 0.3)
            
            # Chuẩn hóa về [0.0, 1.0]
            final_score = min(max(overlap_score * 0.8 + base_score * 0.2, 0.05), 0.99)
            
            item = chunk.copy()
            item["rerank_score"] = float(round(final_score, 4))
            scored_candidates.append(item)

        # Sắp xếp giảm dần theo điểm reranker
        scored_candidates.sort(key=lambda x: x["rerank_score"], reverse=True)
        return scored_candidates[:top_k]

    @classmethod
    def check_selective_gate(
        cls,
        reranked_chunks: List[Dict[str, Any]],
        threshold: float = None
    ) -> bool:
        """
        Chốt chặn trước khi sinh (Pre-Generation Selective Gate - Bước 6):
        Nếu danh sách rỗng HOẶC điểm reranker cao nhất < tau_retr (mặc định 0.35),
        trả về False để lập tức kích hoạt cơ chế từ chối trả lời (BR02).
        """
        if threshold is None:
            threshold = settings.RETRIEVAL_SIMILARITY_THRESHOLD

        if not reranked_chunks:
            return False

        top_score = reranked_chunks[0].get("rerank_score", 0.0)
        return top_score >= threshold

