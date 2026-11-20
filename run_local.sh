#!/usr/bin/env bash
set -e
echo "================================================================"
echo " KHỞI CHẠY HỆ THỐNG TRỢ LÝ HỌC VỤ AI & KIOSK SẢNH SINH VIÊN HUCE"
echo "================================================================"
python3 tests/test_all_features.py
echo ""
echo ">>> Tất cả kịch bản kiểm thử tự động đã PASS 100%!"
echo ">>> QUAN TRỌNG: Hãy mở trình duyệt tại http://localhost:8000 (KHÔNG dùng địa chỉ IP 0.0.0.0 để trình duyệt cho phép bật Camera WebRTC!)"
python3 -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
