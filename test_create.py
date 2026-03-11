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

create_resp = session.get('https://simkatmawa.kemdiktisaintek.go.id/sertifikasi/create')
print("Status:", create_resp.status_code)

match_csrf = re.search(r'name="_token"\s+value="([^"]+)"', create_resp.text)
if match_csrf:
    print("Found CSRF:", match_csrf.group(1)[:10], "...")

# Get form action
action_match = re.search(r'<form[^>]*action="([^"]*)"', create_resp.text)
if action_match:
    print("Form action:", action_match.group(1))

