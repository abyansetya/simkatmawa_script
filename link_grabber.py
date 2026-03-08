from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
import csv

SCOPES = ['https://www.googleapis.com/auth/drive.readonly']

def authenticate():
    flow = InstalledAppFlow.from_client_secrets_file(
        'credentials.json', SCOPES)
    creds = flow.run_local_server(port=0)
    return creds

def get_pdf_links(folder_id):

    creds = authenticate()
    service = build('drive', 'v3', credentials=creds)

    query = f"'{folder_id}' in parents and mimeType='application/pdf'"

    results = service.files().list(
        q=query,
        fields="files(id, name)"
    ).execute()

    files = results.get('files', [])

    with open("Agribisnis_S1_(3)_2025_1.pdf.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["File Name", "Link"])

        for file in files:
            link = f"https://drive.google.com/file/d/{file['id']}/view"
            writer.writerow([file['name'], link])
            print(file['name'], link)

if __name__ == "__main__":

    folder_id = "1uJT2Dq66sH42hjrddckGAQYR-avJ2ipY"
    get_pdf_links(folder_id)