"""
============================================================
  SIMKATMAWA - Auto Upload Sertifikasi (Web Session)
============================================================
  Script ini membaca data sertifikasi dari file CSV,
  mengelompokkan mahasiswa & dosen per sertifikasi,
  lalu mengupload ke SIMKATMAWA menggunakan Web Session
  (Otomatis Login via Email & Password).
============================================================
"""

import csv
import json
import time
import configparser
import sys
import re
from datetime import datetime
from pathlib import Path

try:
    import requests
except ImportError:
    print("\033[91m[!] Module 'requests' belum terinstall. Jalankan: pip install requests\033[0m")
    sys.exit(1)

# --- Configuration ---
BASE_URL = "https://simkatmawa.kemdiktisaintek.go.id"
CSV_FILE = "sertifikat_test.csv"

def load_config(config_path: str = "config.ini"):
    config = configparser.ConfigParser()
    if not Path(config_path).exists():
        print(f"\033[91m[!] File {config_path} tidak ditemukan!\033[0m")
        sys.exit(1)
    config.read(config_path, encoding="utf-8")
    return config

# ─── 1. Login Web ──────────────────────────────────────────
def login_web(session, config):
    email = config.get("credentials", "email")
    password = config.get("credentials", "password")
    login_url = f"{BASE_URL}/login"
    
    print(f"\033[94m[*] Melakukan login web untuk:\033[0m {email}")
    try:
        resp = session.get(login_url, timeout=15)
        match = re.search(r'name="_token"\s+value="([^"]+)"', resp.text)
        if not match: 
            print("\033[91m[!] Gagal mendapatkan token login HTML.\033[0m")
            return False
            
        token = match.group(1)
        payload = {"_token": token, "email": email, "password": password, "remember": "on"}
        
        resp = session.post(login_url, data=payload, timeout=15, allow_redirects=False)
        if resp.status_code == 302:
            print("\033[92m  [+] Login Berhasil!\033[0m")
            return True
        else:
            print(f"\033[91m  [-] Login Gagal. Status Code: {resp.status_code}\033[0m")
            return False
    except Exception as e: 
        print(f"\033[91m  [-] Error saat login: {e}\033[0m")
        return False

def get_csrf_token(session):
    url = f"{BASE_URL}/sertifikasi/create"
    try:
        resp = session.get(url, timeout=10)
        if "login" in resp.url.lower(): return "EXPIRED"
        
        match = re.search(r'name="_token"\s+value="([^"]+)"', resp.text)
        if not match: 
            match = re.search(r'content="([^"]+)"\s+name="csrf-token"', resp.text)
            
        if match: 
            return match.group(1)
    except: 
        pass
    return None

# ─── 2. Parsing CSV & Grouping ────────────────────────────
def read_csv(csv_path: str) -> list[dict]:
    file_path = Path(csv_path)
    if not file_path.exists():
        print(f"\033[91m[!] File CSV '{csv_path}' tidak ditemukan!\033[0m")
        sys.exit(1)

    rows = []
    with open(file_path, "r", encoding="utf-8-sig") as f:
        # Deteksi delimiter (koma atau titik koma)
        sample = f.read(1024)
        f.seek(0)
        delimiter = ";" if ";" in sample else ","
        reader = csv.DictReader(f, delimiter=delimiter)

        required_cols = [
            "level", "nama", "penyelenggara", "url_peserta",
            "url_sertifikat", "tgl_sertifikat", "url_foto_upp",
            "url_dokumen_undangan", "keterangan",
            "nim", "nama_mahasiswa",
        ]
        
        missing = [c for c in required_cols if c not in (reader.fieldnames or [])]
        if missing:
            print(f"\033[91m[!] Kolom CSV yang hilang: {missing}\033[0m")
            sys.exit(1)

        for row in reader:
            rows.append(row)

    print(f"\033[92m[+] Berhasil membaca {len(rows)} baris dari CSV '{csv_path}'\033[0m")
    return rows

