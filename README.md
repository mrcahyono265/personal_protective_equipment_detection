# SiteGazer - Drone Safety Monitoring System

---

## 📖 Overview

SiteGazer adalah sistem pemantauan keselamatan kerja (K3) berbasis kecerdasan buatan (AI) yang dirancang untuk mendeteksi penggunaan Alat Pelindung Diri (APD) secara *real-time*. Menggunakan arsitektur model YOLOv11 yang ringan (Nano) dan *backend* FastAPI, sistem ini dapat menganalisis aliran video dari kamera pengawas (CCTV), *webcam*, atau *drone* untuk mengidentifikasi pekerja yang tidak mematuhi standar keselamatan, seperti tidak menggunakan helm, rompi, atau sarung tangan.

---

## 🎯 Objectives

- **Otomatisasi Pengawasan K3:** Menggantikan pemantauan manual dengan deteksi AI yang terus berjalan (*continuous monitoring*) untuk mengidentifikasi kepatuhan APD.
- **Dokumentasi Pelanggaran:** Mengambil dan menyimpan tangkapan layar (*snapshot*) secara otomatis ketika terjadi pelanggaran K3 sebagai bukti audit.
- **Manajemen Berbasis Zona:** Memungkinkan operator keamanan untuk melacak area spesifik (seperti *Lobby*, *Warehouse*, atau *Site*) di mana pelanggaran terjadi.
- **Performa Real-Time:** Menghadirkan antarmuka *streaming* video tanpa *delay* (*buffer-less*) menggunakan pemrosesan *asynchronous* FastAPI.

---

## 🛠️ Tech Stack

- **Deep Learning Framework:** PyTorch + Ultralytics
- **Object Detection Model:** YOLOv11n (Ultralytics)
- **Backend API:** FastAPI & Uvicorn
- **Computer Vision:** OpenCV (`cv2`)
- **Frontend Dashboard:** HTML5, CSS3, Vanilla JavaScript, FontAwesome

---

## ✨ Key Features

- **Single Model PPE Detection:** Model AI terlatih (YOLOv11n) yang mampu mengenali kelas APD (helm, rompi) beserta negatifnya (No-Helmet, No-Vest).
- **Buffer-less Video Streaming:** Kelas `VideoCamera` khusus menggunakan *threading* untuk membaca *frame* terakhir dari kamera, memastikan aliran video *real-time* tanpa penumpukan *delay* (*lag*).
- **Automated Violation Snapshot:** Sistem hanya mengklasifikasikan "Pelanggaran" jika mendeteksi ketiadaan APD (seperti *No-Helmet*), lalu otomatis menyimpan gambar kejadian beserta label waktu dan zonanya ke `static/snapshots/`.
- **Multi-Camera & Drone Support:** Tiga sumber kamera — `webcam` (kamera lokal/IP), `tello` (DJI Tello, kontrol penuh), dan `e99` (E88 Pro/E99, pasif) — dipilih via konfigurasi.
- **Interactive Security Log:** Panel *log* keamanan *real-time* di sisi antarmuka yang menampilkan riwayat kejadian, statistik peringatan kritis, dan jumlah tangkapan layar, lengkap dengan modal untuk melihat gambar *full-size*.

---

## 📁 Project Structure

