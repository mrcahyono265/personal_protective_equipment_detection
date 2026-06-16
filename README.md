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

- **Deep Learning Framework:** PyTorch 2.9.1
- **Object Detection Model:** YOLOv11 (Ultralytics)
- **Backend API:** FastAPI & Uvicorn
- **Computer Vision:** OpenCV (`cv2`)
- **Frontend Dashboard:** HTML5, CSS3, Vanilla JavaScript, FontAwesome

---

## ✨ Key Features

- **Single Model PPE Detection:** Model AI terlatih yang mampu mengenali 6 kelas secara akurat (Gloves, Helmet, Vest, No-gloves, No-Helmet, No-vest).
- **Buffer-less Video Streaming:** Kelas `VideoCamera` khusus menggunakan *threading* untuk membaca *frame* terakhir dari kamera, memastikan aliran video *real-time* tanpa penumpukan *delay* (*lag*).
- **Automated Violation Snapshot:** Sistem memiliki logika prapemrosesan yang hanya mengklasifikasikan "Pelanggaran" jika mendeteksi ketiadaan APD (seperti *No-Helmet*). Sistem kemudian otomatis menyimpan gambar kejadian beserta label waktu dan zonanya.
- **Dynamic Camera Configuration:** Pengguna dapat mengganti sumber video secara langsung dari antarmuka *dashboard* (misalnya dari *webcam* lokal '0' ke IP Camera DroidCam).
- **Interactive Security Log:** Panel *log* keamanan *real-time* di sisi antarmuka yang menampilkan riwayat kejadian, statistik peringatan kritis, dan jumlah tangkapan layar, lengkap dengan modal untuk melihat gambar *full-size*.

---

## 📁 Project Structure

```bash
├── templates/
│   ├── index.html            # Frontend Dashboard K3
│   └── snapshots/            # Direktori penyimpanan otomatis bukti pelanggaran
├── runs/                     # Log hasil validasi Ultralytics
├── yolo11_ppe/               # Direktori penyimpanan model, log training, dan metrik (train_v1)
├── app.py                    # Script Backend utama FastAPI
├── best_ppe_yolo11n.pt       # Bobot model terbaik YOLOv11 untuk deteksi APD
├── yolo11n.pt                # Pre-trained weights awal YOLOv11
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

# Membuat dan mengaktifkan virtual environment
python -m venv venv
source venv/bin/activate  # Untuk Linux/Mac
venv\Scripts\activate     # Untuk Windows
```

### 2. Instalasi Dependensi

```bash
# Gunakan list requirement di atas atau install secara manual
pip install ultralytics fastapi uvicorn opencv-python pydantic
```

### 3. Menjalankan Dashboard Deteksi (Inference)

Pastikan model best_ppe_yolo11n.pt berada di root directory, lalu jalankan server FastAPI:

```bash
python app.py
```

Akses dashboard pemantauan melalui browser di tautan: `http://localhost:8000/`

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