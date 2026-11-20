"""
FastAPI Application Server for HUCE Smart AI Kiosk & Web Academic Assistant.
Provides:
- /api/v1/health
- /api/v1/auth/detect-face (Real-time OpenCV Face & Eye Detection)
- /api/v1/auth/scan-card (Physical HUCE Student ID Card Scanner - Front Portrait/Text & Back 1D Barcode)
- /api/v1/auth/enroll-face (Register live webcam face into Student Card)
- /api/v1/auth/capture-local-camera (Server-side OpenCV USB Webcam capture fallback)
- /api/v1/auth/kiosk-login (2FA Student Card + Real Face Biometric Verification)
- /api/v1/auth/logout (Revoke JWT Access Token)
- /api/v1/chat/query (Agentic RAG + Function Calling with Guest vs Authenticated RBAC)
- /api/v1/academic/* (Profile, Scholarship, Roadmap DAG, Class & Exam Schedules with Anti-IDOR)
- /api/v1/admin/documents (RBAC Admin Document Ingestion with UUID Primary Key)
"""

import os
from typing import Any, Dict, Optional
import uuid
from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .database import db_connection, get_connection, init_db
from .services.agentic_rag import answer_academic_query, detect_query_intent
from .services.biometric_auth import (
    authenticate_kiosk_card_and_face,
    capture_frame_from_local_usb_webcam,
    detect_face_in_frame,
    enroll_student_face_from_camera,
    scan_student_card_from_frame,
)
from .services.dag_recommender import (
    evaluate_student_scholarship,
    get_student_schedules_and_exams,
    recommend_courses_dag,
)
from .services.security import (
    assert_student_owner_or_admin,
    get_current_user,
    get_optional_user,
    require_admin,
    revoke_token,
)

app = FastAPI(
    title="HUCE Smart AI Kiosk & Academic Assistant API",
    description="Hệ thống Trợ lý Học vụ AI Đa nền tảng & Kiosk Thông minh tại Sảnh Sinh viên - Trường Đại học Xây dựng Hà Nội (HUCE)",
    version="2.2.0",
)

allowed_origins_env = os.environ.get("HUCE_ALLOWED_ORIGINS", "http://localhost:8000,http://127.0.0.1:8000")
allowed_origins = [o.strip() for o in allowed_origins_env.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization", "Content-Type"],
)

init_db()


class FaceFrameRequest(BaseModel):
    face_image_b64: str = Field(..., description="Ảnh chụp từ Webcam hoặc tải lên (DataURL Base64)")


class CardScanRequest(BaseModel):
    card_image_b64: str = Field(..., description="Ảnh chụp Mặt trước hoặc Mặt sau Thẻ sinh viên HUCE từ Camera/File")
    decoded_barcode: Optional[str] = Field(default=None, description="Mã vạch 1D đã giải mã (Code 128 / EAN-13) từ client")


class FaceEnrollRequest(BaseModel):
    card_identifier: str = Field(
        default="0206968",
        description="Mã thẻ sinh viên hoặc MSSV cần đăng ký mẫu khuôn mặt thật",
    )
    face_image_b64: str = Field(..., description="Ảnh khuôn mặt từ Webcam (DataURL Base64)")
    pin_code: str = Field(..., description="Mã PIN chủ thẻ để xác nhận quyền cập nhật khuôn mặt")


class KioskAuthRequest(BaseModel):
    card_identifier: str = Field(
        default="0206968",
        description="Mã thẻ sinh viên RFID UID, Barcode hoặc MSSV (VD: 0206968 - Đặng Xuân Đồng, hoặc 0213368 - Nguyễn Đức Thiện)",
        examples=["0206968"],
    )
    face_image_b64: Optional[str] = Field(
        default=None,
        description="Ảnh khuôn mặt chụp từ Camera Kiosk (JPEG Base64)",
    )
    simulated_face_identity: Optional[str] = Field(
        default=None,
        description="Tùy chọn mô phỏng khuôn mặt khi chạy kiểm thử tự động",
    )
    pin_fallback: Optional[str] = Field(
        default=None,
        description="Mã PIN dự phòng 6 số (Mặc định ngày sinh 310305 cho Đặng Xuân Đồng hoặc 123456)",
    )
    kiosk_id: str = Field(default="KIOSK_LOBBY_H1", description="Mã định danh trạm Kiosk sảnh sinh viên")


