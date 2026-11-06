import re
from typing import Optional
import httpx
from app.models.enums import IntentEnum
from app.core.config import settings

class IntentRouter:
    """
    Bộ phân loại ý định & Định tuyến (FR02 - Bước 3)
    Phân loại câu hỏi vào 6 nhãn:
    - REGULATION (Quy chế đào tạo, chuẩn đầu ra, điểm rèn luyện, học vụ)
    - SCHEDULE (Lịch học, lịch thi cá nhân)
    - ROOM (Tra cứu phòng trống, không gian tự học)
    - SERVICE (Dịch vụ sinh viên, thủ tục hành chính, biểu mẫu)
    - ANNOUNCEMENT (Thông báo của trường, khoa, đơn vị)
    - OUT_OF_SCOPE (Ngoài phạm vi học đường)
    """

    PATTERNS = {
        IntentEnum.OUT_OF_SCOPE: re.compile(
            r'(?i)(?:bỏ\s*qua\s*(?:toàn\s*bộ|hết|mọi|các)\s*(?:hướng\s*dẫn|chỉ\s*thị)|bây\s*giờ\s*bạn\s*là|thời\s*tiết|nấu\s*ăn|bóng\s*đá|chính\s*trị|viết\s*thơ|kể\s*chuyện|game|chơi\s*gì|giá\s*vàng|mua\s*bán)'
        ),
        IntentEnum.SCHEDULE: re.compile(
            r'(?i)(?:lịch\s*học|lịch\s*thi|thời\s*khóa\s*biểu|hôm\s*nay\s*học|ngày\s*mai\s*học|ca\s*học|tiết\s*học|thi\s*môn|phòng\s*thi\s*của\s*tôi)'
        ),
        IntentEnum.ROOM: re.compile(
            r'(?i)(?:tìm\s*phòng|phòng\s*trống|phòng\s*nào\s*còn|mượn\s*phòng|phòng\s*tự\s*học|tra\s*cứu\s*phòng|phòng\s*học\s*trống)'
        ),
        IntentEnum.SERVICE: re.compile(
            r'(?i)(?:thủ\s*tục|cấp\s*lại\s*thẻ|bảng\s*điểm|giấy\s*xác\s*nhận|xin\s*giấy|vay\s*vốn|biểu\s*mẫu|dịch\s*vụ|đăng\s*ký\s*xe|ký\s*túc\s*xá)'
        ),
        IntentEnum.ANNOUNCEMENT: re.compile(
            r'(?i)(?:thông\s*báo|tin\s*mới|tin\s*tức|sự\s*kiện|hội\s*thảo|nghỉ\s*lễ|học\s*bổng\s*mới)'
        ),
        IntentEnum.REGULATION: re.compile(
            r'(?i)(?:bảo\s*lưu|thôi\s*học|quy\s*chế|quy\s*định|điều\s*kiện|tốt\s*nghiệp|điểm\s*chữ|cảnh\s*báo\s*học\s*tập|học\s*vụ|rèn\s*luyện|tín\s*chỉ|chuẩn\s*đầu\s*ra|miễn\s*giảm|học\s*phí|chuyển\s*ngành|học\s*bổng|rút\s*học\s*phần|rút\s*môn|cpa|gpa)'
        )
    }

    @classmethod
    async def classify(cls, query: str) -> IntentEnum:
        # 1. Khớp nhanh bằng Rule-based Regex
        for intent, pattern in cls.PATTERNS.items():
            if pattern.search(query):
                return intent

        # 2. Nếu có cấu hình LLM API, fallback sang LLM Few-shot classifier
        if settings.OPENAI_API_KEY and settings.OPENAI_API_KEY != "demo_key":
            try:
                system_prompt = (
                    "Bạn là bộ phân loại ý định trong trường đại học. "
                    "Hãy phân loại câu hỏi sau vào duy nhất một trong 6 nhãn: "
                    "REGULATION, SCHEDULE, ROOM, SERVICE, ANNOUNCEMENT, OUT_OF_SCOPE. "
                    "Chỉ trả về đúng tên nhãn in hoa, không giải thích thêm."
                )
                async with httpx.AsyncClient(timeout=5.0) as client:
                    resp = await client.post(
                        f"{settings.OPENAI_BASE_URL}/chat/completions",
                        headers={"Authorization": f"Bearer {settings.OPENAI_API_KEY}"},
                        json={
                            "model": settings.LLM_MODEL,
                            "messages": [
                                {"role": "system", "content": system_prompt},
                                {"role": "user", "content": query}
                            ],
                            "temperature": 0.0,
                            "max_tokens": 10
                        }
                    )
                    if resp.status_code == 200:
                        predicted = resp.json()["choices"][0]["message"]["content"].strip()
                        for valid_intent in IntentEnum:
                            if valid_intent.value in predicted:
                                return valid_intent
            except Exception:
                pass

        # Mặc định với câu hỏi chưa khớp rõ ràng trong khuôn khổ cổng thông tin
        return IntentEnum.REGULATION

