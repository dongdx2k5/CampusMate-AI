# ĐẶC TẢ KỸ THUẬT & NGHIỆP VỤ: HỆ THỐNG CAMPUSMATE AI
**Vai trò:** Kỹ sư Full-Stack & Học máy (AI/ML Engineer)
**Nhiệm vụ:** Xây dựng mã nguồn hoàn chỉnh cho **CampusMate AI** — Cổng thông tin và Trợ lý số đại học tích hợp RAG tiếng Việt, tuân thủ tuyệt đối các quy tắc nghiệp vụ, cấu trúc cơ sở dữ liệu, hợp đồng API và luồng xử lý AI/ML dưới đây.

---

## 1. CÔNG NGHỆ SỬ DỤNG & KIẾN TRÚC
- **Frontend:** Next.js (App Router, TypeScript, TailwindCSS, Shadcn UI). Dùng chung một mã nguồn cho cả Cổng Sinh viên/Giảng viên và Cổng Quản trị/Cán bộ (phân chia giao diện theo quyền RBAC).
- **Backend:** FastAPI (Python 3.11+, SQLAlchemy 2.0 Async, Pydantic v2, Alembic).
- **Cơ sở dữ liệu:** PostgreSQL 16 tích hợp sẵn extension `pgvector` (lưu trữ cả dữ liệu quan hệ, vector embedding và tìm kiếm toàn văn bản `tsvector`).
- **Bộ nhớ đệm & Hàng đợi (Cache & Queue):** Redis (cache câu hỏi lặp lại, chạy tác vụ nền qua Celery hoặc ARQ cho việc lập chỉ mục văn bản, đồng bộ lịch SIS/LMS và phân cụm câu hỏi).
- **Lưu trữ tệp (Object Storage):** MinIO hoặc S3-compatible (lưu trữ file PDF/DOCX quy chế gốc).
- **Lõi AI/ML tiếng Việt:**
  - Tách từ tiếng Việt ( phục vụ BM25): `underthesea` hoặc `pyvi`
  - Mô hình Embedding: `BAAI/bge-m3` hoặc `intfloat/multilingual-e5-base`
  - Mô hình Xếp hạng lại (Reranker): `BAAI/bge-reranker-v2-m3`
  - Phân loại ý định (Intent Classifier): Tinh chỉnh `vinai/phobert-base-v2` (có cơ chế fallback sang LLM Few-shot)
  - Phân cụm câu hỏi (Clustering): `HDBSCAN` hoặc `K-Means` (`scikit-learn`)
  - Khung gọi LLM: Tương thích chuẩn OpenAI API (hỗ trợ cả OpenAI API và mô hình mã nguồn mở tự host qua `vLLM`)

---

## 2. PHÂN QUYỀN (RBAC) & QUY TẮC NGHIỆP VỤ BẮT BUỘC

### 2.1 Các vai trò trong hệ thống (`UserRole` Enum)
- `STUDENT` (Sinh viên): Hỏi đáp quy chế (RAG) nhiều lượt, xem lịch học/lịch thi cá nhân, xem thông báo thuộc đối tượng của mình, tìm phòng trống, tra cứu dịch vụ, đánh giá/báo sai câu trả lời của AI.
- `LECTURER` (Giảng viên): Xem lịch giảng dạy cá nhân, tìm phòng trống để dạy bù hoặc họp nhóm, tra cứu dịch vụ.
- `STAFF` (Cán bộ phòng ban): Soạn/quản lý thông báo, tải văn bản quy chế, quản lý phiên bản quy chế, xác nhận hiệu lực văn bản để kích hoạt lập chỉ mục AI, xem thống kê phân tích câu hỏi.
- `UNIT_HEAD` / `ADMIN` (Trưởng đơn vị / Quản trị hệ thống): Duyệt thông báo cấp toàn trường, quản lý tài khoản/vai trò/cấu hình hệ thống, xem nhật ký kiểm toán (`audit_logs`) và báo cáo phân tích.

