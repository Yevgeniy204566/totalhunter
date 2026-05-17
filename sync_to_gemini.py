import os
import time

SA_PATH = r"C:\BattleBot\service_account.json"
SCOPES  = ["https://www.googleapis.com/auth/documents"]

FILES = [
    (r"C:\BattleBot\ANTI-PATTERNS.md",
     "14JVf2k-hzw9Aci0Ju8yBPGFKoT8n3RuX9PSGp8j3qvE"),
    (r"C:\BattleBot\CLAUDE.md",
     "1CBEhm1g1pGLHNwhpkcRZtNA03kOZ9N-N00gsGlGuM3I"),
    (r"C:\Users\Admin\.claude\projects\C--BattleBot\memory\MEMORY.md",
     "18xMjHfyq754LuhrIf1zWgynm3SAFLWimA0cYiN37ZoA"),
    (r"C:\BattleBot\STATE.md",
     "10rqfqo2UCF25FZWRj9TCZOaIJCGuav6ZP_JyJUVEYdA"),
]


def read_local(path):
    if not os.path.exists(path):
        return None
    if os.path.getsize(path) == 0:
        return None
    with open(path, encoding="utf-8") as f:
        return f.read()


def replace_doc(service, doc_id, content):
    doc = service.documents().get(documentId=doc_id).execute()
    end_index = doc["body"]["content"][-1]["endIndex"]
    requests = []
    if end_index > 2:
        requests.append({
            "deleteContentRange": {
                "range": {"startIndex": 1, "endIndex": end_index - 1}
            }
        })
    requests.append({
        "insertText": {
            "location": {"index": 1},
            "text": content,
        }
    })
    service.documents().batchUpdate(
        documentId=doc_id,
        body={"requests": requests},
    ).execute()


def sync(service):
    ok = 0
    for path, doc_id in FILES:
        name = os.path.basename(path)
        content = read_local(path)
        if content is None:
            print(f"  [SKIP] {name}")
            time.sleep(1)
            continue
        try:
            replace_doc(service, doc_id, content)
            print(f"  [OK]   {name}")
            ok += 1
        except Exception as e:
            print(f"  [ERR]  {name} → {e}")
        time.sleep(1)
    print(f"\n  Готово: {ok}/{len(FILES)}")


def build_service():
    from google.oauth2.service_account import Credentials
    from googleapiclient.discovery import build

    creds = Credentials.from_service_account_file(SA_PATH, scopes=SCOPES)
    return build("docs", "v1", credentials=creds)


if __name__ == "__main__":
    print("=== Gemini Sync ===\n")
    svc = build_service()
    sync(svc)
