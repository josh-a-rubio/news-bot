import os
import requests
import feedparser
import time
from dotenv import load_dotenv
from datetime import datetime, timezone

#Load environmnet variables from .env
load_dotenv()

NOTION_TOKEN = os.getenv("NOTION_TOKEN")
DATABASE_ID = os.getenv("NOTION_DATABASE_ID")

if not NOTION_TOKEN or not  DATABASE_ID:
    raise ValueError("NOTION_TOKEN or NOTION_DATABASE_ID is missing in .env")

#Notion API headers
NOTION_HEADERS = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json"
}

RSS_HEADERS = {"User-Agent": "Mozilla/5.0"}

# RSS blog feeds
RSS_FEED_URL = "https://www.theverge.com/rss/index.xml"

# Parse RSS feed
response = requests.get(RSS_FEED_URL, headers=RSS_HEADERS)
feed = feedparser.parse(response.text)
print("HTTP status:", response.status_code)



# Debug: check entries
print(f"Found {len(feed.entries)} entries in feed")
for i, entry in enumerate(feed.entries[:5]):  # show first 5 for sanity
    print(f"{i+1}. Title: {getattr(entry, 'title', 'Untitled')}")
    print(f"   URL: {getattr(entry, 'link', 'No URL')}")
    print("-" * 20)


# Fetch existing articles from Notion
def get_existing_urls():
    url_list = []
    query_url = f"https://api.notion.com/v1/databases/{DATABASE_ID}/query"
    has_more = True
    start_cursor = None

    while has_more:
        payload = {"page_size": 100}
        if start_cursor:
            payload["start_cursor"] = start_cursor

        response = requests.post(query_url, headers=NOTION_HEADERS, json=payload)

        #Error check for query
        if response.status_code != 200:
            print(f"Error querying Notion database: {response.status_code}")
            print(response.text)
            return set()

        data = response.json()

        for page in data.get("results", []):
            properties = page.get("properties", {})
            url_prop = properties.get("URL", {}).get("url")
            if url_prop:
                url_list.append(url_prop)

        has_more = data.get("has_more", False)
        start_cursor = data.get("next_cursor")

    return set(url_list)

print("\nFetching existing URLs from Notion...")
existing_urls = get_existing_urls()
print(f"Found {len(existing_urls)} existing articles in Notion\n")

# Parse RSS feed
def add_article_to_notion_from_rss(entry):
    """Add an article to Notion database."""
    title = getattr(entry, 'title', 'Untitled')
    url = getattr(entry, 'link', None)


    if not url:
        print(f"Skipping entry without URL: {title}")
        return False

    data = {
        "parent": {"database_id": DATABASE_ID},
        "properties": {
            "Title": {"title": [{"text": {"content": title}}]},
            "URL": {"url": url},
            "Selected": {"checkbox": False},
            "Added Date": {"date": {"start": datetime.now(timezone.utc).isoformat()}},
        }
    }

    #Send request to Notion
    response = requests.post(
        "https://api.notion.com/v1/pages",
        headers=NOTION_HEADERS,
        json=data
    )

    if response.status_code == 200:
        print(f"✓ Added: {title}")
        return True
    else:
        print(f"✗ Error adding: {title}")
        print(f"  Status code: {response.status_code}")
        print(f"  Response: {response.text}")
        return False

# Iterate through feed and add only new articles
added_count = 0
skipped_count = 0

for entry in feed.entries:
    url = getattr(entry, "link", None)
    title = getattr(entry, 'title', 'Untitled')

    if url in existing_urls:
        print(f"⊝ Skipping (already exists): {title}")
        skipped_count += 1
    else:
        if add_article_to_notion_from_rss(entry):
            added_count += 1
        time.sleep(0.5)
        
print(f"\n{'='*40}")
print(f"Summary: {added_count} added, {skipped_count} skipped")