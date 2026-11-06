import os
import sys
import json
import re
import uuid
import asyncio
from datetime import datetime, date, time, timedelta

# Đảm bảo đường dẫn import cho backend app
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, text, delete

from app.core.database import AsyncSessionLocal, engine, Base
from app.core.security import get_password_hash
from app.models.unit import Unit
from app.models.user import User
from app.models.document import Document, DocumentVersion, Chunk
from app.models.schedule import Room, ClassSection, ScheduleEntry, Service
from app.models.announcement import Announcement
from app.models.enums import (
    UserRole,
    UnitKind,
    DocumentStatus,
    VersionStatus,
    RoomType,
    ScheduleEntryType,
    AnnouncementStatus
)
from app.ml.chunker import LegalChunker
from app.ml.hybrid_retriever import HybridRetriever

SEED_DIR = os.path.dirname(os.path.abspath(__file__))
OPERATIONAL_DATA_FILE = os.path.join(SEED_DIR, "seed_operational_data.json")
REGULATIONS_FILE = os.path.join(SEED_DIR, "sample_regulations.md")
GOLDEN_QA_FILE = os.path.join(SEED_DIR, "golden_qa.json")

def parse_regulations_md(file_path: str):
    """
    Phân tích file markdown thành các tài liệu và trang tương ứng.
    Nhận diện [Trang X] để gán số trang chính xác cho từng đoạn quy chế.
    """
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Tách 2 tài liệu qua vạch ngăn cách
    docs_raw = content.split("================================================================================")
    parsed_docs = []

    for doc_raw in docs_raw:
        if not doc_raw.strip():
            continue

        is_active = "CÒN HIỆU LỰC" in doc_raw or "ACTIVE" in doc_raw
        ver_no = "2025.1" if is_active else "2021.0"
        status = VersionStatus.ACTIVE if is_active else VersionStatus.EXPIRED
        eff_from = date(2025, 9, 1) if is_active else date(2021, 9, 1)
        eff_to = None if is_active else date(2025, 8, 31)

        # Tách các trang theo mẫu [Trang X]
        page_pattern = re.compile(r'\[Trang\s+(\d+)\]')
        splits = page_pattern.split(doc_raw)

        pages_content = []
        # Phần trước [Trang 1] nếu có
        header_text = splits[0].strip()
        current_page = 1

        for i in range(1, len(splits), 2):
            p_num = int(splits[i])
            p_text = splits[i+1].strip()
            pages_content.append({
                "page": p_num,
                "text": p_text
            })

        if not pages_content and header_text:
            pages_content.append({"page": 1, "text": header_text})

        parsed_docs.append({
            "version_no": ver_no,
            "status": status,
            "effective_from": eff_from,
            "effective_to": eff_to,
            "is_active": is_active,
            "pages": pages_content
        })

    return parsed_docs

