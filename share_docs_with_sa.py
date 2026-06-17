"""
Одноразовый скрипт — расшаривает 4 Google Docs с Service Account.
Запускать один раз. После этого sync_to_gemini.py работает вечно без браузера.
"""
import os
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

CREDS_PATH = r"C:\BattleBot\credentials.json"
TOKEN_PATH  = r"C:\BattleBot\token.json"
SCOPES = ["https://www.googleapis.com/auth/drive"]

SA_EMAIL = "gemini-sync@digital-arcade-274010.iam.gserviceaccount.com"

DOC_IDS = [
    ("ANTI-PATTERNS.md", "14JVf2k-hzw9Aci0Ju8yBPGFKoT8n3RuX9PSGp8j3qvE"),
    ("CLAUDE.md",        "1CBEhm1g1pGLHNwhpkcRZtNA03kOZ9N-N00gsGlGuM3I"),
    ("MEMORY.md",        "18xMjHfyq754LuhrIf1zWgynm3SAFLWimA0cYiN37ZoA"),
    ("STATE.md",         "10rqfqo2UCF25FZWRj9TCZOaIJCGuav6ZP_JyJUVEYdA"),
]


def get_drive_service():
    # удаляем протухший токен чтобы форсировать браузерный вход
    if os.path.exists(TOKEN_PATH):
        os.remove(TOKEN_PATH)
    flow = InstalledAppFlow.from_client_secrets_file(CREDS_PATH, SCOPES)
    creds = flow.run_local_server(port=0)
    return build("drive", "v3", credentials=creds)


def share_all(service):
    permission = {
        "type": "user",
        "role": "writer",
        "emailAddress": SA_EMAIL,
    }
    for name, doc_id in DOC_IDS:
        try:
            service.permissions().create(
                fileId=doc_id,
                body=permission,
                sendNotificationEmail=False,
            ).execute()
            print(f"  [OK]   {name}")
        except Exception as e:
            print(f"  [ERR]  {name} -> {e}")


if __name__ == "__main__":
    print(f"=== Расшариваем 4 документа с {SA_EMAIL} ===\n")
    svc = get_drive_service()
    share_all(svc)
    print("\nГотово! Теперь sync_to_gemini.py работает без браузера навсегда.")
