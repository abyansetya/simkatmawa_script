"""
============================================================
  SIMKATMAWA - Bulk Edit (Debug Version)
============================================================
"""

import requests
import urllib.parse
import time
import re

# --- Session Configuration ---
# Update these values dari browser (Application -> Cookies)
XSRF_TOKEN = "eyJpdiI6IkIwb09hUDdrT3FiZzlTWm0rVG9lM1E9PSIsInZhbHVlIjoidm1TaW0zR1ZkbnlNWC9JRVQ3a1pLUGFRaTlpMWJENlNnWjVnMEtxc2NoZXRqTDB0ZWt4dDlkeUFtWjlELzhpcFczY2dGdTg1RHA0L1VHeVJGamdORGJTY0tSNjdOTlJpMjYxMU5NWkZJeE91RUJxVUY5TEpzSlRlRzB1MHdsVmciLCJtYWMiOiJhYjc0MGNmZDcyYTAxNzg3NzgyY2NkMzAwNjIwYTM4N2IzZTBhYzBiZjQ1MjhkNTUxYjg4MzlhNGU4MDJkMjBhIiwidGFnIjoiIn0%3D"
SESS_COOKIE = "eyJpdiI6IlBRTHRxbzdpT2sxdXgvTlpOVC9XVUE9PSIsInZhbHVlIjoiRXlWYS91Y290Q1VjZCsyNVNNUXRoMWNmUDRqMGRBaTl0R0x3N083ZzVocjVZK3pNUUFmZDMxMHl4akJOcjJkK1BMYUlNUTRUUGF6ZHdJdkd0M3lJMWRUM1N1NzRXRUtzYXZzTVd5ejhPRlBrWWJNb3IyUmRvTFhuOVhCK0N5VWkiLCJtYWMiOiIwZGZhNDM2ZWFjZjVlM2JmMDUxYzBmYTU3YzY1ZTlmNDVhY2Y5OTg3YWJiNGM4MmY0YjI4OTg2ZWM5ZjczZDlhIiwidGFnIjoiIn0%3D"

# Token statis terakhir yang Anda berikan
STATIC_TOKEN = "6eK7j4V1kdQynGIxqlAIagEUacS8kOi2tXoxGuiF"

DECODED_XSRF = urllib.parse.unquote(XSRF_TOKEN)
BASE_URL = "https://simkatmawa.kemdiktisaintek.go.id"

# --- IDs to Edit ---
IDs_TO_EDIT = [153316]

# --- Data Update ---
EDIT_DATA = {
    "level": "INT",
    "nama": "Sertifikasi Kompetensi Bahasa Inggris (Learn Social)",
    "penyelenggara": "PT. Edu First Solusindo",
    "url_peserta": "https://www.edufirst.id",
    "url_sertifikat": "https://drive.google.com/file/d/1g51eAbhzT7bvsTFS54x_eeB3cWZ9nnVX/view?usp=sharing",
    "tgl_sertifikat": "2025-06-05",
    "url_foto_upp": "-",
    "url_dokumen_undangan": "-",
    "keterangan": "",
}

def get_csrf_token(session, cert_id):
    """Mencoba mengambil token CSRF dari web dengan berbagai cara."""
    url = f"{BASE_URL}/sertifikasi/edit/{cert_id}"
    try:
        print(f"  [*] Mencoba ambil token dari {url}...")
        resp = session.get(url, timeout=10)
        
        print(f"  [*] GET Status: {resp.status_code}")
        
        if "login" in resp.url.lower():
            print("  [!] Error: Session Logout! Browser mengarahkan ke halaman login.")
            return None

        # Cari token di meta tag atau input hidden
        token = None
        
        # Cara 1: Mencari <input name="_token" value="...">
        match = re.search(r'name="_token"\s+value="([^"]+)"', resp.text)
        if match:
            token = match.group(1)
        
        # Cara 2: Mencari <meta name="csrf-token" content="...">
        if not token:
            match = re.search(r'content="([^"]+)"\s+name="csrf-token"', resp.text)
            if not match:
                match = re.search(r'name="csrf-token"\s+content="([^"]+)"', resp.text)
            if match:
                token = match.group(1)

        if token:
            print(f"  [+] Token otomatis ditemukan: {token[:15]}...")
            return token
            
        print("  [!] Token tidak ditemukan di dalam HTML halaman.")
        # Jika gagal, tampilkan sedikit isi body untuk diagnosa
        print(f"  [*] Body Preview: {resp.text[:200].replace('\n', ' ')}")
        
    except Exception as e:
        print(f"  [!] Error saat request GET: {e}")
    
    print(f"  [!] Fallback ke STATIC_TOKEN: {STATIC_TOKEN[:15]}...")
    return STATIC_TOKEN

def edit_certification(session, cert_id):
    url = f"{BASE_URL}/sertifikasi/update/{cert_id}"
    print(f"\n[*] Memproses ID: {cert_id}")

    csrf_token = get_csrf_token(session, cert_id)

    form_payload = {
        "id": (None, str(cert_id)),
        "_token": (None, csrf_token),
        "_method": (None, "POST"),
        "level": (None, EDIT_DATA["level"]),
        "nama": (None, EDIT_DATA["nama"]),
        "penyelenggara": (None, EDIT_DATA["penyelenggara"]),
        "url_peserta": (None, EDIT_DATA["url_peserta"]),
        "url_sertifikat": (None, EDIT_DATA["url_sertifikat"]),
        "tgl_sertifikat": (None, EDIT_DATA["tgl_sertifikat"]),
        "url_foto_upp": (None, EDIT_DATA["url_foto_upp"]),
        "url_dokumen_undangan": (None, EDIT_DATA["url_dokumen_undangan"]),
        "keterangan": (None, EDIT_DATA["keterangan"]),
        "send": (None, "Simpan"),
    }

    try:
        custom_headers = {
            "Origin": BASE_URL,
            "Referer": f"{BASE_URL}/sertifikasi/edit/{cert_id}",
        }
        
        resp = session.post(url, files=form_payload, headers=custom_headers, timeout=15, allow_redirects=False)
        
        print(f"  [*] Status POST: {resp.status_code}")
        location = resp.headers.get("Location", "None")
        
        if resp.status_code == 419:
            print("  [-] GAGAL: 419 Page Expired. Token CSRF atau Cookie Salah!")
        elif resp.status_code == 302:
            if "login" in location.lower():
                print("  [-] GAGAL: Terlempar ke /login. Cookie sudah hangus.")
            else:
                print(f"  [+] BERHASIL: Redirect ke {location}")
        else:
            print(f"  [*] Respon: {resp.text[:100]}")

    except Exception as e:
        print(f"  [!] Error saat request POST: {e}")

def main():
    print("=== SIMKATMAWA Bulk Edit (Diagnostics Mode) ===")
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    })
    
    session.cookies.set("XSRF-TOKEN", XSRF_TOKEN, domain="simkatmawa.kemdiktisaintek.go.id")
    session.cookies.set("simkatmawa-session", SESS_COOKIE, domain="simkatmawa.kemdiktisaintek.go.id")

    for cert_id in IDs_TO_EDIT:
        edit_certification(session, cert_id)
        time.sleep(1)

if __name__ == "__main__":
    main()
