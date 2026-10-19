# End-of-Line QC & Defect Rate Tracker
### PT. Ardiva Clothing (Muslim Wear Division)

Sistem otomasi pencatatan, kalkulasi *defect rate*, dan penentuan status kelayakan batch garmen berbasis web interaktif (Streamlit) dengan pengujian otomatis dan pipeline CI/CD (GitHub Actions).

---

## Latar Belakang & Masalah Bisnis
Pada industri garmen (khususnya busana muslim seperti gamis, tunik, hijab, dan mukena), cacat produksi pada tahap akhir dapat menimbulkan kerugian material yang tinggi:
1. **Pewarnaan Sublimasi Permanen:** Cacat cetak atau jahit pada jersey sublimasi tidak bisa diperbaiki dan harus dibuang (*scrap*).
2. **Keterlambatan Keputusan QC:** Pencatatan kertas manual memperlambat isolasi batch bermasalah, sehingga pakaian cacat berisiko terkirim ke pelanggan.
3. **Standarisasi Keputusan:** Mencegah subjektivitas antar-operator inspeksi dengan aturan ambang batas (*threshold*) yang terotomasi dan teruji.

---

## ⚙️ Ambang Batas Kualitas (Quality Thresholds)

Sistem mengelompokkan hasil inspeksi ke dalam 3 status berdasarkan **Defect Rate (%)**:
$$\text{Defect Rate} = \left( \frac{\text{Total Cacat}}{\text{Total Pakaian Diperiksa}} \right) \times 100$$

| Defect Rate (%) | Status | Indikator | Rekomendasi Tindakan Operasional |
| :--- | :--- | :---: | :--- |
| **$\le$ 3.0%** | **LOLOS QC (PASS)** | 🟢 Hijau | Batch aman. Lanjutkan ke proses Packing & Gudang Barang Jadi. |
| **3.0% < Rate $\le$ 5.0%** | **PERINGATAN (WARNING)** | 🟠 Oranye | Perlu inspeksi ulang oleh Supervisor QC dan perbaikan (*rework*) pada pakaian cacat. |
| **> 5.0%** | **TAHAN BATCH (HOLD / REJECT)** | 🔴 Merah | **STOP pengiriman batch!** Kembalikan ke lini jahit dan evaluasi mesin/operator. |

---

## 📂 Struktur File Proyek

```text
Otomasi Data/
├── .github/
│   └── workflows/
│       └── ci_cd.yml        # Pipeline GitHub Actions (CI Quality Gate & CD Simulation)
├── qc_logic.py              # Logika bisnis inti (pure functions & data validation)
├── test_qc_logic.py         # Automated unit test menggunakan Pytest
├── app.py                   # Dashboard web interaktif berbasis Streamlit
├── requirements.txt         # Daftar pustaka Python (streamlit, pytest, pandas)
└── README.md                # Dokumentasi & panduan demo interview
```

---

## 🚀 Panduan Instalasi & Menjalankan Aplikasi

### 1. Prasyarat
- Python 3.10 atau versi lebih baru terpasang di sistem.

### 2. Instalasi Dependensi
Buka terminal / PowerShell di direktori proyek dan jalankan:
```bash
pip install -r requirements.txt
```

### 3. Menjalankan Unit Tests (CI Simulation)
Untuk menguji akurasi seluruh rumus dan validasi data:
```bash
pytest -v
```

### 4. Menjalankan Web Dashboard
Jalankan aplikasi Streamlit:
```bash
streamlit run app.py
```
Aplikasi akan otomatis terbuka di browser pada alamat: `http://localhost:8501`.

---

## 🔄 Alur Pipeline CI/CD (GitHub Actions)

Setiap ada perintah `git push` atau `pull request` ke branch `main`, GitHub Actions akan menjalankan 2 pekerjaan berurutan:
1. **`ci-quality-gate` (Continuous Integration):**
   - Menjalankan `python -m py_compile` untuk memastikan nol *syntax error*.
   - Menjalankan `pytest -v` untuk menguji semua logika perhitungan.
   - Jika ada test yang gagal, pipeline **langsung berhenti (MERAH)** untuk mencegah kode cacat dirilis ke pabrik.
2. **`cd-deployment-ready` (Continuous Delivery):**
   - Berjalan jika tahap CI lolos 100%.
   - Menyiapkan proses rilis otomatis ke server produksi / Streamlit Cloud.

---

## ⏱️ Panduan Skenario Demo 2 Menit Saat Interview

Gunakan skenario ini di depan manajer / tim penilai untuk menunjukkan pemahaman teknis dan *mindset* kualitas IT Manufaktur:

### Skenario 1: Demo Aplikasi di Lantai Produksi (1 Menit)
1. Buka browser pada `http://localhost:8501`.
2. **Kasus Lolos:** Pilih *Line 1 - Jersey & Sportswear*, isi total periksa `100`, cacat jahit `1`, noda `1`, ukuran `0` (Total cacat 2 pcs = 2.0%). Tunjukkan banner hijau **LOLOS QC (PASS)**.
3. Klik tombol **"Simpan Hasil Batch Ini ke Riwayat Harian"**. Tunjukkan tabel rekapitulasi di bawah otomatis terisi.
4. **Kasus Tahan Batch:** Ubah cacat jahit menjadi `5`, noda `2` (Total 7 pcs = 7.0%). Tunjukkan banner merah **TAHAN BATCH (HOLD)** dan rekomendasi penghentian pengiriman.
5. **Fitur Ekspor:** Klik **"Unduh Rekap Harian (CSV)"** untuk menunjukkan kemudahan integrasi data ke Excel manajemen.

### Skenario 2: Demo Kekuatan Robot CI/CD ("Pencegah Bug Masuk Pabrik") (1 Menit)
1. Buka terminal dan jalankan:
   ```bash
   pytest -v
   ```
   *Tunjukkan bahwa semua tes hijau (PASSED).*
2. Buka file `qc_logic.py`, lalu sengaja ubah salah satu batas, misalnya:
   ```python
   # Ubah sementara untuk simulasi:
   if defect_rate <= 1.0: # dari sebelumnya 3.0
   ```
3. Jalankan kembali di terminal:
   ```bash
   pytest -v
   ```
4. **Hasilnya GAGAL (FAILED / MERAH)!**
5. **Sampaikan ke Pewawancara:**
   > *"Dengan adanya pipeline CI/CD ini, jika seorang developer secara tidak sengaja mengubah batas toleransi atau salah menulis rumus, robot otomatis GitHub Actions akan menggagalkan deploy. Sistem pabrik terlindungi dari bug yang bisa meloloskan baju cacat ke konsumen."*
6. Kembalikan kode ke `3.0` dan jalankan `pytest -v` kembali hingga hijau.
