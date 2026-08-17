#!/usr/bin/env bash
# ============================================
#  SiteGazer - Setup (Linux/macOS)
#  Jalankan SEKALI setelah clone:
#    chmod +x setup.sh && ./setup.sh
#  Lalu jalankan aplikasi:
#    python app.py
#
#  Catatan: kontrol drone (keyboard/gamepad)
#  hanya berfungsi di Windows. Di Linux gunakan
#  mode "e99" (video saja + remote fisik).
# ============================================
set -e
python3 -m venv venv
source venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
echo
echo "============================================"
echo " Setup selesai. Jalankan: python app.py"
echo " Buka browser: http://localhost:8000"
echo "============================================"