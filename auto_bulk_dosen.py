"""
============================================================
  SIMKATMAWA - Auto Bulk Edit Dosen (Prepend "00" ke NUPTK)
============================================================
  Script ini membaca ID sertifikasi dari CSV, mengambil data 
  dosen dari halaman web, lalu mengedit NUPTK dengan menambahkan
  "00" di depan nilai asli.
============================================================
"""

import requests
import re
import time
import csv
import configparser
import sys
from pathlib import Path

# --- Configuration ---
BASE_URL = "https://simkatmawa.kemdiktisaintek.go.id"

# --- Input IDs (Pilih salah satu) ---
IDs_TO_EDIT = [170496]
# CSV_FILE = "nyoba.csv"
CSV_DELIMITER = ","
ID_COLUMN_NAME = "id"

# --- Prefix yang ditambahkan di depan NUPTK ---
NUPTK_PREFIX = "00"

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
        if resp.status_code == 302:
            print("\033[92m  [+] Login Berhasil!\033[0m")
            return True
        return False
    except:
        return False

def get_dosen_data(session, cert_id):
    """
    Mengambil halaman dosen untuk sertifikasi tertentu.
    Mengembalikan list of dict: [{dosen_id, nuptk, nama, url_surat_tugas}, ...]
    """
    url = f"{BASE_URL}/sertifikasi/dosen/{cert_id}"
    try:
        resp = session.get(url, timeout=15)
        if "login" in resp.url.lower():
            return "EXPIRED"
        
        html = resp.text
        dosen_list = []
        
        # Cari semua form update dosen
        # Pattern: form action="/sertifikasi/updatedatadosen/{cert_id}/{dosen_id}"
        form_pattern = re.findall(
            r'<form\s+action="[^"]*?/sertifikasi/updatedatadosen/(\d+)/(\d+)".*?</form>',
            html, re.DOTALL
        )
        
        for match_cert_id, dosen_id in form_pattern:
            # Ambil CSRF token dari form ini
            form_block_pattern = re.search(
                rf'<form\s+action="[^"]*?/sertifikasi/updatedatadosen/{match_cert_id}/{dosen_id}".*?</form>',
                html, re.DOTALL
            )
            if not form_block_pattern:
                continue
            
            form_html = form_block_pattern.group(0)
            
            # Ekstrak _token
            token_match = re.search(r'name="_token"\s+value="([^"]+)"', form_html)
            csrf_token = token_match.group(1) if token_match else None
            
            # Ekstrak nuptk
            nuptk_match = re.search(
                r'name="nuptk"[^>]*value="([^"]*)"', form_html
            )
            nuptk = nuptk_match.group(1) if nuptk_match else ""
            
            # Ekstrak nama
            nama_match = re.search(
                r'name="nama"[^>]*value="([^"]*)"', form_html
            )
            nama = nama_match.group(1) if nama_match else ""
            
            # Ekstrak url_surat_tugas
            url_st_match = re.search(
                r'name="url_surat_tugas"[^>]*value="([^"]*)"', form_html
            )
            url_surat_tugas = url_st_match.group(1) if url_st_match else ""
            
            dosen_list.append({
                "cert_id": match_cert_id,
                "dosen_id": dosen_id,
                "csrf_token": csrf_token,
                "nuptk": nuptk,
                "nama": nama,
                "url_surat_tugas": url_surat_tugas,
            })
        
        return dosen_list
        
    except Exception as e:
        print(f"\033[91m    [!] Error mengambil data dosen: {e}\033[0m")
        return None

def update_dosen(session, cert_id, dosen_id, csrf_token, new_nuptk, nama, url_surat_tugas):
    """
    Mengirim request update dosen ke web form.
    """
    url = f"{BASE_URL}/sertifikasi/updatedatadosen/{cert_id}/{dosen_id}"
    
    form_payload = {
        "_token": (None, csrf_token),
        "_method": (None, "POST"),
        "nuptk": (None, new_nuptk),
        "nama": (None, nama),
        "url_surat_tugas": (None, url_surat_tugas),
    }
    
    try:
        headers = {
            "Origin": BASE_URL, 
            "Referer": f"{BASE_URL}/sertifikasi/dosen/{cert_id}"
        }
        resp = session.post(url, files=form_payload, headers=headers, timeout=15, allow_redirects=False)
        if resp.status_code in [200, 302]:
            if "login" in resp.headers.get("Location", "").lower():
                return "EXPIRED"
            return True
        return False
    except:
        return False

