import json
import os

ipynb_path = r'c:\Users\ACER\Downloads\sertifikasi_runner\scriptt.ipynb'

with open(ipynb_path, 'r', encoding='utf-8') as f:
    nb = json.load(f)

for cell in nb.get('cells', []):
    if cell.get('cell_type') == 'code':
        source = cell.get('source', [])
        is_target = any('tokentot =' in line for line in source)
        if is_target:
            config_path = r'c:\Users\ACER\Downloads\sertifikasi_runner\config.ini'
            new_source = [
                "BASE_URL = \"https://simkatmawa.kemdiktisaintek.go.id\"\n",
                "CONFIG_PATH = r\"{}\"\n".format(config_path),
                "\n",
                "import configparser\n",
                "import requests\n",
                "\n",
                "config = configparser.ConfigParser()\n",
                "config.read(CONFIG_PATH, encoding='utf-8')\n",
                "email = config.get('credentials', 'email')\n",
                "password = config.get('credentials', 'password')\n",
                "\n",
                "print(f\"[*] Melakukan login API untuk: {email} ...\")\n",
                "resp = requests.post(f\"{BASE_URL}/api/login\", json={\"email\": email, \"password\": password})\n",
                "if resp.status_code == 200:\n",
                "    data = resp.json()\n",
                "    tokentot = data.get('token')\n",
                "    print(\"  [+] Login Berhasil! Token didapatkan.\")\n",
                "else:\n",
                "    print(\"  [-] Login Gagal:\", resp.text)\n",
                "    tokentot = \"\"\n"
            ]
            cell['source'] = new_source

with open(ipynb_path, 'w', encoding='utf-8') as f:
    json.dump(nb, f, indent=1)
print("Notebook patched successfully!")
