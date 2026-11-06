import json
import math
import re
import sys
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import numpy as np

# Đảm bảo import được module app khi chạy từ bất kỳ thư mục nào
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.ml.chunker import LegalChunk, VietnameseLegalChunker
from app.ml.hybrid_retriever import HybridRetriever


# =====================================================================
# 1. CÁC HÀM ĐO LƯỜNG CHUẨN (Recall@k, MRR, nDCG@k, Citation, Refusal)
# =====================================================================
def is_chunk_match(chunk: LegalChunk, expected: Dict, doc_version: str) -> bool:
    """Kiểm tra một chunk có khớp với nhãn (version, Điều, Khoản) trong bộ câu hỏi vàng không."""
    if doc_version != expected["version"]:
        return False
    exp_art = expected["article"].lower().strip()
    chunk_art = (chunk.article or "").lower().strip()
    if exp_art != chunk_art:
        return False

    # Hỗ trợ trường hợp nhãn ghi "Khoản 1, 2"
    exp_clauses = re.findall(r"\d+", expected.get("clause", ""))
    chunk_clauses = re.findall(r"\d+", chunk.clause or "")
    if exp_clauses and chunk_clauses:
        return any(c in exp_clauses for c in chunk_clauses)
    return True


def compute_ir_metrics(
    ranked_chunks: List[Tuple[LegalChunk, str]],
    expected_citations: List[Dict],
    k_values: List[int] = [5, 10],
) -> Dict[str, float]:
    """Tính Recall@k, MRR và nDCG@10 cho một câu hỏi."""
    if not expected_citations:
        return {f"Recall@{k}": 1.0 for k in k_values} | {"MRR": 1.0, "nDCG@10": 1.0}

    total_gold = len(expected_citations)
    metrics: Dict[str, float] = {}

    # 1. Recall@k
    for k in k_values:
        top_k = ranked_chunks[:k]
        matched_gold = 0
        for gold in expected_citations:
            if any(is_chunk_match(ch, gold, ver) for ch, ver in top_k):
                matched_gold += 1
        metrics[f"Recall@{k}"] = matched_gold / total_gold

    # 2. MRR (Mean Reciprocal Rank)
    rr = 0.0
    for rank_idx, (ch, ver) in enumerate(ranked_chunks, start=1):
        if any(is_chunk_match(ch, gold, ver) for gold in expected_citations):
            rr = 1.0 / rank_idx
            break
    metrics["MRR"] = rr

    # 3. nDCG@10
    k_ndcg = 10
    dcg = 0.0
    matched_set = set()
    for rank_idx, (ch, ver) in enumerate(ranked_chunks[:k_ndcg], start=1):
        rel = 0.0
        for g_idx, gold in enumerate(expected_citations):
            if g_idx not in matched_set and is_chunk_match(ch, gold, ver):
                rel = 1.0
                matched_set.add(g_idx)
                break
        dcg += rel / math.log2(rank_idx + 1)

    idcg = sum(1.0 / math.log2(i + 1) for i in range(1, min(total_gold, k_ndcg) + 1))
    metrics["nDCG@10"] = dcg / idcg if idcg > 0 else 0.0
    return metrics


