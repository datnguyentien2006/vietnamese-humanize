"""Liệt kê các model Groq mà API key hiện tại có thể truy cập."""
import os
import sys

from dotenv import load_dotenv
from groq import Groq

load_dotenv()

api_key = os.environ.get("GROQ_API_KEY", "").strip()
if not api_key:
    print("LỖI: GROQ_API_KEY chưa được set trong .env", file=sys.stderr)
    sys.exit(1)

client = Groq(api_key=api_key)
models = client.models.list()

print(f"Tìm thấy {len(models.data)} model khả dụng:\n")
for model in sorted(models.data, key=lambda m: m.id):
    print(f"  - {model.id}")