import os
import time

CREDS_PATH = r"C:\BattleBot\credentials.json"
TOKEN_PATH  = r"C:\BattleBot\token.json"
SCOPES      = ["https://www.googleapis.com/auth/documents"]

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
    raise NotImplementedError


def replace_doc(service, doc_id, content):
    raise NotImplementedError


def sync(service):
    raise NotImplementedError


def build_service():
    raise NotImplementedError


if __name__ == "__main__":
    print("=== Gemini Sync ===\n")
    svc = build_service()
    sync(svc)