def group_sertifikasi(rows: list[dict]) -> list[dict]:
    groups = {}
    for row in rows:
        key = (
            row["level"].strip(), row["nama"].strip(),
            row["penyelenggara"].strip(), row["tgl_sertifikat"].strip(),
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
        nim = row.get("nim", "").strip()
        nama_mhs = row.get("nama_mahasiswa", "").strip()
        if nim and nim not in group["_seen_nim"]:
            group["mahasiswa"].append({"nim": nim, "nama": nama_mhs})
            group["_seen_nim"].add(nim)

        nuptk = row.get("nuptk_dosen", "").strip()
        nama_dosen = row.get("nama_dosen", "").strip()
        url_surat = row.get("url_surat_tugas", "").strip()
        if nuptk and nuptk not in group["_seen_nuptk"]:
            group["dosen"].append({
                "nuptk": nuptk, "nama": nama_dosen, "url_surat_tugas": url_surat
            })
            group["_seen_nuptk"].add(nuptk)

    result = []
    for group in groups.values():
        del group["_seen_nim"]
        del group["_seen_nuptk"]
        result.append(group)

    print(f"\033[94m[*] Data dikelompokkan menjadi {len(result)} sertifikasi unik.\033[0m")
    return result

# ─── 3. Upload ke Web (Form-Data) ─────────────────────────
def upload_sertifikasi_web(session, payload, index, total):
    url = f"{BASE_URL}/sertifikasi/store"
    csrf_token = get_csrf_token(session)
    
    if csrf_token == "EXPIRED": return "EXPIRED"
    if not csrf_token: return False

    # Mapping Form Data Array
    LEVEL_MAP = {
        "Internasional": "INT", "Nasional": "NAS", 
        "Provinsi": "PROV", "Regional": "REG", "Institusi": "PT"
    }
    
    lvl_val = "INT"
    for k, v in LEVEL_MAP.items():
        if k.lower() in payload["level"].lower(): 
            lvl_val = v
            break

    form_payload = {
        "_token": (None, csrf_token),
        "level": (None, lvl_val),
        "nama": (None, payload["nama"]),
        "penyelenggara": (None, payload["penyelenggara"]),
        "url_peserta": (None, payload["url_peserta"]),
        "url_sertifikat": (None, payload["url_sertifikat"]),
        "tgl_sertifikat": (None, payload["tgl_sertifikat"]),
        "url_foto_upp": (None, payload["url_foto_upp"]),
        "url_dokumen_undangan": (None, payload["url_dokumen_undangan"]),
        "keterangan": (None, payload["keterangan"]),
        "send": (None, "Simpan"),
    }
    
    # Tambahkan Array Mahasiswa
    # Web form is expecting nim[] and nama_mahasiswa[]
    for mhs in payload["mahasiswa"]:
        form_payload.setdefault("nim[]", []).append((None, mhs["nim"]))
        form_payload.setdefault("nama_mahasiswa[]", []).append((None, mhs["nama"]))

    # Tambahkan Array Dosen
    # Web form is expecting nuptk_dosen[], nama_dosen[], url_surat_tugas[]
    for dosen in payload["dosen"]:
        form_payload.setdefault("nuptk_dosen[]", []).append((None, dosen["nuptk"]))
        form_payload.setdefault("nama_dosen[]", []).append((None, dosen["nama"]))
        form_payload.setdefault("url_surat_tugas[]", []).append((None, dosen.get("url_surat_tugas", "")))

    print(f"\n  [{index}/{total}] Mengupload: \033[96m{payload['nama']}\033[0m")
    print(f"        Mahasiswa: {len(payload['mahasiswa'])} | Dosen: {len(payload['dosen'])}")
    
    try:
        headers = {"Origin": BASE_URL, "Referer": f"{BASE_URL}/sertifikasi/create"}
        # request logic for multiple keys with same name in python requests:
        # we can pass a list of tuples to `files`
        files_list = []
        for k, v in form_payload.items():
            if isinstance(v, list):
                for item in v: files_list.append((k, item))
            else:
                files_list.append((k, v))
                
        resp = session.post(url, files=files_list, headers=headers, timeout=30, allow_redirects=False)
        
        if resp.status_code in [200, 302]:
            if "login" in resp.headers.get("Location", "").lower(): return "EXPIRED"
            return True
        else:
            print(f"      \033[91m[-] Gagal (HTTP {resp.status_code})\033[0m")
            return False
    except Exception as e:
        print(f"      \033[91m[-] Error Request: {e}\033[0m")
        return False

# ─── Main Execution ───────────────────────────────────────
def main():
    print("\033[96m" + "┏" + "━"*54 + "┓")
    print("┃     SIMKATMAWA AUTO UPLOAD - WEB SESSION AUTOLOGIN     ┃")
    print("┗" + "━"*54 + "┛\033[0m")
    
    import argparse
    parser = argparse.ArgumentParser(description="Upload data sertifikasi ke SIMKATMAWA via Web Form")
    parser.add_argument("csv_file", nargs='?', default=CSV_FILE, help="Path ke file CSV berisi data sertifikasi")
    parser.add_argument("--dry-run", action="store_true", help="Hanya menampilkan data tanpa upload")
    args = parser.parse_args()

    # 1. Baca & Siapkan Data
    rows = read_csv(args.csv_file)
    payloads = group_sertifikasi(rows)
    if not payloads: return

    if args.dry_run:
        print("\033[93m\n[!] MODE DRY-RUN TEPILIH. Menampilkan struktur payload pertama saja:\033[0m")
        print(json.dumps(payloads[0], indent=2))
        return

    # 2. Login
    config = load_config()
    session = requests.Session()
    session.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"})
    
    if not login_web(session, config):
        sys.exit(1)

    # 3. Proses Upload
    total = len(payloads)
    success = 0
    fail = 0
    fail_list = []

    print(f"\n\033[95m[*] Memulai {total} proses upload...\033[0m")
    for i, payload in enumerate(payloads, 1):
        result = upload_sertifikasi_web(session, payload, i, total)
        if result == "EXPIRED":
            print("      \033[91m[-] Sesi Expired di tengah jalan!\033[0m")
            break
        elif result:
            print("      \033[92m[+] SUKSES!\033[0m")
            success += 1
        else:
            fail += 1
            fail_list.append(payload["nama"])
        time.sleep(1)

    # 4. Summary
    print("\n\033[96m" + "━" * 56)
    print(f"  RINGKASAN UPLOAD:")
    print(f"  - Total   : {total}")
    print(f"  - Berhasil: \033[92m{success}\033[0m")
    print(f"  - Gagal   : \033[91m{fail}\033[0m")
    if fail_list:
        print(f"\n  \033[93m[!] DAFTAR GAGAL:\033[0m")
        for f in fail_list: print(f"    - {f}")
    print("━" * 56 + "\033[0m\n")

if __name__ == "__main__":
    main()