### 2.2 Quy tắc nghiệp vụ bắt buộc (Phải kiểm soát chặt trong Code)
- **BR01 (Hiệu lực văn bản):** Khi truy hồi RAG, BẮT BUỘC phải lọc `chunks.is_active == True` (tương ứng với `document_versions.status == 'ACTIVE'`). Các phiên bản đã hết hiệu lực (`status == 'EXPIRED'`) CHỈ được truy vấn khi trong câu hỏi của sinh viên có nêu rõ năm hoặc số phiên bản cũ.
- **BR02 (Bắt buộc trích dẫn & Từ chối có kiểm soát):** Mọi câu trả lời về quy chế BẮT BUỘC phải có ít nhất 1 trích dẫn hợp lệ (tên văn bản, điều, khoản, trang). Nếu không tìm thấy đoạn văn bản phù hợp HOẶC điểm tin cậy `confidence < CONFIDENCE_THRESHOLD` (mặc định `0.65`), hệ thống PHẢI từ chối trả lời: gán `answer = ""`, và trả về đối tượng `fallback` gợi ý phòng ban phụ trách (`Unit`) kèm thông tin liên hệ.
- **BR03 (Cảnh báo tham khảo):** Mọi phản hồi của AI phải đính kèm dòng cảnh báo: *"Câu trả lời của AI chỉ mang tính tham khảo; văn bản gốc là căn cứ chính thức."*
- **BR04 (Cô lập dữ liệu cá nhân & Đúng đối tượng):**
  - Người dùng CHỈ được truy vấn lịch học/lịch thi của chính mình (`schedule_entries.user_id == current_user.id`).
  - Sinh viên CHỈ nhìn thấy thông báo khớp với thuộc tính cá nhân của mình (`unit_id`, `cohort` - khóa, `major` - ngành, hoặc thông báo toàn trường `"ALL"`).
- **BR05 (Máy trạng thái duyệt thông báo):**
  - Vòng đời: `DRAFT` (Nháp) -> `PENDING_APPROVAL` (Chờ duyệt) -> `SCHEDULED` (Hẹn giờ) -> `PUBLISHED` (Đã đăng) -> `REVOKED` (Thu hồi).
  - Thông báo nội bộ cấp đơn vị/khoa (`audience.scope == "UNIT"`) có thể được đăng trực tiếp bởi cán bộ/trưởng đơn vị đó.
  - Thông báo cấp toàn trường (`audience.scope == "SCHOOL"`) BẮT BUỘC phải qua trạng thái `PENDING_APPROVAL` và được phê duyệt trước khi chuyển sang `PUBLISHED`.
  - Thông báo đã đăng (`PUBLISHED`) KHÔNG BAO GIỜ được xóa cứng (hard-delete); khi cần gỡ chỉ được chuyển sang trạng thái `REVOKED` để lưu vết kiểm toán.
- **BR06 (Điều kiện phòng trống):** Một phòng được coi là trống trong khung giờ `[date, start_time, end_time]` khi và chỉ khi KHÔNG tồn tại bất kỳ bản ghi nào trong bảng `schedule_entries` (gồm lịch học, lịch thi, lịch đặt phòng) thỏa mãn:
  `entry.date == date AND entry.start_time < end_time AND entry.end_time > start_time`.
- **BR07 (Kiểm soát lập chỉ mục AI):** Khi cán bộ mới tải lên một phiên bản văn bản quy chế (`DocumentVersion`), trạng thái ban đầu là `DRAFT` và CHƯA được đưa vào kho AI. Tiến trình cắt đoạn và lập chỉ mục vector CHỈ được kích hoạt khi cán bộ bấm xác nhận hiệu lực (`status = 'ACTIVE'`). Khi một phiên bản mới được kích hoạt `ACTIVE`, toàn bộ các phiên bản `ACTIVE` trước đó của cùng văn bản phải tự động chuyển sang `EXPIRED` và cập nhật `chunks.is_active = False`.
- **BR08 (Ẩn danh hóa dữ liệu cá nhân - PII):** Trước khi lưu câu hỏi vào bảng phân tích/phân cụm hoặc nhật ký huấn luyện, phải chạy bộ lọc xóa thông tin định danh cá nhân (Mã số sinh viên dạng chuỗi 7–10 chữ số, email, số điện thoại, họ tên đi kèm từ khóa nhận diện) và lưu vào cột `anonymized_content`. Tuyệt đối không đưa dữ liệu cá nhân vào bảng `chunks`.

---

## 3. THIẾT KẾ CƠ SỞ DỮ LIỆU (PostgreSQL + pgvector)
Cài đặt đầy đủ các bảng sau bằng SQLAlchemy 2.0 và tạo migration với Alembic:

1. **`units`** (Đơn vị / Khoa / Phòng ban):
   - `id` (UUID, PK), `name` (VARCHAR), `kind` (ENUM: `FACULTY`, `DEPARTMENT`, `CENTER`), `contact_email` (VARCHAR), `phone` (VARCHAR), `office_location` (VARCHAR).
