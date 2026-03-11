"""
============================================================
  SIMKATMAWA - Automated Bulk Edit (Full Automation)
============================================================
  Script ini melakukan login otomatis dan mengedit data 
  sertifikasi secara bulk menggunakan ID dari list atau CSV.
  Setelah berhasil edit, data akan diekstrak dan disimpan.
============================================================
"""

import requests
import re
import time
import configparser
import sys
import csv
from pathlib import Path

# --- Configuration ---
BASE_URL = "https://simkatmawa.kemdiktisaintek.go.id"

# --- Input IDs (Pilih salah satu) ---
IDs_TO_EDIT = [] 
CSV_FILE = "edit_pls.csv"
CSV_DELIMITER = ","
ID_COLUMN_NAME = "id"

# --- Output Log ---
LOG_EXTRACT_FILE = "edit_log_extracted.csv"

# --- Data Update ---
# Hanya field yang ada di dictionary ini yang akan DIGANTI.
# Field yang TIDAK ADA di sini akan DIPERTAHANKAN sesuai data asli dari web.
EDIT_DATA = {
    "keterangan":"English proficiency, Common European Framework of Reference for Languages (CEFR)"
}

def load_config(config_path: str = "config.ini"):
    config = configparser.ConfigParser()
    if not Path(config_path).exists():
        print(f"\033[91m[!] File {config_path} tidak ditemukan!\033[0m")
        sys.exit(1)
    config.read(config_path, encoding="utf-8")
    return config

def load_ids_from_csv(file_path):
    ids = []
    if not Path(file_path).exists():
        print(f"\033[91m[!] File CSV {file_path} tidak ditemukan!\033[0m")
        return []
    try:
        with open(file_path, mode='r', encoding='utf-8') as f:
            reader = csv.DictReader(f, delimiter=CSV_DELIMITER)
            for row in reader:
                if ID_COLUMN_NAME in row:
                    ids.append(row[ID_COLUMN_NAME].strip())
        print(f"\033[92m[+] Berhasil memuat {len(ids)} ID dari {file_path}\033[0m")
    except Exception as e:
        print(f"\033[91m[!] Gagal membaca CSV: {e}\033[0m")
    return ids

def login_web(session, config):
    email = config.get("credentials", "email")
    password = config.get("credentials", "password")
    login_url = f"{BASE_URL}/login"
    print(f"\033[94m[*] Melakukan login untuk:\033[0m {email}")
    try:
        resp = session.get(login_url, timeout=15)
        match = re.search(r'name="_token"\s+value="([^"]+)"', resp.text)
        if not match: return False
        token = match.group(1)
        payload = {"_token": token, "email": email, "password": password, "remember": "on"}
        resp = session.post(login_url, data=payload, timeout=15, allow_redirects=False)
        return resp.status_code == 302
    except: return False

def get_csrf_token(session, cert_id=None):
    urls = [f"{BASE_URL}/sertifikasi/edit/{cert_id}"] if cert_id else []
    urls.append(f"{BASE_URL}/sertifikasi")
    for url in urls:
        try:
            resp = session.get(url, timeout=10)
            if "login" in resp.url.lower(): return "EXPIRED"
            match = re.search(r'name="_token"\s+value="([^"]+)"', resp.text)
            if not match: match = re.search(r'content="([^"]+)"\s+name="csrf-token"', resp.text)
            if match: return match.group(1)
        except: continue
    return None