# =====================================================================
# 2. BỘ TRUY HỒI IN-MEMORY PHỤC VỤ CHẠY THỰC NGHIỆM NHANH (E1, E2, E7)
# =====================================================================
class InMemoryExperimentRunner:
    def __init__(self, chunks_with_version: List[Tuple[LegalChunk, str]]):
        self.corpus = chunks_with_version
        self.tokenized_corpus = [
            set(HybridRetriever.segment_vietnamese_for_fts(c.text).split())
            for c, _ in self.corpus
        ]
        # Tính IDF đơn giản cho nhánh BM25
        N = len(self.corpus)
        df: Dict[str, int] = {}
        for tokens in self.tokenized_corpus:
            for t in tokens:
                df[t] = df.get(t, 0) + 1
        self.idf = {t: math.log((N - freq + 0.5) / (freq + 0.5) + 1.0) for t, freq in df.items()}

    def score_bm25(self, query: str, idx: int) -> float:
        q_tokens = set(HybridRetriever.segment_vietnamese_for_fts(query).split())
        doc_tokens = self.tokenized_corpus[idx]
        return sum(self.idf.get(t, 0.0) for t in q_tokens if t in doc_tokens)

    def score_char_ngram_vector(self, query: str, idx: int) -> float:
        """
        Mô phỏng tương đồng ngữ nghĩa bằng Character 3-gram Cosine Similarity
        khi chạy offline không có GPU (hoặc thay bằng BGE-M3 khi chạy trên server).
        """
        def get_ngrams(s: str, n: int = 3) -> Dict[str, int]:
            s = re.sub(r"\s+", " ", s.lower().strip())
            vec: Dict[str, int] = {}
            for i in range(max(0, len(s) - n + 1)):
                g = s[i : i + n]
                vec[g] = vec.get(g, 0) + 1
            return vec

        v1 = get_ngrams(query)
        v2 = get_ngrams(self.corpus[idx][0].text)
        common = set(v1.keys()) & set(v2.keys())
        num = sum(v1[k] * v2[k] for k in common)
        den1 = math.sqrt(sum(v * v for v in v1.values()))
        den2 = math.sqrt(sum(v * v for v in v2.values()))
        return num / (den1 * den2) if den1 * den2 > 0 else 0.0

    def search(
        self, query: str, mode: str = "hybrid", rrf_k: int = 60
    ) -> Tuple[List[Tuple[LegalChunk, str]], float]:
        # Kiểm tra BR01: Chỉ lấy văn bản còn hiệu lực trừ khi hỏi đích danh năm cũ
        only_active = not bool(HybridRetriever.YEAR_VERSION_PATTERN.search(query))

        valid_indices = [
            i for i, (ch, _) in enumerate(self.corpus) if (not only_active or ch.is_active)
        ]

        bm25_scores = [(i, self.score_bm25(query, i)) for i in valid_indices]
        bm25_scores.sort(key=lambda x: x[1], reverse=True)
        bm25_ranks = {i: rank + 1 for rank, (i, sc) in enumerate(bm25_scores) if sc > 0}

        vec_scores = [(i, self.score_char_ngram_vector(query, i)) for i in valid_indices]
        vec_scores.sort(key=lambda x: x[1], reverse=True)
        vec_ranks = {i: rank + 1 for rank, (i, _) in enumerate(vec_scores)}

        final_scores: List[Tuple[int, float]] = []
        for i in valid_indices:
            if mode == "bm25_only":
                sc = 1.0 / (rrf_k + bm25_ranks[i]) if i in bm25_ranks else 0.0
            elif mode == "vector_only":
                sc = 1.0 / (rrf_k + vec_ranks[i])
            else:
                s_b = 0.45 / (rrf_k + bm25_ranks[i]) if i in bm25_ranks else 0.0
                s_v = 0.55 / (rrf_k + vec_ranks[i])
                sc = s_b + s_v
            final_scores.append((i, sc))

        final_scores.sort(key=lambda x: x[1], reverse=True)
        ranked_chunks = [self.corpus[i] for i, _ in final_scores[:10]]

        # Tính điểm tin cậy giả lập từ điểm tương đồng cao nhất để kiểm thử ngưỡng từ chối (E7)
        max_sim = max((self.score_char_ngram_vector(query, i) for i, _ in final_scores[:3]), default=0.0)
        return ranked_chunks, max_sim


# =====================================================================
# 3. HÀM CHẠY TOÀN BỘ THỰC NGHIỆM TRÊN BỘ CÂU HỎI VÀNG
# =====================================================================
def load_sample_regulations(md_path: Path, chunk_mode: str) -> List[Tuple[LegalChunk, str]]:
    raw_content = md_path.read_text(encoding="utf-8")
    parts = raw_content.split("================================================================================")
    doc_2025 = parts[0]
    doc_2021 = parts[1] if len(parts) > 1 else ""

    chunker = VietnameseLegalChunker(max_words=180, overlap_words=30)
    if chunk_mode == "legal":
        c_2025 = chunker.chunk_by_legal_structure(doc_2025, version_id="v2025", is_active=True)
        c_2021 = chunker.chunk_by_legal_structure(doc_2021, version_id="v2021", is_active=False)
    else:
        c_2025 = chunker.chunk_by_fixed_size(doc_2025, version_id="v2025", is_active=True)
        c_2021 = chunker.chunk_by_fixed_size(doc_2021, version_id="v2021", is_active=False)

    return [(c, "2025.1") for c in c_2025] + [(c, "2021.0") for c in c_2021]