2. **`users`** (Người dùng):
   - `id` (UUID, PK), `email` (VARCHAR, Unique, Indexed), `full_name` (VARCHAR), `role` (ENUM: `STUDENT`, `LECTURER`, `STAFF`, `ADMIN`), `unit_id` (UUID, FK -> `units.id`), `cohort` (VARCHAR, nullable - Khóa học), `major` (VARCHAR, nullable - Ngành học), `is_active` (BOOL).
3. **`documents`** (Văn bản quy chế):
   - `id` (UUID, PK), `title` (VARCHAR), `issuer_unit_id` (UUID, FK -> `units.id`), `status` (ENUM: `ACTIVE`, `ARCHIVED`), `created_at` (TIMESTAMP).
4. **`document_versions`** (Phiên bản văn bản):
   - `id` (UUID, PK), `document_id` (UUID, FK -> `documents.id`), `version_no` (VARCHAR), `effective_from` (DATE), `effective_to` (DATE, nullable), `status` (ENUM: `DRAFT`, `ACTIVE`, `EXPIRED`), `file_url` (VARCHAR), `approved_by` (UUID, FK -> `users.id`, nullable), `indexed_at` (TIMESTAMP, nullable).
5. **`chunks`** (Đoạn văn bản phục vụ RAG):
   - `id` (UUID, PK), `version_id` (UUID, FK -> `document_versions.id`, ondelete=CASCADE), `article` (VARCHAR, nullable - Điều), `clause` (VARCHAR, nullable - Khoản), `page` (INT - Trang), `text` (TEXT), `embedding` (`VECTOR(1024)`), `tsv` (`TSVECTOR`), `is_active` (BOOL, Indexed).
   - **Chỉ mục (Indexes):** Tạo HNSW index trên cột `embedding` (`vector_cosine_ops`) và GIN index trên cột `tsv`.
6. **`chat_sessions`** (Phiên hội thoại):
   - `id` (UUID, PK), `user_id` (UUID, FK -> `users.id`), `title` (VARCHAR), `started_at` (TIMESTAMP), `channel` (VARCHAR, default `'WEB'`).
7. **`messages`** (Tin nhắn hỏi đáp):
   - `id` (UUID, PK), `session_id` (UUID, FK -> `chat_sessions.id`, ondelete=CASCADE), `role` (ENUM: `USER`, `ASSISTANT`), `content` (TEXT), `anonymized_content` (TEXT, nullable), `intent` (ENUM: `REGULATION`, `SCHEDULE`, `ROOM`, `SERVICE`, `ANNOUNCEMENT`, `OUT_OF_SCOPE`, nullable), `confidence` (FLOAT, nullable), `fallback` (JSONB, nullable), `latency_ms` (INT, nullable), `model_version` (VARCHAR, nullable), `created_at` (TIMESTAMP).
8. **`citations`** (Trích dẫn nguồn cho câu trả lời):
   - `message_id` (UUID, FK -> `messages.id`, PK), `chunk_id` (UUID, FK -> `chunks.id`, PK), `rank` (INT), `quote` (TEXT).
9. **`feedback`** (Đánh giá câu trả lời từ sinh viên):
   - `id` (UUID, PK), `message_id` (UUID, FK -> `messages.id`, Unique), `user_id` (UUID, FK -> `users.id`), `rating` (ENUM: `HELPFUL`, `UNHELPFUL`), `comment` (TEXT, nullable), `is_reported_wrong` (BOOL, default False), `created_at` (TIMESTAMP).
10. **`announcements`** (Thông báo):
    - `id` (UUID, PK), `unit_id` (UUID, FK -> `units.id`), `author_id` (UUID, FK -> `users.id`), `title` (VARCHAR), `body` (TEXT), `audience` (JSONB: `{"scope": "SCHOOL"|"UNIT", "unit_ids": [], "cohorts": [], "majors": []}`), `status` (ENUM: `DRAFT`, `PENDING_APPROVAL`, `SCHEDULED`, `PUBLISHED`, `REVOKED`), `publish_at` (TIMESTAMP, nullable), `approved_by` (UUID, FK -> `users.id`, nullable), `created_at` (TIMESTAMP).
11. **`announcement_reads`** (Trạng thái đã đọc thông báo):
    - `announcement_id` (UUID, FK -> `announcements.id`, PK), `user_id` (UUID, FK -> `users.id`, PK), `read_at` (TIMESTAMP), `channel` (VARCHAR).
