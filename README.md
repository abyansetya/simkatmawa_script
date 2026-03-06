# SIMKATMAWA - Upload Sertifikasi Otomatis

Script Python untuk mengupload data sertifikasi dari file CSV ke API SIMKATMAWA secara otomatis.

## Fitur

- ✅ Login otomatis ke API SIMKATMAWA
- ✅ Membaca data dari file CSV
- ✅ Mengelompokkan mahasiswa & dosen per sertifikasi secara otomatis
- ✅ Upload batch dengan retry otomatis jika gagal
- ✅ Mode **dry-run** untuk validasi data sebelum upload
- ✅ Logging lengkap ke file dan console
- ✅ Hasil upload tersimpan dalam file JSON

## Struktur File

```
sertifikasi_runner/
├── upload_sertifikasi.py      # Script utama
├── config.ini                 # Konfigurasi API & kredensial
├── sample_sertifikasi.csv     # Contoh file CSV
├── README.md                  # Dokumentasi ini
└── logs/                      # Folder log (otomatis dibuat)
    ├── upload_YYYYMMDD_HHMMSS.log
    └── result_YYYYMMDD_HHMMSS.json
```

## Instalasi

```bash
pip install requests
```

## Konfigurasi

Edit file `config.ini` dan isi dengan kredensial API:

```ini
[credentials]
email = email_anda@univ.ac.id
password = password_anda
```

## Format CSV

| Kolom                  | Keterangan                      | Wajib |
| ---------------------- | ------------------------------- | ----- |
| `level`                | Level sertifikasi (NAS/INT)     | ✅    |
| `nama`                 | Nama sertifikasi                | ✅    |
| `penyelenggara`        | Nama penyelenggara              | ✅    |
| `url_peserta`          | URL peserta                     | ✅    |
| `url_sertifikat`       | URL sertifikat                  | ✅    |
| `tgl_sertifikat`       | Tanggal sertifikat (YYYY-MM-DD) | ✅    |
| `url_foto_upp`         | URL foto UPP                    | ✅    |
| `url_dokumen_undangan` | URL dokumen undangan            | ✅    |
| `keterangan`           | Catatan/keterangan              | ✅    |
| `nim`                  | NIM mahasiswa                   | ✅    |
| `nama_mahasiswa`       | Nama mahasiswa                  | ✅    |
| `nuptk_dosen`          | NUPTK dosen pembimbing          | ❌    |
| `nama_dosen`           | Nama dosen pembimbing           | ❌    |
| `url_surat_tugas`      | URL surat tugas dosen           | ❌    |

> **Catatan:** Baris dengan `level`, `nama`, `penyelenggara`, dan `tgl_sertifikat` yang sama akan otomatis dikelompokkan menjadi satu sertifikasi dengan banyak mahasiswa.

## Cara Pakai

### 1. Dry-run (validasi tanpa upload)

```bash
python upload_sertifikasi.py sample_sertifikasi.csv --dry-run
```

### 2. Upload ke API

```bash
python upload_sertifikasi.py data_sertifikasi.csv
```

### 3. Custom config file

```bash
python upload_sertifikasi.py data.csv --config config_prod.ini
```
