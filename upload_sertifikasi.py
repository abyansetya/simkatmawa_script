"""
============================================================
  SIMKATMAWA - Automation Upload Sertifikasi dari CSV
============================================================
  Script ini membaca data sertifikasi dari file CSV,
  mengelompokkan mahasiswa & dosen per sertifikasi,
  lalu mengupload ke API SIMKATMAWA secara otomatis.
============================================================
"""

import csv
import json
import time
import logging
import argparse
import configparser
import sys
from datetime import datetime
from pathlib import Path

try:
    import requests
except ImportError:
    print("=" * 60)
    print("ERROR: Module 'requests' belum terinstall.")
    print("Jalankan: pip install requests")
    print("=" * 60)
    sys.exit(1)


# ─── Setup Logging ────────────────────────────────────────
LOG_DIR = Path(__file__).parent / "logs"
LOG_DIR.mkdir(exist_ok=True)

log_filename = LOG_DIR / f"upload_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(log_filename, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger(__name__)


# ─── Load Config ──────────────────────────────────────────
def load_config(config_path: str = "config.ini") -> configparser.ConfigParser:
    """Membaca konfigurasi dari file .ini"""
    config = configparser.ConfigParser()
    config_file = Path(__file__).parent / config_path
    if not config_file.exists():
        logger.error(f"File konfigurasi '{config_file}' tidak ditemukan!")
        sys.exit(1)
    config.read(config_file, encoding="utf-8")
    return config