12. **`rooms`** (Phòng học & Không gian tự học):
    - `id` (UUID, PK), `code` (VARCHAR, Unique), `building` (VARCHAR, Indexed), `capacity` (INT, Indexed), `room_type` (ENUM: `CLASSROOM`, `LAB`, `SELF_STUDY`, `COMMON_SPACE`), `equipment` (JSONB, ví dụ: `["PROJECTOR", "AC", "MIC"]`), `opening_hours` (VARCHAR).
13. **`class_sections`** (Lớp học phần):
    - `id` (UUID, PK), `course_code` (VARCHAR), `course_name` (VARCHAR), `semester` (VARCHAR), `lecturer_id` (UUID, FK -> `users.id`, nullable).
14. **`schedule_entries`** (Bản ghi lịch học / lịch thi / đặt phòng):
    - `id` (UUID, PK), `section_id` (UUID, FK -> `class_sections.id`, nullable), `user_id` (UUID, FK -> `users.id`, Indexed), `room_id` (UUID, FK -> `rooms.id`, Indexed), `entry_type` (ENUM: `CLASS`, `EXAM`, `BOOKING`), `date` (DATE, Indexed), `start_time` (TIME), `end_time` (TIME), `synced_at` (TIMESTAMP).
15. **`services`** (Danh bạ dịch vụ & Thủ tục hành chính):
    - `id` (UUID, PK), `unit_id` (UUID, FK -> `units.id`), `name` (VARCHAR), `procedure` (TEXT), `form_urls` (JSONB), `opening_hours` (VARCHAR), `contact` (VARCHAR).
16. **Các bảng phục vụ Phân tích, Kiểm toán & Thực nghiệm:**
    - `query_clusters`: `id` (UUID, PK), `period_start` (DATE), `period_end` (DATE), `label` (VARCHAR), `size` (INT), `sample_questions` (JSONB), `is_failed_cluster` (BOOL).
    - `audit_logs`: `id` (UUID, PK), `actor_id` (UUID, FK -> `users.id`), `action` (VARCHAR), `target_type` (VARCHAR), `target_id` (VARCHAR), `metadata` (JSONB), `created_at` (TIMESTAMP).
    - `eval_runs`: `id` (UUID, PK), `config` (JSONB), `commit_sha` (VARCHAR), `metrics_summary` (JSONB), `created_at` (TIMESTAMP).
    - `eval_results`: `id` (UUID, PK), `run_id` (UUID, FK -> `eval_runs.id`), `question_id` (VARCHAR), `metrics` (JSONB).

---

## 4. LUỒNG NGHIỆP VỤ CHI TIẾT & THUẬT TOÁN AI/ML

### Luồng 1: Hội thoại nhiều lượt & Pipeline RAG tiếng Việt (`POST /api/v1/chat/sessions/{id}/messages`)
Khi sinh viên gửi một câu hỏi, hệ thống thực thi tuần tự 8 bước sau:

1. **Ẩn danh hóa PII & Lấy ngữ cảnh hội thoại:**
   - Lấy $N = 4$ tin nhắn gần nhất trong cùng `session_id`.
   - Chạy hàm ẩn danh hóa câu hỏi của người dùng (xóa MSSV, SĐT, email, tên riêng) để lưu vào `anonymized_content` (tuân thủ BR08).
2. **Viết lại truy vấn (Query Rewriting - FR03):**
   - Nếu phiên chat đã có lịch sử trước đó, gọi LLM nhỏ với prompt cố định để gộp ngữ cảnh các lượt trước và câu hỏi hiện tại thành một câu hỏi tiếng Việt độc lập, đầy đủ chủ ngữ/vị ngữ.
3. **Phân loại ý định & Định tuyến (Intent Classification & Routing - FR02):**
   - Phân loại câu hỏi độc lập vào 1 trong 6 nhãn: `REGULATION` (Quy chế), `SCHEDULE` (Lịch học/thi), `ROOM` (Phòng trống), `SERVICE` (Dịch vụ/Thủ tục), `ANNOUNCEMENT` (Thông báo), `OUT_OF_SCOPE` (Ngoài phạm vi).
   - **Nếu là `SCHEDULE` / `ROOM` / `SERVICE` / `ANNOUNCEMENT`:** Gọi trực tiếp Service nội bộ tương ứng để truy vấn DB, tổng hợp câu trả lời tự nhiên, trả về qua SSE và kết thúc.
   - **Nếu là `OUT_OF_SCOPE`:** Chuyển thẳng sang Bước 8 (Từ chối có kiểm soát).
   - **Nếu là `REGULATION`:** Đi tiếp sang Bước 4 (Pipeline RAG).
