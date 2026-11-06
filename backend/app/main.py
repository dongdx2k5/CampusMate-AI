import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy import select, func

from app.core.config import settings
from app.core.database import engine, Base, AsyncSessionLocal
from app.core.security import get_password_hash
from app.models import (
    User, Unit, UserRole, UnitKind, Document, DocumentVersion, Chunk,
    VersionStatus, DocumentStatus, Room, RoomType, ClassSection,
    ScheduleEntry, ScheduleEntryType, Service, Announcement, AnnouncementStatus
)
from app.api.v1.auth import router as auth_router
from app.api.v1.chat import router as chat_router
from app.api.v1.schedule import router as schedule_router
from app.api.v1.rooms import router as rooms_router
from app.api.v1.announcements import router as announcements_router
from app.api.v1.services import router as services_router
from app.api.v1.admin import router as admin_router
from app.services.storage import UPLOAD_DIR
from app.ml.hybrid_retriever import HybridRetriever
from datetime import date, time, datetime, timedelta

async def seed_demo_data():
    """Tự động khởi tạo dữ liệu mẫu nếu hệ thống chưa có dữ liệu."""
    async with AsyncSessionLocal() as db:
        user_cnt = await db.execute(select(func.count(User.id)))
        if (user_cnt.scalar_one() or 0) > 0:
            return  # Đã có dữ liệu

        # 1. Tạo các đơn vị (Units)
        fit_unit = Unit(
            name="Khoa Công nghệ Thông tin",
            kind=UnitKind.FACULTY,
            contact_email="fit@uni.edu.vn",
            phone="024-3869-1234",
            office_location="Nhà B1, Phòng 302"
        )
        dt_unit = Unit(
            name="Phòng Đào tạo",
            kind=UnitKind.DEPARTMENT,
            contact_email="daotao@uni.edu.vn",
            phone="024-3869-2345",
            office_location="Nhà C1, Phòng 101"
        )
        ctsv_unit = Unit(
            name="Phòng Công tác Sinh viên",
            kind=UnitKind.DEPARTMENT,
            contact_email="ctsv@uni.edu.vn",
            phone="024-3869-3456",
            office_location="Nhà C1, Phòng 102"
        )
        db.add_all([fit_unit, dt_unit, ctsv_unit])
        await db.flush()

        # 2. Tạo người dùng theo 4 vai trò
        default_pwd = get_password_hash("CampusMate2026!")
        student_user = User(
            email="demo.student@uni.edu.vn",
            hashed_password=default_pwd,
            full_name="Nguyễn Văn An",
            role=UserRole.STUDENT,
            unit_id=fit_unit.id,
            cohort="K65",
            major="Khoa học Máy tính",
            is_active=True
        )
        lecturer_user = User(
            email="demo.lecturer@uni.edu.vn",
            hashed_password=default_pwd,
            full_name="TS. Trần Văn Bình",
            role=UserRole.LECTURER,
            unit_id=fit_unit.id,
            is_active=True
        )
        staff_user = User(
            email="demo.staff@uni.edu.vn",
            hashed_password=default_pwd,
            full_name="ThS. Lê Thị Cúc",
            role=UserRole.STAFF,
            unit_id=dt_unit.id,
            is_active=True
        )
        admin_user = User(
            email="demo.admin@uni.edu.vn",
            hashed_password=default_pwd,
            full_name="Quản trị viên Hệ thống",
            role=UserRole.ADMIN,
            unit_id=dt_unit.id,
            is_active=True
        )
        db.add_all([student_user, lecturer_user, staff_user, admin_user])
        await db.flush()

        # 3. Tạo văn bản quy chế & phiên bản
        doc1 = Document(
            title="Quy chế đào tạo đại học chính quy theo hệ thống tín chỉ",
            issuer_unit_id=dt_unit.id,
            status=DocumentStatus.ACTIVE
        )
        doc2 = Document(
            title="Quy định đánh giá điểm rèn luyện và xét học bổng khuyến khích",
            issuer_unit_id=ctsv_unit.id,
            status=DocumentStatus.ACTIVE
        )
        db.add_all([doc1, doc2])
        await db.flush()

        ver1 = DocumentVersion(
            document_id=doc1.id,
            version_no="2025",
            effective_from=date(2025, 1, 1),
            status=VersionStatus.ACTIVE,
            file_url="/api/v1/storage/quy_che_dao_tao_2025.pdf",
            approved_by=admin_user.id,
            indexed_at=datetime.utcnow()
        )
        ver2 = DocumentVersion(
            document_id=doc2.id,
            version_no="2024",
            effective_from=date(2024, 9, 1),
            status=VersionStatus.ACTIVE,
            file_url="/api/v1/storage/quy_dinh_hoc_bong_2024.pdf",
            approved_by=admin_user.id,
            indexed_at=datetime.utcnow()
        )
        db.add_all([ver1, ver2])
        await db.flush()

        # 4. Tạo các Chunks mẫu phục vụ RAG
        sample_chunks_data = [
            {
                "version_id": ver1.id,
                "article": "Điều 15. Nghỉ học tạm thời và bảo lưu kết quả học tập",
                "clause": "Khoản 1",
                "page": 9,
                "text": "Sinh viên được quyền xin nghỉ học tạm thời và bảo lưu kết quả học tập đã tích lũy trong các trường hợp: (a) Được điều động vào lực lượng vũ trang; (b) Bị ốm hoặc tai nạn phải điều trị dài ngày có chứng nhận của cơ sở y tế có thẩm quyền; (c) Vì nhu cầu cá nhân nếu đã học tối thiểu 01 học kỳ tại trường và không thuộc diện bị buộc thôi học."
            },
            {
                "version_id": ver1.id,
                "article": "Điều 15. Nghỉ học tạm thời và bảo lưu kết quả học tập",
                "clause": "Khoản 2",
                "page": 9,
                "text": "Thời gian nghỉ học tạm thời vì nhu cầu cá nhân được tính vào tổng thời gian học tập tối đa quy định cho toàn khóa học. Thời gian mỗi đợt nghỉ tạm thời không vượt quá 02 học kỳ chính."
            },
            {
                "version_id": ver1.id,
                "article": "Điều 22. Cảnh báo học tập và buộc thôi học",
                "clause": "Khoản 1",
                "page": 14,
                "text": "Sinh viên bị cảnh báo kết quả học tập nếu: (a) Điểm trung bình chung học kỳ đạt dưới 1.0 đối với học kỳ đầu tiên, dưới 1.2 đối với các học kỳ tiếp theo; hoặc (b) Tổng số tín chỉ chưa tích lũy tính từ đầu khóa học vượt quá 24 tín chỉ. Sinh viên bị cảnh báo 03 lần liên tiếp sẽ bị buộc thôi học."
            },
            {
                "version_id": ver2.id,
                "article": "Điều 8. Điều kiện xét cấp học bổng khuyến khích học tập",
                "clause": "Khoản 2",
                "page": 5,
                "text": "Sinh viên có kết quả học tập và rèn luyện từ loại Khá trở lên, không bị kỷ luật từ mức khiển trách trở lên trong học kỳ xét học bổng, và tích lũy tối thiểu 15 tín chỉ trong học kỳ chính sẽ được đưa vào danh sách xét cấp học bổng theo thứ tự từ cao xuống thấp cho đến hết quỹ học bổng."
            }
        ]

        for sc in sample_chunks_data:
            vec = await HybridRetriever.get_embedding(sc["text"])
            chk = Chunk(
                version_id=sc["version_id"],
                article=sc["article"],
                clause=sc["clause"],
                page=sc["page"],
                text=sc["text"],
                embedding=vec,
                is_active=True
            )
            db.add(chk)
        await db.flush()

        # 5. Tạo phòng học & không gian tự học
        r1 = Room(code="A1-101", building="A1", capacity=60, room_type=RoomType.CLASSROOM, equipment=["PROJECTOR", "AC", "MIC"], opening_hours="07:00 - 21:00")
        r2 = Room(code="A1-205", building="A1", capacity=120, room_type=RoomType.CLASSROOM, equipment=["PROJECTOR", "AC", "MIC", "SOUND"], opening_hours="07:00 - 21:00")
        r3 = Room(code="B1-301", building="B1", capacity=40, room_type=RoomType.LAB, equipment=["PC", "AC", "PROJECTOR"], opening_hours="07:30 - 17:30")
        r4 = Room(code="D3-Lib01", building="D3", capacity=80, room_type=RoomType.SELF_STUDY, equipment=["WIFI", "AC", "POWER_OUTLET"], opening_hours="07:00 - 22:00")
        db.add_all([r1, r2, r3, r4])
        await db.flush()

        # 6. Tạo lớp học phần và lịch cá nhân của demo student
        sec1 = ClassSection(course_code="IT3010", course_name="Cấu trúc dữ liệu và giải thuật", semester="20251", lecturer_id=lecturer_user.id)
        sec2 = ClassSection(course_code="IT3040", course_name="Kỹ thuật lập trình Web", semester="20251", lecturer_id=lecturer_user.id)
        db.add_all([sec1, sec2])
        await db.flush()

        today = date.today()
        # Lịch học hôm nay
        sched1 = ScheduleEntry(
            section_id=sec1.id,
            user_id=student_user.id,
            room_id=r1.id,
            entry_type=ScheduleEntryType.CLASS,
            date=today,
            start_time=time(8, 0),
            end_time=time(10, 0),
            synced_at=datetime.utcnow()
        )
        # Lịch thi cuối kỳ tuần tới
        sched2 = ScheduleEntry(
            section_id=sec2.id,
            user_id=student_user.id,
            room_id=r2.id,
            entry_type=ScheduleEntryType.EXAM,
            date=today + timedelta(days=5),
            start_time=time(13, 30),
            end_time=time(15, 30),
            synced_at=datetime.utcnow()
        )
        db.add_all([sched1, sched2])

        # 7. Tạo danh bạ dịch vụ
        s1 = Service(
            unit_id=dt_unit.id,
            name="Cấp bảng điểm và giấy xác nhận học vụ",
            procedure="1. Nộp phiếu đăng ký trực tuyến tại cổng sinh viên;\n2. Nhận kết quả sau 02 ngày làm việc tại Bộ phận Một cửa Phòng Đào tạo (Nhà C1-101).",
            form_urls=[{"label": "Đơn xin cấp bảng điểm (PDF)", "url": "/forms/don_cap_bang_diem.pdf"}],
            opening_hours="Sáng 08:00 - 11:30, Chiều 13:30 - 17:00 (Thứ 2 - Thứ 6)",
            contact="Phòng C1-101 | Email: daotao@uni.edu.vn | ĐT: 024-3869-2345"
        )
        s2 = Service(
            unit_id=ctsv_unit.id,
            name="Cấp lại thẻ sinh viên tích hợp",
            procedure="1. Khai báo mất thẻ qua ứng dụng;\n2. Nộp lệ phí in lại thẻ (50.000đ);\n3. Nhận thẻ mới sau 05 ngày làm việc.",
            form_urls=[{"label": "Tờ khai cấp lại thẻ SV", "url": "/forms/cap_lai_the_sv.docx"}],
            opening_hours="08:00 - 16:30 các ngày làm việc",
            contact="Phòng C1-102 | Email: ctsv@uni.edu.vn | ĐT: 024-3869-3456"
        )
        db.add_all([s1, s2])

        # 8. Tạo thông báo mẫu
        ann1 = Announcement(
            unit_id=dt_unit.id,
            author_id=staff_user.id,
            title="Kế hoạch đăng ký học phần học kỳ 2 năm học 2025-2026",
            body="Phòng Đào tạo thông báo kế hoạch đăng ký tín chỉ cho sinh viên toàn trường: Đợt 1 mở cổng từ ngày 15/12 đến 22/12. Đề nghị sinh viên hoàn thành khảo sát môn học trước khi mở cổng.",
            audience={"scope": "SCHOOL", "unit_ids": [], "cohorts": [], "majors": []},
            status=AnnouncementStatus.PUBLISHED,
            publish_at=datetime.utcnow() - timedelta(days=2),
            approved_by=admin_user.id
        )
        ann2 = Announcement(
            unit_id=fit_unit.id,
            author_id=staff_user.id,
            title="Hội thảo Khoa học Sinh viên CNTT và Công nghệ AI 2026",
            body="Khoa CNTT tổ chức hội thảo chuyên đề về Generative AI và Trợ lý số ứng dụng. Sinh viên K65 và K66 đăng ký tham dự nhận điểm rèn luyện theo quy chế.",
            audience={"scope": "UNIT", "unit_ids": [str(fit_unit.id)], "cohorts": ["K65", "K66"], "majors": ["Khoa học Máy tính"]},
            status=AnnouncementStatus.PUBLISHED,
            publish_at=datetime.utcnow() - timedelta(days=1),
            approved_by=admin_user.id
        )
        db.add_all([ann1, ann2])

        await db.commit()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Khởi tạo CSDL nếu cần
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    # Tự động nạp dữ liệu mẫu
    try:
        from seed_data.run_seed import seed_operational_data, seed_regulations_data, sync_golden_qa_to_eval
        async with AsyncSessionLocal() as db:
            user_cnt = await db.execute(select(func.count(User.id)))
            if (user_cnt.scalar_one() or 0) == 0:
                await seed_operational_data(db)
                await seed_regulations_data(db)
                sync_golden_qa_to_eval()
    except Exception as e:
        try:
            await seed_demo_data()
        except Exception as e2:
            print(f"Lưu ý khi seed dữ liệu demo: {e2}")
    yield

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Cổng thông tin & Trợ lý số đại học tích hợp RAG tiếng Việt (CampusMate AI)",
    lifespan=lifespan
)