def extract_view_data(session, cert_id):
    """Ekstraksi data dari halaman view sertifikasi dengan isolasi seksi."""
    view_url = f"{BASE_URL}/sertifikasi/view/{cert_id}"
    try:
        resp = session.get(view_url, timeout=15)
        html = resp.text
        
        def clean_html(raw_html):
            clean = re.sub(r'<.*?>', '', raw_html)
            return re.sub(r'\s+', ' ', clean).strip()

        def get_field(label):
            pattern = rf'<label class="form-label">{label}</label>.*?<div class="form-icon position-relative bg-light p-3">(.*?)</div>'
            match = re.search(pattern, html, re.DOTALL)
            if match: return clean_html(match.group(1))
            return "-"

        data = {
            "id": cert_id,
            "level": get_field("Level"),
            "nama_sertifikasi": get_field("Nama Sertifikasi"),
            "penyelenggara": get_field("Penyelenggara"),
            "url_sertifikasi": get_field("URL Sertifikasi"),
            "link_dokumen_sertifikat": get_field("Link Dokumen Sertifikat"),
            "tanggal_sertifikat": get_field("Tanggal Sertifikat"),
            "link_foto": get_field("Link Foto"),
            "link_dokumen_undangan": get_field("Link Dokumen Undangan"),
            "keterangan": get_field("Keterangan"),
        }

        mhs_section = ""
        dosen_section = ""
        parts = re.split(r'Data Mahasiswa|Data Dosen', html)
        if len(parts) >= 2: mhs_section = parts[1]
        if len(parts) >= 3: dosen_section = parts[2]

        mahasiswa = []
        if mhs_section:
            for row in re.findall(r'<tr>(.*?)</tr>', mhs_section, re.DOTALL):
                cols = re.findall(r'<td.*?>(.*?)</td>', row, re.DOTALL)
                if len(cols) >= 2:
                    nim, nama = clean_html(cols[0]), clean_html(cols[1])
                    if nim and nama: mahasiswa.append(f"{nim} - {nama}")
        data["mahasiswa"] = " | ".join(mahasiswa)

        dosen = []
        if dosen_section:
            for row in re.findall(r'<tr>(.*?)</tr>', dosen_section, re.DOTALL):
                cols = re.findall(r'<td.*?>(.*?)</td>', row, re.DOTALL)
                if len(cols) >= 3:
                    nidn, nama = clean_html(cols[0]), clean_html(cols[1])
                    link_match = re.search(r'href="(.*?)"', cols[2])
                    link = link_match.group(1) if link_match else clean_html(cols[2])
                    if nidn and nama: dosen.append(f"{nidn} ({nama}) [{link}]")
        data["dosen"] = " | ".join(dosen)

        return data
    except Exception as e:
        print(f"\033[93m    [!] Gagal ekstraksi data: {e}\033[0m")
        return None

def edit_certification(session, cert_id):
    url = f"{BASE_URL}/sertifikasi/update/{cert_id}"
    
    # 1. Ambil data asli terlebih dahulu untuk dipertahankan
    old_data = extract_view_data(session, cert_id)
    if not old_data:
        print(f"    \033[91m[-] Gagal mengambil data existing. Melewati.\033[0m")
        return False

    # 2. Ambil token CSRF
    csrf_token = get_csrf_token(session, cert_id)
    if csrf_token == "EXPIRED": return "EXPIRED"
    if not csrf_token: return False

    # Helper map level text ke enum
    LEVEL_MAP = {
        "Internasional": "INT", "Nasional": "NAS", 
        "Provinsi": "PROV", "Regional": "REG", "Institusi": "PT"
    }

    def get_val(key, old_key, is_level=False):
        # Jika user mau mengubah data ini (ada di EDIT_DATA), pakai yang baru
        if key in EDIT_DATA: return str(EDIT_DATA[key])
        
        # Jika tidak, pakai data lama
        val = old_data.get(old_key, "-")
        if is_level:
            for k, v in LEVEL_MAP.items():
                if k.lower() in val.lower(): return v
            return "INT" # Fallback
        return "" if val == "-" else val

    # 3. Gabungkan form payload
    form_payload = {
        "id": (None, str(cert_id)),
        "_token": (None, csrf_token),
        "_method": (None, "POST"),
        "level": (None, get_val("level", "level", is_level=True)),
        "nama": (None, get_val("nama", "nama_sertifikasi")),
        "penyelenggara": (None, get_val("penyelenggara", "penyelenggara")),
        "url_peserta": (None, get_val("url_peserta", "url_sertifikasi")),
        "url_sertifikat": (None, get_val("url_sertifikat", "link_dokumen_sertifikat")),
        "tgl_sertifikat": (None, get_val("tgl_sertifikat", "tanggal_sertifikat")),
        "url_foto_upp": (None, get_val("url_foto_upp", "link_foto")),
        "url_dokumen_undangan": (None, get_val("url_dokumen_undangan", "link_dokumen_undangan")),
        "keterangan": (None, get_val("keterangan", "keterangan")),
        "send": (None, "Simpan"),
    }
    
    try:
        headers = {"Origin": BASE_URL, "Referer": f"{BASE_URL}/sertifikasi/edit/{cert_id}"}
        resp = session.post(url, files=form_payload, headers=headers, timeout=15, allow_redirects=False)
        if resp.status_code in [200, 302]:
            if "login" in resp.headers.get("Location", "").lower(): return "EXPIRED"
            return True
        return False
    except: return False