# ─── Login ────────────────────────────────────────────────
def login(config: configparser.ConfigParser) -> str:
    """
    Login ke API SIMKATMAWA dan mengembalikan access token.
    """
    base_url = config.get("api", "base_url")
    login_endpoint = config.get("api", "login_endpoint")
    email = config.get("credentials", "email")
    password = config.get("credentials", "password")
    timeout = config.getint("settings", "timeout", fallback=30)

    url = f"{base_url}{login_endpoint}"

    logger.info("=" * 50)
    logger.info("🔐 Memulai proses login...")
    logger.info(f"   URL  : {url}")
    logger.info(f"   Email: {email}")

    payload = {"email": email, "password": password}

    try:
        response = requests.post(url, json=payload, timeout=timeout)
        response.raise_for_status()
        data = response.json()

        if data.get("success"):
            token = data.get("token")
            kode_pt = data.get("kode_pt")
            logger.info(f"✅ Login berhasil! Kode PT: {kode_pt}")
            logger.info(f"   Token: {token[:30]}...")
            return token
        else:
            logger.error(f"❌ Login gagal! Response: {json.dumps(data, indent=2)}")
            sys.exit(1)

    except requests.exceptions.ConnectionError:
        logger.error("❌ Tidak dapat terhubung ke server. Periksa koneksi internet.")
        sys.exit(1)
    except requests.exceptions.Timeout:
        logger.error("❌ Request timeout. Server tidak merespon.")
        sys.exit(1)
    except requests.exceptions.HTTPError as e:
        logger.error(f"❌ HTTP Error: {e}")
        logger.error(f"   Response: {response.text}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"❌ Error tidak terduga saat login: {e}")
        sys.exit(1)


# ─── Baca CSV ─────────────────────────────────────────────
def read_csv(csv_path: str) -> list[dict]:
    """
    Membaca file CSV dan mengembalikan list of dict.
    """
    file_path = Path(csv_path)
    if not file_path.exists():
        logger.error(f"❌ File CSV '{csv_path}' tidak ditemukan!")
        sys.exit(1)

    rows = []
    with open(file_path, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)

        # Validasi kolom
        required_cols = [
            "level", "nama", "penyelenggara", "url_peserta",
            "url_sertifikat", "tgl_sertifikat", "url_foto_upp",
            "url_dokumen_undangan", "keterangan",
            "nim", "nama_mahasiswa",
        ]
        missing = [c for c in required_cols if c not in (reader.fieldnames or [])]
        if missing:
            logger.error(f"❌ Kolom CSV yang hilang: {missing}")
            logger.error(f"   Kolom yang ada: {reader.fieldnames}")
            sys.exit(1)

        for row in reader:
            rows.append(row)

    logger.info(f"📄 Berhasil membaca {len(rows)} baris dari CSV")
    return rows


# ─── Grouping Data ────────────────────────────────────────
def group_sertifikasi(rows: list[dict]) -> list[dict]:
    """
    Mengelompokkan baris CSV menjadi payload sertifikasi.
    Baris dengan sertifikasi yang sama (berdasarkan level + nama +
    penyelenggara + tgl_sertifikat) akan digabung mahasiswa & dosennya.
    """
    groups = {}

    for row in rows:
        # Buat kunci grup berdasarkan identitas sertifikasi
        key = (
            row["level"].strip(),
            row["nama"].strip(),
            row["penyelenggara"].strip(),
            row["tgl_sertifikat"].strip(),
        )

        if key not in groups:
            groups[key] = {
                "level": row["level"].strip(),
                "nama": row["nama"].strip(),
                "penyelenggara": row["penyelenggara"].strip(),
                "url_peserta": row["url_peserta"].strip(),
                "url_sertifikat": row["url_sertifikat"].strip(),
                "tgl_sertifikat": row["tgl_sertifikat"].strip(),
                "url_foto_upp": row["url_foto_upp"].strip(),
                "url_dokumen_undangan": row["url_dokumen_undangan"].strip(),
                "keterangan": row.get("keterangan", "").strip(),
                "mahasiswa": [],
                "dosen": [],
                "_seen_nim": set(),
                "_seen_nuptk": set(),
            }

        group = groups[key]

        # Tambahkan mahasiswa (hindari duplikat)
        nim = row.get("nim", "").strip()
        nama_mhs = row.get("nama_mahasiswa", "").strip()
        if nim and nim not in group["_seen_nim"]:
            group["mahasiswa"].append({
                "nim": nim,
                "nama": nama_mhs,
            })
            group["_seen_nim"].add(nim)

        # Tambahkan dosen (hindari duplikat)
        nuptk = row.get("nuptk_dosen", "").strip()
        nama_dosen = row.get("nama_dosen", "").strip()
        url_surat = row.get("url_surat_tugas", "").strip()
        if nuptk and nuptk not in group["_seen_nuptk"]:
            dosen_data = {
                "nuptk": nuptk,
                "nama": nama_dosen,
            }
            if url_surat:
                dosen_data["url_surat_tugas"] = url_surat
            group["dosen"].append(dosen_data)
            group["_seen_nuptk"].add(nuptk)

    # Hapus field internal tracking
    result = []
    for group in groups.values():
        del group["_seen_nim"]
        del group["_seen_nuptk"]
        result.append(group)

    logger.info(f"📦 Data dikelompokkan menjadi {len(result)} sertifikasi")
    for i, g in enumerate(result, 1):
        logger.info(
            f"   [{i}] {g['nama']} - {g['level']} | "
            f"{len(g['mahasiswa'])} mahasiswa, {len(g['dosen'])} dosen"
        )

    return result


# ─── Upload Sertifikasi ──────────────────────────────────
def upload_sertifikasi(
    config: configparser.ConfigParser,
    token: str,
    payload: dict,
    index: int,
    total: int,
    max_retries: int = 3,
    delay: float = 1.0,
    timeout: int = 30,
) -> dict | None:
    """
    Upload satu data sertifikasi ke API.
    Mendukung retry otomatis jika gagal.
    """
    base_url = config.get("api", "base_url")
    sertif_endpoint = config.get("api", "sertif_endpoint")
    url = f"{base_url}{sertif_endpoint}"

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    logger.info("")
    logger.info(f"{'─' * 50}")
    logger.info(f"📤 Upload [{index}/{total}]: {payload['nama']}")
    logger.info(f"   Level       : {payload['level']}")
    logger.info(f"   Penyelenggara: {payload['penyelenggara']}")
    logger.info(f"   Tanggal     : {payload['tgl_sertifikat']}")
    logger.info(f"   Mahasiswa   : {len(payload['mahasiswa'])} orang")
    logger.info(f"   Dosen       : {len(payload['dosen'])} orang")

    for attempt in range(1, max_retries + 1):
        try:
            if attempt > 1:
                wait = delay * attempt
                logger.info(f"   ⏳ Retry {attempt}/{max_retries} (tunggu {wait}s)...")
                time.sleep(wait)

            response = requests.post(
                url, json=payload, headers=headers, timeout=timeout
            )
            data = response.json()

            if response.status_code == 200 and data.get("status"):
                sertif_id = data.get("data", {}).get("id", "N/A")
                logger.info(f"   ✅ Berhasil! ID: {sertif_id}")
                return data
            else:
                logger.warning(
                    f"   ⚠️  Gagal (attempt {attempt}): "
                    f"HTTP {response.status_code} - {json.dumps(data, indent=2)}"
                )

        except requests.exceptions.Timeout:
            logger.warning(f"   ⚠️  Timeout (attempt {attempt}/{max_retries})")
        except requests.exceptions.ConnectionError:
            logger.warning(f"   ⚠️  Connection error (attempt {attempt}/{max_retries})")
        except Exception as e:
            logger.warning(f"   ⚠️  Error (attempt {attempt}/{max_retries}): {e}")

    logger.error(f"   ❌ GAGAL setelah {max_retries} percobaan: {payload['nama']}")
    return None


# ─── Main ─────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(
        description="Upload data sertifikasi dari CSV ke API SIMKATMAWA",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Contoh penggunaan:
  python upload_sertifikasi.py data_sertif.csv
  python upload_sertifikasi.py data_sertif.csv --config config.ini
  python upload_sertifikasi.py data_sertif.csv --dry-run
        """,
    )
    parser.add_argument("csv_file", help="Path ke file CSV berisi data sertifikasi")
    parser.add_argument(
        "--config", default="config.ini", help="Path ke file konfigurasi (default: config.ini)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Hanya menampilkan data tanpa upload (untuk validasi)",
    )
    args = parser.parse_args()

    # Banner
    logger.info("=" * 58)
    logger.info("  SIMKATMAWA - Upload Sertifikasi Otomatis")
    logger.info(f"  Waktu mulai: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 58)

    # Load configuration
    config = load_config(args.config)
    delay = config.getfloat("settings", "request_delay", fallback=1.0)
    max_retries = config.getint("settings", "max_retries", fallback=3)
    timeout = config.getint("settings", "timeout", fallback=30)

    # Step 1: Baca CSV
    logger.info("")
    logger.info("📌 STEP 1: Membaca file CSV...")
    rows = read_csv(args.csv_file)

    # Step 2: Grouping
    logger.info("")
    logger.info("📌 STEP 2: Mengelompokkan data sertifikasi...")
    payloads = group_sertifikasi(rows)

    if not payloads:
        logger.warning("⚠️  Tidak ada data untuk diupload!")
        return

    # Dry-run mode: tampilkan data saja
    if args.dry_run:
        logger.info("")
        logger.info("🔍 MODE DRY-RUN: Menampilkan payload tanpa upload")
        logger.info("=" * 50)
        for i, p in enumerate(payloads, 1):
            logger.info(f"\n--- Sertifikasi #{i} ---")
            logger.info(json.dumps(p, indent=2, ensure_ascii=False))
        logger.info("")
        logger.info("✅ Dry-run selesai. Tidak ada data yang diupload.")
        return

    # Step 3: Login
    logger.info("")
    logger.info("📌 STEP 3: Login ke API SIMKATMAWA...")
    token = login(config)

    # Step 4: Upload
    logger.info("")
    logger.info("📌 STEP 4: Upload data sertifikasi...")
    total = len(payloads)
    success_count = 0
    fail_count = 0
    results = []

    for i, payload in enumerate(payloads, 1):
        result = upload_sertifikasi(
            config, token, payload, i, total,
            max_retries=max_retries, delay=delay, timeout=timeout,
        )

        if result:
            success_count += 1
            results.append({"status": "success", "nama": payload["nama"], "data": result})
        else:
            fail_count += 1
            results.append({"status": "failed", "nama": payload["nama"], "data": None})

        # Delay antar request
        if i < total:
            time.sleep(delay)

    # ─── Summary ──────────────────────────────────────────
    logger.info("")
    logger.info("=" * 58)
    logger.info("  📊 RINGKASAN UPLOAD")
    logger.info("=" * 58)
    logger.info(f"  Total sertifikasi : {total}")
    logger.info(f"  ✅ Berhasil       : {success_count}")
    logger.info(f"  ❌ Gagal          : {fail_count}")
    logger.info(f"  📁 Log file       : {log_filename}")
    logger.info("=" * 58)

    if fail_count > 0:
        logger.info("")
        logger.info("  ❌ Sertifikasi yang gagal:")
        for r in results:
            if r["status"] == "failed":
                logger.info(f"     - {r['nama']}")

    # Simpan hasil ke JSON
    result_file = LOG_DIR / f"result_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(result_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    logger.info(f"\n  📄 Hasil detail tersimpan di: {result_file}")

    logger.info(f"\n  Waktu selesai: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Exit code berdasarkan hasil
    if fail_count > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