async def seed_operational_data(db: AsyncSession):
    print("🔹 [1/3] Đang nạp dữ liệu vận hành từ seed_operational_data.json...")
    with open(OPERATIONAL_DATA_FILE, "r", encoding="utf-8") as f:
        op_data = json.load(f)

    # 1. Units
    unit_map = {}
    for u in op_data["units"]:
        u_id = uuid.UUID(u["id"])
        unit_map[u["name"]] = u_id
        existing = await db.get(Unit, u_id)
        if not existing:
            unit_obj = Unit(
                id=u_id,
                name=u["name"],
                kind=UnitKind(u["kind"]),
                contact_email=u["contact_email"],
                phone=u["phone"],
                office_location=u["office_location"]
            )
            db.add(unit_obj)
        else:
            existing.name = u["name"]
            existing.contact_email = u["contact_email"]
            existing.phone = u["phone"]
            existing.office_location = u["office_location"]
    await db.flush()

    # 2. Users
    user_map = {}
    default_hashed_pwd = get_password_hash("CampusMate2026!")
    for user_item in op_data["users"]:
        uid = uuid.UUID(user_item["id"])
        user_map[user_item["email"]] = uid
        existing_u = await db.get(User, uid)
        unit_fk = uuid.UUID(user_item["unit_id"]) if user_item.get("unit_id") else None

        if not existing_u:
            user_obj = User(
                id=uid,
                email=user_item["email"],
                hashed_password=default_hashed_pwd,
                full_name=user_item["full_name"],
                role=UserRole(user_item["role"]),
                unit_id=unit_fk,
                cohort=user_item.get("cohort"),
                major=user_item.get("major"),
                is_active=user_item.get("is_active", True)
            )
            db.add(user_obj)
        else:
            existing_u.full_name = user_item["full_name"]
            existing_u.role = UserRole(user_item["role"])
            existing_u.unit_id = unit_fk
            existing_u.cohort = user_item.get("cohort")
            existing_u.major = user_item.get("major")
    await db.flush()

    # 3. Rooms
    room_map = {}
    for r in op_data["rooms"]:
        rid = uuid.UUID(r["id"])
        room_map[r["code"]] = rid
        existing_r = await db.get(Room, rid)
        if not existing_r:
            room_obj = Room(
                id=rid,
                code=r["code"],
                building=r["building"],
                capacity=r["capacity"],
                room_type=RoomType(r["room_type"]),
                equipment=r.get("equipment", []),
                opening_hours=r.get("opening_hours", "07:00 - 21:00")
            )
            db.add(room_obj)
        else:
            existing_r.capacity = r["capacity"]
            existing_r.building = r["building"]
            existing_r.equipment = r.get("equipment", [])
    await db.flush()

    # 4. Services
    for s in op_data["services"]:
        sid = uuid.UUID(s["id"])
        existing_s = await db.get(Service, sid)
        u_fk = uuid.UUID(s["unit_id"])
        if not existing_s:
            service_obj = Service(
                id=sid,
                unit_id=u_fk,
                name=s["name"],
                procedure=s["procedure"],
                form_urls=[{"label": os.path.basename(u), "url": u} for u in s.get("form_urls", [])],
                opening_hours=s["opening_hours"],
                contact=s["contact"]
            )
            db.add(service_obj)
        else:
            existing_s.name = s["name"]
            existing_s.procedure = s["procedure"]
            existing_s.opening_hours = s["opening_hours"]
            existing_s.contact = s["contact"]
    await db.flush()

    # 5. Announcements
    for a in op_data["announcements"]:
        aid = uuid.UUID(a["id"])
        existing_a = await db.get(Announcement, aid)
        u_fk = uuid.UUID(a["unit_id"])
        author_fk = uuid.UUID(a["author_id"])
        approver_fk = uuid.UUID(a["approved_by"]) if a.get("approved_by") else None

        if not existing_a:
            ann_obj = Announcement(
                id=aid,
                unit_id=u_fk,
                author_id=author_fk,
                title=a["title"],
                body=a["body"],
                audience=a["audience"],
                status=AnnouncementStatus(a["status"]),
                publish_at=datetime.utcnow() - timedelta(days=1),
                approved_by=approver_fk,
                created_at=datetime.utcnow() - timedelta(days=2)
            )
            db.add(ann_obj)
        else:
            existing_a.title = a["title"]
            existing_a.body = a["body"]
            existing_a.audience = a["audience"]
            existing_a.status = AnnouncementStatus(a["status"])
    await db.flush()

    # 6. Bổ sung Lớp học phần & Lịch cá nhân cho sinh viên demo (Trần Minh Quân)
    student_id = user_map.get("sv.cntt@uni.edu.vn")
    lecturer_id = user_map.get("gv.cntt@uni.edu.vn")
    room_a2_201 = room_map.get("A2-201")
    room_a2_202 = room_map.get("A2-202")

    if student_id and room_a2_201:
        # Kiểm tra lớp học phần IT3010
        sec_stmt = select(ClassSection).where(ClassSection.course_code == "IT4010")
        sec_res = await db.execute(sec_stmt)
        sec = sec_res.scalar_one_or_none()
        if not sec:
            sec = ClassSection(
                course_code="IT4010",
                course_name="Học máy và Ứng dụng AI",
                semester="20251",
                lecturer_id=lecturer_id
            )
            db.add(sec)
            await db.flush()

        today = date.today()
        # Xóa các lịch cũ của student để tránh trùng lặp khi chạy seed lại
        await db.execute(delete(ScheduleEntry).where(ScheduleEntry.user_id == student_id))

        # Lịch học chính khóa sáng hôm nay
        sched1 = ScheduleEntry(
            section_id=sec.id,
            user_id=student_id,
            room_id=room_a2_201,
            entry_type=ScheduleEntryType.CLASS,
            date=today,
            start_time=time(8, 0),
            end_time=time(10, 0),
            synced_at=datetime.utcnow()
        )
        # Lịch thi kết thúc học phần tuần tới
        sched2 = ScheduleEntry(
            section_id=sec.id,
            user_id=student_id,
            room_id=room_a2_202 or room_a2_201,
            entry_type=ScheduleEntryType.EXAM,
            date=today + timedelta(days=4),
            start_time=time(14, 0),
            end_time=time(16, 0),
            synced_at=datetime.utcnow()
        )
        db.add_all([sched1, sched2])
        await db.flush()

    await db.commit()
    print("✅ Đã nạp thành công Units, Users, Rooms, Services, Announcements và Schedule!")

