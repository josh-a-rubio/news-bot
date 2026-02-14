import os
import smtplib
import requests
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime
from html.parser import HTMLParser
from dotenv import dotenv_values

# Load env
config = dotenv_values(".env")
NOTION_TOKEN = config.get("NOTION_TOKEN") or os.environ.get("NOTION_TOKEN")
ARTICLES_DB_ID = config.get("ARTICLES_DATABASE_ID") or os.environ.get("ARTICLES_DATABASE_ID")
SUBSCRIBERS_DB_ID = config.get("SUBSCRIBERS_DATABASE_ID") or os.environ.get("SUBSCRIBERS_DATABASE_ID")
GMAIL_USER = config.get("GMAIL_USER") or os.environ.get("GMAIL_USER")
GMAIL_APP_PASSWORD = config.get("GMAIL_APP_PASSWORD") or os.environ.get("GMAIL_APP_PASSWORD")
BASE_URL = config.get("NEXT_PUBLIC_BASE_URL") or os.environ.get("NEXT_PUBLIC_BASE_URL")

NOTION_HEADERS = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28",
}

class OGImageParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.og_image = None

    def handle_starttag(self, tag, attrs):
        if tag == "meta":
            attrs_dict = dict(attrs)
            if attrs_dict.get("property") == "og:image":
                self.og_image = attrs_dict.get("content")

def get_og_image(url):
    try:
        res = requests.get(url, timeout=5, headers={"User-Agent": "Mozilla/5.0"})
        parser = OGImageParser()
        parser.feed(res.text)
        return parser.og_image
    except Exception:
        return None

def get_selected_articles():
    res = requests.post(
        f"https://api.notion.com/v1/databases/{ARTICLES_DB_ID}/query",
        headers=NOTION_HEADERS,
        json={
            "filter": {
                "property": "Selected",
                "checkbox": { "equals": True }
            }
        }
    )
    return res.json().get("results", [])

def uncheck_article(page_id):
    requests.patch(
        f"https://api.notion.com/v1/pages/{page_id}",
        headers=NOTION_HEADERS,
        json={
            "properties": {
                "Selected": { "checkbox": False }
            }
        }
    )

def get_active_subscribers():
    res = requests.post(
        f"https://api.notion.com/v1/databases/{SUBSCRIBERS_DB_ID}/query",
        headers=NOTION_HEADERS,
        json={
            "filter": {
                "property": "Status",
                "select": { "equals": "active" }
            }
        }
    )
    return res.json().get("results", [])

def get_subscriber_email_and_token(sub):
    props = sub["properties"]
    email = props.get("Email", {}).get("email", "")
    token_list = props.get("Token", {}).get("rich_text", [])
    token = token_list[0]["text"]["content"] if token_list else ""
    return email, token

