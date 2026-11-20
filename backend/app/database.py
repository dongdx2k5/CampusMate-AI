"""
Database Management & Seed Data for HUCE Smart AI Kiosk & Academic Assistant.
Includes:
- Đặng Xuân Đồng (MSSV: 0206968, Lớp: 68CS1, Khoa CNTT, Khóa 2023-2027, Email: dong0206968@huce.edu.vn)
  with real 128-d OpenCV facial embedding extracted directly from his HUCE Student ID Card photo!
- Nguyễn Đức Thiện (MSSV: 0213368, Lớp: 66IT1, Khoa CNTT)
- Trần Minh Ánh (MSSV: 0214502, Lớp: 66IT2, Khoa CNTT)
"""

from contextlib import contextmanager
import json
import math
import os
import sqlite3
from typing import Any, Dict, Generator, List, Optional

from .services.security import hash_pin

DB_PATH = os.environ.get(
    "HUCE_DB_PATH",
    os.path.join(os.path.dirname(os.path.dirname(__file__)), "huce_academic_kiosk.db"),
)

# Real 128-d OpenCV facial vector extracted from Đặng Xuân Đồng's Student ID card photo (0206968)
DANG_XUAN_DONG_CARD_FACE_VEC = [
    -0.067368, -0.08155, -0.09857, -0.067368, 0.013474, -0.061695, -0.102824, -0.044675,
    0.059567, -0.064531, -0.09857, -0.092897, -0.071622, -0.056731, 0.059567, 0.076586,
    0.046803, -0.036166, -0.058149, -0.041839, -0.052476, -0.031911, 0.031202, 0.051058,
    0.029784, 0.019147, 0.014892, 0.023401, 0.023401, 0.02482, 0.019147, 0.029784,
    0.048221, 0.014892, 0.004964, 0.014892, 0.012055, 0.002127, 0.013474, 0.045385,
    0.063822, 0.038293, 0.006382, -0.006382, -0.009219, 0.007801, 0.036875, 0.06524,
    0.079423, 0.066659, 0.017728, 0.009219, 0.009219, 0.01631, 0.066659, 0.079423,
    0.091478, 0.084387, 0.063822, 0.019147, 0.017728, 0.059567, 0.084387, 0.09006,
    0.056603, 0.148954, 0.059582, 0.06554, 0.074477, 0.068519, 0.160871, 0.050644,
    0.119163, 0.166829, 0.095331, 0.077456, 0.077456, 0.107247, 0.160871, 0.107247,
    0.09831, 0.13108, 0.175766, 0.128101, 0.13108, 0.181724, 0.125122, 0.089373,
    0.047665, 0.110226, 0.113205, 0.142996, 0.140017, 0.116184, 0.113205, 0.047665,
    0.038728, 0.09831, 0.125122, 0.122143, 0.125122, 0.122143, 0.095331, 0.035749,
    0.023833, 0.086394, 0.137038, 0.166829, 0.160871, 0.134059, 0.080435, 0.020854,
    0.014895, 0.053624, 0.145975, 0.104268, 0.104268, 0.145975, 0.053624, 0.011916,
    0.014895, 0.029791, 0.128101, 0.160871, 0.160871, 0.128101, 0.029791, 0.011916
]


def get_connection() -> sqlite3.Connection:
    db_dir = os.path.dirname(DB_PATH)
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


@contextmanager
def db_connection() -> Generator[sqlite3.Connection, None, None]:
    db_dir = os.path.dirname(DB_PATH)
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
    finally:
        conn.close()


def generate_deterministic_face_vector(seed_str: str, dim: int = 128) -> List[float]:
    if "0206968" in seed_str or "DONG" in seed_str.upper():
        norm = math.sqrt(sum(x * x for x in DANG_XUAN_DONG_CARD_FACE_VEC)) or 1.0
        return [round(x / norm, 6) for x in DANG_XUAN_DONG_CARD_FACE_VEC]
    vec = []
    for i in range(dim):
        val = math.sin(sum(ord(c) * (i + 1) for c in seed_str) * 0.017 + i * 0.31)
        vec.append(round(val, 6))
    norm = math.sqrt(sum(x * x for x in vec)) or 1.0
    return [round(x / norm, 6) for x in vec]


def init_db() -> None:
    with db_connection() as conn:
        _init_db_with_conn(conn)


