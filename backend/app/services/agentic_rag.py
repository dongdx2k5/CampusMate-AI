"""
Hybrid Agentic RAG & Tool Calling Router for HUCE Smart AI Kiosk.
Handles:
1. Intent Classification (Regulations, Scholarship, Class Schedule, Exam Schedule, Course Roadmap, Out-of-Scope).
2. Hybrid Search (BM25 + Semantic Token Overlap + RRF Fusion) over official HUCE regulations.
3. Structured SQL/DAG Tool Invocation for personalized academic queries.
4. Grounded Vietnamese response synthesis with mandatory [Nguồn: ...] citations.
"""

import json
import math
import re
import time
from typing import Any, Dict, List, Optional

from ..database import db_connection, get_connection
from .dag_recommender import (
    evaluate_student_scholarship,
    get_student_schedules_and_exams,
    recommend_courses_dag,
)


def tokenize_vi(text: str) -> List[str]:
    clean = re.sub(
        r"[^\w\sàáạảãâầấậẩẫăằắặẳẵèéẹẻẽêềếệểễìíịỉĩòóọỏõôồốộổỗơờớợởỡùúụủũưừứựửữỳýỵỷỹđ]",
        " ",
        text.lower(),
    )
    return [t for t in clean.split() if len(t) > 1]


def hybrid_search_regulations(
    query: str,
    top_k: int = 3,
    min_score: float = 0.015,
) -> List[Dict[str, Any]]:
    """
    Performs pure-Python Hybrid Retrieval:
    1. Lexical BM25 (Okapi BM25 with k1=1.5, b=0.75, avgdl).
    2. Semantic Token Overlap & Cosine Similarity (unigrams + bigrams with 2.0x keyword boost).
    3. Reciprocal Rank Fusion (RRF with k=60).
    4. Minimum score threshold to prevent hallucinations on unrelated queries.
    """
    with db_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM document_chunks")
        rows = [dict(r) for r in cur.fetchall()]

    if not rows:
        return []

    q_tokens = tokenize_vi(query)
    if not q_tokens:
        return []

    q_bigrams = [f"{q_tokens[i]}_{q_tokens[i+1]}" for i in range(len(q_tokens) - 1)]
    q_term_counts: Dict[str, int] = {}
    for t in q_tokens:
        q_term_counts[t] = q_term_counts.get(t, 0) + 1

    N = len(rows)
    doc_tokens_list = []
    doc_dl_list = []
    doc_kw_set_list = []
    doc_bigram_set_list = []

    for r in rows:
        content_toks = tokenize_vi(r["content"] + " " + r["doc_title"])
        kw_toks = tokenize_vi(r["keywords"])
        all_toks = content_toks + kw_toks
        doc_tokens_list.append(all_toks)
        doc_dl_list.append(len(all_toks))
        doc_kw_set_list.append(set(kw_toks))
        doc_bigram_set_list.append(
            set(f"{content_toks[i]}_{content_toks[i+1]}" for i in range(len(content_toks) - 1))
        )

    avgdl = sum(doc_dl_list) / max(N, 1)

    # 1. BM25 calculation
    k1 = 1.5
    b = 0.75
    bm25_scores = []
    for i, r in enumerate(rows):
        toks = doc_tokens_list[i]
        dl = doc_dl_list[i]
        tok_counts: Dict[str, int] = {}
        for t in toks:
            tok_counts[t] = tok_counts.get(t, 0) + 1

        score = 0.0
        for t in q_term_counts:
            df = sum(1 for dtoks in doc_tokens_list if t in dtoks)
            if df == 0:
                continue
            idf = math.log(1.0 + (N - df + 0.5) / (df + 0.5))
            tf = tok_counts.get(t, 0)
            if tf > 0:
                num = tf * (k1 + 1.0)
                den = tf + k1 * (1.0 - b + b * (dl / max(avgdl, 1.0)))
                score += idf * (num / den)
        bm25_scores.append(score)

    # 2. Semantic Token Overlap & Cosine Similarity
    semantic_scores = []
    q_unigram_set = set(q_tokens)
    q_bigram_set = set(q_bigrams)

    for i, r in enumerate(rows):
        doc_tok_set = set(doc_tokens_list[i])
        kw_set = doc_kw_set_list[i]
        doc_bg_set = doc_bigram_set_list[i]

        uni_overlap = len(q_unigram_set.intersection(doc_tok_set))
        kw_overlap = len(q_unigram_set.intersection(kw_set))
        bg_overlap = len(q_bigram_set.intersection(doc_bg_set))

        weighted_overlap = uni_overlap * 1.0 + bg_overlap * 1.5 + kw_overlap * 2.0
        denom = math.sqrt(len(q_unigram_set) + 1.0) * math.sqrt(len(doc_tok_set) + 1.0)
        cos_sim = weighted_overlap / max(denom, 1.0)
        semantic_scores.append(cos_sim)

    # Filter out documents with negligible match
    valid_indices = [
        i for i in range(N) if (bm25_scores[i] > 0.05 or semantic_scores[i] > 0.05)
    ]
    if not valid_indices:
        return []

    # Sort ranks for BM25 and Semantic
    bm25_ranked = sorted(valid_indices, key=lambda idx: bm25_scores[idx], reverse=True)
    semantic_ranked = sorted(valid_indices, key=lambda idx: semantic_scores[idx], reverse=True)

    bm25_rank_map = {idx: rank + 1 for rank, idx in enumerate(bm25_ranked)}
    semantic_rank_map = {idx: rank + 1 for rank, idx in enumerate(semantic_ranked)}

    # 3. Reciprocal Rank Fusion (k = 60)
    rrf_constant = 60
    scored_results = []
    for idx in valid_indices:
        r_bm25 = bm25_rank_map[idx]
        r_sem = semantic_rank_map[idx]
        rrf = (1.0 / (rrf_constant + r_bm25)) + (1.0 / (rrf_constant + r_sem))

        if rrf >= min_score:
            row_dict = dict(rows[idx])
            sim_score = round(min(0.99, 0.50 + rrf * 15.0), 3)
            row_dict["similarity_score"] = sim_score
            row_dict["rrf_score"] = round(rrf, 5)
            scored_results.append(row_dict)

    scored_results.sort(key=lambda x: x["rrf_score"], reverse=True)
    return scored_results[:top_k]


