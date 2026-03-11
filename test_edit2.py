import requests
import re
import configparser
import json

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
    session.post(login_url, data=payload)

edit_resp = session.get('https://simkatmawa.kemdiktisaintek.go.id/sertifikasi/edit/155468')

fields = ['url_peserta', 'url_sertifikat', 'tgl_sertifikat', 'url_foto_upp', 'url_dokumen_undangan', 'keterangan']
data = {}
for f in fields:
    m = re.search(f'name="{f}"[^>]*value="([^"]*)"', edit_resp.text)
    if not m:
        m = re.search(f'value="([^"]*)"[^>]*name="{f}"', edit_resp.text)
    if m: 
        data[f] = m.group(1)
    else:
        # Check textarea
        m2 = re.search(f'<textarea[^>]*name="{f}"[^>]*>(.*?)</textarea>', edit_resp.text, re.DOTALL)
        if m2:
            data[f] = m2.group(1)
        else:
            data[f] = None
print(json.dumps(data, indent=2))
