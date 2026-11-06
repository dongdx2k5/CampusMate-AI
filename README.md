# CampusMate AI — Cổng Thông Tin & Trợ Lý Số Đại Học Tích Hợp RAG Tiếng Việt

**CampusMate AI** là giải pháp Cổng thông tin và Trợ lý học vụ số toàn diện dành cho các trường đại học, ứng dụng kiến trúc **Retrieval-Augmented Generation (RAG)** chuyên sâu cho ngôn ngữ tiếng Việt. Hệ thống tích hợp chặt chẽ các quy tắc nghiệp vụ học đường (BR01–BR08), phân quyền vai trò (RBAC), kiểm chứng trích dẫn nguồn, máy trạng thái thông báo và thuật toán tìm kiếm phòng trống theo thời gian thực.

---

## 1. Tính Năng & Điểm Nổi Bật

### 1.1 Lõi AI/ML & RAG Tiếng Việt
- **Ẩn danh hóa dữ liệu cá nhân (BR08):** Tự động phát hiện và xóa Mã số sinh viên (chuỗi 7–10 chữ số), Email, Số điện thoại và Họ tên đi kèm tiền tố khỏi nội dung câu hỏi trước khi lưu vào nhật ký phân tích hoặc kho tri thức.
- **Viết lại câu hỏi (Query Rewriting):** Kết hợp ngữ cảnh $N=4$ lượt trao đổi gần nhất để tái tạo câu hỏi độc lập, đầy đủ chủ ngữ/vị ngữ.
- **Phân loại ý định 6 nhãn (Intent Routing):** Tự động định tuyến giữa `REGULATION` (Quy chế), `SCHEDULE` (Lịch cá nhân), `ROOM` (Phòng trống), `SERVICE` (Thủ tục dịch vụ), `ANNOUNCEMENT` (Thông báo), và `OUT_OF_SCOPE` (Ngoài phạm vi).
- **Truy hồi lai (Hybrid Retrieval BM25 + Vector):** Tách từ tiếng Việt (`underthesea`), kết hợp tìm kiếm toàn văn (`tsvector`) và tìm kiếm ngữ nghĩa Dense Vector (`pgvector` cosine) qua công thức **Reciprocal Rank Fusion (RRF)**.
- **Chốt chặn & Từ chối có kiểm soát (BR01, BR02, BR03):** 
  - Chỉ truy hồi văn bản đang có hiệu lực `chunks.is_active == True` trừ khi sinh viên hỏi năm cũ.
  - Chốt chặn chọn lọc (Pre-generation Selective Gate) với ngưỡng $\tau_{\text{retr}} = 0.35$.
  - Kiểm chứng trích dẫn và tính điểm tin cậy `confidence`. Nếu điểm tin cậy $< 0.65$, hệ thống từ chối trả lời (`answer = ""`) và trả về `fallback` gợi ý phòng ban phụ trách kèm thông tin liên hệ.
  - Cố định cảnh báo tham khảo trên mọi phản hồi AI.
- **Phát hiện khoảng trống tri thức (UC12 / FR13):** Thuật toán phân cụm HDBSCAN / K-Means tự động nhóm các câu hỏi thất bại hoặc bị đánh giá `UNHELPFUL` để thông báo cho cán bộ nhà trường bổ sung văn bản quy chế.

### 1.2 Nghiệp vụ & Cổng Thông Tin
- **Cổng Sinh viên & Giảng viên:**
  - Khung chat trực quan hỗ trợ streaming token Server-Sent Events (SSE).
  - Ngăn xem trích dẫn (Citation Drawer) hiển thị nguyên văn đoạn trích, số điều, khoản và trang PDF gốc.
  - Lịch học/lịch thi cá nhân (BR04) kèm nút xuất tệp chuẩn iCal (`.ics`).
  - Tìm kiếm phòng học & không gian tự học trống theo thời gian thực (BR06 `NOT EXISTS` kiểm tra giao thoa khung giờ).
  - Danh bạ thủ tục hành chính, quy trình thực hiện và link tải biểu mẫu trực tuyến.
- **Cổng Cán bộ & Quản trị:**
  - Quản lý thông báo theo máy trạng thái FSM (BR05: Draft -> Pending Approval -> Scheduled -> Published -> Revoked).
  - Quản lý kho quy chế, tải file PDF/DOCX, chuyển đổi hiệu lực và kích hoạt lập chỉ mục AI ngầm (BR07).
  - Báo cáo phân tích câu hỏi và khoảng trống tri thức.
  - Phân quyền tài khoản (RBAC) và nhật ký kiểm toán hệ thống (`audit_logs`).

---

## 2. Kiến Trúc Kỹ Thuật