def _init_db_with_conn(conn: sqlite3.Connection) -> None:
    cur = conn.cursor()

    cur.executescript(
        """
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            student_code TEXT UNIQUE NOT NULL,
            full_name TEXT NOT NULL,
            dob TEXT,
            email TEXT,
            class_name TEXT NOT NULL,
            major_name TEXT NOT NULL,
            cohort_year INTEGER NOT NULL,
            course_period TEXT,
            gpa_semester REAL NOT NULL,
            gpa_cumulative REAL NOT NULL,
            training_score INTEGER NOT NULL,
            credits_accumulated INTEGER NOT NULL,
            role TEXT NOT NULL DEFAULT 'STUDENT'
        );

        CREATE TABLE IF NOT EXISTS student_cards_biometrics (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL UNIQUE,
            card_uid TEXT UNIQUE NOT NULL,
            barcode_data TEXT UNIQUE NOT NULL,
            face_embedding_json TEXT NOT NULL,
            pin_code TEXT NOT NULL,
            card_status TEXT NOT NULL DEFAULT 'ACTIVE',
            last_kiosk_login TEXT,
            FOREIGN KEY (user_id) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS courses (
            id TEXT PRIMARY KEY,
            course_code TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            credits INTEGER NOT NULL,
            recommended_semester INTEGER NOT NULL,
            is_mandatory INTEGER NOT NULL DEFAULT 1,
            career_track TEXT NOT NULL DEFAULT 'CORE'
        );

        CREATE TABLE IF NOT EXISTS course_prerequisites (
            course_id TEXT NOT NULL,
            prerequisite_id TEXT NOT NULL,
            relation_type TEXT NOT NULL DEFAULT 'PREREQUISITE',
            PRIMARY KEY (course_id, prerequisite_id),
            FOREIGN KEY (course_id) REFERENCES courses(id),
            FOREIGN KEY (prerequisite_id) REFERENCES courses(id)
        );

        CREATE TABLE IF NOT EXISTS student_progress (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            course_id TEXT NOT NULL,
            semester_taken TEXT NOT NULL,
            grade_10 REAL NOT NULL,
            grade_4 REAL NOT NULL,
            letter_grade TEXT NOT NULL,
            status TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (course_id) REFERENCES courses(id)
        );

        CREATE TABLE IF NOT EXISTS class_schedules (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            course_id TEXT NOT NULL,
            semester TEXT NOT NULL,
            day_of_week TEXT NOT NULL,
            day_index INTEGER NOT NULL,
            periods TEXT NOT NULL,
            time_range TEXT NOT NULL,
            room TEXT NOT NULL,
            building TEXT NOT NULL,
            lecturer TEXT NOT NULL,
            class_group TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (course_id) REFERENCES courses(id)
        );

        CREATE TABLE IF NOT EXISTS exam_schedules (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            course_id TEXT NOT NULL,
            semester TEXT NOT NULL,
            exam_date TEXT NOT NULL,
            exam_time TEXT NOT NULL,
            exam_room TEXT NOT NULL,
            seat_number TEXT NOT NULL,
            exam_format TEXT NOT NULL,
            notes TEXT,
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (course_id) REFERENCES courses(id)
        );

        CREATE TABLE IF NOT EXISTS scholarships_criteria (
            id TEXT PRIMARY KEY,
            scholarship_code TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            level_rank TEXT NOT NULL,
            min_gpa REAL NOT NULL,
            min_training_score INTEGER NOT NULL,
            min_credits_semester INTEGER NOT NULL,
            allow_failed_course INTEGER NOT NULL DEFAULT 0,
            reward_amount_vnd INTEGER NOT NULL,
            description TEXT NOT NULL,
            regulation_ref TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS document_chunks (
            id TEXT PRIMARY KEY,
            doc_title TEXT NOT NULL,
            doc_number TEXT NOT NULL,
            article_ref TEXT NOT NULL,
            category TEXT NOT NULL,
            keywords TEXT NOT NULL,
            content TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS chat_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT,
            kiosk_id TEXT,
            question_text TEXT NOT NULL,
            intent_detected TEXT NOT NULL,
            answer_text TEXT NOT NULL,
            citations_json TEXT NOT NULL,
            response_time_ms INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
    )

    cur.execute("SELECT COUNT(*) as cnt FROM users WHERE student_code = '0206968'")
    if cur.fetchone()["cnt"] > 0:
        return

    # Clear old seed tables if upgrading schema
    for tbl in [
        "chat_logs", "document_chunks", "scholarships_criteria", "exam_schedules",
        "class_schedules", "student_progress", "course_prerequisites", "courses",
        "student_cards_biometrics", "users"
    ]:
        cur.execute(f"DELETE FROM {tbl}")

    # 1. Seed Users (Including Đặng Xuân Đồng - 0206968 from the real student ID card & Nguyễn Đức Thiện - 0213368)
    users_data = [
        (
            "USR_DONG",
            "0206968",
            "Đặng Xuân Đồng",
            "31/03/2005",
            "dong0206968@huce.edu.vn",
            "68CS1",
            "Khoa học Máy tính – Khoa Công nghệ thông tin (HUCE)",
            68,
            "2023-2027",
            3.68,
            3.54,
            93,
            98,
            "STUDENT",
        ),
        (
            "USR_01",
            "0213368",
            "Nguyễn Đức Thiện",
            "15/08/2003",
            "thien0213368@huce.edu.vn",
            "66IT1",
            "Công nghệ thông tin (Khoa CNTT - HUCE)",
            66,
            "2021-2026",
            3.65,
            3.48,
            92,
            96,
            "STUDENT",
        ),
        (
            "USR_02",
            "0214502",
            "Trần Minh Ánh",
            "20/11/2003",
            "anh0214502@huce.edu.vn",
            "66IT2",
            "Khoa học dữ liệu & AI (Khoa CNTT - HUCE)",
            66,
            "2021-2026",
            3.15,
            3.05,
            78,
            92,
            "STUDENT",
        ),
        (
            "USR_ADMIN",
            "ADMIN01",
            "TS. Lê Hoàng Nam (Quản trị Học vụ)",
            "01/01/1980",
            "daotao@huce.edu.vn",
            "PHONG_DAOTAO",
            "Phòng Quản lý Đào tạo - HUCE",
            0,
            "N/A",
            4.0,
            4.0,
            100,
            0,
            "ADMIN",
        ),
    ]
    cur.executemany(
        "INSERT INTO users VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", users_data
    )

    # 2. Seed Biometrics & Student Cards
    admin_pin = os.environ.get("HUCE_ADMIN_PIN", "999888")
    cards_data = [
        (
            "CARD_DONG",
            "USR_DONG",
            "RFID-HUCE-0206968",
            "BARCODE-0206968",
            json.dumps(generate_deterministic_face_vector("FACE_0206968_DONG")),
            hash_pin("310305"),
            "ACTIVE",
            "2026-11-07 22:35:00",
        ),
        (
            "CARD_01",
            "USR_01",
            "RFID-HUCE-0213368",
            "BARCODE-0213368",
            json.dumps(generate_deterministic_face_vector("FACE_0213368_THIEN")),
            hash_pin("123456"),
            "ACTIVE",
            "2026-11-07 08:15:00",
        ),
        (
            "CARD_02",
            "USR_02",
            "RFID-HUCE-0214502",
            "BARCODE-0214502",
            json.dumps(generate_deterministic_face_vector("FACE_0214502_ANH")),
            hash_pin("654321"),
            "ACTIVE",
            "2026-11-06 14:20:00",
        ),
        (
            "CARD_ADMIN",
            "USR_ADMIN",
            "RFID-HUCE-ADMIN01",
            "BARCODE-ADMIN01",
            json.dumps(generate_deterministic_face_vector("FACE_ADMIN01")),
            hash_pin(admin_pin),
            "ACTIVE",
            "2026-11-08 08:00:00",
        ),
    ]
    cur.executemany(
        "INSERT INTO student_cards_biometrics VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        cards_data,
    )

    # 3. Seed Courses (HUCE IT / CS Curriculum)
    courses_data = [
        ("CRS_01", "IT1010", "Nhập môn Lập trình", 3, 1, 1, "CORE"),
        ("CRS_02", "IT2010", "Cấu trúc dữ liệu và Giải thuật", 4, 3, 1, "CORE"),
        ("CRS_03", "IT2020", "Cơ sở dữ liệu", 3, 3, 1, "CORE"),
        ("CRS_04", "IT2030", "Lập trình Hướng đối tượng", 3, 3, 1, "CORE"),
        ("CRS_05", "IT3010", "Mạng máy tính", 3, 4, 1, "NETWORK"),
        ("CRS_06", "IT3020", "Hệ điều hành", 3, 4, 1, "CORE"),
        ("CRS_07", "IT3040", "Công nghệ phần mềm", 3, 5, 1, "SE"),
        ("CRS_08", "IT3080", "Trí tuệ nhân tạo (Artificial Intelligence)", 3, 5, 1, "AI"),
        ("CRS_09", "IT4010", "Học máy (Machine Learning)", 3, 6, 1, "AI"),
        ("CRS_10", "IT4025", "Phát triển Ứng dụng Web & Cloud", 3, 6, 1, "SE"),
        ("CRS_11", "IT4060", "Xử lý Ngôn ngữ Tự nhiên & LLM (NLP)", 3, 7, 0, "AI"),
        ("CRS_12", "IT4070", "Thị giác Máy tính & Sinh trắc học (Computer Vision)", 3, 7, 0, "AI"),
        ("CRS_13", "IT4080", "Kiến trúc Phần mềm & Microservices", 3, 7, 0, "SE"),
        ("CRS_14", "IT4090", "An toàn và Bảo mật Hệ thống Thông tin", 3, 7, 1, "NETWORK"),
        ("CRS_15", "IT4990", "Đồ án Tốt nghiệp Kỹ sư CNTT / KHMT", 6, 8, 1, "CORE"),
    ]
    cur.executemany("INSERT INTO courses VALUES (?, ?, ?, ?, ?, ?, ?)", courses_data)

    # 4. Seed Prerequisites (DAG edges)
    prereq_data = [
        ("CRS_02", "CRS_01", "PREREQUISITE"),
        ("CRS_04", "CRS_01", "PREREQUISITE"),
        ("CRS_07", "CRS_03", "PREREQUISITE"),
        ("CRS_07", "CRS_04", "PREREQUISITE"),
        ("CRS_08", "CRS_02", "PREREQUISITE"),
        ("CRS_09", "CRS_08", "PREREQUISITE"),
        ("CRS_10", "CRS_03", "PREREQUISITE"),
        ("CRS_10", "CRS_07", "PREREQUISITE"),
        ("CRS_11", "CRS_09", "PREREQUISITE"),
        ("CRS_12", "CRS_09", "PREREQUISITE"),
        ("CRS_13", "CRS_07", "PREREQUISITE"),
        ("CRS_14", "CRS_05", "PREREQUISITE"),
        ("CRS_15", "CRS_09", "PREREQUISITE"),
        ("CRS_15", "CRS_10", "PREREQUISITE"),
    ]
    cur.executemany("INSERT INTO course_prerequisites VALUES (?, ?, ?)", prereq_data)

    # 5. Seed Student Progress for Đặng Xuân Đồng (USR_DONG) & Nguyễn Đức Thiện (USR_01)
    progress_data = [
        # Đặng Xuân Đồng (0206968 - 68CS1)
        ("PRG_D01", "USR_DONG", "CRS_01", "2023-1", 9.0, 4.0, "A", "PASSED"),
        ("PRG_D02", "USR_DONG", "CRS_02", "2024-1", 8.7, 3.7, "A-", "PASSED"),
        ("PRG_D03", "USR_DONG", "CRS_03", "2024-1", 8.5, 4.0, "A", "PASSED"),
        ("PRG_D04", "USR_DONG", "CRS_04", "2025-2", 8.8, 4.0, "A", "PASSED"),
        ("PRG_D05", "USR_DONG", "CRS_05", "2025-2", 8.1, 3.5, "B+", "PASSED"),
        ("PRG_D06", "USR_DONG", "CRS_06", "2025-2", 8.4, 3.5, "B+", "PASSED"),
        ("PRG_D07", "USR_DONG", "CRS_07", "2025-2", 8.9, 4.0, "A", "PASSED"),
        ("PRG_D08", "USR_DONG", "CRS_08", "2025-2", 9.2, 4.0, "A", "PASSED"),
        ("PRG_D09", "USR_DONG", "CRS_09", "2025-2", 9.1, 4.0, "A", "PASSED"),
        # Nguyễn Đức Thiện (0213368 - 66IT1)
        ("PRG_01", "USR_01", "CRS_01", "2024-1", 8.8, 4.0, "A", "PASSED"),
        ("PRG_02", "USR_01", "CRS_02", "2024-2", 8.5, 3.7, "A-", "PASSED"),
        ("PRG_03", "USR_01", "CRS_03", "2024-2", 8.2, 3.5, "B+", "PASSED"),
        ("PRG_04", "USR_01", "CRS_04", "2025-2", 8.6, 3.7, "A-", "PASSED"),
        ("PRG_05", "USR_01", "CRS_05", "2025-2", 7.9, 3.0, "B", "PASSED"),
        ("PRG_06", "USR_01", "CRS_06", "2025-2", 8.4, 3.5, "B+", "PASSED"),
        ("PRG_07", "USR_01", "CRS_07", "2025-2", 8.7, 3.7, "A-", "PASSED"),
        ("PRG_08", "USR_01", "CRS_08", "2025-2", 9.1, 4.0, "A", "PASSED"),
        # Trần Minh Ánh (0214502 - has 1 failed course CRS_08)
        ("PRG_11", "USR_02", "CRS_01", "2024-1", 7.5, 3.0, "B", "PASSED"),
        ("PRG_12", "USR_02", "CRS_02", "2024-2", 7.2, 3.0, "B", "PASSED"),
        ("PRG_13", "USR_02", "CRS_03", "2024-2", 7.8, 3.2, "B", "PASSED"),
        ("PRG_14", "USR_02", "CRS_04", "2024-2", 7.0, 2.5, "C+", "PASSED"),
        ("PRG_15", "USR_02", "CRS_08", "2025-2", 3.5, 0.0, "F", "FAILED"),
    ]
    cur.executemany(
        "INSERT INTO student_progress VALUES (?, ?, ?, ?, ?, ?, ?, ?)", progress_data
    )

    # 6. Seed Class Schedules for Current Semester (2026-1) for both Đặng Xuân Đồng & Nguyễn Đức Thiện
    schedules_data = [
        # Đặng Xuân Đồng (0206968 - Lớp 68CS1)
        (
            "SCH_D01",
            "USR_DONG",
            "CRS_09",
            "2026-1",
            "Thứ Hai",
            2,
            "Tiết 1 - 3",
            "07:00 - 09:25",
            "H1-302",
            "Giảng đường H1",
            "PGS.TS. Nguyễn Văn Hiếu",
            "68CS1.01",
        ),
        (
            "SCH_D02",
            "USR_DONG",
            "CRS_10",
            "2026-1",
            "Thứ Tư",
            4,
            "Tiết 4 - 6",
            "09:35 - 12:00",
            "H2-405",
            "Giảng đường H2",
            "TS. Phạm Quốc Tuấn",
            "68CS1.02",
        ),
        (
            "SCH_D03",
            "USR_DONG",
            "CRS_07",
            "2026-1",
            "Thứ Năm",
            5,
            "Tiết 7 - 9",
            "13:00 - 15:25",
            "H1-204",
            "Giảng đường H1",
            "TS. Lê Hoàng Nam",
            "68CS1.01",
        ),
        (
            "SCH_D04",
            "USR_DONG",
            "CRS_08",
            "2026-1",
            "Thứ Sáu",
            6,
            "Tiết 1 - 3",
            "07:00 - 09:25",
            "PM-502 (Tầng 5 nhà H3)",
            "Tòa nhà Thí nghiệm H3",
            "TS. Đặng Minh Đức",
            "68CS1.TH",
        ),
        # Nguyễn Đức Thiện (0213368 - Lớp 66IT1)
        (
            "SCH_01",
            "USR_01",
            "CRS_09",
            "2026-1",
            "Thứ Hai",
            2,
            "Tiết 1 - 3",
            "07:00 - 09:25",
            "H1-302",
            "Giảng đường H1",
            "PGS.TS. Nguyễn Văn Hiếu",
            "66IT1.01",
        ),
        (
            "SCH_02",
            "USR_01",
            "CRS_10",
            "2026-1",
            "Thứ Tư",
            4,
            "Tiết 4 - 6",
            "09:35 - 12:00",
            "H2-405",
            "Giảng đường H2",
            "TS. Phạm Quốc Tuấn",
            "66IT1.02",
        ),
        (
            "SCH_03",
            "USR_01",
            "CRS_07",
            "2026-1",
            "Thứ Năm",
            5,
            "Tiết 7 - 9",
            "13:00 - 15:25",
            "H1-204",
            "Giảng đường H1",
            "TS. Lê Hoàng Nam",
            "66IT1.01",
        ),
        (
            "SCH_04",
            "USR_01",
            "CRS_08",
            "2026-1",
            "Thứ Sáu",
            6,
            "Tiết 1 - 3",
            "07:00 - 09:25",
            "PM-502 (Tầng 5 nhà H3)",
            "Tòa nhà Thí nghiệm H3",
            "TS. Đặng Minh Đức",
            "66IT1.TH",
        ),
    ]
    cur.executemany(
        "INSERT INTO class_schedules VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        schedules_data,
    )

    # 7. Seed Exam Schedules for Current Semester (2026-1)
    exams_data = [
        # Đặng Xuân Đồng (0206968 - 68CS1)
        (
            "EXM_D01",
            "USR_DONG",
            "CRS_09",
            "2026-1",
            "2026-12-14",
            "07:30 - 09:00 (Ca 1)",
            "H3-201",
            "SBD-12",
            "Trắc nghiệm trên máy + Tự luận",
            "Mang theo Thẻ sinh viên bản cứng (0206968) để quét xác thực tại phòng thi.",
        ),
        (
            "EXM_D02",
            "USR_DONG",
            "CRS_10",
            "2026-1",
            "2026-12-18",
            "09:30 - 11:00 (Ca 2)",
            "PM-401 (Nhà H3)",
            "SBD-09",
            "Thực hành + Vấn đáp Đồ án môn học",
            "Nộp mã nguồn lên hệ thống LMS trước ngày thi 24 giờ.",
        ),
        (
            "EXM_D03",
            "USR_DONG",
            "CRS_07",
            "2026-1",
            "2026-12-21",
            "13:30 - 15:00 (Ca 3)",
            "H1-105",
            "SBD-12",
            "Tự luận (90 phút, không sử dụng tài liệu)",
            "Có mặt trước giờ thi 15 phút.",
        ),
        (
            "EXM_D04",
            "USR_DONG",
            "CRS_08",
            "2026-1",
            "2026-12-24",
            "07:30 - 09:00 (Ca 1)",
            "H2-308",
            "SBD-12",
            "Tự luận kết hợp Bảo vệ bài tập lớn AI",
            "Mang theo Thẻ sinh viên.",
        ),
        # Nguyễn Đức Thiện (0213368 - 66IT1)
        (
            "EXM_01",
            "USR_01",
            "CRS_09",
            "2026-1",
            "2026-12-14",
            "07:30 - 09:00 (Ca 1)",
            "H3-201",
            "SBD-28",
            "Trắc nghiệm trên máy + Tự luận",
            "Mang theo Thẻ sinh viên bản cứng để quét xác thực tại phòng thi.",
        ),
        (
            "EXM_02",
            "USR_01",
            "CRS_10",
            "2026-1",
            "2026-12-18",
            "09:30 - 11:00 (Ca 2)",
            "PM-401 (Nhà H3)",
            "SBD-15",
            "Thực hành + Vấn đáp Đồ án môn học",
            "Nộp mã nguồn lên hệ thống LMS trước ngày thi 24 giờ.",
        ),
        (
            "EXM_03",
            "USR_01",
            "CRS_07",
            "2026-1",
            "2026-12-21",
            "13:30 - 15:00 (Ca 3)",
            "H1-105",
            "SBD-28",
            "Tự luận (90 phút, không sử dụng tài liệu)",
            "Có mặt trước giờ thi 15 phút.",
        ),
        (
            "EXM_04",
            "USR_01",
            "CRS_08",
            "2026-1",
            "2026-12-24",
            "07:30 - 09:00 (Ca 1)",
            "H2-308",
            "SBD-28",
            "Tự luận kết hợp Bảo vệ bài tập lớn AI",
            "Mang theo Thẻ sinh viên.",
        ),
    ]
    cur.executemany(
        "INSERT INTO exam_schedules VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", exams_data
    )

    # 8. Seed Scholarships Criteria (HUCE Official Rules)
    scholarships_data = [
        (
            "SCHOL_XS",
            "HB_KKHT_XUATSAC",
            "Học bổng Khuyến khích Học tập - Loại Xuất sắc",
            "XUAT_SAC",
            3.60,
            90,
            15,
            0,
            15600000,
            "Dành cho sinh viên có GPA học kỳ >= 3.60/4.0, Điểm rèn luyện >= 90/100, tích lũy tối thiểu 15 tín chỉ trong kỳ xét và không có học phần nào dưới điểm B (hoặc bị điểm F).",
            "Quyết định số 1158/QĐ-ĐHXD Điều 8, Khoản 3",
        ),
        (
            "SCHOL_GIOI",
            "HB_KKHT_GIOI",
            "Học bổng Khuyến khích Học tập - Loại Giỏi",
            "GIOI",
            3.20,
            80,
            15,
            0,
            13200000,
            "Dành cho sinh viên có GPA học kỳ >= 3.20/4.0, Điểm rèn luyện >= 80/100, tích lũy tối thiểu 15 tín chỉ trong kỳ xét và không có học phần nào bị điểm F.",
            "Quyết định số 1158/QĐ-ĐHXD Điều 8, Khoản 2",
        ),
        (
            "SCHOL_KHA",
            "HB_KKHT_KHA",
            "Học bổng Khuyến khích Học tập - Loại Khá",
            "KHA",
            2.50,
            70,
            15,
            0,
            11000000,
            "Dành cho sinh viên có GPA học kỳ >= 2.50/4.0, Điểm rèn luyện >= 70/100, tích lũy tối thiểu 15 tín chỉ trong kỳ xét và không có học phần nào bị điểm F.",
            "Quyết định số 1158/QĐ-ĐHXD Điều 8, Khoản 1",
        ),
    ]
    cur.executemany(
        "INSERT INTO scholarships_criteria VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        scholarships_data,
    )

    # 9. Seed Official HUCE Regulations Knowledge Base (Document Chunks)
    docs_data = [
        (
            "DOC_01",
            "Quy định Xét cấp Học bổng Khuyến khích Học tập ĐH Xây dựng Hà Nội",
            "1158/QĐ-ĐHXD",
            "Điều 8, Khoản 1, 2, 3 (Trang 5)",
            "HOC_BONG",
            "học bổng khuyến khích học tập điều kiện xét học bổng giỏi xuất sắc khá điểm rèn luyện tín chỉ gpa",
            "Điều kiện xét Học bổng Khuyến khích Học tập (KKHT) tại Trường Đại học Xây dựng Hà Nội: (1) Sinh viên phải đăng ký và hoàn thành tối thiểu 15 tín chỉ trong học kỳ xét học bổng (trừ học kỳ cuối khóa tối thiểu 10 tín chỉ); (2) Không có học phần nào bị điểm F hoặc điểm dưới quy định trong học kỳ đó; (3) Không bị kỷ luật từ mức khiển trách trở lên. Phân loại mức học bổng: Loại Khá yêu cầu GPA >= 2.50 và Điểm rèn luyện (ĐRL) >= 70 (mức 100% học phí chuẩn ~ 11.000.000đ/kỳ); Loại Giỏi yêu cầu GPA >= 3.20 và ĐRL >= 80 (mức 120% ~ 13.200.000đ/kỳ); Loại Xuất sắc yêu cầu GPA >= 3.60 và ĐRL >= 90 (mức 140% ~ 15.600.000đ/kỳ).",
        ),
        (
            "DOC_02",
            "Quy chế Đào tạo trình độ Đại học theo Hệ thống Tín chỉ HUCE",
            "892/QĐ-ĐHXD",
            "Điều 14, Khoản 2 (Trang 11)",
            "QUY_CHE_TIN_CHI",
            "số tín chỉ tối thiểu tối đa đăng ký học phần mỗi học kỳ lộ trình học tập",
            "Khối lượng học tập đăng ký trong mỗi học kỳ chính: Sinh viên học theo tiến độ chuẩn phải đăng ký tối thiểu 14 tín chỉ và tối đa 24 tín chỉ trong một học kỳ chính (trừ học kỳ cuối khóa). Đối với sinh viên đang trong diện cảnh báo học vụ, số tín chỉ đăng ký tối đa không quá 14 tín chỉ/học kỳ để tập trung cải thiện điểm trung bình tích lũy.",
        ),
        (
            "DOC_03",
            "Quy chế Đào tạo trình độ Đại học theo Hệ thống Tín chỉ HUCE",
            "892/QĐ-ĐHXD",
            "Điều 21, Khoản 1 & 2 (Trang 18)",
            "CANH_BAO_HOC_VU",
            "cảnh báo học vụ buộc thôi học điểm trung bình tích lũy gpa thấp nợ tín chỉ",
            "Cảnh báo kết quả học tập được thực hiện theo từng học kỳ chính. Sinh viên bị cảnh báo học vụ nếu rơi vào một trong các trường hợp: (a) Tổng số tín chỉ không đạt trong học kỳ vượt quá 50% khối lượng đã đăng ký, hoặc tổng số tín chỉ nợ đọng từ đầu khóa vượt quá 24 tín chỉ; (b) Điểm trung bình học kỳ đạt dưới 0.80 đối với học kỳ đầu của khóa học, dưới 1.00 đối với các học kỳ tiếp theo. Sinh viên bị cảnh báo học vụ 2 lần liên tiếp hoặc vượt quá thời gian tối đa được phép học sẽ nằm trong diện xét buộc thôi học.",
        ),
        (
            "DOC_04",
            "Quy định Công tác Khảo thí và Thi kết thúc Học phần HUCE",
            "612/QĐ-ĐHXD",
            "Điều 9, Khoản 1 & 4 (Trang 7)",
            "LICH_THI_KHAO_THI",
            "quy định phòng thi lịch thi thẻ sinh viên vắng thi hoãn thi số báo danh",
            "Khi dự thi kết thúc học phần, sinh viên bắt buộc phải có mặt tại phòng thi trước giờ phát đề 15 phút và xuất trình Thẻ sinh viên hợp lệ (hoặc Căn cước công dân có ảnh rõ nét) để cán bộ coi thi kiểm tra. Sinh viên đến chậm quá 15 phút sau khi đã bóc đề thi sẽ không được dự thi và nhận điểm 0 (F). Nếu sinh viên ốm đau đột xuất có giấy xác nhận của cơ sở y tế cấp Quận/Huyện trở lên hoặc bệnh viện, sinh viên được làm đơn xin hoãn thi gửi Phòng Quản lý Đào tạo trong vòng 05 ngày làm việc kể từ ngày thi.",
        ),
        (
            "DOC_05",
            "Quy chế Đào tạo trình độ Đại học theo Hệ thống Tín chỉ HUCE",
            "892/QĐ-ĐHXD",
            "Điều 19, Khoản 3 (Trang 16)",
            "THANG_DIEM",
            "quy đổi điểm hệ 10 sang hệ 4 điểm chữ A B C D F học lại cải thiện điểm",
            "Thang điểm đánh giá học phần được chấm theo thang điểm 10 (làm tròn đến một chữ số thập phân) và quy đổi sang điểm chữ cùng thang điểm 4 như sau: Điểm A (8.5 – 10.0) = 4.0; Điểm B+ (8.0 – 8.4) = 3.5; Điểm B (7.0 – 7.9) = 3.0; Điểm C+ (6.5 – 6.9) = 2.5; Điểm C (5.5 – 6.4) = 2.0; Điểm D+ (5.0 – 5.4) = 1.5; Điểm D (4.0 – 4.9) = 1.0; Điểm F (< 4.0) = 0.0 (Không đạt - bắt buộc phải học lại nếu là học phần bắt buộc). Sinh viên đạt điểm D hoặc D+ được phép đăng ký học cải thiện điểm để nâng GPA.",
        ),
        (
            "DOC_06",
            "Quy định Chuẩn đầu ra Ngoại ngữ và Tin học HUCE",
            "1024/QĐ-ĐHXD",
            "Điều 5, Khoản 2 (Trang 4)",
            "CHUAN_DAU_RA",
            "chuẩn đầu ra tiếng anh ngoại ngữ xét tốt nghiệp toeic ielts",
            "Điều kiện chuẩn đầu ra ngoại ngữ để xét công nhận tốt nghiệp đại học chính quy tại Trường Đại học Xây dựng Hà Nội đối với khối ngành Kỹ thuật và Công nghệ thông tin là đạt trình độ tương đương bậc 3/6 theo Khung năng lực ngoại ngữ 6 bậc dùng cho Việt Nam (tương đương TOEIC >= 450 điểm hoặc IELTS >= 4.5 hoặc hoàn thành các học phần Tiếng Anh tăng cường theo quy định của trường).",
        ),
        (
            "DOC_07",
            "Quy định Vận hành Kiosk Thông minh và Bảo mật Sinh trắc học Sinh viên",
            "305/QĐ-CNTT-ĐHXD",
            "Điều 4, Khoản 1 & 2 (Trang 3)",
            "KIOSK_BAO_MAT",
            "đăng nhập thẻ sinh viên xác thực khuôn mặt kiosk sảnh sinh viên bảo mật",
            "Tại các trạm Kiosk thông minh đặt ở sảnh giảng đường (H1, H2, H3 và Thư viện), sinh viên sử dụng Thẻ sinh viên (quét mặt trước/mặt sau có mã vạch Barcode qua Camera hoặc chạm thẻ RFID 13.56MHz) kết hợp xác thực khuôn mặt trực tiếp qua Camera để tra cứu thông tin cá nhân (lịch học, lịch thi, bảng điểm, xét học bổng). Phiên đăng nhập tại Kiosk tự động kết thúc và xóa bộ nhớ đệm sau 30 giây không có thao tác nhằm bảo vệ tuyệt đối dữ liệu cá nhân của sinh viên.",
        ),
    ]
    cur.executemany(
        "INSERT INTO document_chunks VALUES (?, ?, ?, ?, ?, ?, ?)", docs_data
    )

    conn.commit()
