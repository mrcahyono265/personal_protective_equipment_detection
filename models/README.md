# Models

Model weights TIDAK di-commit ke repository (di-ignore via `.gitignore`).

## Cara pakai

1. Taruh file model di folder ini:
   - `best_ppe_yolo11n.pt` — model YOLO11n hasil training (default)
   - `yolo11n.pt` — weight pretrained dasar (opsional, untuk fine-tune ulang)
2. Jalankan aplikasi seperti biasa. Default path model di
   `src/sitegazer/config.py` (`MODEL_PATH`), bisa di-override:

   ```bash
   SITEGAZER_MODEL=models/yolo11n.pt python app.py
   ```

## Referensi

- Training & metadata: `train.ipynb`, `model_metadata.json`, `runs/` (chart validasi).
- Class yang dikenali (sesuai `model_metadata.json`): hard_hat, safety_vest,
  no_safety_helmet, no_safety_vest (contoh — cek `data.yaml` hasil training).