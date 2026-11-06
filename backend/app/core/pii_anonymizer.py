import re

class PIIAnonymizer:
    """
    Tuân thủ tuyệt đối quy tắc nghiệp vụ BR08:
    Ẩn danh hóa thông tin định danh cá nhân (PII):
    - Mã số sinh viên (chuỗi 7–10 chữ số)
    - Địa chỉ email
    - Số điện thoại (chuẩn Việt Nam & quốc tế)
    - Họ và tên đi kèm từ khóa ngữ cảnh (ví dụ: 'em tên là', 'tôi tên là', 'sinh viên:', v.v.)
    """

    # Regex nhận diện email
    EMAIL_PATTERN = re.compile(
        r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b',
        re.IGNORECASE
    )

    # Regex nhận diện số điện thoại Việt Nam (10-11 số, có thể bắt đầu bằng +84 hoặc 0)
    PHONE_PATTERN = re.compile(
        r'(?:\+84|0)(?:[.\-\s]?\d){9,10}\b'
    )

    # Regex nhận diện MSSV (chuỗi 7-10 chữ số)
    # Có thể đứng sau các từ khóa như 'mssv', 'mã sinh viên', 'sv', hoặc đứng độc lập
    STUDENT_ID_CONTEXT_PATTERN = re.compile(
        r'(?i)(?:mssv|mã\s+sinh\s+viên|mã\s+sv|sv|ms)\s*[:=\-]?\s*([0-9]{7,10})\b'
    )
    STUDENT_ID_STANDALONE_PATTERN = re.compile(
        r'\b\d{7,10}\b'
    )

    # Regex nhận diện họ tên đi kèm từ khóa ngữ cảnh tiếng Việt
    NAME_PATTERNS = [
        re.compile(r'(?i)(?:em\s+tên\s+là|tôi\s+tên\s+là|mình\s+tên\s+là|tên\s+em\s+là|tên\s+tôi\s+là)\s+([A-ZÀ-Ỹa-zà-ỹ\s]{2,30})(?=[,\.\?!]|\s+mssv|\s+học|\s+lớp|$)', re.UNICODE),
        re.compile(r'(?i)(?:sinh\s+viên|sv)\s*[:\-]\s*([A-ZÀ-Ỹa-zà-ỹ\s]{2,30})(?=[,\.\?!]|\s+mssv|\s+học|\s+lớp|$)', re.UNICODE),
    ]

    @classmethod
    def anonymize(cls, text: str) -> str:
        if not text:
            return ""

        result = text

        # 1. Ẩn danh Email
        result = cls.EMAIL_PATTERN.sub("[EMAIL]", result)

        # 2. Ẩn danh Số điện thoại
        result = cls.PHONE_PATTERN.sub("[PHONE]", result)

        # 3. Ẩn danh Họ và tên theo ngữ cảnh
        for pattern in cls.NAME_PATTERNS:
            def replace_name(match):
                full_matched = match.group(0)
                name_part = match.group(1).strip()
                return full_matched.replace(name_part, "[NAME]")
            result = pattern.sub(replace_name, result)

        # 4. Ẩn danh MSSV có tiền tố
        def replace_mssv(match):
            full_match = match.group(0)
            mssv_digits = match.group(1)
            return full_match.replace(mssv_digits, "[STUDENT_ID]")
        result = cls.STUDENT_ID_CONTEXT_PATTERN.sub(replace_mssv, result)

        # 5. Ẩn danh các chuỗi 7-10 chữ số độc lập còn lại (thường là MSSV)
        result = cls.STUDENT_ID_STANDALONE_PATTERN.sub("[STUDENT_ID]", result)

        return result

# Tiện ích gọi nhanh
def anonymize_text(text: str) -> str:
    return PIIAnonymizer.anonymize(text)