4. **Truy hồi lai (Hybrid Retrieval: BM25 + Vector + Bộ lọc hiệu lực):**
   - Kiểm tra xem câu hỏi có yêu cầu tra cứu năm/phiên bản cũ không. Nếu không, áp đặt điều kiện lọc cứng `chunks.is_active == True` (BR01).
   - **Nhánh từ khóa (BM25/FTS):** Dùng `underthesea` tách từ tiếng Việt (ví dụ: `"bảo_lưu kết_quả học_tập"`), truy vấn trên cột `tsv` của PostgreSQL, lấy top $k_1 = 20$ đoạn.
   - **Nhánh ngữ nghĩa (Dense Vector):** Mã hóa câu hỏi bằng mô hình `BGE-M3`, truy vấn khoảng cách cosine (`embedding <=> :query_vec`) trên `pgvector`, lấy top $k_2 = 20$ đoạn.
   - **Hợp nhất kết quả (Reciprocal Rank Fusion - RRF):**
     $$\text{RRF\_Score}(d) = \frac{w_{\text{bm25}}}{60 + \text{rank}_{\text{bm25}}(d)} + \frac{w_{\text{vec}}}{60 + \text{rank}_{\text{vec}}(d)}$$
     Lấy top $M = 15$ đoạn có điểm RRF cao nhất.
5. **Xếp hạng lại (Cross-Encoder Reranking):**
   - Đưa 15 cặp `(câu_hỏi_độc_lập, chunk.text)` qua mô hình `bge-reranker-v2-m3` để chấm điểm tương đồng sâu.
   - Sắp xếp giảm dần và giữ lại top $K = 5$ đoạn tốt nhất.
6. **Chốt chặn trước khi sinh (Pre-Generation Selective Gate):**
   - Nếu không có đoạn nào trả về HOẶC điểm reranker cao nhất thấp hơn ngưỡng $\tau_{\text{retr}}$ (ví dụ `0.35`), hủy việc gọi LLM và chuyển thẳng tới Bước 8 (Từ chối trả lời).
7. **Sinh câu trả lời có trích dẫn & Kiểm chứng (Cited Generation & Verification):**
   - **Chống Prompt Injection:** Tách biệt hoàn toàn chỉ thị hệ thống (System Prompt) và dữ liệu văn bản đưa vào thẻ `<context>`. Cấm mô hình làm theo bất kỳ mệnh lệnh nào nằm bên trong nội dung văn bản hoặc câu hỏi làm trái quy tắc hệ thống.
   - Yêu cầu LLM trả lời ở mức `temperature = 0.1`, chỉ sử dụng thông tin trong 5 đoạn được cung cấp, mỗi luận điểm phải gắn ký hiệu trích dẫn `[1]`, `[2]` tương ứng với thứ tự đoạn.
   - Stream từng token về giao diện qua giao thức Server-Sent Events (`event: token`).
   - **Kiểm chứng & Tính điểm tin cậy (`confidence`):** Kiểm tra các trích dẫn `[n]` có tồn tại thật trong danh sách chunk đưa vào không, kết hợp xác suất của Reranker và tỷ lệ mệnh đề có dẫn nguồn để tính điểm `confidence` trong khoảng `[0.0, 1.0]`. Nếu `confidence < 0.65`, hủy kết quả và chuyển sang Bước 8.
8. **Xử lý Từ chối (Fallback) & Lưu trữ:**
   - **Khi từ chối (FR05, BR02):** Gán `answer = ""`, trả về `fallback = {"reason": "INSUFFICIENT_EVIDENCE", "suggestedUnit": "Phòng Đào tạo", "contactEmail": "daotao@uni.edu.vn", "message": "Hệ thống chưa tìm thấy điều khoản quy chế chính thức cho câu hỏi này. Bạn vui lòng liên hệ trực tiếp Phòng Đào tạo để được hướng dẫn chính xác."}`.
   - Lưu bản ghi `Message` và các bản ghi `Citation` vào PostgreSQL. Gửi sự kiện SSE cuối cùng (`event: done`) chứa toàn bộ JSON hoàn chỉnh.

---