def build_email_html(articles, token):
    date_str = datetime.now().strftime("%B %d, %Y")

    # Group by topic and fetch og:images
    topics = {}
    for article in articles:
        props = article["properties"]
        title_list = props.get("Title", {}).get("title", [])
        title = title_list[0]["text"]["content"] if title_list else "Untitled"
        url = props.get("URL", {}).get("url", "#")
        topic_obj = props.get("Topic", {}).get("select", {})
        topic = topic_obj.get("name", "General") if topic_obj else "General"

        # Fetch og:image
        og_image = get_og_image(url)

        # Skip article if no image
        if not og_image:
            continue

        if topic not in topics:
            topics[topic] = []
        topics[topic].append({"title": title, "url": url, "image": og_image})

    # Build topic sections in order
    sections = ""
    for topic, items in topics.items():
        articles_html = ""
        for item in items:
            articles_html += f'''
                <div style="margin-bottom: 1.5rem;">
                    <a href="{item["url"]}" style="color: #111; text-decoration: none; 
                              font-size: 0.95rem; font-weight: 600; line-height: 1.4;">
                        {item["title"]}
                    </a>
                    <div style="margin-top: 0.6rem;">
                        <a href="{item["url"]}">
                            <img src="{item["image"]}" alt="{item["title"]}"
                                 style="width: 100%; max-width: 100%; border-radius: 8px; 
                                        display: block; border: 1px solid #e5e5e5;"/>
                        </a>
                    </div>
                </div>
            '''

        sections += f'''
            <div style="margin-bottom: 2rem;">
                <div style="margin-bottom: 1rem;">
                    <span style="display: inline-block; padding: 0.2rem 0.75rem;
                                 background: rgba(74,144,217,0.12); border-radius: 100px;
                                 font-size: 0.75rem; color: #4A90D9; font-weight: 600;">
                        {topic}
                    </span>
                </div>
                {articles_html}
            </div>
        '''

    unsubscribe_url = f"{BASE_URL}/unsubscribe?token={token}"

    html = f"""
    <!DOCTYPE html>
    <html>
    <body style="margin: 0; padding: 0; background: #f5f5f5; 
                 font-family: Inter, -apple-system, BlinkMacSystemFont, sans-serif;">
        <div style="max-width: 600px; margin: 0 auto; padding: 2rem 1rem;">

            <!-- Header Banner -->
            <div style="background: #fff; border: 1px solid #e5e5e5; border-radius: 12px;
                        padding: 1.25rem 1.5rem; margin-bottom: 1rem;
                        box-shadow: 0 4px 24px rgba(0,0,0,0.06);
                        display: flex; align-items: center; justify-content: space-between;">
                <div style="display: flex; align-items: center; gap: 0.75rem;">
                    <span style="font-size: 1.5rem;">🫙</span>
                    <div>
                        <p style="margin: 0; font-size: 1rem; font-weight: 700; 
                                  color: #111; letter-spacing: -0.02em;">
                            SysJosh Weekly
                        </p>
                        <p style="margin: 0; font-size: 0.7rem; color: #999;">{date_str}</p>
                    </div>
                </div>
            </div>

            <!-- Main Card -->
            <div style="background: #fff; border: 1px solid #e5e5e5; border-radius: 12px;
                        padding: 2rem 1.5rem; box-shadow: 0 4px 24px rgba(0,0,0,0.06);">

                <!-- Intro -->
                <p style="font-size: 0.95rem; color: #111; margin: 0 0 1.5rem; line-height: 1.6;">
                    Happy Sunday! Here's this week's picks. ☕
                </p>

                <div style="height: 1px; background: #e5e5e5; margin-bottom: 1.75rem;"></div>

                <!-- Articles -->
                {sections}

            </div>

            <!-- Footer outside card -->
            <p style="font-size: 0.75rem; color: #999; text-align: center; 
                    margin-top: 1rem; line-height: 1.8;">
                You're receiving this because you subscribed to SysJosh Weekly.<br>
                <a href="{unsubscribe_url}" style="color: #999;">Unsubscribe</a>
            </p>

        </div>
    </body>
    </html>
    """
    return html

def send_email(to_email, html):
    msg = MIMEMultipart("alternative")
    msg["Subject"] = "SysJosh Weekly — Your Sunday Tech Briefing"
    msg["From"] = f"SysJosh Weekly (no-reply) <{GMAIL_USER}>"
    msg["To"] = to_email
    msg.attach(MIMEText(html, "html"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(GMAIL_USER, GMAIL_APP_PASSWORD)
        server.sendmail(GMAIL_USER, to_email, msg.as_string())

def main():
    print("Fetching selected articles...")
    articles = get_selected_articles()
    if not articles:
        print("No articles selected. Skipping send.")
        return

    print(f"Found {len(articles)} articles.")

    print("Fetching active subscribers...")
    subscribers = get_active_subscribers()
    if not subscribers:
        print("No active subscribers. Skipping send.")
        return

    print(f"Found {len(subscribers)} subscribers.")

    for sub in subscribers:
        email, token = get_subscriber_email_and_token(sub)
        if not email:
            continue
        html = build_email_html(articles, token)
        send_email(email, html)
        print(f"Sent to {email}")

    print("Unchecking articles...")
    for article in articles:
        uncheck_article(article["id"])

    print("Done!")

if __name__ == "__main__":
    main()