class ChatQueryRequest(BaseModel):
    question: str = Field(..., description="Câu hỏi tiếng Việt của sinh viên")
    student_code: str = Field(default="0206968", description="Mã số sinh viên đang đăng nhập tại Kiosk/Web")
    career_track: Optional[str] = Field(default=None, description="Định hướng chuyên ngành tự chọn (AI, SE, NETWORK)")
    kiosk_id: str = Field(default="KIOSK_LOBBY_H1")


class AdminDocumentRequest(BaseModel):
    doc_title: str
    doc_number: str
    article_ref: str
    category: str = "QUY_CHE_CHUNG"
    keywords: str
    content: str


@app.get("/api/v1/health")
def health_check():
    return {
        "status": "healthy",
        "service": "HUCE Smart AI Kiosk & Academic Assistant",
        "architecture": "Thin-Client Edge Kiosk + FastAPI Agentic RAG Server + OpenCV Face & Student Card Scanner",
        "kiosk_client_ram_footprint_mb": 380,
        "supported_features": [
            "low_spec_lobby_kiosk_mode",
            "large_panorama_face_and_card_viewport",
            "physical_student_card_front_and_back_barcode_scanner",
            "opencv_real_time_face_and_eye_detection",
            "hybrid_rag_regulations_and_scholarships",
            "personalized_class_and_exam_schedules",
            "dag_course_roadmap_recommender",
        ],
    }


@app.post("/api/v1/auth/detect-face")
def detect_face_api(req: FaceFrameRequest):
    return detect_face_in_frame(req.face_image_b64)


@app.post("/api/v1/auth/scan-card")
def scan_student_card_api(req: CardScanRequest):
    """Scans the front (portrait/text) or back (1D barcode) of a physical HUCE Student ID Card."""
    res = scan_student_card_from_frame(req.card_image_b64, decoded_barcode=req.decoded_barcode)
    if not res.get("card_detected"):
        return JSONResponse(status_code=400, content=res)
    return res


@app.post("/api/v1/auth/enroll-face")
def enroll_face_api(req: FaceEnrollRequest):
    res = enroll_student_face_from_camera(req.card_identifier, req.face_image_b64, req.pin_code)
    if not res.get("enrolled"):
        status = 403 if res.get("error_code") in ("INVALID_PIN", "PIN_REQUIRED") else 400
        return JSONResponse(status_code=status, content=res)
    return res


@app.get("/api/v1/auth/capture-local-camera")
def capture_local_camera_api():
    b64 = capture_frame_from_local_usb_webcam()
    if not b64:
        return JSONResponse(
            status_code=404,
            content={
                "captured": False,
                "message": "Không tìm thấy thiết bị USB Camera vật lý trên máy chủ hoặc Camera đang được trình duyệt sử dụng.",
            },
        )
    det = detect_face_in_frame(b64)
    return {
        "captured": True,
        "frame_b64": b64,
        "detection": det,
    }


@app.post("/api/v1/auth/kiosk-login")
def kiosk_biometric_login(req: KioskAuthRequest):
    result = authenticate_kiosk_card_and_face(
        card_identifier=req.card_identifier,
        face_image_b64=req.face_image_b64,
        simulated_face_identity=req.simulated_face_identity,
        pin_fallback=req.pin_fallback,
        kiosk_id=req.kiosk_id,
    )
    if not result["authenticated"]:
        return JSONResponse(status_code=401, content=result)
    return result


@app.post("/api/v1/auth/logout")
def kiosk_logout(user: Dict[str, Any] = Depends(get_current_user)):
    revoke_token(user["jti"], exp=user.get("exp"))
    return {
        "success": True,
        "message": "Đã đăng xuất phiên làm việc an toàn tại Kiosk và thu hồi access token.",
    }


PERSONAL_INTENTS = {"EXAM_SCHEDULE", "CLASS_SCHEDULE", "SCHOLARSHIP", "COURSE_ROADMAP"}