```bash
├── app.py                    # Entry point (shim: menambahkan src/ ke path, memanggil sitegazer.api.main)
├── src/sitegazer/            # Paket utama
│   ├── api.py                # FastAPI: lifespan, streaming, endpoint (termasuk /current_zone)
│   ├── config.py             # Semua konstanta (kamera, model, drone) + override env var
│   ├── camera.py             # VideoCamera (buffer-less) & DroneCamera (adapter)
│   ├── detection.py          # Klasifikasi APD, snapshot bukti, proses frame
│   ├── controller.py         # Thread kontrol drone (keyboard + gamepad)
│   └── drone/                # tello_drone (Tello), e99_drone (E88 Pro/E99),
│                             # input_handler (Windows), video_handler (HUD & rekaman)
├── static/                   # Aset frontend
│   ├── css/style.css         # Semua styling dashboard
│   ├── js/app.js             # Semua logika frontend
│   └── snapshots/            # Bukti pelanggaran (auto-generated, di-ignore git)
├── templates/index.html      # Markup dashboard (HTML murni)
├── models/                   # Bobot model (di-ignore git, lihat models/README.md)
├── tests/                    # Self-check (tanpa framework): config, detection
├── captures/                 # Foto & rekaman drone (auto-generated)
├── runs/                     # Log hasil validasi Ultralytics
├── yolo11_ppe/               # Log training & metrik (train_v1)
├── setup.bat / setup.sh      # Setup satu kali (venv + install dependensi)
├── requirements.txt          # Dependensi Python
├── model_metadata.json       # Metadata informasi model hasil training
└── train.ipynb               # Jupyter notebook untuk training, evaluasi, dan ekspor model
```

---

## 🚀 Installation & Setup

### 0. Requirements

Pastikan sistem Anda telah menginstal perangkat lunak berikut:

- Python (versi 3.10 - 3.13)
- Kamera (Webcam internal atau aplikasi kamera IP seperti DroidCam)
- (Opsional) GPU NVIDIA dengan arsitektur CUDA (untuk performa inferensi yang maksimal)

### 1. Clone Repository & Setup Environment

```bash
git clone https://github.com/mrcahyono265/personal_protective_equipment_detection.git
cd personal_protective_equipment_detection

# Setup satu kali: buat venv + install dependensi
./setup.sh        # Linux/Mac
setup.bat         # Windows
```

Atau manual: `python -m venv venv`, aktifkan venv, lalu `pip install -r requirements.txt`.

### 2. Menjalankan Dashboard Deteksi (Inference)

Taruh model `best_ppe_yolo11n.pt` di folder `models/` (lihat `models/README.md`), lalu:

```bash
python app.py
```

Akses dashboard pemantauan melalui browser di tautan: `http://localhost:8000/`

### 3. Konfigurasi

Semua pengaturan ada di `src/sitegazer/config.py` (ubah langsung), atau override lewat environment variable tanpa menyentuh kode:

```bash
SITEGAZER_CAMERA=e99 python app.py        # pilih sumber kamera: webcam | tello | e99
SITEGAZER_CAMERA_SOURCE=0 python app.py   # hanya untuk webcam (0 atau URL IP camera)
SITEGAZER_MODEL=models/best_ppe_yolo11n.pt
SITEGAZER_PORT=8000
```

### 4. Testing

```bash
python tests/test_config.py      # > all ok
python tests/test_detection.py   # > all ok
```

---

## 🚁 Mode Drone DJI Tello

Sistem mendukung **DJI Tello** sebagai sumber kamera sekaligus dapat dikontrol penuh (keyboard fisik + gamepad XInput, Windows) selama patroli. Deteksi APD berjalan pada video feed drone dan HUD drone (baterai, status terbang, trim, speed, REC) digambar langsung di frame yang tampil di dashboard.

### Setup

1. Sambungkan Wi-Fi ke **Tello-XXXXXX** (internet akan mati selama terhubung — normal).
2. Ubah konstanta `CAMERA_TYPE` di `src/sitegazer/config.py` (atau set env var):

```python
CAMERA_TYPE = "tello"   # "webcam" | "tello" | "e99"
```

3. Jalankan seperti biasa: `python app.py`

> `CAMERA_TYPE = "webcam"` (default) mempertahankan perilaku lama tanpa menyentuh drone sama sekali.

### Keyboard Controls (fokus jendela/terminal server)

| Tombol | Aksi |
|--------|------|
| W / A / S / D | Maju / Kiri / Mundur / Kanan |
| Arrow Up / Down | Naik / Turun |
| Arrow Left / Right | Yaw kiri / Yaw kanan |
| **Space** | Takeoff / Land |
| **Q** | Ambil foto (frame hasil deteksi APD) |
| **E** | Mulai / Hentikan rekaman video |
| **C** / **X** | Speed naik / turun (30/50/70/100%) |
| **[** / **]** | Trim roll kiri / kanan |
| **Tab** | Reset trim |
| **G** | Tampilkan / sembunyikan grid rule of thirds |
| **R** | Switch mode keyboard / gamepad |
| **F** | Emergency land |

