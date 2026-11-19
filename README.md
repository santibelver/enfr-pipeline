# Pipeline ENFR (n8n Cloud + GitHub Actions + Streamlit Community Cloud)

n8n Cloud orquesta → GitHub Actions ejecuta `scripts/etl.py` y `scripts/eda.py` → CSVs en `data/` → `app.py` es el dashboard.

Secrets del repo (Settings → Secrets and variables → Actions):
- `GDRIVE_SA_JSON`: contenido completo del JSON de la cuenta de servicio de Google.
- `DRIVE_RAW_FOLDER_ID`: ID de la carpeta de Drive con los .txt (lo que va después de /folders/ en la URL).

Dashboard: https://share.streamlit.io → New app → este repo, rama main, archivo `app.py`.
