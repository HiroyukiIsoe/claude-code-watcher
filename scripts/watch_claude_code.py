import os
import sys
import requests
import feedparser
from datetime import datetime, timezone

GITHUB_TOKEN = os.environ["GITHUB_TOKEN"]
REPOSITORY = os.environ["GITHUB_REPOSITORY"]

HEADERS = {
    "Authorization": f"Bearer {GITHUB_TOKEN}",
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
    "User-Agent": "claude-code-watcher",
}

ANTHROPIC_BLOG_RSS = "https://www.anthropic.com/news/rss.xml"
RELEASES_API = "https://api.github.com/repos/anthropics/claude-code/releases"

KEYWORDS = [
    "claude code",
    "agentic coding",
    "anthropic teams use claude code",
]

LABELS = ["claude-code-watch"]

def fetch_blog_entries():
    feed = feedparser.parse(ANTHROPIC_BLOG_RSS)
    items = []

    for entry in feed.entries[:20]:
        title = entry.get("title", "")
        link = entry.get("link", "")
        summary = entry.get("summary", "")
        text = f"{title}\n{summary}".lower()

        if any(k in text for k in KEYWORDS):
            items.append({
                "source": "anthropic-blog",
                "title": title,
                "url": link,
                "published": entry.get("published", ""),
                "body": summary,
                "unique_key": link,
            })
    return items


def fetch_releases():
    resp = requests.get(RELEASES_API, headers=HEADERS, timeout=30)
    resp.raise_for_status()

    items = []
    for rel in resp.json()[:10]:
        tag = rel.get("tag_name", "")
        name = rel.get("name") or tag
        url = rel.get("html_url", "")
        body = rel.get("body", "")
        published = rel.get("published_at", "")

        items.append({
            "source": "github-release",
            "title": f"Claude Code release: {name}",
            "url": url,
            "published": published,
            "body": body[:3000],
            "unique_key": f"release:{tag}",
        })
    return items


def search_existing_issue(unique_key):
    query = f'repo:{REPOSITORY} in:title,in:body "{unique_key}" type:issue'
    url = "https://api.github.com/search/issues"
    resp = requests.get(url, headers=HEADERS, params={"q": query}, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    return data.get("total_count", 0) > 0


def ensure_label(name):
    url = f"https://api.github.com/repos/{REPOSITORY}/labels/{name}"
    resp = requests.get(url, headers=HEADERS, timeout=30)

    if resp.status_code == 404:
        create_url = f"https://api.github.com/repos/{REPOSITORY}/labels"
        payload = {
            "name": name,
            "color": "0e8a16",
            "description": "Items collected by Claude Code watcher",
        }
        create_resp = requests.post(create_url, headers=HEADERS, json=payload, timeout=30)
        create_resp.raise_for_status()
    elif not resp.ok:
        resp.raise_for_status()


def create_issue(item):
    issue_title = f"[{item['source']}] {item['title']}"
    issue_body = f"""## source
{item['source']}

## published
{item['published']}

## url
{item['url']}

## unique_key
{item['unique_key']}

## summary
{item['body']}

## triage
- [ ] 読む
- [ ] 試す
- [ ] スキップ
"""
    url = f"https://api.github.com/repos/{REPOSITORY}/issues"
    payload = {
        "title": issue_title,
        "body": issue_body,
        "labels": LABELS,
    }
    resp = requests.post(url, headers=HEADERS, json=payload, timeout=30)
    resp.raise_for_status()
    print(f"Created issue: {issue_title}")


def main():
    for label in LABELS:
        ensure_label(label)

    items = []
    items.extend(fetch_blog_entries())
    items.extend(fetch_releases())

    created = 0
    for item in items:
        try:
            if search_existing_issue(item["unique_key"]):
                print(f"Skip existing: {item['unique_key']}")
                continue

            create_issue(item)
            created += 1
        except Exception as e:
            print(f"Failed for {item['unique_key']}: {e}", file=sys.stderr)

    print(f"Done. created={created}")


if __name__ == "__main__":
    main()
