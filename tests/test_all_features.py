"""
Automated End-to-End & Security Test Suite for HUCE Smart AI Kiosk & Academic Assistant.
Compatible with `python3 tests/test_all_features.py` and `pytest`.

Covers:
1. Low-spec Kiosk Health & Telemetry
2. 2FA Student Card + Genuine Face Verification (0206968 - Đặng Xuân Đồng)
3. Empty payload rejection (401)
4. Face enrollment PIN protection (403 invalid/missing PIN, 200 valid PIN)
5. Physical Student Card Scanner (Front/Back ORB & 1D Barcode decoding)
6. 2FA Impostor Face Rejection & No DB Overwrite (401)
7. 2FA Spoof Photo Attack Rejection (401)
8. 2FA Card + PIN Fallback (200, JWT token issued)
9. OpenCV Frame Processing & 128-d Feature Extraction
10. Agentic RAG: Scholarship Eligibility & Decision 1158/QĐ-ĐHXD
11. Agentic RAG: Weekly Class Schedule Lookup (0206968)
12. Agentic RAG: Semester Exam Schedule & Seat Number Lookup
13. DAG Course Roadmap Recommendation & Failed Core Course Retake
14. Admin Document Ingestion (403 for student, 201 for admin with UUID ID)
15. Anti-IDOR Protection (403 when accessing another student's academic data)
16. Guest vs Authenticated Chat Rules (200 for regulations, 401 for personal schedules)
17. Token Revocation on Logout (401 after logout)
"""

import base64
import json
import os
import sys
import tempfile
import unittest

# 1. Setup isolated temporary test database
_temp_fd, _temp_db_path = tempfile.mkstemp(suffix="_test_kiosk.db")
os.close(_temp_fd)

os.environ["HUCE_DB_PATH"] = _temp_db_path
os.environ["HUCE_ALLOW_SIMULATION"] = "true"
os.environ["HUCE_ADMIN_PIN"] = "999888"
os.environ["HUCE_JWT_SECRET"] = "huce_test_secret_key_2026_super_secure_32_bytes_long"
os.environ["HUCE_ALLOWED_ORIGINS"] = "http://localhost:8000,http://127.0.0.1:8000,http://testserver"

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    import cv2
    if not hasattr(cv2, "imencode"):
        cv2 = None
except Exception:
    cv2 = None
import numpy as np

from backend.app.database import db_connection, init_db
init_db()

from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.services.biometric_auth import extract_128d_cv_face_descriptor

client = TestClient(app)


def tearDownModule():
    if os.path.exists(_temp_db_path):
        try:
            os.remove(_temp_db_path)
        except Exception:
            pass


def create_sample_camera_frame_b64() -> str:
    if cv2 is not None:
        img = np.full((240, 320, 3), 210, dtype=np.uint8)
        cv2.circle(img, (160, 120), 65, (160, 160, 160), -1)
        cv2.circle(img, (135, 100), 10, (30, 30, 30), -1)
        cv2.circle(img, (185, 100), 10, (30, 30, 30), -1)
        cv2.ellipse(img, (160, 145), (25, 10), 0, 0, 180, (40, 40, 40), 3)
        ok, buf = cv2.imencode(".jpg", img, [int(cv2.IMWRITE_JPEG_QUALITY), 90])
        assert ok
        return "data:image/jpeg;base64," + base64.b64encode(buf.tobytes()).decode("utf-8")
    else:
        from PIL import Image, ImageDraw
        import io
        img = Image.new("RGB", (320, 240), color=(210, 210, 210))
        draw = ImageDraw.Draw(img)
        draw.ellipse([95, 55, 225, 185], fill=(160, 160, 160))
        draw.ellipse([125, 90, 145, 110], fill=(30, 30, 30))
        draw.ellipse([175, 90, 195, 110], fill=(30, 30, 30))
        draw.arc([135, 135, 185, 155], start=0, end=180, fill=(40, 40, 40), width=3)
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=90)
        return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode("utf-8")


