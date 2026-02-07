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
RSS_FEEDS = {
   # General Tech News
    "The Verge": "https://www.theverge.com/rss/index.xml",
    "Ars Technica": "https://feeds.arstechnica.com/arstechnica/index",
    "TechCrunch": "https://techcrunch.com/feed/",
    "Wired": "https://www.wired.com/feed/rss",
    
    # Cloud Platforms & Services
    "AWS Blog": "https://aws.amazon.com/blogs/aws/feed/",
    "AWS Architecture": "https://aws.amazon.com/blogs/architecture/feed/",
    "AWS Security": "https://aws.amazon.com/blogs/security/feed/",
    "Google Cloud Platform": "https://cloudblog.withgoogle.com/products/gcp/rss",
    "Cloudflare Blog": "https://blog.cloudflare.com/rss/",
    "Fly.io Blog": "https://fly.io/blog/feed.xml",
    
    # Infrastructure & Architecture
    "InfoQ Architecture": "https://feed.infoq.com/architecture-design",
    "Airbnb Engineering": "https://medium.com/feed/airbnb-engineering",
    "Meta Engineering": "https://engineering.fb.com/feed/",
    "Slack Engineering": "https://slack.engineering/feed/",
    "Spotify Engineering": "https://engineering.atspotify.com/feed/",
    
    # AI & Machine Learning
    "OpenAI Blog": "https://openai.com/blog/rss.xml",
    "Google AI Blog": "https://blog.research.google/feeds/posts/default",
    "DeepMind Blog": "https://deepmind.google/blog/rss.xml",
    "Hugging Face Blog": "https://huggingface.co/blog/feed.xml",
    "LangChain Blog": "https://blog.langchain.dev/rss/",
}

#Map to predifined categories as infra, cloud, or AI
FEED_CATEGORIES = {
    # General Tech News
    "The Verge": "General Tech",
    "Ars Technica": "General Tech",
    "TechCrunch": "General Tech",
    "Wired": "General Tech",
    
    # Cloud
    "AWS Blog": "Cloud",
    "AWS Architecture": "Cloud",
    "AWS Security": "Cloud",
    "Google Cloud Platform": "Cloud",
    "Cloudflare Blog": "Cloud",
    "Fly.io Blog": "Cloud",
    
    # Infra
    "InfoQ Architecture": "Infra",
    "Airbnb Engineering": "Infra",
    "Meta Engineering": "Infra",
    "Slack Engineering": "Infra",
    "Spotify Engineering": "Infra",
    
    # AI
    "OpenAI Blog": "AI",
    "Google AI Blog": "AI",
    "DeepMind Blog": "AI",
    "Hugging Face Blog": "AI",
    "LangChain Blog": "AI",
}

# Parse all RSS feeds
all_entries = []
MAX_ARTICLES_PER_FEED = 3

for source_name, feed_url in RSS_FEEDS.items():
    print(f"\n📰 Fetching {source_name}...")
    try:
        response = requests.get(feed_url, headers=RSS_HEADERS, timeout=10)
        if response.status_code == 200:
            feed = feedparser.parse(response.text)

            if not feed.entries:
                print(f"   ✓ Found 0 entries (skipping)")
                continue

            recent_entries = feed.entries[:MAX_ARTICLES_PER_FEED]
            print(f"   ✓ Found {len(feed.entries)} entries (taking {len(recent_entries)})")
            
            # Add source name to each entry for tracking
            for entry in recent_entries:

                if hasattr(entry, '__dict__'):
                    entry.source = source_name
                    all_entries.append(entry)
        else:
            print(f"   ✗ HTTP {response.status_code}")
    except Exception as e:
        print(f"   ✗ Error: {e}")

print(f"\n{'='*40}")
print(f"Total entries from all feeds: {len(all_entries)}")
print(f"{'='*40}\n")

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
    source = getattr(entry, 'source', 'Unknown')

    if not url:
        print(f"Skipping entry without URL: {title}")
        return False
    
    category = FEED_CATEGORIES.get(source, None)

    properties = {
        "Title": {"title": [{"text": {"content": title}}]},
        "URL": {"url": url},
        "Selected": {"checkbox": False},
        "Added Date": {"date": {"start": datetime.now(timezone.utc).isoformat()}},
    }

    if category:
        properties["Topic"] = {"select": {"name": category}}

    data = {
        "parent": {"database_id": DATABASE_ID},
        "properties": properties
    }

    #Send request to Notion
    response = requests.post(
        "https://api.notion.com/v1/pages",
        headers=NOTION_HEADERS,
        json=data
    )

    if response.status_code == 200:
        category_label = f"[{category}]" if category else "[Uncategorized]"
        print(f"✓ Added {category_label}: {title}")
        return True
    else:
        print(f"✗ Error adding: {title}")
        print(f"  Status code: {response.status_code}")
        print(f"  Response: {response.text}")
        return False

# Iterate through feed and add only new articles
added_count = 0
skipped_count = 0

for entry in all_entries:
    url = getattr(entry, "link", None)
    title = getattr(entry, 'title', 'Untitled')
    source = getattr(entry, 'source', 'Unknown')

    if url in existing_urls:
        print(f"⊝ Skipping (already exists): {title}")
        skipped_count += 1
    else:
        if add_article_to_notion_from_rss(entry):
            added_count += 1
        time.sleep(0.5)
        
print(f"\n{'='*40}")
print(f"Summary: {added_count} added, {skipped_count} skipped")