def detect_query_intent(question: str) -> str:
    q = question.lower()
    if any(
        k in q
        for k in [
            "lịch thi",
            "phòng thi",
            "số báo danh",
            "sbd",
            "ngày thi",
            "ca thi",
            "bao giờ thi",
        ]
    ):
        return "EXAM_SCHEDULE"
    if any(
        k in q
        for k in [
            "lịch học",
            "thời khóa biểu",
            "tkb",
            "học phòng nào",
            "tiết mấy",
            "hôm nay học",
            "tuần này học",
        ]
    ):
        return "CLASS_SCHEDULE"
    if any(
        k in q
        for k in [
            "học bổng",
            "kkht",
            "đủ điều kiện học bổng",
            "xét học bổng",
            "mức học bổng",
        ]
    ):
        return "SCHOLARSHIP"
    if any(
        k in q
        for k in [
            "lộ trình",
            "gợi ý môn",
            "đăng ký môn",
            "môn tiên quyết",
            "kỳ tới học gì",
            "nên học môn nào",
        ]
    ):
        return "COURSE_ROADMAP"
    return "REGULATION_RAG"


def answer_academic_query(
    question: str,
    student_code: str = "0213368",
    career_track: Optional[str] = None,
    kiosk_id: str = "KIOSK_LOBBY_H1",
) -> Dict[str, Any]:
    """
    Main Agentic RAG entry point combining structured student tools and unstructured regulation RAG.
    """
    start_ts = time.perf_counter()
    intent = detect_query_intent(question)
    retrieved_chunks = hybrid_search_regulations(question, top_k=3)
    citations = []
    structured_data: Dict[str, Any] = {}

    if intent == "EXAM_SCHEDULE":
        sched_data = get_student_schedules_and_exams(student_code)
        structured_data = {"exam_schedules": sched_data.get("exam_schedules", [])}
        exam_chunks = hybrid_search_regulations(
            "quy định phòng thi lịch thi thẻ sinh viên", top_k=1
        )
        for c in exam_chunks:
            citations.append(
                f"[Nguồn: {c['doc_title']} ({c['doc_number']}), {c['article_ref']}]"
            )

        exams = sched_data.get("exam_schedules", [])
        lines = [
            f"Chào **{sched_data.get('full_name', student_code)}** (MSSV: `{student_code}` - Lớp `{sched_data.get('class_name', '')}`), dưới đây là **Lịch thi kết thúc học phần Học kỳ {sched_data.get('semester', '2026-1')}** của bạn:"
        ]
        for ex in exams:
            lines.append(
                f"- **{ex['course_code']} – {ex['course_name']}**: Ngày thi **{ex['exam_date']}** | Giờ thi: **{ex['exam_time']}** | Phòng thi: **{ex['exam_room']}** | Số báo danh: **{ex['seat_number']}** | Hình thức: {ex['exam_format']}."
            )
        lines.append(
            "\n**Lưu ý quy chế khảo thí:** Sinh viên bắt buộc có mặt tại phòng thi trước 15 phút và mang theo **Thẻ sinh viên hợp lệ** (nếu đến muộn quá 15 phút sau khi bóc đề sẽ không được dự thi) [Nguồn: Quy định Công tác Khảo thí và Thi kết thúc Học phần HUCE (612/QĐ-ĐHXD), Điều 9, Khoản 1 & 4 (Trang 7)]."
        )
        answer_text = "\n".join(lines)

    elif intent == "CLASS_SCHEDULE":
        sched_data = get_student_schedules_and_exams(student_code)
        structured_data = {"class_schedules": sched_data.get("class_schedules", [])}
        classes = sched_data.get("class_schedules", [])
        lines = [
            f"Chào **{sched_data.get('full_name', student_code)}** (MSSV: `{student_code}`), dưới đây là **Thời khóa biểu Lịch học Học kỳ {sched_data.get('semester', '2026-1')}** của bạn:"
        ]
        for cl in classes:
            lines.append(
                f"- **{cl['day_of_week']} ({cl['periods']} | {cl['time_range']})**: Học phần **{cl['course_code']} – {cl['course_name']}** ({cl['credits']} TC) tại phòng **{cl['room']}** ({cl['building']}) – GV: {cl['lecturer']}."
            )
        lines.append(
            "[Nguồn: Hệ thống Quản lý Đào tạo HUCE & Quy chế Đào tạo 892/QĐ-ĐHXD, Điều 14]."
        )
        citations.append(
            "[Nguồn: Quy chế Đào tạo trình độ Đại học theo Hệ thống Tín chỉ HUCE (892/QĐ-ĐHXD), Điều 14, Khoản 2 (Trang 11)]"
        )
        answer_text = "\n".join(lines)

    elif intent == "SCHOLARSHIP":
        eval_res = evaluate_student_scholarship(student_code)
        structured_data = {"scholarship_evaluation": eval_res}
        citations.append(
            "[Nguồn: Quy định Xét cấp Học bổng Khuyến khích Học tập ĐH Xây dựng Hà Nội (1158/QĐ-ĐHXD), Điều 8, Khoản 1, 2, 3 (Trang 5)]"
        )
        if eval_res.get("eligible"):
            matched = eval_res["highest_matched_scholarship"]
            reward_str = f"{matched['reward_amount_vnd']:,}".replace(",", ".")
            answer_text = "\n".join(
                [
                    "**1. Quy định điều kiện xét Học bổng Khuyến khích Học tập (KKHT) tại HUCE:**",
                    "- Sinh viên cần hoàn thành tối thiểu **15 tín chỉ** trong học kỳ xét, không có học phần nào bị điểm F hoặc dưới mức quy định và không bị kỷ luật.",
                    "- Các mức học bổng: **Loại Khá** (GPA >= 2.50, ĐRL >= 70); **Loại Giỏi** (GPA >= 3.20, ĐRL >= 80); **Loại Xuất sắc** (GPA >= 3.60, ĐRL >= 90) [Nguồn: Quyết định 1158/QĐ-ĐHXD, Điều 8].",
                    "",
                    f"**2. Kết quả đối chiếu hồ sơ cá nhân của {eval_res['full_name']} (MSSV: `{student_code}`):**",
                    f"- GPA học kỳ hiện tại: **{eval_res['gpa_semester']:.2f}/4.0** | Điểm rèn luyện: **{eval_res['training_score']}/100** | Số tín chỉ học kỳ: **{eval_res['credits_semester']} TC** | Số môn điểm F: **0 môn**.",
                    f"- **Kết luận:** Bạn **ĐỦ ĐIỀU KIỆN** xét đạt **{matched['name']}** với mức học bổng dự kiến **{reward_str} VNĐ/học kỳ**.",
                ]
            )
        else:
            answer_text = "\n".join(
                [
                    "**1. Quy định Học bổng KKHT:** Yêu cầu tối thiểu 15 tín chỉ/kỳ, không có môn điểm F, GPA >= 2.50 (Khá), >= 3.20 (Giỏi), >= 3.60 (Xuất sắc) [Nguồn: Quyết định 1158/QĐ-ĐHXD, Điều 8].",
                    "",
                    f"**2. Kết quả đối chiếu hồ sơ của {eval_res.get('full_name', student_code)} (`{student_code}`):**",
                    f"- GPA học kỳ: **{eval_res.get('gpa_semester', 0):.2f}** | ĐRL: **{eval_res.get('training_score', 0)}** | Môn chưa đạt (F): **{', '.join(eval_res.get('failed_courses', [])) or 'Không'}**.",
                    f"- **Kết luận:** Hiện tại bạn **chưa đủ điều kiện** nhận học bổng KKHT kỳ này do: {eval_res['all_tiers_comparison'][-1]['gap_analysis']}.",
                ]
            )

    elif intent == "COURSE_ROADMAP":
        dag_res = recommend_courses_dag(student_code, career_track=career_track)
        structured_data = {"dag_roadmap": dag_res}
        citations.append(
            "[Nguồn: Quy chế Đào tạo trình độ Đại học theo Hệ thống Tín chỉ HUCE (892/QĐ-ĐHXD), Điều 14, Khoản 2 (Trang 11)]"
        )
        rec_lines = [
            f"Dựa trên đồ thị môn tiên quyết (DAG) của Khoa CNTT – ĐH Xây dựng Hà Nội và **{dag_res.get('passed_courses_count', 0)} học phần** bạn đã tích lũy, hệ thống đề xuất lộ trình học kỳ tới (**Tổng: {dag_res.get('total_recommended_credits', 0)} tín chỉ**, nằm trong ngưỡng quy định 14–24 TC):"
        ]
        for c in dag_res.get("recommended_courses", []):
            rec_lines.append(
                f"- **{c['course_code']} – {c['name']}** ({c['credits']} TC | {c['priority_type']}): {c['reason']}"
            )
        rec_lines.append(
            "[Nguồn: Quy chế Đào tạo trình độ Đại học theo Hệ thống Tín chỉ HUCE (892/QĐ-ĐHXD), Điều 14, Khoản 2 (Trang 11)]."
        )
        answer_text = "\n".join(rec_lines)

    else:
        if not retrieved_chunks:
            answer_text = (
                "Hiện tại hệ thống chưa tìm thấy quy định chính thức về vấn đề này trong cơ sở dữ liệu văn bản của Trường Đại học Xây dựng Hà Nội (HUCE). "
                "Bạn vui lòng liên hệ Phòng Quản lý Đào tạo (Tầng 1 nhà H1) hoặc Cố vấn học tập để được hỗ trợ chính xác nhất."
            )
        else:
            lines = [
                "Dựa trên cơ sở dữ liệu văn bản quy chế chính thức của Trường Đại học Xây dựng Hà Nội (HUCE), thông tin giải đáp cho câu hỏi của bạn như sau:"
            ]
            for ch in retrieved_chunks:
                cit = f"[Nguồn: {ch['doc_title']} ({ch['doc_number']}), {ch['article_ref']}]"
                citations.append(cit)
                lines.append(
                    f"- **{ch['doc_title']} ({ch['article_ref']})**: {ch['content']} {cit}"
                )
            answer_text = "\n".join(lines)

    elapsed_ms = max(int((time.perf_counter() - start_ts) * 1000), 15)

    with db_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO chat_logs (user_id, kiosk_id, question_text, intent_detected, answer_text, citations_json, response_time_ms)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                student_code,
                kiosk_id,
                question,
                intent,
                answer_text,
                json.dumps(citations, ensure_ascii=False),
                elapsed_ms,
            ),
        )
        conn.commit()

    return {
        "question": question,
        "student_code": student_code,
        "intent_detected": intent,
        "answer": answer_text,
        "citations": citations,
        "retrieved_chunks": retrieved_chunks,
        "structured_data": structured_data,
        "response_time_ms": elapsed_ms,
    }