@app.post("/api/v1/chat/query")
def chat_query(
    req: ChatQueryRequest,
    user: Optional[Dict[str, Any]] = Depends(get_optional_user),
):
    if not req.question.strip():
        raise HTTPException(status_code=400, detail="Câu hỏi không được để trống.")

    intent = detect_query_intent(req.question)
    if intent in PERSONAL_INTENTS:
        if not user:
            raise HTTPException(
                status_code=401,
                detail="Vui lòng quét thẻ hoặc xác thực khuôn mặt để tra cứu thông tin học vụ cá nhân (lịch học, lịch thi, học bổng, lộ trình môn học).",
            )
        if user.get("role") != "ADMIN":
            effective_student_code = user["sub"]
        else:
            effective_student_code = req.student_code or user["sub"]
    else:
        effective_student_code = user["sub"] if user else req.student_code

    return answer_academic_query(
        question=req.question,
        student_code=effective_student_code,
        career_track=req.career_track,
        kiosk_id=req.kiosk_id,
    )


@app.get("/api/v1/academic/profile/{student_code}")
def get_full_student_kiosk_dashboard(
    student_code: str,
    user: Dict[str, Any] = Depends(get_current_user),
):
    assert_student_owner_or_admin(student_code, user)
    sched = get_student_schedules_and_exams(student_code)
    if not sched.get("found"):
        raise HTTPException(status_code=404, detail="Không tìm thấy sinh viên.")
    schol = evaluate_student_scholarship(student_code)
    roadmap = recommend_courses_dag(student_code)
    return {
        "student_code": student_code,
        "full_name": sched["full_name"],
        "class_name": sched["class_name"],
        "semester": sched["semester"],
        "scholarship_summary": schol,
        "schedules": sched,
        "dag_roadmap": roadmap,
    }


@app.get("/api/v1/academic/scholarship/{student_code}")
def check_scholarship_api(
    student_code: str,
    user: Dict[str, Any] = Depends(get_current_user),
):
    assert_student_owner_or_admin(student_code, user)
    res = evaluate_student_scholarship(student_code)
    if not res.get("found"):
        raise HTTPException(status_code=404, detail=res.get("message", "Not found"))
    return res


@app.get("/api/v1/academic/roadmap/{student_code}")
def get_roadmap_api(
    student_code: str,
    career_track: Optional[str] = None,
    user: Dict[str, Any] = Depends(get_current_user),
):
    assert_student_owner_or_admin(student_code, user)
    res = recommend_courses_dag(student_code, career_track=career_track)
    if not res.get("found"):
        raise HTTPException(status_code=404, detail=res.get("message", "Not found"))
    return res


@app.get("/api/v1/academic/schedules/{student_code}")
def get_schedules_api(
    student_code: str,
    user: Dict[str, Any] = Depends(get_current_user),
):
    assert_student_owner_or_admin(student_code, user)
    res = get_student_schedules_and_exams(student_code)
    if not res.get("found"):
        raise HTTPException(status_code=404, detail="Không tìm thấy lịch học/lịch thi của sinh viên.")
    return res


@app.post("/api/v1/admin/documents", status_code=201)
def ingest_regulation_document(
    req: AdminDocumentRequest,
    admin_user: Dict[str, Any] = Depends(require_admin),
):
    next_id = f"DOC_{uuid.uuid4().hex[:8].upper()}"
    with db_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO document_chunks VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                next_id,
                req.doc_title,
                req.doc_number,
                req.article_ref,
                req.category,
                req.keywords,
                req.content,
            ),
        )
        conn.commit()
    return {
        "status": "created",
        "chunk_id": next_id,
        "doc_title": req.doc_title,
        "message": "Đã phân đoạn ngữ nghĩa (Semantic Chunking) và nạp điều khoản vào cơ sở tri thức thành công.",
    }


FRONTEND_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "frontend-kiosk")
ASSETS_CARDS_DIR = os.path.join(os.path.dirname(__file__), "assets_cards")

if os.path.exists(ASSETS_CARDS_DIR):
    app.mount("/cards", StaticFiles(directory=ASSETS_CARDS_DIR), name="cards")

if os.path.exists(FRONTEND_DIR):
    app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")

    @app.get("/")
    def serve_kiosk_ui():
        return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))
