import requests
import json
import urllib.parse

# --- Configuration ---
SESS_COOKIE = "eyJpdiI6InNKWDdoMlBKeGVMZGh3SmlwelR4K0E9PSIsInZhbHVlIjoiSis5R0RQVWIvRGRNM1gvN1hKeFhvcWFaTVNJZmdTUUlKcWRyZFBzVy82dGVQSmRzbHVhcmZGbEJqNUJlQmpHbnp3cnM2R01Ec0tkOTBWQlRiUi90RnNFZkFOaEkzc1JmMjdRYkEzQUdUMSt3RjhLcGptQlloQzUzbFlvaXN4T2ciLCJtYWMiOiI3OGY3MDBhMDg2MzlkODE4NzM1NzgzNjVkNjJiMDNiYjhmYzM5MWMwMDE2NDRhNzY1NGU3OGQ0YjZlMjJhNWEzIiwidGFnIjoiIn0%3D"
XSRF_TOKEN = "eyJpdiI6InJ6TytQcEkvNU5mdXlKNlVEalBpWlE9PSIsInZhbHVlIjoiL1FwNXVZSWVnSExNNzIzTEFUb1BVUExGenVlclNvZkJuZDh6YkxBb1J1cnNKSEZmZmNEOEpSeFh2bjFPUEFJY0NvdkdERGZZc2pIbFZTNGdDU0JlZVVlcWtaWnl2K0hVc0IrZDdCOGgwVVBlT3J5VTRQRFV3a2lkR2pXeXQ1MEgiLCJtYWMiOiJhZjQzZDNhYWIwYjBhZWZkNzdkMWYzZjMwYzczNzNiM2I1ZDMyNjFjMGZlMGMxYTgyNmYzYjMwYWI3NWI0YmUwIiwidGFnIjoiIn0%3D"

# Decode XSRF-TOKEN for use in header if it was double-encoded, 
# although usually for Laravel/Laravel-like apps it is the literal value from the cookie.
# We'll use the decoded value for the X-XSRF-TOKEN header.
DECODED_XSRF = urllib.parse.unquote(XSRF_TOKEN)

URL_TEMPLATE = "https://simkatmawa.kemdiktisaintek.go.id/sertifikasi/delete/{id}"

# List ID yang akan dihapus (dari upload_log_Serkom BNSP FISIP.csv)
IDs_TO_DELETE = [
    135835, 135836, 135837, 135838, 135839, 135840, 135841, 135842, 135843,
    135844, 135845, 135846, 135847, 135848, 135849, 135850, 135851, 135852, 135853,
    135854, 135855, 135856, 135857, 135858, 135859, 135860, 135861, 135862, 135863,
    135864, 135865, 135866, 135867, 135868, 135869, 135870, 135871, 135872, 135873,
    135874, 135875, 135876, 135877, 135878, 135879, 135880, 135881, 135882, 135883,
    135884, 135885, 135886, 135887, 135888, 135889, 135890, 135891, 135892, 135893,
    135894, 135895, 135896, 135897, 135898, 135899, 135900, 135901, 135902, 135903,
    135904, 135905, 135906, 135907, 135908, 135909, 135910, 135911, 135912, 135913,
    135914, 135915, 135916, 135917, 135918, 135919, 135920, 135921, 135922, 135923,
    135925, 135926, 135927, 135928, 135929, 135930, 135931, 135932, 135933, 135934,
    135935, 135936, 135937, 135938, 135939, 135940, 135941, 135942, 135943, 135944,
    135945, 135946, 135947, 135948, 135949, 135950, 135951, 135952, 135953, 135954,
    135956, 135957, 135958, 135959, 135960, 135961, 135962, 135963, 135964, 135965,
    135966, 135967, 135968, 135969, 135970, 135971, 135972, 135973, 135974, 135975,
    135976, 135977, 135978, 135979, 135980, 135981, 135982, 135983, 135984, 135985,
    135986, 135987, 135988, 135989, 135990, 135991, 135992, 135993, 135994, 135995,
    135996, 135997, 135998, 135999, 136000, 136001, 136002, 136003, 136004, 136005,
    136006, 136007, 136008, 136009, 136010,
]

def delete_certification(cert_id):
    url = URL_TEMPLATE.format(id=cert_id)
    
    headers = {
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "X-Requested-With": "XMLHttpRequest",
        "X-XSRF-TOKEN": DECODED_XSRF,
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Cookie": f"XSRF-TOKEN={XSRF_TOKEN}; simkatmawa-session={SESS_COOKIE}"
    }

    print(f"[*] Attempting to delete ID: {cert_id}")
    try:
        # User requested HTTP DELETE
        response = requests.delete(url, headers=headers, timeout=10)
        
        print(f"[*] Response Status: {response.status_code}")
        try:
            data = response.json()
            print(f"[*] Response Body: {json.dumps(data, indent=2)}")
        except:
            print(f"[*] Response Body: {response.text[:200]}")

        if response.status_code == 200:
            print(f"[+] Successfully triggered delete for ID: {cert_id}")
            return True
        else:
            print(f"[-] Failed to delete ID: {cert_id}")
            return False

    except Exception as e:
        print(f"[!] Error deleting ID {cert_id}: {e}")
        return False

def main():
    print("=== SIMKATMAWA Bulk Delete Script ===")
    
    success_count = 0
    fail_count = 0
    
    for cert_id in IDs_TO_DELETE:
        if delete_certification(cert_id):
            success_count += 1
        else:
            fail_count += 1
            
    print("\n=== Summary ===")
    print(f"Total: {len(IDs_TO_DELETE)}")
    print(f"Success: {success_count}")
    print(f"Failed: {fail_count}")

if __name__ == "__main__":
    main()
