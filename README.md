# 🫙 SysJosh Weekly

A fully automated newsletter system that ingests RSS feeds daily, lets you hand-pick articles from a Notion dashboard, and delivers a clean HTML email to subscribers every Sunday at 8am EST.

---

## Demo / Screenshots

> <img width="760" height="1375" alt="Screenshot 2026-02-15 at 11 56 00 AM" src="https://github.com/user-attachments/assets/11a4e8f8-7a4b-4694-9c7a-20bce90bc24d" />


---

## Overview

### Problem

Keeping up with the tech industry across General Tech, Infrastructure, Cloud, and AI is time-consuming. Existing newsletters are either too broad, too frequent, or hard to find.

### Solution

SysJosh Weekly is a fully automated, self-hosted newsletter pipeline. RSS feeds from industry-leading engineering blogs are ingested daily into Notion. Each week, articles are hand-picked with a single checkbox and automatically sent to subscribers every Sunday morning. No third-party email service required.

---

## Key Features

- **Automated RSS ingestion** — pulls the latest articles from 22 feeds daily via GitHub Actions
- **Notion as CMS** — browse and select articles with a simple checkbox, no code needed
- **Duplicate detection** — never ingests the same article twice
- **Topic categorization** — articles automatically tagged as General Tech, Infra, Cloud, or AI
- **og:image fetching** — email previews include article images pulled from Open Graph metadata
- **Double opt-in** — subscribers confirm via email before being added to the active list
- **One-click unsubscribe** — every email includes a token-based unsubscribe link
- **No paid email service** — sends via Gmail SMTP, completely free
- **Fully automated sending** — GitHub Actions triggers every Sunday at 8am EST

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | Next.js, TypeScript, Tailwind CSS |
| Hosting | Vercel |
| Automation | Python, GitHub Actions |
| CMS / Database | Notion API |
| Email Sending | Gmail SMTP via Nodemailer (signup) + smtplib (newsletter) |
| RSS Parsing | feedparser |
| HTTP | requests |

---

## Architecture / System Design

```
┌─────────────────────────────────────────────────────────┐
│                     GitHub Actions                      │
│                                                         │
│  ingest.py (daily 5pm UTC)    send.py (Sunday 8am EST)  │
│         │                              │                │
│         ▼                              ▼                │
│   Fetch 22 RSS feeds           Fetch selected articles  │
│   Check for duplicates         Fetch active subscribers │
│   Add new → Notion DB          Build HTML email         │
│                                Fetch og:images          │
│                                Send via Gmail SMTP      │
│                                Uncheck articles         │
└─────────────────────────────────────────────────────────┘
         │                              │
         ▼                              ▼
┌─────────────────┐          ┌──────────────────┐
│   Notion CMS    │          │   Subscribers    │
│                 │          │                  │
│ Articles DB     │          │ Subscribers DB   │
│ - Title         │          │ - Email          │
│ - URL           │          │ - Token          │
│ - Topic         │          │ - Status         │
│ - Selected ✅   │          │ - Subscribed Date│
│ - Added Date    │          └──────────────────┘
└─────────────────┘

┌──────────────────────────────────────────────────────────┐
│                   news-frontend (Vercel)                 |
│                                                          │
│  /           → Signup landing page                       │
│  /confirm    → Double opt-in confirmation                │
│  /unsubscribe→ One-click + manual unsubscribe            │
│  /privacy    → Privacy policy                            │
│  /terms      → Terms of service                          │
│                                                          │
│  /api/subscribe   → Add pending subscriber to Notion     │
│  /api/confirm     → Set subscriber status to active      │
│  /api/unsubscribe → Set subscriber status to unsubscribed│
└──────────────────────────────────────────────────────────┘
```

---

## Getting Started

### Clone and Prepare

```bash
# Clone the repo
git clone https://github.com/josh-a-rubio/sysjosh-news.git
cd sysjosh-news

# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

Create a `.env` file in the root:

```env
NOTION_TOKEN=your_notion_token
ARTICLES_DATABASE_ID=your_articles_db_id
SUBSCRIBERS_DATABASE_ID=your_subscribers_db_id
GMAIL_USER=your_gmail@gmail.com
GMAIL_APP_PASSWORD=your_gmail_app_password
```

### Build

No build step required for the Python scripts. For the frontend, clone and run the separate repo:
```bash
git clone https://github.com/josh-a-rubio/news-frontend.git
```

Import the repo into Vercel and add the following environment variables in **Settings → Environment Variables**:
```
NOTION_TOKEN=your_notion_token
SUBSCRIBERS_DATABASE_ID=your_subscribers_db_id
GMAIL_USER=your_gmail@gmail.com
GMAIL_APP_PASSWORD=your_gmail_app_password
```

### Run

Run the ingest script locally:

```bash
python ingest.py
```

Run the send script locally:

```bash
python send.py
```

In production both scripts run automatically via GitHub Actions. Add all `.env` values as repository secrets in **Settings → Secrets and variables → Actions**.

---

## Usage / Application Flow

1. **Daily at 5pm** — `ingest.py` fetches the latest 3 articles from each of 22 RSS feeds and adds new ones to the Notion Articles database, tagged by topic
2. **Throughout the week** — browse the Notion Articles database and check the `Selected` checkbox on articles you want to include
3. **Sunday 8am EST** — `send.py` fetches all selected articles, groups them by topic, fetches og:images, builds a personalized HTML email for each active subscriber, sends via Gmail SMTP, then unchecks all selected articles
4. **Subscriber signup** — visitors go to the frontend, enter their email, receive a confirmation email, click the link to activate their subscription
5. **Unsubscribe** — every email includes a one-click unsubscribe link with a unique token, or subscribers can manually unsubscribe via the frontend

---

## Security Considerations and Limitations

- **No custom domain** — emails are sent from a Gmail address which may affect deliverability and spam scoring
- **Gmail SMTP limits** — Gmail has a daily sending limit of ~500 emails; not suitable for large lists
- **Notion as database** — Notion API has rate limits and is not designed as a production database; may need migration at scale
- **Token-based unsubscribe** — tokens are UUIDs stored in Notion; no expiry currently implemented
- **No open/click tracking** — there is currently no analytics on email engagement
- **Environment variables** — all secrets stored as GitHub Actions secrets and Vercel environment variables; never committed to the repo

---

## Design Decisions

**Why Notion as a CMS?**
Zero setup, great UI for manually curating articles, free tier is sufficient, and the API is straightforward.

**Why Gmail SMTP over a service like Resend or SendGrid?**
Free and requires no custom domain. Sufficient for a small growing list. A proper email service would be the next step when scaling.

**Why GitHub Actions for scheduling?**
Free, reliable, and keeps all automation in one repo with no separate server needed.

**Why double opt-in?**
Ensures list quality, reduces spam complaints, and is best practice for any email newsletter.

**Why footer outside the email card?**
Gmail clips emails over ~102kb. Keeping the footer outside the main content card ensures the unsubscribe link is always visible without expanding the clipped email.

**Why og:image fetching?**
Adds visual context to articles in the email without requiring manual image curation.

---

## Roadmap / Future Work

- [ ] Custom domain for improved email deliverability
- [ ] Migrate to a dedicated email service (Resend, SendGrid) for scale
- [ ] Open rate and click tracking analytics
- [ ] Archive page on the frontend for past issues
- [ ] Subscriber count display on the landing page
- [ ] Token expiry for unsubscribe links
- [ ] A/B testing for email subject lines and layouts

---

## License

MIT License

---

## Author

**Josh A. Rubio**
