@echo off
REM ============================================
REM  SiteGazer - Setup (Windows)
REM  Jalankan SEKALI setelah clone/download:
REM    setup.bat
REM  Lalu jalankan aplikasi:
REM    python app.py
REM ============================================
python -m venv venv
call venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r requirements.txt
echo.
echo ============================================
echo  Setup selesai. Jalankan: python app.py
echo  Buka browser: http://localhost:8000
echo ============================================
pause