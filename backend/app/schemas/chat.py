import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, ConfigDict
from app.models.enums import MessageRole, IntentEnum, FeedbackRating

class ChatSessionCreate(BaseModel):
    title: Optional[str] = "Cuộc trò chuyện mới"

class ChatSessionResponse(BaseModel):
    sessionId: str
    title: str
    startedAt: datetime

    model_config = ConfigDict(from_attributes=True)

class ChatMessageCreate(BaseModel):
    content: str = Field(..., min_length=1, max_length=2000, description="Nội dung câu hỏi của sinh viên")

class CitationItem(BaseModel):
    ref: int
    documentTitle: str
    version: str
    article: Optional[str] = None
    page: int
    quote: str
    url: str

class FallbackInfo(BaseModel):
    reason: str
    suggestedUnit: str
    contactEmail: str
    message: str

class ChatDoneResponse(BaseModel):
    messageId: str
    answer: str
    disclaimer: str = "Câu trả lời của AI chỉ mang tính tham khảo; văn bản gốc là căn cứ chính thức."
    confidence: float
    citations: List[CitationItem] = []
    fallback: Optional[FallbackInfo] = None

class FeedbackCreate(BaseModel):
    rating: FeedbackRating
    comment: Optional[str] = None
    isReportedWrong: bool = False

class FeedbackResponse(BaseModel):
    status: str = "ok"

