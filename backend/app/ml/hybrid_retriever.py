import re
import math
import hashlib
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Tuple, Any
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

try:
    from underthesea import word_tokenize
except ImportError:
    # Fallback nếu môi trường chưa cài underthesea
    def word_tokenize(sentence: str, format: str = None) -> str:
        return sentence


@dataclass
class RetrievedChunk:
    chunk_id: str
    document_title: str
    version_no: str
    article: str
    clause: str
    page: int
    content: str
    is_active: bool
    version_id: Optional[str] = None
    bm25_rank: Optional[int] = None
    vector_rank: Optional[int] = None
    rrf_score: float = 0.0
    rerank_score: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "chunk_id": self.chunk_id,
            "version_id": self.version_id or self.chunk_id,
            "document_title": self.document_title,
            "doc_title": self.document_title,
            "version_no": self.version_no,
            "article": self.article,
            "clause": self.clause,
            "page": self.page,
            "content": self.content,
            "text": self.content,
            "is_active": self.is_active,
            "bm25_rank": self.bm25_rank,
            "vector_rank": self.vector_rank,
            "rrf_score": self.rrf_score,
            "rerank_score": self.rerank_score,
        }

    def __getitem__(self, item: str) -> Any:
        return self.to_dict()[item]

    def get(self, item: str, default: Any = None) -> Any:
        return self.to_dict().get(item, default)

    def copy(self) -> Dict[str, Any]:
        return self.to_dict()