### Luồng 2: Nạp văn bản quy chế & Cắt đoạn theo cấu trúc pháp lý (UC10, UC11)
1. **Tải tệp lên (`POST /api/v1/admin/documents/{id}/versions`):**
   - Cán bộ tải file PDF/DOCX lên MinIO/S3. Hệ thống tạo bản ghi `DocumentVersion` ở trạng thái `DRAFT`.
2. **Xác nhận hiệu lực & Lập chỉ mục (`POST /api/v1/admin/documents/{id}/reindex`):**
   - Cán bộ bấm xác nhận hiệu lực (BR07).
   - Trong một Transaction CSDL: chuyển `DocumentVersion` hiện tại sang `ACTIVE`; chuyển toàn bộ các phiên bản cũ của cùng `document_id` sang `EXPIRED` và cập nhật toàn bộ chunk cũ `SET is_active = FALSE`.
   - Đẩy tác vụ chạy nền (Background Task) thực hiện lập chỉ mục:
     - **Trích xuất văn bản:** Đọc text và số trang từ PDF (`PyMuPDF`) hoặc DOCX (`python-docx`). Nếu phát hiện trang PDF là ảnh scan (độ dài text trích xuất gần bằng 0), tự động gọi OCR tiếng Việt (`Tesseract` / `VietOCR`).
     - **Cắt đoạn theo cấu trúc văn bản pháp lý (Legal Structure Chunking):** Dùng biểu thức chính quy (Regex) nhận diện cấu trúc:
       - Chương: `^Chương\s+[IVXLCDM\d]+`
       - Điều: `^Điều\s+(\d+)[\.\:]?\s*(.*)`
       - Khoản: `^(\d+)\.\s+(.*)`
     - Cắt văn bản theo từng **Điều** và **Khoản**. Nếu một khoản dài quá `512 tokens`, áp dụng cửa sổ trượt (sliding window) với độ chồng lấn `overlap = 64 tokens` nhưng vẫn giữ nguyên metadata `article` (Điều), `clause` (Khoản), `page` (Trang) cho mọi đoạn con.
     - **Tạo Vector & Full-text:** Tính vector embedding (`BGE-M3`) và tách từ tiếng Việt tạo `tsvector` cho từng đoạn, sau đó bulk-insert vào bảng `chunks` với `is_active = True`.
     - Ghi nhận thao tác vào bảng `audit_logs`.

---

### Luồng 3: Phân tích câu hỏi & Phát hiện khoảng trống tri thức (UC12 / FR13)
Tác vụ chạy định kỳ hằng ngày (hoặc kích hoạt qua API quản trị):
1. Lấy toàn bộ tin nhắn của người dùng (`role == 'USER'`) trong khoảng thời gian `[from_date, to_date]`, chỉ đọc cột `anonymized_content` đã ẩn danh (BR08).
2. Chia làm 2 tập để phân cụm:
   - **Tập A (Toàn bộ câu hỏi):** Đưa vector embedding của câu hỏi vào thuật toán `HDBSCAN` hoặc `K-Means` để tìm các cụm chủ đề được sinh viên hỏi nhiều nhất (`is_failed_cluster = False`).
   - **Tập B (Câu hỏi thất bại / Khoảng trống tri thức):** Lọc các câu hỏi mà câu trả lời của AI bị rơi vào `fallback IS NOT NULL` hoặc bị sinh viên đánh giá `UNHELPFUL` / báo sai. Phân cụm riêng nhóm này (`is_failed_cluster = True`) để chỉ ra cho cán bộ biết nhà trường đang thiếu văn bản hướng dẫn ở mảng nào.
3. Với mỗi cụm, lấy 5 câu hỏi đại diện gần tâm cụm nhất đưa vào LLM để đặt tên nhãn chủ đề ngắn gọn bằng tiếng Việt (4–8 từ).
4. Lưu kết quả vào bảng `query_clusters`.

---

### Luồng 4: Đồng bộ lịch học & Tìm phòng trống (UC06, UC07)
1. **Đồng bộ dữ liệu từ hệ thống đào tạo (SIS/LMS Sync):**
   - Worker định kỳ gọi API của hệ thống đào tạo (hoặc đọc từ file CSV/JSON xuất định kỳ nếu không có API trực tiếp) để cập nhật `rooms`, `class_sections`, `schedule_entries` kèm mốc thời gian `synced_at`.
   - Khi hệ thống ngoài mất kết nối, CampusMate vẫn trả về dữ liệu đồng bộ gần nhất trong DB kèm trường `lastSyncedAt` để người dùng biết độ mới của dữ liệu.