def run_benchmark(seed_dir: Optional[str] = None):
    if seed_dir is None:
        potential_paths = [
            Path(__file__).resolve().parent.parent / "seed_data",
            Path("backend/seed_data"),
            Path("seed_data"),
        ]
        base_path = next((p for p in potential_paths if p.exists()), potential_paths[0])
    else:
        base_path = Path(seed_dir)

    reg_path = base_path / "sample_regulations.md"
    qa_path = base_path / "golden_qa.json"

    if not reg_path.exists() or not qa_path.exists():
        print(f"Lỗi: Không tìm thấy file dữ liệu tại {base_path}")
        return

    golden_qa = json.loads(qa_path.read_text(encoding="utf-8"))
    # Lọc các câu hỏi thuộc nhánh Hỏi đáp quy chế và Kiểm thử từ chối
    rag_questions = [
        q for q in golden_qa if q["intent"] in ("REGULATION", "OUT_OF_SCOPE")
    ]

    configs = [
        ("E1-Baseline: Cắt cố định + Hybrid", "fixed", "hybrid"),
        ("E2-BM25: Cắt Điều/Khoản + Chỉ BM25", "legal", "bm25_only"),
        ("E2-Vector: Cắt Điều/Khoản + Chỉ Vector", "legal", "vector_only"),
        ("Đề xuất: Cắt Điều/Khoản + Hybrid RRF", "legal", "hybrid"),
    ]

    print(f"{'Cấu hình thực nghiệm':<40} | {'Recall@5':<9} | {'Recall@10':<9} | {'MRR':<7} | {'nDCG@10':<8} | {'Refusal F1':<10}")
    print("-" * 96)

    for label, chunk_mode, retr_mode in configs:
        corpus = load_sample_regulations(reg_path, chunk_mode)
        runner = InMemoryExperimentRunner(corpus)

        rec5_list, rec10_list, mrr_list, ndcg_list = [], [], [], []
        tp_refuse, fp_refuse, fn_refuse = 0, 0, 0
        refusal_threshold = 0.22  # Ngưỡng điểm tin cậy để từ chối trả lời (BR02)

        for q in rag_questions:
            ranked, confidence = runner.search(q["raw_question"], mode=retr_mode)
            pred_refuse = confidence < refusal_threshold
            gold_refuse = q["should_refuse"]

            if gold_refuse and pred_refuse:
                tp_refuse += 1
            elif not gold_refuse and pred_refuse:
                fp_refuse += 1
            elif gold_refuse and not pred_refuse:
                fn_refuse += 1

            if not gold_refuse:
                m = compute_ir_metrics(ranked, q["expected_citations"])
                rec5_list.append(m["Recall@5"])
                rec10_list.append(m["Recall@10"])
                mrr_list.append(m["MRR"])
                ndcg_list.append(m["nDCG@10"])

        precision = tp_refuse / (tp_refuse + fp_refuse) if (tp_refuse + fp_refuse) > 0 else 1.0
        recall = tp_refuse / (tp_refuse + fn_refuse) if (tp_refuse + fn_refuse) > 0 else 1.0
        f1_refuse = (2 * precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0

        print(
            f"{label:<40} | "
            f"{np.mean(rec5_list):<9.3f} | "
            f"{np.mean(rec10_list):<9.3f} | "
            f"{np.mean(mrr_list):<7.3f} | "
            f"{np.mean(ndcg_list):<8.3f} | "
            f"{f1_refuse:<10.3f}"
        )


if __name__ == "__main__":
    run_benchmark()