class HybridRetriever:
    """
    Thực hiện Truy hồi lai (Hybrid Retrieval) kết hợp:
      - Nhánh từ khóa (BM25 / Full-Text Search với tách từ tiếng Việt)
      - Nhánh ngữ nghĩa (Dense Vector trên pgvector)
      - Hợp nhất thứ hạng bằng Reciprocal Rank Fusion (RRF)
      - Kiểm soát hiệu lực văn bản theo quy tắc BR01
    """

    YEAR_VERSION_PATTERN = re.compile(
        r"(?:năm|quy chế|phiên bản|bản|khóa)\s*(201\d|202[0-4])", re.IGNORECASE
    )
    HISTORICAL_QUERY_REGEX = YEAR_VERSION_PATTERN

    _cached_model = None

    def __init__(
        self,
        embedding_model=None,
        reranker_model=None,
        rrf_k: int = 60,
        w_bm25: float = 0.45,
        w_vec: float = 0.55,
    ):
        self.embedding_model = embedding_model
        self.reranker_model = reranker_model
        self.rrf_k = rrf_k
        self.w_bm25 = w_bm25
        self.w_vec = w_vec

    @staticmethod
    def segment_vietnamese_for_fts(query: str) -> str:
        """
        Tách từ tiếng Việt ghép bằng dấu gạch dưới (VD: 'bảo_lưu kết_quả học_tập')
        để khớp với cột tsvector trong PostgreSQL.
        """
        cleaned = re.sub(r"[^\w\s]", " ", query.lower()).strip()
        segmented = word_tokenize(cleaned, format="text")
        return segmented

    @staticmethod
    def tokenize_vietnamese(query: str) -> str:
        """Bí danh hỗ trợ các module indexing và seed data."""
        return HybridRetriever.segment_vietnamese_for_fts(query)

    def detect_version_filter(self, query: str) -> Tuple[bool, Optional[str]]:
        """
        Quy tắc BR01:
        - Mặc định chỉ tìm trên văn bản còn hiệu lực (only_active = True).
        - Nếu câu hỏi nhắc rõ năm/phiên bản cũ (VD: 'quy chế 2021'), cho phép truy hồi cả bản cũ.
        """
        match = self.YEAR_VERSION_PATTERN.search(query)
        if match:
            requested_year = match.group(1)
            return False, requested_year
        return True, None

    @classmethod
    def is_asking_historical(cls, query: str) -> bool:
        only_active, _ = cls().detect_version_filter(query)
        return not only_active

    @classmethod
    async def get_embedding(cls, text: str) -> List[float]:
        """Tạo vector embedding 1024 chiều (tương thích BGE-M3)."""
        if cls._cached_model is None:
            try:
                from sentence_transformers import SentenceTransformer
                cls._cached_model = SentenceTransformer("BAAI/bge-m3")
            except Exception:
                cls._cached_model = "MOCK"

        if cls._cached_model != "MOCK":
            try:
                emb = cls._cached_model.encode(text, normalize_embeddings=True)
                return emb.tolist()
            except Exception:
                pass

        # Thuật toán sinh vector giả lập tất định 1024 chiều cho môi trường dev/test
        dim = 1024
        vec = [0.0] * dim
        tokens = re.sub(r"[^\w\s]", " ", text.lower()).split()
        for i, token in enumerate(tokens):
            h = int(hashlib.sha256(token.encode("utf-8")).hexdigest(), 16)
            pos = h % dim
            sign = 1.0 if ((h >> 4) % 2 == 0) else -1.0
            vec[pos] += sign * (1.0 / math.sqrt(i + 1))
        norm = math.sqrt(sum(x * x for x in vec))
        if norm > 0:
            vec = [round(x / norm, 6) for x in vec]
        else:
            vec[0] = 1.0
        return vec

    async def _search_bm25(
        self,
        session: AsyncSession,
        segmented_query: str,
        only_active: bool,
        top_k: int = 20,
    ) -> List[RetrievedChunk]:
        ts_query_terms = " | ".join(segmented_query.split())
        if not ts_query_terms.strip():
            return []
        sql = text(
            """
            SELECT
                c.id::text AS chunk_id,
                c.version_id::text AS version_id,
                d.title AS document_title,
                dv.version_no AS version_no,
                c.article AS article,
                c.clause AS clause,
                c.page AS page,
                c.text AS content,
                c.is_active AS is_active,
                ts_rank_cd(c.tsv, to_tsquery('simple', :ts_query)) AS score
            FROM chunks c
            JOIN document_versions dv ON c.version_id = dv.id
            JOIN documents d ON dv.document_id = d.id
            WHERE (:only_active = FALSE OR c.is_active = TRUE)
              AND c.tsv @@ to_tsquery('simple', :ts_query)
            ORDER BY score DESC
            LIMIT :top_k
            """
        )
        result = await session.execute(
            sql,
            {
                "ts_query": ts_query_terms,
                "only_active": only_active,
                "top_k": top_k,
            },
        )
        rows = result.mappings().all()
        return [
            RetrievedChunk(
                chunk_id=r["chunk_id"],
                version_id=r.get("version_id"),
                document_title=r["document_title"],
                version_no=r["version_no"],
                article=r["article"] or "",
                clause=r["clause"] or "",
                page=r["page"] or 1,
                content=r["content"],
                is_active=r["is_active"],
                bm25_rank=idx + 1,
            )
            for idx, r in enumerate(rows)
        ]

    async def _search_vector(
        self,
        session: AsyncSession,
        query_embedding: List[float],
        only_active: bool,
        top_k: int = 20,
    ) -> List[RetrievedChunk]:
        sql = text(
            """
            SELECT
                c.id::text AS chunk_id,
                c.version_id::text AS version_id,
                d.title AS document_title,
                dv.version_no AS version_no,
                c.article AS article,
                c.clause AS clause,
                c.page AS page,
                c.text AS content,
                c.is_active AS is_active,
                1 - (c.embedding <=> :embedding_vec) AS cosine_sim
            FROM chunks c
            JOIN document_versions dv ON c.version_id = dv.id
            JOIN documents d ON dv.document_id = d.id
            WHERE (:only_active = FALSE OR c.is_active = TRUE)
            ORDER BY c.embedding <=> :embedding_vec
            LIMIT :top_k
            """
        )
        vec_str = "[" + ",".join(f"{x:.6f}" for x in query_embedding) + "]"
        result = await session.execute(
            sql,
            {
                "embedding_vec": vec_str,
                "only_active": only_active,
                "top_k": top_k,
            },
        )
        rows = result.mappings().all()
        return [
            RetrievedChunk(
                chunk_id=r["chunk_id"],
                version_id=r.get("version_id"),
                document_title=r["document_title"],
                version_no=r["version_no"],
                article=r["article"] or "",
                clause=r["clause"] or "",
                page=r["page"] or 1,
                content=r["content"],
                is_active=r["is_active"],
                vector_rank=idx + 1,
            )
            for idx, r in enumerate(rows)
        ]

    def fuse_rrf(
        self,
        bm25_results: List[RetrievedChunk],
        vector_results: List[RetrievedChunk],
        top_m: int = 15,
    ) -> List[RetrievedChunk]:
        """
        Công thức Reciprocal Rank Fusion (RRF):
        RRF_Score(d) = w_bm25 / (k + rank_bm25(d)) + w_vec / (k + rank_vec(d))
        """
        merged: Dict[str, RetrievedChunk] = {}

        for item in bm25_results:
            merged[item.chunk_id] = item
            merged[item.chunk_id].rrf_score += self.w_bm25 / (self.rrf_k + item.bm25_rank)

        for item in vector_results:
            if item.chunk_id in merged:
                merged[item.chunk_id].vector_rank = item.vector_rank
                merged[item.chunk_id].rrf_score += self.w_vec / (self.rrf_k + item.vector_rank)
            else:
                item.rrf_score = self.w_vec / (self.rrf_k + item.vector_rank)
                merged[item.chunk_id] = item

        sorted_chunks = sorted(merged.values(), key=lambda x: x.rrf_score, reverse=True)
        return sorted_chunks[:top_m]

    async def retrieve(
        self,
        session: AsyncSession,
        query: str,
        mode: str = "hybrid",  # 'bm25_only' | 'vector_only' | 'hybrid' (phục vụ thí nghiệm E2)
        top_k_branch: int = 20,
        top_m_fusion: int = 15,
        top_k_final: int = 5,
        use_reranker: bool = True,
    ) -> List[RetrievedChunk]:
        only_active, _ = self.detect_version_filter(query)

        bm25_res: List[RetrievedChunk] = []
        vec_res: List[RetrievedChunk] = []

        if mode in ("bm25_only", "hybrid"):
            segmented_q = self.segment_vietnamese_for_fts(query)
            bm25_res = await self._search_bm25(session, segmented_q, only_active, top_k_branch)

        if mode in ("vector_only", "hybrid"):
            if self.embedding_model is not None and hasattr(self.embedding_model, "encode"):
                q_emb = self.embedding_model.encode(query, normalize_embeddings=True).tolist()
            else:
                q_emb = await self.get_embedding(query)
            vec_res = await self._search_vector(session, q_emb, only_active, top_k_branch)

        if mode == "bm25_only":
            candidates = bm25_res[:top_m_fusion]
        elif mode == "vector_only":
            candidates = vec_res[:top_m_fusion]
        else:
            candidates = self.fuse_rrf(bm25_res, vec_res, top_m=top_m_fusion)

        if not candidates:
            return []

        # Bước 5: Xếp hạng lại bằng Cross-Encoder (bge-reranker-v2-m3) cho thí nghiệm E4
        if use_reranker and self.reranker_model is not None and hasattr(self.reranker_model, "compute_score"):
            pairs = [(query, c.content) for c in candidates]
            scores = self.reranker_model.compute_score(pairs, normalize=True)
            for chunk, sc in zip(candidates, scores):
                chunk.rerank_score = float(sc)
            candidates.sort(key=lambda x: x.rerank_score, reverse=True)
        else:
            for chunk in candidates:
                chunk.rerank_score = chunk.rrf_score

        return candidates[:top_k_final]

    @classmethod
    async def search(
        cls,
        db: AsyncSession,
        query: str,
        k1: int = 20,
        k2: int = 20,
        top_m: int = 15,
        mode: str = "hybrid",
    ) -> List[RetrievedChunk]:
        """Phương thức lớp tương thích với luồng RAG pipeline hiện tại."""
        retriever = cls()
        return await retriever.retrieve(
            session=db,
            query=query,
            mode=mode,
            top_k_branch=max(k1, k2),
            top_m_fusion=top_m,
            top_k_final=top_m,
            use_reranker=False,
        )
