# app.py - Entry point SiteGazer
# Tambahkan folder src/ ke path Python agar paket "sitegazer" bisa diimport.
# Semua logika ada di src/sitegazer/ (lihat README.md untuk struktur).
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "src"))

from sitegazer.api import main

if __name__ == "__main__":
    main()