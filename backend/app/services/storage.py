import os
import uuid
from typing import Optional
from fastapi import UploadFile, HTTPException, status
from app.core.config import settings

UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "storage_uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

ALLOWED_EXTENSIONS = {".pdf", ".docx"}
MAX_FILE_SIZE = 25 * 1024 * 1024  # 25 MB

class StorageService:
    """
    Dịch vụ lưu trữ văn bản quy chế tuân thủ Secure Web Backend File Upload guidelines:
    - Kiểm tra định dạng tệp (allow-list: PDF, DOCX)
    - Giới hạn kích thước tệp
    - Đổi tên tệp thành UUID ngẫu nhiên để chống Path Traversal và ghi đè
    - Lưu trữ bên ngoài web root
    """

    @classmethod
    async def upload_file(cls, file: UploadFile) -> str:
        # 1. Kiểm tra phần mở rộng
        original_name = file.filename or "unknown.pdf"
        ext = os.path.splitext(original_name)[1].lower()
        if ext not in ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Định dạng tệp không được hỗ trợ. Chỉ chấp nhận các tệp: {', '.join(ALLOWED_EXTENSIONS)}"
            )

        # 2. Đọc nội dung và kiểm tra kích thước
        content = await file.read()
        if len(content) > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Kích thước tệp vượt quá giới hạn tối đa ({MAX_FILE_SIZE // (1024 * 1024)}MB)."
            )

        # 3. Đổi tên tệp thành UUID an toàn
        safe_filename = f"{uuid.uuid4().hex}{ext}"
        destination_path = os.path.join(UPLOAD_DIR, safe_filename)

        with open(destination_path, "wb") as f:
            f.write(content)

        # Trả về đường dẫn truy cập tệp
        file_url = f"/api/v1/storage/{safe_filename}"
        return file_url

    @classmethod
    def get_file_bytes(cls, file_url: str) -> bytes:
        filename = os.path.basename(file_url)
        path = os.path.join(UPLOAD_DIR, filename)
        if not os.path.exists(path):
            raise FileNotFoundError(f"Không tìm thấy tệp: {filename}")
        with open(path, "rb") as f:
            return f.read()