2. **Truy vấn tìm phòng trống (`GET /api/v1/rooms/available`):**
   - Nhận tham số lọc: `date`, `start`, `end`, và tùy chọn `building`, `capacity`, `equipment`.
   - Áp dụng đúng quy tắc BR06 bằng truy vấn SQL `NOT EXISTS` kiểm tra giao thoa khung giờ trên bảng `schedule_entries`.

---

## 5. ĐẶC TẢ HỢP ĐỒNG REST API (`/api/v1`)
Tất cả API đều xác thực qua Bearer Token từ SSO (`Authorization: Bearer <token>`).

| Phương thức & Đường dẫn | Vai trò | Tham số đầu vào (Body / Query) | Phản hồi (Response) |
| :--- | :--- | :--- | :--- |
| `POST /chat/sessions` | `STUDENT` | `{"title": "Tùy chọn"}` | `{"sessionId": "uuid", "startedAt": "..."}` |
| `POST /chat/sessions/{id}/messages` | `STUDENT` | `{"content": "Điều kiện bảo lưu kết quả học tập?"}` | **SSE Stream:** trả dần `event: token` và kết thúc bằng `event: done` kèm JSON chuẩn bên dưới |
| `POST /chat/messages/{id}/feedback` | `STUDENT` | `{"rating": "HELPFUL"\|"UNHELPFUL", "comment": "...", "isReportedWrong": false}` | `{"status": "ok"}` |
| `GET /schedule` | `STUDENT`, `LECTURER` | `?from=YYYY-MM-DD&to=YYYY-MM-DD` | `{"lastSyncedAt": "...", "entries": [...]}` (Chỉ trả lịch của chính người dùng đang đăng nhập) |
| `GET /schedule/export.ics` | `STUDENT`, `LECTURER` | `?semester=20251` | File lịch chuẩn `text/calendar` (`.ics`) |
| `GET /announcements` | `STUDENT` | `?unread=true&page=1&size=20` | Danh sách thông báo khớp đối tượng (`unit_id`, `cohort`, `major`) |
| `POST /announcements/{id}/read` | `STUDENT` | `{}` | `{"readAt": "..."}` |
| `GET /rooms/available` | `STUDENT`, `LECTURER` | `?date=YYYY-MM-DD&start=08:00&end=10:00&building=A1&capacity=40` | `{"rooms": [...], "lastSyncedAt": "..."}` |
| `GET /services` | `STUDENT` | `?q=cấp lại thẻ sinh viên&unitId=...` | `{"services": [...]}` |
| `POST /admin/announcements` | `STAFF` | `{"title": "...", "body": "...", "audience": {...}, "publishAt": "..."}` | Bản ghi thông báo (`DRAFT` hoặc `PENDING_APPROVAL`) |
| `POST /admin/announcements/{id}/publish` | `STAFF`, `ADMIN` | `{}` | Kiểm tra quyền duyệt theo BR05 và chuyển sang `PUBLISHED` |
| `POST /admin/announcements/{id}/revoke` | `STAFF`, `ADMIN` | `{"reason": "..."}` | Chuyển trạng thái sang `REVOKED` + ghi `AuditLog` |
| `POST /admin/documents` | `STAFF` | `{"title": "...", "issuerUnitId": "..."}` | Tạo đầu mục văn bản quy chế mới |
| `POST /admin/documents/{id}/versions` | `STAFF` | `multipart/form-data` (`file`, `versionNo`, `effectiveFrom`, `effectiveTo`) | Tạo `DocumentVersion` ở trạng thái `DRAFT` |
| `POST /admin/documents/{id}/reindex` | `STAFF` | `{"versionId": "uuid"}` | Kích hoạt hiệu lực theo BR07 & chạy ngầm tiến trình cắt đoạn/lập chỉ mục |
| `GET /admin/analytics/top-questions` | `STAFF`, `ADMIN` | `?from=YYYY-MM-DD&to=YYYY-MM-DD` | `{"topClusters": [...], "failedClusters": [...], "satisfactionRate": 0.88}` |
| `GET /admin/users` & `POST /admin/users` | `ADMIN` | Bộ lọc người dùng / Cập nhật vai trò | Danh sách người dùng / Cập nhật + ghi `AuditLog` |
| `GET /admin/audit-logs` | `ADMIN` | `?actorId=...&action=...&from=...` | Danh sách nhật ký kiểm toán có phân trang |

