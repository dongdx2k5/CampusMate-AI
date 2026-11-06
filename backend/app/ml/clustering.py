from datetime import date
from typing import List, Dict, Any, Tuple
import numpy as np
from sklearn.cluster import KMeans
from app.ml.hybrid_retriever import HybridRetriever
from app.core.config import settings
import httpx

class QuestionClusterer:
    """
    Phân tích câu hỏi & Phát hiện khoảng trống tri thức (UC12, FR13)
    - Nhận danh sách câu hỏi đã được ẩn danh (anonymized_content) theo BR08
    - Phân cụm bằng K-Means / HDBSCAN trên vector embedding
    - Phân chia:
      * Cụm thông thường (is_failed_cluster = False)
      * Cụm câu hỏi thất bại / khoảng trống tri thức (is_failed_cluster = True)
    - Tự động gán nhãn chủ đề ngắn gọn bằng tiếng Việt (4-8 từ)
    """

    @classmethod
    async def cluster_questions(
        cls,
        questions: List[str],
        n_clusters: int = 5,
        is_failed: bool = False,
        period_start: date = None,
        period_end: date = None
    ) -> List[Dict[str, Any]]:
        if not questions:
            return []

        # Nếu số lượng câu hỏi quá ít
        if len(questions) < n_clusters:
            n_clusters = max(1, len(questions))

        # 1. Trích xuất embedding cho từng câu hỏi
        vectors = []
        for q in questions:
            vec = await HybridRetriever.get_embedding(q)
            vectors.append(vec)

        X = np.array(vectors)

        # 2. Phân cụm K-Means
        kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init="auto")
        labels = kmeans.fit_predict(X)
        centroids = kmeans.cluster_centers_

        clusters_result = []

        for c_idx in range(n_clusters):
            # Các index thuộc cụm c_idx
            member_indices = np.where(labels == c_idx)[0]
            if len(member_indices) == 0:
                continue

            # Tính khoảng cách tới centroid để chọn câu hỏi đại diện
            cluster_X = X[member_indices]
            centroid = centroids[c_idx]
            dists = np.linalg.norm(cluster_X - centroid, axis=1)
            sorted_relative_indices = np.argsort(dists)

            sample_questions = [
                questions[member_indices[i]]
                for i in sorted_relative_indices[:5]
            ]

            # 3. Tạo nhãn chủ đề ngắn gọn tiếng Việt (4-8 từ)
            label = await cls.generate_cluster_label(sample_questions, is_failed)

            clusters_result.append({
                "period_start": period_start or date.today(),
                "period_end": period_end or date.today(),
                "label": label,
                "size": int(len(member_indices)),
                "sample_questions": sample_questions,
                "is_failed_cluster": is_failed
            })

        return clusters_result

    @staticmethod
    async def generate_cluster_label(samples: List[str], is_failed: bool) -> str:
        """
        Gọi LLM để đặt tên nhãn ngắn gọn tiếng Việt (4-8 từ) từ danh sách câu hỏi mẫu.
        """
        prefix = "Khoảng trống: " if is_failed else "Chủ đề: "
        if settings.OPENAI_API_KEY and settings.OPENAI_API_KEY != "demo_key":
            try:
                prompt = (
                    f"Dưới đây là một số câu hỏi của sinh viên đại học:\n"
                    + "\n".join(f"- {s}" for s in samples)
                    + "\nHãy đặt tên một nhãn chủ đề ngắn gọn (4 đến 8 từ tiếng Việt) "
                    "khái quát nội dung các câu hỏi trên. Chỉ trả về đúng tên nhãn."
                )
                async with httpx.AsyncClient(timeout=5.0) as client:
                    resp = await client.post(
                        f"{settings.OPENAI_BASE_URL}/chat/completions",
                        headers={"Authorization": f"Bearer {settings.OPENAI_API_KEY}"},
                        json={
                            "model": settings.LLM_MODEL,
                            "messages": [{"role": "user", "content": prompt}],
                            "temperature": 0.2,
                            "max_tokens": 30
                        }
                    )
                    if resp.status_code == 200:
                        content = resp.json()["choices"][0]["message"]["content"].strip()
                        return f"{prefix}{content.strip('\"')}"
            except Exception:
                pass

        # Fallback tạo nhãn nhanh theo từ khóa thường gặp
        joined = " ".join(samples).lower()
        if "bảo lưu" in joined:
            return f"{prefix}Quy định bảo lưu kết quả học tập"
        if "học phí" in joined or "miễn giảm" in joined:
            return f"{prefix}Chính sách học phí và miễn giảm"
        if "tốt nghiệp" in joined or "chuẩn đầu ra" in joined:
            return f"{prefix}Điều kiện xét tốt nghiệp đại học"
        if "phòng" in joined:
            return f"{prefix}Tra cứu phòng học và tự học"
        if "lịch" in joined:
            return f"{prefix}Lịch học và thời khóa biểu thi"
        return f"{prefix}Quy chế và thủ tục học vụ chung"

