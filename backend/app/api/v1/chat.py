import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.security import get_current_user, require_roles
from app.models.user import User
from app.models.chat import ChatSession, Message, Feedback
from app.models.enums import UserRole, FeedbackRating
from app.schemas.chat import (
    ChatSessionCreate,
    ChatSessionResponse,
    ChatMessageCreate,
    FeedbackCreate,
    FeedbackResponse,
)
from app.ml.rag_pipeline import RAGPipeline

router = APIRouter(prefix="/chat", tags=["Chat & RAG"])

@router.post("/sessions", response_model=ChatSessionResponse)
async def create_chat_session(
    payload: ChatSessionCreate,
    current_user: User = Depends(require_roles(["STUDENT", "LECTURER", "STAFF", "ADMIN"])),
    db: AsyncSession = Depends(get_db)
):
    """
    Khởi tạo phiên hội thoại mới cho người dùng.
    """
    session = ChatSession(
        user_id=current_user.id,
        title=payload.title or "Cuộc trò chuyện mới",
        channel="WEB"
    )
    db.add(session)
    await db.commit()
    await db.refresh(session)
    return ChatSessionResponse(
        sessionId=str(session.id),
        title=session.title,
        startedAt=session.started_at
    )

@router.get("/sessions", response_model=List[ChatSessionResponse])
async def list_chat_sessions(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    stmt = (
        select(ChatSession)
        .where(ChatSession.user_id == current_user.id)
        .order_by(ChatSession.started_at.desc())
        .limit(20)
    )
    res = await db.execute(stmt)
    sessions = res.scalars().all()
    return [
        ChatSessionResponse(
            sessionId=str(s.id),
            title=s.title,
            startedAt=s.started_at
        )
        for s in sessions
    ]

@router.post("/sessions/{id}/messages")
async def send_message_stream(
    id: str,
    payload: ChatMessageCreate,
    current_user: User = Depends(require_roles(["STUDENT", "LECTURER", "STAFF", "ADMIN"])),
    db: AsyncSession = Depends(get_db)
):
    """
    Gửi câu hỏi và nhận câu trả lời qua luồng Server-Sent Events (SSE).
    Tuân thủ tuần tự 8 bước xử lý AI/ML và các quy tắc BR01, BR02, BR03, BR08.
    """
    # Kiểm tra session tồn tại và thuộc về user
    stmt = select(ChatSession).where(ChatSession.id == id, ChatSession.user_id == current_user.id)
    res = await db.execute(stmt)
    session = res.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Không tìm thấy phiên hội thoại.")

    # Cập nhật tiêu đề session nếu là tin nhắn đầu tiên
    if session.title == "Cuộc trò chuyện mới":
        session.title = payload.content[:30] + ("..." if len(payload.content) > 30 else "")
        await db.commit()

    return StreamingResponse(
        RAGPipeline.process_chat_stream(
            session_id=id,
            user=current_user,
            user_raw_content=payload.content,
            db=db
        ),
        media_type="text/event-stream"
    )

@router.post("/messages/{id}/feedback", response_model=FeedbackResponse)
async def submit_feedback(
    id: str,
    payload: FeedbackCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Đánh giá câu trả lời của AI: HELPFUL, UNHELPFUL hoặc báo sai (FR04).
    """
    # Kiểm tra message tồn tại
    msg_stmt = select(Message).where(Message.id == id)
    msg_res = await db.execute(msg_stmt)
    message = msg_res.scalar_one_or_none()
    if not message:
        raise HTTPException(status_code=404, detail="Không tìm thấy tin nhắn cần đánh giá.")

    # Kiểm tra xem đã có feedback chưa
    fb_stmt = select(Feedback).where(Feedback.message_id == id)
    fb_res = await db.execute(fb_stmt)
    existing_fb = fb_res.scalar_one_or_none()

    if existing_fb:
        existing_fb.rating = payload.rating
        existing_fb.comment = payload.comment
        existing_fb.is_reported_wrong = payload.isReportedWrong
    else:
        new_fb = Feedback(
            message_id=message.id,
            user_id=current_user.id,
            rating=payload.rating,
            comment=payload.comment,
            is_reported_wrong=payload.isReportedWrong
        )
        db.add(new_fb)

    await db.commit()
    return FeedbackResponse(status="ok")