### Gamepad Controls (XInput)

| Input | Aksi |
|-------|------|
| Left stick | Yaw + Naik/Turun |
| Right stick | Maju/Mundur/Kiri/Kanan |
| **START** (< 0.8s) | Takeoff / Land |
| **START** (>= 0.8s) | Emergency land |
| **A** | Ambil foto |
| **B** | Mulai / Hentikan rekaman video |
| **LB** / **RB** | Speed turun / naik |
| **BACK** | Reset trim |
| **D-Pad** kiri/kanan | Trim roll kiri / kanan |

### Safety

- **Auto-land otomatis** saat baterai <= 10% (indikator kuning "LOW BATTERY" saat <= 20%).
- Foto & rekaman disimpan di `captures/photos` dan `captures/videos` (frame hasil deteksi APD + HUD).

### Troubleshooting Drone

- **av DLL diblokir Windows Security**: pin `av<18` sudah ada di `requirements.txt`. Jika tetap diblokir, tambahkan pengecualian di Windows Security.
- **Gagal konek ke Tello**: pastikan Wi-Fi terhubung ke Tello, matikan firewall/antivirus sementara.
- **Video pixelated / lag 2-3 detik setelah takeoff**: batasan firmware Tello standard, bukan error.
- **Kontrol keyboard tidak merespons**: pastikan fokus ada di mesin server (keyboard fisik), bukan di browser di perangkat lain.

---

## 📷 Mode Drone E88 Pro / E99 (Pasif)

Mendukung drone murah keluarga **E88 Pro / E99** sebagai sumber kamera. Mode ini **pasif**: kontrol terbang tetap memakai **remote fisik bawaan drone**, program hanya menangani **video + deteksi APD + foto (Q) + rekaman (E)**.

### Setup

1. Sambungkan Wi-Fi ke **drone (192.168.1.1)** — remote fisik tetap bisa terbang karena RF, tidak konflik dengan Wi-Fi.
2. Ubah konstanta `CAMERA_TYPE` di `src/sitegazer/config.py` (atau set env var `SITEGAZER_CAMERA=e99`).
3. Jalankan: `python app.py`

### Karakteristik Mode E99

- Video RTSP (`rtsp://192.168.1.1:7070/webcam`) dibaca via OpenCV, dirotasi 90° CW (sesuai orientasi kamera drone; matikan via `ROTATE = False` di `src/sitegazer/drone/e99_drone.py`).
- **Tanpa telemetri**: HUD menampilkan `BAT --`, `ALT --`, `TM --`; **auto-land baterai tidak berlaku** (tidak ada API baterai).
- Tombol **Q** (foto) & **E** (rekam) aktif dari keyboard mesin server; tombol kontrol terbang (Space/WASD dll.) tidak berlaku.
- Deteksi APD, log pelanggaran, snapshot, dan zona berfungsi sama seperti mode lain.

---

## 🏋️ Training a New Model (Optional)

Jika Anda ingin melatih ulang model dengan dataset baru menggunakan `train.ipynb`:

1. Buka Jupyter Notebook atau VS Code.
2. Siapkan dataset format YOLOv11 di lokal atau unduh langsung dari Roboflow menggunakan API Key Anda.
3. Jalankan semua cell pada `train.ipynb`. Konfigurasi awal dirancang secara optimal untuk GPU berkapasitas VRAM 4GB (seperti RTX 2050), menggunakan Automatic Mixed Precision (AMP) dan ukuran batch 16.
4. Hasil training (best.pt dan format onnx) akan disimpan secara otomatis di dalam folder `yolo11_ppe/train_v1/weights/``.

---

## 🧑‍💻 Author

Mohammad Ridho Cahyono

Full Stack Developer | Leadership Experience in Technology & Innovation

Developing Digital Solutions Through Web Development, Machine Learning, and IoT to Help Businesses and Organizations Grow.