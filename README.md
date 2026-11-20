# CampusMate-AI: Hệ thống Trợ lý Học vụ AI Đa nền tảng & Kiosk Thông minh tại Sảnh Sinh viên (HUCE Smart AI Kiosk)

[![Repository](https://img.shields.io/badge/GitHub-dongdx2k5%2FCampusMate--AI-blue?logo=github)](https://github.com/dongdx2k5/CampusMate-AI)
[![Python](https://img.shields.io/badge/Python-3.10%2B-brightgreen?logo=python)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-2.2.0-teal?logo=fastapi)](https://fastapi.tiangolo.com)
[![OpenCV](https://img.shields.io/badge/OpenCV-Haar%20Cascade%20%2B%20ORB-orange?logo=opencv)](https://opencv.org)
[![Tests](https://img.shields.io/badge/Tests-17%20Passed%20(100%25)-success)](tests/test_all_features.py)

- **Trường:** Trường Đại học Xây dựng Hà Nội (HUCE) – Khoa Công nghệ Thông tin
- **Sinh viên nghiên cứu & phát triển:**
  - **Đặng Xuân Đồng** – MSSV: `0206968` (Lớp 68CS1 - Khoa học Máy tính) – GitHub: [@dongdx2k5](https://github.com/dongdx2k5)
  - **Nguyễn Đức Thiện** – MSSV: `0213368` (Lớp 66IT1 - Công nghệ Thông tin)

---

## 1. Kiến trúc Tổng thể & Tính năng Cốt lõi

Hệ thống được thiết kế theo mô hình **Thin-Client Edge Kiosk kết hợp Agentic RAG Server**:
1. **Giao diện Kiosk Màn hình Cảm ứng Sảnh Sinh viên (Thin-Client Edge)**:
   - Giao diện cảm ứng toàn màn hình (`frontend-kiosk/index.html` & `app.js`), tối ưu hoạt động mượt mà trên phần cứng phổ thông / Mini PC / Raspberry Pi (RAM 2GB–4GB, không yêu cầu GPU rời).
   - Tự động khóa và xóa phiên làm việc sau **30 giây không hoạt động** để bảo vệ dữ liệu cá nhân tại nơi công cộng.
   - Hỗ trợ nhập liệu giọng nói tiếng Việt qua Web Speech API và các phím tắt chạm nhanh (Touch Shortcuts).

2. **Xác thực Sinh trắc học 2FA & Quét Thẻ Sinh viên HUCE (Physical Card + Facial Biometrics)**:
   - **Mặt trước thẻ**: Nhận diện chân dung ảnh thẻ, so khớp ORB Keypoints với phôi chuẩn và trích xuất vector khuôn mặt.
   - **Mặt sau thẻ**: Quét mã vạch 1D Barcode (Code-128 / Code-39) bằng thư viện ZXing Browser kết hợp thuật toán phân tích hình thái Sobel/Scharr gradient phía máy chủ.
   - **Webcam trực tiếp**: Thuật toán Haar Cascade (`frontalface_default` + `eye`), phân tích liveness chống giả mạo (`Liveness Score >= 0.75`), trích xuất vector đặc trưng 128 chiều (CLAHE + Gradient).
   - **Đối sánh Cosine**: Ngưỡng chấp nhận nghiêm ngặt `Cosine Similarity >= 0.72`, tuyệt đối **không tự động ghi đè mẫu khuôn mặt khi thất bại**.
   - **Mã PIN dự phòng**: Hỗ trợ đăng nhập bằng mã PIN 6 số được băm an toàn theo chuẩn PBKDF2.

3. **Agentic RAG & Điều hướng Tri thức Học vụ (Zero Hallucination)**:
   - Tìm kiếm kết hợp Hybrid Search: Thuật toán BM25 tiếng Việt + Semantic Cosine TF-IDF, hợp nhất xếp hạng bằng Reciprocal Rank Fusion (RRF với hằng số `k=60`).
   - Tự động phân loại ý định (Intent Routing): Điều hướng linh hoạt giữa tri thức quy chế chung (cho phép khách vãng lai) và dữ liệu cá nhân hóa (yêu cầu đăng nhập 2FA).
   - Tự động đối chiếu học bổng KKHT theo Quyết định `1158/QĐ-ĐHXD`.
   - Lộ trình học tập DAG (Directed Acyclic Graph): Kiểm tra ràng buộc môn tiên quyết và đề xuất môn đăng ký học kỳ mới.
   - Tra cứu Thời khóa biểu và Lịch thi kèm Số báo danh (SBD) theo thời gian thực.

---

## 2. Cấu trúc Thư mục & Mô tả Chi tiết Từng Module Mã Nguồn

```text
CampusMate-AI/
├── backend/
│   ├── app/
│   │   ├── assets_cards/               # Dữ liệu ảnh phôi thẻ sinh viên mẫu (mặt trước & mặt sau barcode)
│   │   │   ├── card_0206968_front.jpg  # Ảnh mặt trước Thẻ SV Đặng Xuân Đồng (phục vụ đối sánh ORB và ảnh thẻ)
│   │   │   └── card_0206968_back.jpg   # Ảnh mặt sau Thẻ SV (chứa dải mã vạch Barcode 1D Code-128)
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── agentic_rag.py          # Động cơ RAG lai (BM25 + TF-IDF Cosine + RRF k=60) & Intent Detection
│   │   │   ├── biometric_auth.py       # Computer Vision: Haar Cascade, Eyes, Liveness, Cosine 128-d, Card Scanner
│   │   │   ├── dag_recommender.py      # Thuật toán duyệt đồ thị DAG môn tiên quyết & Đánh giá học bổng KKHT
│   │   │   └── security.py             # JWT HS256, In-Memory JTI Revocation, PBKDF2 PIN Hashing, Anti-IDOR, RBAC
│   │   ├── database.py                 # SQLite Schema, Context Manager an toàn, Seed data 4 tài khoản mẫu
│   │   ├── main.py                     # FastAPI REST API Server, Router, Middleware CORS & Anti-IDOR
│   │   └── __init__.py
├── edge-client/
│   └── kiosk_launcher.sh               # Shell script tự khởi động trình duyệt chế độ Kiosk Fullscreen trên Linux
├── frontend-kiosk/
│   ├── app.js                          # Logic Kiosk: WebRTC Camera, ZXing Barcode, Auto-scan, Chat UI, Voice API
│   └── index.html                      # Giao diện cảm ứng chuẩn Touch Kiosk, bố cục chia 2 cột HD sắc nét
├── tests/
│   └── test_all_features.py            # Toàn bộ 17 ca kiểm thử tự động (Functional + Security Hardening)
├── .gitignore                          # Quy tắc bỏ qua tệp nhị phân, cache, môi trường ảo và file tạm
├── Dockerfile                          # Cấu hình đóng gói container chạy FastAPI Uvicorn
├── docker-compose.yml                  # Cấu hình triển khai hạ tầng với volume dữ liệu độc lập /app/data
├── requirements.txt                    # Danh sách các thư viện Python phụ thuộc
├── run_local.bat                       # Script khởi chạy nhanh máy chủ trên Windows
├── run_local.sh                        # Script khởi chạy nhanh máy chủ trên Linux/macOS
└── README.md                           # Tài liệu hướng dẫn sử dụng và báo cáo kỹ thuật dự án
```

### Chi tiết vai trò các file nghiệp vụ:
- **`backend/app/main.py`**: Điểm khởi đầu của ứng dụng Backend. Định nghĩa toàn bộ REST API endpoints (`/api/v1/auth/*`, `/api/v1/chat/*`, `/api/v1/academic/*`, `/api/v1/admin/*`), thiết lập CORS policy, phân quyền RBAC và tích hợp dependency injection cho xác thực phiên.
- **`backend/app/services/security.py`**: Trụ cột an ninh của hệ thống. Quản lý việc cấp phát và kiểm tra JWT HS256, duy trì danh sách đen JTI thu hồi khi sinh viên logout, băm mật khẩu mã PIN thẻ bằng PBKDF2 với muối ngẫu nhiên (salt 16 bytes), và kiểm tra quyền sở hữu bản ghi (Anti-IDOR).
- **`backend/app/services/biometric_auth.py`**: Module thị giác máy tính xử lý khung hình camera và thẻ sinh viên. Tích hợp bộ phát hiện khuôn mặt và mắt Haar Cascade, tính toán chỉ số nét Laplacian và độ sáng để đo Liveness, trích xuất đặc trưng 128 chiều bằng CLAHE + Gradient, so khớp Cosine với ngưỡng nghiêm ngặt `0.72` (tuyệt đối không tự động ghi đè vector khi thất bại).
- **`backend/app/services/agentic_rag.py`**: Module trả lời câu hỏi quy chế học vụ tự động không ảo giác (zero hallucination). Sử dụng giải thuật tìm kiếm kết hợp Hybrid Search (BM25 tiếng Việt + Semantic TF-IDF Vector) và thuật toán hợp nhất Reciprocal Rank Fusion (RRF, `k=60`) để trích xuất chính xác Điều/Khoản quy chế HUCE.
- **`backend/app/services/dag_recommender.py`**: Module thuật toán đồ thị và học bổng. Duyệt cấu trúc cây điều kiện tiên quyết (DAG) để cảnh báo môn rớt (điểm F) và gợi ý lộ trình học tập tối ưu từ 14 đến 24 tín chỉ; tự động đối chiếu GPA, điểm rèn luyện và số tín chỉ để xếp loại học bổng Khuyến khích học tập theo Quyết định 1158/QĐ-ĐHXD.
- **`backend/app/database.py`**: Quản trị cơ sở dữ liệu SQLite cục bộ. Sử dụng context manager `db_connection()` kích hoạt `PRAGMA foreign_keys = ON`, tự động tạo thư mục DB nếu chưa tồn tại, tự động nạp sẵn dữ liệu 4 tài khoản thử nghiệm, lịch học, lịch thi và kho tài liệu quy chế.
- **`frontend-kiosk/app.js`**: Điều khiển toàn bộ logic giao diện Kiosk tại sảnh. Quản lý luồng video WebRTC, vẽ khung Bounding Box chuẩn xác, tích hợp thư viện ZXing giải mã Barcode 1D, quản lý thời gian đếm ngược tự động đăng xuất 30 giây bảo vệ quyền riêng tư, và gọi API nhận dạng giọng nói tiếng Việt.

---

## 3. Cơ chế An toàn & Bảo mật Chuyên sâu (Security Hardening)

- **Vá triệt để Bypass 2FA**: Loại bỏ hoàn toàn nhánh fallback tự sinh vector và nhánh tự động ghi đè vector khi so khớp trượt. Chế độ mô phỏng (`simulated_face_identity`) chỉ được kích hoạt khi biến môi trường `HUCE_ALLOW_SIMULATION=true`.
- **Mã hóa Mật khẩu PIN Thẻ bằng PBKDF2**: Sử dụng thuật toán PBKDF2-HMAC-SHA256 với muối ngẫu nhiên (salt) 16 bytes và 100.000 vòng lặp, thay thế hoàn toàn lưu trữ plain-text.
- **Quản lý Phiên bằng JWT HS256 & Thu hồi Token khi Đăng xuất (JTI Revocation)**: Khi sinh viên kết thúc phiên hoặc hết thời gian chờ, JWT ID (`jti`) được lưu vào danh sách đen thu hồi (revocation store) với cơ chế tự dọn dẹp theo thời hạn hết hạn (`exp`). Gọi `/logout` thiếu token sẽ trả mã lỗi `401 Unauthorized`.
- **Chống Lỗ hổng Truy cập Trái phép IDOR (Anti-IDOR)**: Toàn bộ API học vụ cá nhân (`/academic/profile`, `/scholarship`, `/roadmap`, `/schedules`) áp dụng hàm kiểm soát quyền `assert_student_owner_or_admin(student_code, user)`. Sinh viên chỉ được truy cập dữ liệu của chính mình; quản trị viên (`ADMIN`) có quyền tra cứu toàn hệ thống.
- **Phân quyền Khách vãng lai vs Sinh viên đã Xác thực (RBAC)**: Khách vãng lai chỉ được hỏi quy chế đào tạo chung; các câu hỏi liên quan đến dữ liệu cá nhân bắt buộc phải đăng nhập 2FA.
- **Quản trị viên Quản lý Tài liệu Quy chế**: Endpoint `POST /api/v1/admin/documents` yêu cầu xác thực JWT quyền `ADMIN` và cấp phát khóa chính UUID v4 chuẩn.
- **Bảo toàn Dữ liệu Docker**: Volume lưu trữ cơ sở dữ liệu được tách biệt vào thư mục `/app/data`, ngăn chặn tình trạng mount volume đè lên mã nguồn ứng dụng.

---

## 4. Danh mục Tài khoản Mẫu để Kiểm thử

| Họ và tên | MSSV / Mã định danh | Mã Thẻ RFID | Mã vạch Barcode | Mã PIN | Vai trò | Đặc điểm Hồ sơ & Kịch bản Kiểm thử |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Đặng Xuân Đồng** | `0206968` | `RFID-HUCE-0206968` | `BARCODE-0206968` | `310305` | `STUDENT` | Lớp 68CS1. Vector khuôn mặt trích xuất từ ảnh thẻ thật. Kỳ 2025-2 tích lũy 15 tín chỉ toàn điểm A/B+, GPA kỳ `3.75`, ĐRL `93` ➔ **Đủ điều kiện Học bổng KKHT Xuất sắc (15.600.000đ)**. |
| **Nguyễn Đức Thiện** | `0213368` | `RFID-HUCE-0213368` | `BARCODE-0213368` | `123456` | `STUDENT` | Lớp 66IT1. Kỳ 2025-2 tích lũy 15 tín chỉ toàn điểm A/B, GPA kỳ `3.65`, ĐRL `92` ➔ **Đủ điều kiện Học bổng KKHT Xuất sắc (15.600.000đ)**. |
| **Trần Minh Ánh** | `0214502` | `RFID-HUCE-0214502` | `BARCODE-0214502` | `654321` | `STUDENT` | Lớp 66IT2. Có 1 môn bị điểm F (`IT3080`) ➔ **Bị loại khỏi danh sách học bổng; Đồ thị DAG cảnh báo học lại môn tiên quyết**. |
| **TS. Lê Hoàng Nam** | `ADMIN01` | `RFID-HUCE-ADMIN01` | `BARCODE-ADMIN01` | `999888` | `ADMIN` | Quản trị viên Phòng Đào tạo ➔ Toàn quyền nạp chunk tài liệu quy chế mới và xem thông tin học vụ của mọi sinh viên. |

---

## 5. Danh sách Biến Môi trường Cấu hình

| Tên biến môi trường | Giá trị mặc định | Giải thích chi tiết |
| :--- | :--- | :--- |
| `HUCE_DB_PATH` | `huce_academic_kiosk.db` (hoặc `/app/data/huce_academic_kiosk.db` trong Docker) | Đường dẫn tuyệt đối hoặc tương đối tới tệp SQLite Database. Hệ thống tự động khởi tạo thư mục cha nếu chưa tồn tại. |
| `HUCE_JWT_SECRET` | Khóa bí mật ngẫu nhiên (>= 32 bytes) | Khóa ký JWT theo thuật toán HS256, độ dài tối thiểu 256 bits (32 bytes) để triệt tiêu `InsecureKeyLengthWarning`. |
| `HUCE_ALLOWED_ORIGINS` | `http://localhost:8000,http://127.0.0.1:8000` | Danh sách tên miền được phép gọi API (CORS whitelist). |
| `HUCE_ADMIN_PIN` | `999888` | Mã PIN khởi tạo mặc định cho tài khoản Quản trị viên `ADMIN01`. |
| `HUCE_ALLOW_SIMULATION` | `false` | Cờ an toàn kiểm soát tính năng mô phỏng khuôn mặt (`simulated_face_identity`). Khi tắt (`false`), API sẽ từ chối mọi yêu cầu đăng nhập giả lập. |

---

## 6. Hướng dẫn Cài đặt & Khởi chạy

### Bước 1: Cài đặt phụ thuộc Python
```bash
pip install -r requirements.txt
```

### Bước 2: Chạy bộ kiểm thử tự động (17 Test Suites)
```bash
pytest tests/test_all_features.py -v
```

### Bước 3: Khởi chạy Máy chủ Backend & Giao diện Kiosk
```bash
uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload
```
- Truy cập Giao diện Kiosk: `http://localhost:8000`
- Truy cập Tài liệu API (Swagger UI): `http://localhost:8000/docs`

### Bước 4: Triển khai qua Docker Compose (Tùy chọn)
```bash
docker-compose up --build -d
```

---

## 7. Danh mục 17 Kịch bản Kiểm thử Tự động (100% Passed)

| STT | Tên ca kiểm thử (`test_all_features.py`) | Mục đích & Nghiệp vụ kiểm tra |
| :---: | :--- | :--- |
| 1 | `test_01_health_check` | Kiểm tra tình trạng hoạt động của hệ thống và thông số Thin-Client Kiosk. |
| 2 | `test_02_face_detection_real_frame` | Nhận diện khuôn mặt, phát hiện vị trí mắt và chỉ số Liveness qua OpenCV. |
| 3 | `test_03_student_card_scanner_orb_front_and_barcode_back` | Quét mặt trước (ảnh thẻ, ORB) và mặt sau (mã vạch 1D Barcode) của thẻ sinh viên. |
| 4 | `test_04_facial_biometrics_verification_cosine` | Đối sánh độ tương đồng Cosine vector khuôn mặt 128 chiều với mẫu trong thẻ. |
| 5 | `test_05_agentic_rag_official_regulations_hybrid_search` | Truy vấn Hybrid RAG (BM25 + Semantic + RRF) về quy chế đào tạo tín chỉ HUCE. |
| 6 | `test_06_scholarship_auto_evaluation_rule_1158` | Đánh giá điều kiện cấp học bổng KKHT (Xuất sắc / Giỏi / Khá / Không đạt). |
| 7 | `test_07_class_schedule_and_room_lookup` | Tra cứu thời khóa biểu tuần, ca học, giảng đường (H1, H2, H3) và giảng viên. |
| 8 | `test_08_exam_schedule_and_seat_number` | Tra cứu lịch thi, phòng thi, số báo danh và quy chế mang thẻ dự thi. |
| 9 | `test_09_dag_course_prerequisite_and_roadmap` | Duyệt đồ thị DAG kiểm tra môn tiên quyết và gợi ý lộ trình học tập tối ưu. |
| 10 | `test_10_local_usb_camera_fallback` | Kiểm tra cơ chế chụp ảnh từ USB Camera vật lý máy chủ qua `VideoCapture(0)`. |
| 11 | `test_11_security_prevent_biometric_bypass_and_face_overwrite` | Ngăn chặn bypass 2FA: từ chối mặt không khớp, cấm tự ghi đè vector, cấm mô phỏng khi tắt cờ. |
| 12 | `test_12_security_pin_fallback_pbkdf2_hashing` | Xác thực đăng nhập bằng mã PIN dự phòng được băm an toàn theo chuẩn PBKDF2. |
| 13 | `test_13_security_anti_idor_student_profile_access` | Kiểm tra cơ chế chống IDOR: sinh viên không thể xem chéo dữ liệu của sinh viên khác (403). |
| 14 | `test_14_security_chat_guest_vs_authenticated_rules` | Phân quyền RBAC trong Chat: khách chỉ được hỏi quy chế chung; hỏi dữ liệu cá nhân bị chặn (401). |
| 15 | `test_15_security_token_revocation_on_logout` | Thu hồi JWT ID (`jti`) khi đăng xuất và từ chối yêu cầu logout không có token (401). |
| 16 | `test_16_security_admin_document_chunk_ingestion` | Kiểm soát quyền ADMIN khi nạp thêm chunk tài liệu quy chế mới vào Knowledge Base. |
| 17 | `test_17_security_barcode_strict_validation` | Xác thực mã vạch 1D nghiêm ngặt: từ chối mã không tồn tại thay vì nhận diện sai. |