```
campusmate-ai/
├── docker-compose.yml          # PostgreSQL 16 (pgvector), Redis 7, MinIO, Backend, Frontend
├── SPEC.md                     # Đặc tả kỹ thuật & nghiệp vụ chi tiết
├── backend/
│   ├── app/
│   │   ├── main.py             # Khởi tạo FastAPI, CORS, Lifespan auto-seed
│   │   ├── core/               # config.py, security.py (SSO JWT + RBAC), pii_anonymizer.py
│   │   ├── models/             # 16 bảng CSDL SQLAlchemy 2.0 (HNSW & GIN index)
│   │   ├── schemas/            # Schemas Pydantic v2
│   │   ├── ml/                 # chunker.py, hybrid_retriever.py, reranker.py, intent_router.py, clustering.py, rag_pipeline.py
│   │   ├── services/           # announcement_fsm.py, room_finder.py, sis_sync.py, storage.py
│   │   ├── tasks/              # indexing.py, background tasks
│   │   └── api/v1/             # chat.py, schedule.py, rooms.py, announcements.py, services.py, admin.py, auth.py
│   ├── eval/                   # Bộ kịch bản thực nghiệm E0-E8 (Recall@k, MRR, nDCG, AUROC)
│   └── requirements.txt
└── frontend/
    ├── src/
    │   ├── app/                # Next.js App Router ((portal) và admin screens)
    │   ├── components/         # ChatWindow, CitationDrawer, RoomFilter, AnnouncementEditor, AnalyticsCharts, Navbar
    │   └── lib/                # API client, SSE stream reader, AuthProvider & Role switcher
    └── package.json
```

---

## 3. Hướng Dẫn Cài Đặt & Chạy Hệ Thống

### Cách 1: Khởi chạy toàn bộ bằng Docker Compose (Khuyến nghị)
```bash
docker compose up -d --build
```
Dịch vụ sẽ tự động kích hoạt:
- **Frontend Portal:** [http://localhost:3000](http://localhost:3000)
- **Backend API & Swagger Docs:** [http://localhost:8000/docs](http://localhost:8000/docs)
- **MinIO Console:** [http://localhost:9001](http://localhost:9001)

### Cách 2: Chạy trực tiếp cho Phát triển (Development)

#### Backend (FastAPI):
```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

#### Frontend (Next.js):
```bash
cd frontend
npm install
npm run dev
```

---

## 4. Tài Khoản Thử Nghiệm Nhanh (Demo Accounts)

Hệ thống tích hợp sẵn bộ chuyển đổi vai trò (Role Switcher) ở góc phải thanh điều hướng Navbar. Bạn có thể chuyển đổi tức thì giữa các vai trò để kiểm tra phân quyền RBAC:

| Vai trò | Email Demo | Mật khẩu mặc định | Quyền hạn chính |
| :--- | :--- | :--- | :--- |
| **Sinh viên (STUDENT)** | `demo.student@uni.edu.vn` | `CampusMate2026!` | Hỏi đáp RAG, xem lịch học cá nhân, thông báo đối tượng, tìm phòng trống, đánh giá AI |
| **Giảng viên (LECTURER)** | `demo.lecturer@uni.edu.vn` | `CampusMate2026!` | Xem lịch dạy, tìm phòng trống dạy bù/họp |
| **Cán bộ (STAFF)** | `demo.staff@uni.edu.vn` | `CampusMate2026!` | Soạn thông báo khoa, tải văn bản quy chế, lập chỉ mục AI, xem phân tích |
| **Quản trị viên (ADMIN)** | `demo.admin@uni.edu.vn` | `CampusMate2026!` | Duyệt thông báo toàn trường, phân quyền người dùng, xem nhật ký kiểm toán (Audit Logs) |

---

## 5. Chạy Bộ Thực Nghiệm Đánh Giá AI/ML (E0 – E8)

Để đo đạc các chỉ số kỹ thuật của pipeline RAG:
```bash
python backend/eval/run_eval.py
```
Bộ script thực thi và đo đạc:
- **E0:** Baseline độ trễ đường ống (Latency ms)
- **E1:** Recall@1, Recall@3, Recall@5
- **E2:** Mean Reciprocal Rank (MRR)
- **E3:** Normalized Discounted Cumulative Gain (nDCG@5)
- **E4:** Độ chính xác phân loại ý định (Intent Accuracy)
- **E5:** Độ chính xác chốt chặn từ chối câu hỏi ngoài phạm vi (Selective Gate Rejection & AUROC)
- **E6:** Tỷ lệ trích dẫn hợp lệ (Citation Grounding Rate theo BR02)
- **E7:** Tỷ lệ bảo toàn ẩn danh PII (BR08)
- **E8:** Tự động ghi nhận báo cáo thực nghiệm vào bảng `eval_runs` và `eval_results` trong CSDL.

