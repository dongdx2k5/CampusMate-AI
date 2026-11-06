import re
import os
import io
from dataclasses import dataclass, asdict
from typing import List, Optional, Dict, Any

try:
    import fitz  # PyMuPDF
except ImportError:
    fitz = None

try:
    from docx import Document as DocxDocument
except ImportError:
    DocxDocument = None


@dataclass
class LegalChunk:
    version_id: str
    chapter: Optional[str]
    article: Optional[str]
    clause: Optional[str]
    page: int
    text: str
    is_active: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def __getitem__(self, item: str):
        return getattr(self, item)

    def get(self, item: str, default: Any = None):
        return getattr(self, item, default)

    def copy(self) -> Dict[str, Any]:
        return self.to_dict()


class VietnameseLegalChunker:
    """
    Bộ cắt đoạn văn bản quy chế đại học tiếng Việt.
    Hỗ trợ 2 chế độ để chạy thực nghiệm E1:
      1. legal_hierarchy: Cắt theo cấu trúc Chương -> Điều -> Khoản (kèm sliding window nếu Khoản quá dài).
      2. fixed_overlap: Cắt theo độ dài từ cố định có chồng lấn (Baseline cho thí nghiệm E1).
    """

    # Biểu thức chính quy nhận diện cấu trúc văn bản pháp quy tiếng Việt
    PAGE_PATTERN = re.compile(r"^\[Trang\s+(\d+)\]", re.IGNORECASE)
    CHAPTER_PATTERN = re.compile(
        r"^(Chương\s+[IVXLCDM\d]+)\s*[\:\.\-]?\s*(.*)$", re.IGNORECASE
    )
    ARTICLE_PATTERN = re.compile(
        r"^Điều\s+(\d+)\s*[\.\:\-]?\s*(.*)$", re.IGNORECASE
    )
    CLAUSE_PATTERN = re.compile(r"^(\d+)\.\s+(.*)$")

    def __init__(self, max_words: int = 380, overlap_words: int = 50):
        # 380 từ tiếng Việt tương đương ~512 subword tokens của BGE-M3
        self.max_words = max_words
        self.overlap_words = overlap_words

    def chunk_by_legal_structure(
        self, raw_text: str, version_id: str, is_active: bool = True
    ) -> List[LegalChunk]:
        chunks: List[LegalChunk] = []

        current_page = 1
        current_chapter: Optional[str] = None
        current_article_no: Optional[str] = None
        current_article_title: str = ""
        current_clause_no: Optional[str] = None
        buffer_lines: List[str] = []

        def flush_buffer():
            nonlocal buffer_lines
            if not buffer_lines or not current_article_no:
                buffer_lines = []
                return

            body_text = "\n".join(buffer_lines).strip()
            if not body_text:
                buffer_lines = []
                return

            # Tạo header ngữ cảnh để mọi chunk đều mang tên Chương & tiêu đề Điều
            header_parts = []
            if current_chapter:
                header_parts.append(current_chapter)
            article_header = f"Điều {current_article_no}"
            if current_article_title:
                article_header += f". {current_article_title}"
            header_parts.append(article_header)

            context_prefix = " | ".join(header_parts)
            clause_label = f"Khoản {current_clause_no}" if current_clause_no else "Toàn điều"

            # Kiểm tra độ dài, nếu vượt quá max_words thì cắt trượt có chồng lấn nhưng giữ nguyên metadata
            words = body_text.split()
            if len(words) <= self.max_words:
                full_text = f"[{context_prefix} - {clause_label}]\n{body_text}"
                chunks.append(
                    LegalChunk(
                        version_id=version_id,
                        chapter=current_chapter,
                        article=f"Điều {current_article_no}",
                        clause=clause_label,
                        page=current_page,
                        text=full_text,
                        is_active=is_active,
                    )
                )
            else:
                step = max(1, self.max_words - self.overlap_words)
                for idx in range(0, len(words), step):
                    sub_words = words[idx : idx + self.max_words]
                    if len(sub_words) < self.overlap_words and idx > 0:
                        break
                    sub_text = " ".join(sub_words)
                    full_text = f"[{context_prefix} - {clause_label}]\n{sub_text}"
                    chunks.append(
                        LegalChunk(
                            version_id=version_id,
                            chapter=current_chapter,
                            article=f"Điều {current_article_no}",
                            clause=clause_label,
                            page=current_page,
                            text=full_text,
                            is_active=is_active,
                        )
                    )
            buffer_lines = []

        for raw_line in raw_text.splitlines():
            line = raw_line.strip()
            if not line or line.startswith("---") or line.startswith("==="):
                continue

            # 1. Cập nhật số trang
            page_match = self.PAGE_PATTERN.match(line)
            if page_match:
                flush_buffer()
                current_page = int(page_match.group(1))
                continue

            # 2. Nhận diện Chương
            chapter_match = self.CHAPTER_PATTERN.match(line)
            if chapter_match:
                flush_buffer()
                chap_num = chapter_match.group(1).strip()
                chap_title = chapter_match.group(2).strip()
                current_chapter = f"{chap_num}: {chap_title}" if chap_title else chap_num
                current_article_no = None
                current_clause_no = None
                continue

            # 3. Nhận diện Điều
            article_match = self.ARTICLE_PATTERN.match(line)
            if article_match:
                flush_buffer()
                current_article_no = article_match.group(1).strip()
                current_article_title = article_match.group(2).strip()
                current_clause_no = None
                continue

            # 4. Nhận diện Khoản (1., 2., 3. ở đầu dòng)
            clause_match = self.CLAUSE_PATTERN.match(line)
            if clause_match and current_article_no is not None:
                flush_buffer()
                current_clause_no = clause_match.group(1).strip()
                buffer_lines.append(f"{current_clause_no}. {clause_match.group(2).strip()}")
                continue

            # 5. Các điểm a), b), c) hoặc nội dung tiếp nối thuộc Khoản hiện tại
            if current_article_no is not None:
                buffer_lines.append(line)

        flush_buffer()
        return chunks

    def chunk_by_fixed_size(
        self, raw_text: str, version_id: str, is_active: bool = True
    ) -> List[LegalChunk]:
        """Phương pháp cắt cố định có chồng lấn dùng làm mốc so sánh cho thí nghiệm E1."""
        words = raw_text.split()
        chunks: List[LegalChunk] = []
        step = max(1, self.max_words - self.overlap_words)

        for idx in range(0, len(words), step):
            sub_words = words[idx : idx + self.max_words]
            if not sub_words:
                break
            chunk_text = " ".join(sub_words)
            # Cố gắng bắt số Điều gần nhất trong đoạn cắt để điền metadata cơ bản
            art_match = re.search(r"Điều\s+(\d+)", chunk_text)
            clause_match = re.search(r"(?:^|\n|\s)(\d+)\.\s+", chunk_text)
            chunks.append(
                LegalChunk(
                    version_id=version_id,
                    chapter=None,
                    article=f"Điều {art_match.group(1)}" if art_match else None,
                    clause=f"Khoản {clause_match.group(1)}" if clause_match else None,
                    page=1,
                    text=chunk_text,
                    is_active=is_active,
                )
            )
        return chunks

    @classmethod
    def chunk_document(
        cls,
        pages_content: List[Dict[str, Any]],
        version_id: str = "default",
        is_active: bool = True,
    ) -> List[LegalChunk]:
        """
        Hàm cầu nối cho indexing task và run_seed: nhận pages_content dạng [{'page': 1, 'text': '...'}]
        """
        full_text_parts = []
        for p in pages_content:
            pg = p.get("page", 1)
            txt = p.get("text", "")
            full_text_parts.append(f"[Trang {pg}]\n{txt}")
        combined = "\n\n".join(full_text_parts)
        chunker = cls()
        return chunker.chunk_by_legal_structure(combined, version_id=version_id, is_active=is_active)

    @staticmethod
    def extract_text_from_pdf(file_bytes: bytes) -> List[Dict[str, Any]]:
        """Trích xuất văn bản và số trang từ PDF."""
        pages_content = []
        if fitz is None:
            return [{"page": 1, "text": file_bytes.decode("utf-8", errors="ignore")}]
        doc = fitz.open(stream=file_bytes, filetype="pdf")
        for page_num in range(len(doc)):
            page = doc[page_num]
            text = page.get_text("text").strip()
            pages_content.append({"page": page_num + 1, "text": text})
        return pages_content

    @staticmethod
    def extract_text_from_docx(file_bytes: bytes) -> List[Dict[str, Any]]:
        """Trích xuất văn bản từ tệp DOCX."""
        if DocxDocument is None:
            return [{"page": 1, "text": file_bytes.decode("utf-8", errors="ignore")}]
        doc = DocxDocument(io.BytesIO(file_bytes))
        full_text = [para.text.strip() for para in doc.paragraphs if para.text.strip()]
        return [{"page": 1, "text": "\n".join(full_text)}]


# Compatibility alias
LegalChunker = VietnameseLegalChunker
