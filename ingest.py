import os
import requests
from dotenv import load_dotenv
from datetime import datetime

#Load environmnet variables from .env
load_dotenv()

NOTION_TOKEN = os.getenv("NOTION_TOKEN")
DATABASE_ID = os.getenv("NOTION_DATABASE_ID")

if not NOTION_TOKEN or not  DATABASE_ID:
    raise ValueError("NOTION_TOKEN or NOTION_DATABASE_ID is missing in .env")

#Notion API headers
headers = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Notion-Version": "2025-09-03",
    "Content-Type": "application/json"
}

#Minimal test
data = {
    "parent": {"database_id": DATABASE_ID},
    "properties": {
        "Name": {
            "title": [
                {"text": {"content": "Test entry from python"}}
            ]
        },
        "URL": {"url": "https://example.com"},
    }
}

#Send request to Notion
response = requests.post(
    "https://api.notion.com/v1/pages",
    headers=headers,
    json=data
)

print("Status code:", response.status_code)
print("Response:", response.text)