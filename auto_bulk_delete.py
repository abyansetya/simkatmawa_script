"""
============================================================
  SIMKATMAWA - Automated Bulk Delete (Full Automation)
============================================================
  Script ini melakukan login otomatis dan menghapus data 
  sertifikasi secara bulk menggunakan ID dari list atau CSV.
============================================================
"""

import requests
import re
import time
import configparser
import sys
import csv
import urllib.parse
from pathlib import Path

# --- Configuration ---
BASE_URL = "https://simkatmawa.kemdiktisaintek.go.id"

# --- Input IDs (Pilih salah satu) ---
# 1. Manual List
IDs_TO_DELETE = [162491] 

# 2. Atau ambil dari CSV (kosongkan IDs_TO_DELETE jika ingin pakai CSV)
CSV_FILE = ""
CSV_DELIMITER = ";"
ID_COLUMN_NAME = "id"

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
        if not match:
            print("  \033[91m[!] Gagal mengambil CSRF token awal.\033[0m")
            return False
        
        token = match.group(1)
        payload = {"_token": token, "email": email, "password": password, "remember": "on"}
        resp = session.post(login_url, data=payload, timeout=15, allow_redirects=False)
        
        if resp.status_code == 302:
            print("  \033[92m[+] Login Berhasil!\033[0m")
            return True
        else:
            print(f"  \033[91m[-] Login Gagal (Status: {resp.status_code})\033[0m")
            return False
    except Exception as e:
        print(f"  \033[91m[!] Error saat login: {e}\033[0m")
        return False

def get_csrf_token(session):
    url = f"{BASE_URL}/sertifikasi"
    try:
        resp = session.get(url, timeout=10)
        if "login" in resp.url.lower(): return "EXPIRED"

        match = re.search(r'content="([^"]+)"\s+name="csrf-token"', resp.text)
        if not match:
            match = re.search(r'name="csrf-token"\s+content="([^"]+)"', resp.text)
        
        if match:
            return match.group(1)
            
        xsrf_cookie = session.cookies.get("XSRF-TOKEN")
        if xsrf_cookie:
            return urllib.parse.unquote(xsrf_cookie)
    except:
        pass
    return None

def delete_certification(session, cert_id):
    url = f"{BASE_URL}/sertifikasi/delete/{cert_id}"
    csrf_token = get_csrf_token(session)
    
    if csrf_token == "EXPIRED": return "EXPIRED"
    if not csrf_token: return False

    headers = {
        "X-Requested-With": "XMLHttpRequest",
        "X-XSRF-TOKEN": csrf_token,
        "Referer": f"{BASE_URL}/sertifikasi"
    }

    try:
        resp = session.delete(url, headers=headers, timeout=15)
        if resp.status_code == 200:
            return True
        return False
    except:
        return False

def main():
    print("\033[95m" + "┏" + "━"*48 + "┓")
    print("┃     SIMKATMAWA BULK DELETE - AUTOMATED         ┃")
    print("┗" + "━"*48 + "┛\033[0m")

    config = load_config()
    session = requests.Session()
    session.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"})

    # Tentukan ID yang akan dikerjakan
    final_ids = IDs_TO_DELETE if IDs_TO_DELETE else load_ids_from_csv(CSV_FILE)
    
    if not final_ids:
        print("\033[91m[!] Tidak ada ID yang ditemukan untuk diproses!\033[0m")
        return

    if login_web(session, config):
        total = len(final_ids)
        success_list, failed_list = [], []
        
        print(f"\n\033[93m[*] Memproses {total} penghapusan data...\033[0m")
        
        for i, cert_id in enumerate(final_ids, 1):
            print(f"  [{i}/{total}] Menghapus ID: \033[94m{cert_id}\033[0m ... ", end="", flush=True)
            result = delete_certification(session, cert_id)
            
            if result == "EXPIRED":
                print("\033[91mEXPIRED\033[0m")
                print(f"\n\033[91m[!] Sesi login berakhir!\033[0m")
                failed_list.extend(final_ids[i-1:])
                break
            elif result:
                print("\033[92mSUKSES\033[0m")
                success_list.append(cert_id)
            else:
                print("\033[91mGAGAL\033[0m")
                failed_list.append(cert_id)
            time.sleep(0.5)

        print("\n\033[96m" + "━" * 50)
        print(f"  RINGKASAN:")
        print(f"  - Total   : {total}")
        print(f"  - Berhasil: \033[92m{len(success_list)}\033[0m")
        print(f"  - Gagal   : \033[91m{len(failed_list)}\033[0m")
        if failed_list:
            print(f"\n  \033[93m[!] DAFTAR ID GAGAL/TERSISA:\033[0m\n  {', '.join(map(str, failed_list))}")
        print("━" * 50 + "\033[0m\n")

if __name__ == "__main__":
    main()
