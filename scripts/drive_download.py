"""Descarga los .txt crudos de una carpeta de Google Drive a data/raw/ (cuenta de servicio, solo lectura)."""
import io, json, os
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

FOLDER_ID = os.environ["DRIVE_RAW_FOLDER_ID"]
creds = service_account.Credentials.from_service_account_info(
    json.loads(os.environ["GDRIVE_SA_JSON"]),
    scopes=["https://www.googleapis.com/auth/drive.readonly"])
svc = build("drive", "v3", credentials=creds, cache_discovery=False)

os.makedirs("data/raw", exist_ok=True)
archivos, token = [], None
while True:
    r = svc.files().list(
        q=f"'{FOLDER_ID}' in parents and trashed = false and name contains '.txt'",
        fields="nextPageToken, files(id, name, size)", pageToken=token,
        supportsAllDrives=True, includeItemsFromAllDrives=True).execute()
    archivos += r["files"]
    token = r.get("nextPageToken")
    if not token:
        break

assert archivos, "No se encontraron .txt en la carpeta (¿compartiste la carpeta con el email de la cuenta de servicio?)"
for f in archivos:
    buf = io.FileIO(os.path.join("data/raw", f["name"]), "wb")
    dl = MediaIoBaseDownload(buf, svc.files().get_media(fileId=f["id"], supportsAllDrives=True), chunksize=32 * 1024 * 1024)
    done = False
    while not done:
        _, done = dl.next_chunk()
    buf.close()
    print("descargado:", f["name"])
