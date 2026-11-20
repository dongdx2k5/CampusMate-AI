@echo off
echo ================================================================
echo  KHOI CHAY HE THONG TRO LY HOC VU AI VA KIOSK SANH SINH VIEN HUCE
echo ================================================================
python tests/test_all_features.py
echo.
echo [QUAN TRONG] Trinh duyet se tu dong mo tai: http://localhost:8000
echo (Luu y: Luon truy cap qua localhost hoac 127.0.0.1 de trinh duyet cho phep bat Webcam!)
start http://localhost:8000
python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
