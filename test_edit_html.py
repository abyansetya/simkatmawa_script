import requests
import re
import configparser
import json
import sys

try:
    config = configparser.ConfigParser()
    config.read('config.ini')

    session = requests.Session()
    login_url = 'https://simkatmawa.kemdiktisaintek.go.id/login'
    resp = session.get(login_url)
    match = re.search(r'name="_token"\s+value="([^"]+)"', resp.text)
    if match:
        token = match.group(1)
        payload = {
            '_token': token,
            'email': config.get('credentials', 'email'),
            'password': config.get('credentials', 'password'),
            'remember': 'on'
        }
        resp_post = session.post(login_url, data=payload, allow_redirects=False)
        print("Login Status:", resp_post.status_code)

    edit_resp = session.get('https://simkatmawa.kemdiktisaintek.go.id/sertifikasi/edit/155468')
    print("Edit Status:", edit_resp.status_code)

    fields = ['url_peserta', 'url_sertifikat', 'tgl_sertifikat', 'url_foto_upp', 'url_dokumen_undangan', 'keterangan', 'level', 'nama', 'penyelenggara']
    data = {}
    for f in fields:
        # Try finding standard input value
        m = re.search(rf'name="{f}"[^>]*value="([^"]*)"', edit_resp.text)
        if not m:
            m = re.search(rf'value="([^"]*)"[^>]*name="{f}"', edit_resp.text)
            
        if m: 
            data[f] = m.group(1)
        else:
            # Check textarea
            m2 = re.search(rf'<textarea[^>]*name="{f}"[^>]*>(.*?)</textarea>', edit_resp.text, re.DOTALL)
            if m2:
                data[f] = m2.group(1)
            else:
                # Check select options (selected)
                m3 = re.search(rf'<select[^>]*name="{f}"[^>]*>.*?<option[^>]*value="([^"]*)"[^>]*selected.*?</select>', edit_resp.text, re.DOTALL)
                if m3:
                    data[f] = m3.group(1)
                else:
                    data[f] = None

    print(json.dumps(data, indent=2))

except Exception as e:
    print(f"Error: {e}")
