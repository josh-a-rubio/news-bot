import os
import smtplib
import requests
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
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
    # Group by topic
    topics = {}
    for article in articles:
        props = article["properties"]
        title_list = props.get("Title", {}).get("title", [])
        title = title_list[0]["text"]["content"] if title_list else "Untitled"
        url = props.get("URL", {}).get("url", "#")
        topic_list = props.get("Topic", {}).get("select", {})
        topic = topic_list.get("name", "General") if topic_list else "General"

        if topic not in topics:
            topics[topic] = []
        topics[topic].append({"title": title, "url": url})

    # Build HTML
    sections = ""
    for topic, items in topics.items():
        links = "".join(
            f'<li><a href="{item["url"]}">{item["title"]}</a></li>'
            for item in items
        )
        sections += f"<h3>{topic}</h3><ul>{links}</ul>"

    unsubscribe_url = f"{BASE_URL}/unsubscribe?token={token}"

    html = f"""
    <div style="font-family: Inter, sans-serif; max-width: 600px; margin: 0 auto; padding: 2rem;">
        <h2>🫙 SysJosh Weekly</h2>
        <p>Your Sunday morning tech briefing</p>
        <hr>
        {sections}
        <hr>
        <p style="font-size: 0.75rem; color: #bbb;">
            You're receiving this because you subscribed to SysJosh Weekly.<br>
            <a href="{unsubscribe_url}" style="color: #bbb;">Unsubscribe</a>
        </p>
    </div>
    """
    return html

def send_email(to_email, html):
    msg = MIMEMultipart("alternative")
    msg["Subject"] = "SysJosh Weekly — Your Sunday Tech Briefing"
    msg["From"] = f"SysJosh Weekly <{GMAIL_USER}>"
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