def main():
    print("\033[96m" + "┏" + "━"*52 + "┓")
    print("┃   SIMKATMAWA BULK EDIT DOSEN - PREPEND NUPTK       ┃")
    print("┗" + "━"*52 + "┛\033[0m")
    
    config = load_config()
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
    })
    
    final_ids = IDs_TO_EDIT if IDs_TO_EDIT else load_ids_from_csv(CSV_FILE)
    if not final_ids:
        print("\033[91m[!] Tidak ada ID untuk diproses.\033[0m")
        return
    
    if not login_web(session, config):
        print("\033[91m[!] Login gagal. Keluar.\033[0m")
        return
    
    total = len(final_ids)
    success_count = 0
    fail_count = 0
    skip_count = 0
    failed_list = []
    
    print(f"\n\033[95m[*] Memproses {total} sertifikasi...\033[0m")
    print(f"\033[93m    Prefix NUPTK: \"{NUPTK_PREFIX}\"\033[0m\n")
    
    for i, cert_id in enumerate(final_ids, 1):
        print(f"  [{i}/{total}] Sertifikasi ID: \033[94m{cert_id}\033[0m")
        
        # 1. Ambil data dosen
        dosen_list = get_dosen_data(session, cert_id)
        
        if dosen_list == "EXPIRED":
            print("    \033[91m[-] Sesi Expired!\033[0m")
            failed_list.extend(final_ids[i-1:])
            break
        
        if not dosen_list:
            print("    \033[91m[-] Gagal mengambil data dosen atau tidak ada dosen.\033[0m")
            fail_count += 1
            failed_list.append(cert_id)
            continue
        
        # 2. Proses setiap dosen
        for dosen in dosen_list:
            old_nuptk = dosen["nuptk"]
            
            # Cek apakah sudah punya prefix
            if old_nuptk.startswith(NUPTK_PREFIX):
                print(f"    \033[93m[~] Dosen {dosen['dosen_id']} ({dosen['nama'][:30]}...) "
                      f"NUPTK sudah dimulai \"{NUPTK_PREFIX}\": {old_nuptk} → SKIP\033[0m")
                skip_count += 1
                continue
            
            new_nuptk = NUPTK_PREFIX + old_nuptk
            
            print(f"    [>] Dosen {dosen['dosen_id']} ({dosen['nama'][:30]}...)")
            print(f"        NUPTK: {old_nuptk} → \033[92m{new_nuptk}\033[0m ... ", end="", flush=True)
            
            result = update_dosen(
                session,
                dosen["cert_id"],
                dosen["dosen_id"],
                dosen["csrf_token"],
                new_nuptk,
                dosen["nama"],
                dosen["url_surat_tugas"],
            )
            
            if result == "EXPIRED":
                print("\033[91mEXPIRED\033[0m")
                failed_list.extend(final_ids[i-1:])
                break
            elif result:
                print("\033[92mSUKSES\033[0m")
                success_count += 1
            else:
                print("\033[91mGAGAL\033[0m")
                fail_count += 1
                failed_list.append(f"{cert_id}/dosen-{dosen['dosen_id']}")
        
        time.sleep(0.3)
    
    # Summary
    print("\n\033[96m" + "━" * 54)
    print(f"  RINGKASAN:")
    print(f"  - Total Sertifikasi : {total}")
    print(f"  - Dosen Berhasil    : \033[92m{success_count}\033[0m")
    print(f"  - Dosen Dilewati    : \033[93m{skip_count}\033[0m")
    print(f"  - Gagal             : \033[91m{fail_count}\033[0m")
    if failed_list:
        print(f"\n  \033[93m[!] DAFTAR GAGAL:\033[0m")
        for f in failed_list:
            print(f"    - {f}")
    print("━" * 54 + "\033[0m\n")

if __name__ == "__main__":
    main()