async def seed_regulations_data(db: AsyncSession):
    print("🔹 [2/3] Đang nạp văn bản quy chế từ sample_regulations.md...")
    parsed_docs = parse_regulations_md(REGULATIONS_FILE)

    # Lấy ID của Phòng Đào tạo
    unit_stmt = select(Unit).where(Unit.name == "Phòng Đào tạo")
    u_res = await db.execute(unit_stmt)
    dt_unit = u_res.scalar_one_or_none()
    issuer_id = dt_unit.id if dt_unit else uuid.uuid4()

    # Tạo hoặc lấy đầu mục văn bản Quy chế đào tạo
    doc_stmt = select(Document).where(Document.title == "Quy chế đào tạo trình độ đại học hệ chính quy")
    doc_res = await db.execute(doc_stmt)
    document = doc_res.scalar_one_or_none()

    if not document:
        document = Document(
            title="Quy chế đào tạo trình độ đại học hệ chính quy",
            issuer_unit_id=issuer_id,
            status=DocumentStatus.ACTIVE
        )
        db.add(document)
        await db.flush()

    total_chunks_created = 0

    for doc_item in parsed_docs:
        ver_no = doc_item["version_no"]
        status = doc_item["status"]
        is_active = doc_item["is_active"]
        pages = doc_item["pages"]

        # Kiểm tra xem DocumentVersion đã có chưa
        ver_stmt = select(DocumentVersion).where(
            DocumentVersion.document_id == document.id,
            DocumentVersion.version_no == ver_no
        )
        ver_res = await db.execute(ver_stmt)
        version_obj = ver_res.scalar_one_or_none()

        if not version_obj:
            version_obj = DocumentVersion(
                document_id=document.id,
                version_no=ver_no,
                effective_from=doc_item["effective_from"],
                effective_to=doc_item["effective_to"],
                status=status,
                file_url=f"/api/v1/storage/quy_che_dao_tao_{ver_no}.pdf",
                indexed_at=datetime.utcnow()
            )
            db.add(version_obj)
            await db.flush()
        else:
            version_obj.status = status
            version_obj.effective_from = doc_item["effective_from"]
            version_obj.effective_to = doc_item["effective_to"]
            version_obj.indexed_at = datetime.utcnow()
            # Xóa các chunk cũ của version này để cập nhật lại
            await db.execute(delete(Chunk).where(Chunk.version_id == version_obj.id))
            await db.flush()

        # Chạy qua bộ cắt đoạn pháp lý theo Chương/Điều/Khoản (chunker.py)
        raw_chunks = LegalChunker.chunk_document(pages)
        print(f"   -> Phiên bản {ver_no} ({status.value}): Cắt được {len(raw_chunks)} đoạn quy chế.")

        created_chunks = []
        for rc in raw_chunks:
            text_str = rc["text"]
            # Tính vector embedding và tsvector
            embedding_vec = await HybridRetriever.get_embedding(text_str)

            chunk = Chunk(
                version_id=version_obj.id,
                article=rc.get("article"),
                clause=rc.get("clause"),
                page=rc.get("page", 1),
                text=text_str,
                embedding=embedding_vec,
                is_active=is_active  # BR01: Bản 2025 is_active=True, Bản 2021 is_active=False
            )
            db.add(chunk)
            created_chunks.append(chunk)

        await db.flush()

        # Cập nhật cột tsv với to_tsvector tiếng Việt
        for chk in created_chunks:
            await db.execute(
                text("UPDATE chunks SET tsv = to_tsvector('simple', :txt) WHERE id = :cid"),
                {"txt": chk.text, "cid": chk.id}
            )

        total_chunks_created += len(created_chunks)

    await db.commit()
    print(f"✅ Đã lập chỉ mục xong {total_chunks_created} đoạn quy chế vào bảng chunks (Đảm bảo BR01 & BR07)!")

def sync_golden_qa_to_eval():
    print("🔹 [3/3] Đang đồng bộ golden_qa.json sang backend/eval/dataset.json...")
    with open(GOLDEN_QA_FILE, "r", encoding="utf-8") as f:
        golden_qa = json.load(f)

    eval_dataset = []
    for item in golden_qa:
        eval_dataset.append({
            "id": item["question_id"],
            "category": item.get("category"),
            "question": item["raw_question"],
            "anonymized_question": item.get("anonymized_question"),
            "intent": item["intent"],
            "expected_version": item.get("expected_version"),
            "expected_citations": item.get("expected_citations", []),
            "reference_answer": item.get("reference_answer", ""),
            "should_refuse": item.get("should_refuse", False),
            "expected_fallback_unit": item.get("expected_fallback_unit")
        })

    eval_dest = os.path.join(os.path.dirname(SEED_DIR), "eval", "dataset.json")
    with open(eval_dest, "w", encoding="utf-8") as f:
        json.dump(eval_dataset, f, ensure_ascii=False, indent=2)

    print(f"✅ Đã đồng bộ 10 câu hỏi vàng vào {eval_dest} phục vụ các bài kiểm thử E0-E8.")

async def main():
    print("=" * 70)
    print("🚀 BẮT ĐẦU NẠP DỮ LIỆU SEED CHUẨN HÓA CHO CAMPUSMATE AI")
    print("=" * 70)

    # 1. Khởi tạo schema CSDL nếu chưa có
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # 2. Nạp dữ liệu
    async with AsyncSessionLocal() as db:
        await seed_operational_data(db)
        await seed_regulations_data(db)

    # 3. Đồng bộ dataset đánh giá
    sync_golden_qa_to_eval()

    print("=" * 70)
    print("🎉 TẤT CẢ DỮ LIỆU ĐÃ ĐƯỢC NẠP THÀNH CÔNG VÀO CƠ SỞ DỮ LIỆU!")
    print("=" * 70)

if __name__ == "__main__":
    asyncio.run(main())