def load_card_asset_b64(filename: str) -> str:
    path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "backend",
        "app",
        "assets_cards",
        filename,
    )
    with open(path, "rb") as f:
        return "data:image/jpeg;base64," + base64.b64encode(f.read()).decode("utf-8")


class TestHUCESmartKioskAI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Obtain tokens for tests
        r1 = client.post(
            "/api/v1/auth/kiosk-login",
            json={
                "card_identifier": "0206968",
                "simulated_face_identity": "FACE_0206968_DONG",
            },
        )
        cls.token_dong = r1.json().get("session_token") or r1.json().get("access_token")

        r2 = client.post(
            "/api/v1/auth/kiosk-login",
            json={
                "card_identifier": "0213368",
                "simulated_face_identity": "FACE_0213368_THIEN",
            },
        )
        cls.token_thien = r2.json().get("session_token") or r2.json().get("access_token")

        r3 = client.post(
            "/api/v1/auth/kiosk-login",
            json={
                "card_identifier": "0214502",
                "simulated_face_identity": "FACE_0214502_ANH",
            },
        )
        cls.token_anh = r3.json().get("session_token") or r3.json().get("access_token")

        r_admin = client.post(
            "/api/v1/auth/kiosk-login",
            json={
                "card_identifier": "BARCODE-ADMIN01",
                "pin_fallback": "999888",
            },
        )
        cls.token_admin = r_admin.json().get("session_token") or r_admin.json().get("access_token")

    def test_01_kiosk_health_check(self):
        resp = client.get("/api/v1/health")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["status"], "healthy")
        self.assertLessEqual(data["kiosk_client_ram_footprint_mb"], 400)

    def test_02_kiosk_login_dang_xuan_dong_0206968_success(self):
        resp = client.post(
            "/api/v1/auth/kiosk-login",
            json={
                "card_identifier": "0206968",
                "simulated_face_identity": "FACE_0206968_DONG",
                "kiosk_id": "KIOSK_LOBBY_H1",
            },
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data["authenticated"])
        self.assertEqual(data["student"]["student_code"], "0206968")
        self.assertEqual(data["student"]["full_name"], "Đặng Xuân Đồng")
        self.assertEqual(data["student"]["class_name"], "68CS1")
        self.assertTrue("session_token" in data or "access_token" in data)
        self.assertEqual(data["token_type"], "bearer")
        self.assertGreaterEqual(data["biometric_metrics"]["cosine_similarity"], 0.72)

    def test_02b_kiosk_login_empty_payload_rejected(self):
        resp = client.post("/api/v1/auth/kiosk-login", json={"card_identifier": "0206968"})
        self.assertEqual(resp.status_code, 401)
        self.assertFalse(resp.json()["authenticated"])

    def test_02c_kiosk_enroll_face_pin_protection(self):
        b64 = create_sample_camera_frame_b64()

        # 1. Missing PIN -> 403
        resp_no_pin = client.post(
            "/api/v1/auth/enroll-face",
            json={
                "card_identifier": "0206968",
                "face_image_b64": b64,
                "pin_code": "",
            },
        )
        self.assertEqual(resp_no_pin.status_code, 403)

        # 2. Invalid PIN -> 403
        resp_wrong = client.post(
            "/api/v1/auth/enroll-face",
            json={
                "card_identifier": "0206968",
                "face_image_b64": b64,
                "pin_code": "999999",
            },
        )
        self.assertEqual(resp_wrong.status_code, 403)

        # 3. Valid PIN (310305 for Đặng Xuân Đồng) -> 200 enrolled
        try:
            resp_valid = client.post(
                "/api/v1/auth/enroll-face",
                json={
                    "card_identifier": "0206968",
                    "face_image_b64": b64,
                    "pin_code": "310305",
                },
            )
            self.assertEqual(resp_valid.status_code, 200)
            self.assertTrue(resp_valid.json().get("enrolled"))
        finally:
            # --- THÊM ĐOẠN NÀY: Khôi phục vector gốc của 0206968 cho test_15 ---
            import json
            import sqlite3
            from backend.app.database import DB_PATH, generate_deterministic_face_vector

            conn = sqlite3.connect(DB_PATH)
            try:
                conn.execute(
                    "UPDATE student_cards_biometrics SET face_embedding_json = ? WHERE card_uid = 'RFID-HUCE-0206968'",
                    (json.dumps(generate_deterministic_face_vector("FACE_0206968_DONG")),),
                )
                conn.commit()
            finally:
                conn.close()

    def test_03_physical_student_card_front_and_back_scanner(self):
        # Scan Front
        front_b64 = load_card_asset_b64("card_0206968_front.jpg")
        resp_front = client.post("/api/v1/auth/scan-card", json={"card_image_b64": front_b64})
        self.assertEqual(resp_front.status_code, 200)
        data_front = resp_front.json()
        self.assertTrue(data_front["card_detected"])
        self.assertEqual(data_front["student_code"], "0206968")
        self.assertEqual(data_front["full_name"], "Đặng Xuân Đồng")

        # Scan Back
        back_b64 = load_card_asset_b64("card_0206968_back.jpg")
        resp_back = client.post("/api/v1/auth/scan-card", json={"card_image_b64": back_b64})
        self.assertEqual(resp_back.status_code, 200)
        data_back = resp_back.json()
        self.assertTrue(data_back["card_detected"])
        self.assertEqual(data_back["student_code"], "0206968")

        # Scan with decoded barcode
        resp_bc = client.post(
            "/api/v1/auth/scan-card",
            json={
                "card_image_b64": back_b64,
                "decoded_barcode": "BARCODE-0213368",
            },
        )
        self.assertEqual(resp_bc.status_code, 200)
        data_bc = resp_bc.json()
        self.assertTrue(data_bc["card_detected"])
        self.assertEqual(data_bc["student_code"], "0213368")
        self.assertEqual(data_bc["full_name"], "Nguyễn Đức Thiện")

    def test_04_kiosk_login_impostor_face_rejected(self):
        # Fetch current enrolled face vector for 0206968
        with db_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT face_embedding_json FROM student_cards_biometrics WHERE card_uid = 'RFID-HUCE-0206968'"
            )
            initial_face = cur.fetchone()["face_embedding_json"]

        resp = client.post(
            "/api/v1/auth/kiosk-login",
            json={
                "card_identifier": "0206968",
                "simulated_face_identity": "IMPOSTOR_FACE",
                "kiosk_id": "KIOSK_LOBBY_H1",
            },
        )
        self.assertEqual(resp.status_code, 401)
        self.assertEqual(resp.json()["error_code"], "FACE_MISMATCH")

        # Ensure enrolled face vector was NOT overwritten
        with db_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT face_embedding_json FROM student_cards_biometrics WHERE card_uid = 'RFID-HUCE-0206968'"
            )
            current_face = cur.fetchone()["face_embedding_json"]
        self.assertEqual(initial_face, current_face)

    def test_05_kiosk_login_spoof_photo_rejected(self):
        resp = client.post(
            "/api/v1/auth/kiosk-login",
            json={
                "card_identifier": "0206968",
                "simulated_face_identity": "SPOOF_PHOTO_ATTACK",
                "kiosk_id": "KIOSK_LOBBY_H1",
            },
        )
        self.assertEqual(resp.status_code, 401)
        self.assertEqual(resp.json()["error_code"], "LIVENESS_FAILED")

    def test_06_kiosk_login_pin_fallback(self):
        resp = client.post(
            "/api/v1/auth/kiosk-login",
            json={
                "card_identifier": "BARCODE-0206968",
                "pin_fallback": "310305",
                "kiosk_id": "KIOSK_LOBBY_H1",
            },
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data["authenticated"])
        self.assertEqual(data["auth_method"], "CARD_PLUS_PIN_FALLBACK")
        self.assertTrue("session_token" in data or "access_token" in data)

    def test_07_opencv_frame_decoding_and_128d_descriptor(self):
        b64 = create_sample_camera_frame_b64()
        resp = client.post("/api/v1/auth/detect-face", json={"face_image_b64": b64})
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("face_detected", data)

        gray_patch = np.random.randint(40, 220, (112, 112), dtype=np.uint8)
        vec = extract_128d_cv_face_descriptor(gray_patch)
        self.assertEqual(len(vec), 128)

    def test_08_agentic_rag_scholarship_evaluation(self):
        headers = {"Authorization": f"Bearer {self.token_dong}"}
        resp = client.post(
            "/api/v1/chat/query",
            json={
                "question": "Điều kiện xét học bổng là gì và điểm của tôi kỳ này có đạt học bổng không?",
                "student_code": "0206968",
            },
            headers=headers,
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["intent_detected"], "SCHOLARSHIP")
        self.assertIn("Đặng Xuân Đồng", data["answer"])
        self.assertIn("ĐỦ ĐIỀU KIỆN", data["answer"])
        self.assertIn("Loại Xuất sắc", data["answer"])

    def test_09_agentic_rag_class_schedule(self):
        headers = {"Authorization": f"Bearer {self.token_dong}"}
        resp = client.post(
            "/api/v1/chat/query",
            json={
                "question": "Cho tôi xem lịch học thời khóa biểu tuần này học ở phòng nào?",
                "student_code": "0206968",
            },
            headers=headers,
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["intent_detected"], "CLASS_SCHEDULE")
        self.assertIn("H1-302", data["answer"])
        self.assertIn("IT4010", data["answer"])

    def test_10_agentic_rag_exam_schedule(self):
        headers = {"Authorization": f"Bearer {self.token_dong}"}
        resp = client.post(
            "/api/v1/chat/query",
            json={
                "question": "Lịch thi cuối kỳ của tôi ngày nào, phòng thi và số báo danh bao nhiêu?",
                "student_code": "0206968",
            },
            headers=headers,
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["intent_detected"], "EXAM_SCHEDULE")
        self.assertIn("SBD-12", data["answer"])
        self.assertIn("H3-201", data["answer"])
        self.assertNotIn("\\n", data["answer"])

    def test_11_dag_roadmap_and_failed_course_alert(self):
        # 1. 0206968 AI track recommendation
        headers_dong = {"Authorization": f"Bearer {self.token_dong}"}
        r1 = client.get("/api/v1/academic/roadmap/0206968?career_track=AI", headers=headers_dong)
        self.assertEqual(r1.status_code, 200)
        d1 = r1.json()
        rec_codes_1 = [c["course_code"] for c in d1["recommended_courses"]]
        self.assertTrue("IT4060" in rec_codes_1 or "IT4070" in rec_codes_1 or "IT4025" in rec_codes_1)

        # 2. 0214502 mandatory retake
        headers_anh = {"Authorization": f"Bearer {self.token_anh}"}
        r2 = client.get("/api/v1/academic/roadmap/0214502", headers=headers_anh)
        self.assertEqual(r2.status_code, 200)
        d2 = r2.json()
        self.assertEqual(d2["recommended_courses"][0]["course_code"], "IT3080")
        self.assertIn("HỌC LẠI BẮT BUỘC", d2["recommended_courses"][0]["priority_type"])

    def test_12_admin_ingest_and_profile_dashboard(self):
        doc_payload = {
            "doc_title": "Quy định Học bổng Doanh nghiệp Tài trợ Khoa CNTT HUCE",
            "doc_number": "450/QĐ-CNTT",
            "article_ref": "Điều 3, Khoản 1",
            "category": "HOC_BONG",
            "keywords": "học bổng doanh nghiệp tài trợ cntt ielts",
            "content": "Sinh viên Khoa CNTT có GPA >= 3.20 và có chứng chỉ tiếng Anh IELTS >= 6.0 được ưu tiên xét Học bổng Doanh nghiệp trị giá 20.000.000 VNĐ.",
        }

        # Student token cannot ingest documents (403)
        resp_forbidden = client.post(
            "/api/v1/admin/documents",
            json=doc_payload,
            headers={"Authorization": f"Bearer {self.token_dong}"},
        )
        self.assertEqual(resp_forbidden.status_code, 403)

        # Admin token can ingest documents (201)
        resp_admin = client.post(
            "/api/v1/admin/documents",
            json=doc_payload,
            headers={"Authorization": f"Bearer {self.token_admin}"},
        )
        self.assertEqual(resp_admin.status_code, 201)
        res_data = resp_admin.json()
        self.assertEqual(res_data["status"], "created")
        self.assertTrue(res_data["chunk_id"].startswith("DOC_"))

        # Ingest a second document -> verify unique ID (no PK conflict)
        doc_payload_2 = dict(doc_payload)
        doc_payload_2["doc_title"] = "Quy định Học bổng Doanh nghiệp Lần 2"
        resp_admin_2 = client.post(
            "/api/v1/admin/documents",
            json=doc_payload_2,
            headers={"Authorization": f"Bearer {self.token_admin}"},
        )
        self.assertEqual(resp_admin_2.status_code, 201)
        self.assertNotEqual(res_data["chunk_id"], resp_admin_2.json()["chunk_id"])

        # Student dashboard retrieval
        dash_resp = client.get(
            "/api/v1/academic/profile/0206968",
            headers={"Authorization": f"Bearer {self.token_dong}"},
        )
        self.assertEqual(dash_resp.status_code, 200)
        dash = dash_resp.json()
        self.assertEqual(dash["student_code"], "0206968")
        self.assertTrue(dash["scholarship_summary"]["eligible"])

    def test_13_security_anti_idor_protection(self):
        # Student 0213368 tries to access 0206968's academic endpoints
        headers_thien = {"Authorization": f"Bearer {self.token_thien}"}

        r_profile = client.get("/api/v1/academic/profile/0206968", headers=headers_thien)
        self.assertEqual(r_profile.status_code, 403)

        r_schol = client.get("/api/v1/academic/scholarship/0206968", headers=headers_thien)
        self.assertEqual(r_schol.status_code, 403)

        r_roadmap = client.get("/api/v1/academic/roadmap/0206968", headers=headers_thien)
        self.assertEqual(r_roadmap.status_code, 403)

        r_sched = client.get("/api/v1/academic/schedules/0206968", headers=headers_thien)
        self.assertEqual(r_sched.status_code, 403)

    def test_14_security_chat_guest_vs_authenticated_rules(self):
        # 1. Guest asks general regulation -> 200 OK
        r_gen = client.post(
            "/api/v1/chat/query",
            json={"question": "Số tín chỉ tối đa được đăng ký trong mỗi học kỳ chính là bao nhiêu?"},
        )
        self.assertEqual(r_gen.status_code, 200)
        self.assertIn("tín chỉ", r_gen.json()["answer"])

        # 2. Guest asks personal schedule -> 401 Unauthorized
        r_sched = client.post(
            "/api/v1/chat/query",
            json={"question": "Cho tôi xem thời khóa biểu tuần này học phòng nào?"},
        )
        self.assertEqual(r_sched.status_code, 401)

    def test_15_security_token_revocation_on_logout(self):
        # 0. Unauthorized logout attempt without token -> 401 Unauthorized
        r_unauth = client.post("/api/v1/auth/logout")
        self.assertEqual(r_unauth.status_code, 401)

        # Login a new session for 0206968
        resp_login = client.post(
            "/api/v1/auth/kiosk-login",
            json={"card_identifier": "0206968", "simulated_face_identity": "FACE_0206968_DONG"},
        )
        self.assertEqual(resp_login.status_code, 200)
        token = resp_login.json().get("session_token") or resp_login.json().get("access_token")
        headers = {"Authorization": f"Bearer {token}"}

        # Token is valid
        r1 = client.get("/api/v1/academic/profile/0206968", headers=headers)
        self.assertEqual(r1.status_code, 200)

        # Logout
        r_logout = client.post("/api/v1/auth/logout", headers=headers)
        self.assertEqual(r_logout.status_code, 200)
        self.assertTrue(r_logout.json()["success"])

        # Token is now revoked
        r2 = client.get("/api/v1/academic/profile/0206968", headers=headers)
        self.assertEqual(r2.status_code, 401)
        self.assertIn("thu hồi", r2.json()["detail"].lower())


if __name__ == "__main__":
    unittest.main(verbosity=2)