# Cấu hình CORS an toàn theo Security Guidelines
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000",
        "http://127.0.0.1:8000"
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

# Endpoint phục vụ tải file đính kèm an toàn
@app.get("/api/v1/storage/{filename}")
async def serve_file(filename: str):
    # Chống Path Traversal bằng basename
    safe_name = os.path.basename(filename)
    file_path = os.path.join(UPLOAD_DIR, safe_name)
    if not os.path.exists(file_path):
        return JSONResponse(status_code=404, content={"detail": "Không tìm thấy tệp."})
    return FileResponse(
        file_path,
        headers={
            "X-Content-Type-Options": "nosniff",
            "Content-Disposition": f"inline; filename={safe_name}"
        }
    )

# Đăng ký các router REST API v1
api_prefix = settings.API_V1_STR
app.include_router(auth_router, prefix=api_prefix)
app.include_router(chat_router, prefix=api_prefix)
app.include_router(schedule_router, prefix=api_prefix)
app.include_router(rooms_router, prefix=api_prefix)
app.include_router(announcements_router, prefix=api_prefix)
app.include_router(services_router, prefix=api_prefix)
app.include_router(admin_router, prefix=api_prefix)

@app.get("/health")
async def health_check():
    return {"status": "ok", "app": settings.PROJECT_NAME, "version": settings.VERSION}

@app.get("/")
async def root():
    return {
        "message": f"Chào mừng tới {settings.PROJECT_NAME} API!",
        "docs": "/docs",
        "version": settings.VERSION
    }