**Cấu trúc JSON bắt buộc ở sự kiện kết thúc luồng stream (`event: done`) của API Hỏi đáp:**
```json
{
  "messageId": "msg_123",
  "answer": "Sinh viên được phép nghỉ học tạm thời và bảo lưu kết quả học tập khi có đủ các điều kiện theo quy định [1].",
  "disclaimer": "Câu trả lời của AI chỉ mang tính tham khảo; văn bản gốc là căn cứ chính thức.",
  "confidence": 0.82,
  "citations": [
    {
      "ref": 1,
      "documentTitle": "Quy chế đào tạo đại học chính quy",
      "version": "2025",
      "article": "Điều 15, khoản 2",
      "page": 9,
      "quote": "Sinh viên được nghỉ học tạm thời và bảo lưu kết quả...",
      "url": "/documents/42?page=9"
    }
  ],
  "fallback": null
}
```

---

## 6. YÊU CẦU GIAO DIỆN NGƯỜI DÙNG (FRONTEND SCREENS)
Thiết kế giao diện tiếng Việt hiện đại, tương thích tốt trên điện thoại (Responsive) và đạt chuẩn trợ năng WCAG 2.1 AA:

### 6.1 Cổng Sinh viên & Giảng viên (`/app/(portal)/...`)
- **Trang chủ / Trợ lý AI (`/`):**
  - Cột chính: Khung chat hội thoại nhiều lượt hiển thị chữ chạy dần (SSE streaming), các thẻ trích dẫn `[1]` có thể bấm vào để mở ngăn bên cạnh (Citation Drawer) xem nguyên văn đoạn trích, số điều/khoản và trang PDF gốc. Hiển thị cố định cảnh báo tham khảo (BR03) và cụm nút đánh giá Hữu ích / Không hữu ích / Báo sai (FR04).
  - Nếu AI từ chối trả lời (`fallback != null`), hiển thị hộp thông báo nổi bật kèm thông tin liên hệ của phòng ban được gợi ý.
  - Cột phụ: Tóm tắt lịch học/lịch thi hôm nay, thông báo mới chưa đọc và các nút gợi ý câu hỏi thường gặp.
- **Lịch cá nhân (`/schedule`):** Xem lịch theo Ngày/Tuần/Tháng, phân biệt màu lịch học và lịch thi, có nút "Xuất lịch iCal (.ics)".
- **Thông báo (`/announcements`):** Lọc theo trạng thái Chưa đọc/Tất cả, tự động gọi API đánh dấu đã đọc khi sinh viên mở xem chi tiết.
- **Tìm phòng trống (`/rooms`):** Thanh bộ lọc theo Ngày, Giờ bắt đầu, Giờ kết thúc, Tòa nhà, Sức chứa tối thiểu, Thiết bị; hiển thị kết quả trực quan theo từng tòa nhà/tầng.
- **Danh bạ dịch vụ (`/services`):** Ô tìm kiếm thủ tục hành chính, hiển thị quy trình thực hiện, giờ mở cửa, thông tin liên hệ và link tải biểu mẫu.

### 6.2 Cổng Cán bộ & Quản trị viên (`/app/admin/...`)
- **Quản trị thông báo (`/admin/announcements`):** Trình soạn thảo văn bản, bộ chọn đối tượng nhận (Toàn trường, Khoa/Viện, Khóa, Ngành), các nút thao tác theo đúng luồng duyệt (Gửi duyệt, Phê duyệt & Đăng, Hẹn giờ đăng, Thu hồi).
- **Quản lý kho quy chế (`/admin/documents`):** Tải lên PDF/DOCX, bảng quản lý các phiên bản (Nháp, Còn hiệu lực, Hết hiệu lực), nút "Xác nhận hiệu lực & Lập chỉ mục AI" kèm trạng thái xử lý thời gian thực.
- **Phân tích câu hỏi (`/admin/analytics`):** Biểu đồ số lượng câu hỏi và tỷ lệ hài lòng theo thời gian, bảng Top chủ đề sinh viên hỏi nhiều nhất, và bảng Các cụm câu hỏi AI chưa trả lời được (Khoảng trống tri thức) để cán bộ kịp thời bổ sung văn bản.
- **Người dùng & Nhật ký kiểm toán (`/admin/users`, `/admin/audit-logs`):** Quản lý phân quyền người dùng và tra cứu lịch sử thao tác hệ thống.