def main():
    print("\033[96m" + "┏" + "━"*48 + "┓")
    print("┃      SIMKATMAWA BULK EDIT - AUTOMATED          ┃")
    print("┗" + "━"*48 + "┛\033[0m")
    
    config = load_config()
    session = requests.Session()
    session.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"})

    final_ids = IDs_TO_EDIT if IDs_TO_EDIT else load_ids_from_csv(CSV_FILE)
    if not final_ids: return

    if login_web(session, config):
        total = len(final_ids)
        success_list, failed_list = [], []
        
        # Inisialisasi CSV Header
        fieldnames = ["id", "level", "nama_sertifikasi", "penyelenggara", "url_sertifikasi", 
                      "link_dokumen_sertifikat", "tanggal_sertifikat", "link_foto", 
                      "link_dokumen_undangan", "keterangan", "mahasiswa", "dosen"]
        
        write_header = not Path(LOG_EXTRACT_FILE).exists() or Path(LOG_EXTRACT_FILE).stat().st_size == 0
        
        print(f"\n\033[95m[*] Memproses {total} data sertifikasi...\033[0m")
        with open(LOG_EXTRACT_FILE, mode='a', encoding='utf-8', newline='') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames, delimiter=';')
            if write_header: writer.writeheader()

            for i, cert_id in enumerate(final_ids, 1):
                print(f"  [{i}/{total}] Memproses ID: \033[94m{cert_id}\033[0m ... ", end="", flush=True)
                result = edit_certification(session, cert_id)
                
                if result == "EXPIRED":
                    print("\033[91mEXPIRED\033[0m")
                    failed_list.extend(final_ids[i-1:])
                    break
                elif result:
                    print("\033[92mSUKSES\033[0m", end=" ")
                    success_list.append(cert_id)
                    
                    # Ekstraksi Data
                    ext_data = extract_view_data(session, cert_id)
                    if ext_data:
                        writer.writerow(ext_data)
                        csvfile.flush()
                        print("\033[92m(LOG OK)\033[0m")
                    else:
                        print("\033[93m(LOG FAIL)\033[0m")
                else:
                    print("\033[91mGAGAL\033[0m")
                    failed_list.append(cert_id)
                time.sleep(0.1)

        print("\n\033[96m" + "━" * 50)
        print(f"  RINGKASAN:")
        print(f"  - Total   : {total}")
        print(f"  - Berhasil: \033[92m{len(success_list)}\033[0m")
        print(f"  - Log Saved: {LOG_EXTRACT_FILE}")
        if failed_list:
            print(f"\n  \033[93m[!] DAFTAR ID GAGAL/TERSISA:\033[0m\n  {', '.join(map(str, failed_list))}")
        print("━" * 50 + "\033[0m\n")

if __name__ == "__main__":
    main()
