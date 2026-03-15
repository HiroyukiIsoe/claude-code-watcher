import os
import sys
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

GITHUB_TOKEN = os.environ["GITHUB_TOKEN"]
REPOSITORY = os.environ["GITHUB_REPOSITORY"]

HEADERS = {
    "Authorization": f"Bearer {GITHUB_TOKEN}",
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
    "User-Agent": "claude-code-watcher",
}

WEB_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/145.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "ja,en-US;q=0.9,en;q=0.8",
}

NEWSROOM_URL = "https://www.anthropic.com/news"
RELEASES_API = "https://api.github.com/repos/anthropics/claude-code/releases"

KEYWORDS = [
    "claude code",
    "agentic coding",
    "coding",
    "subagents",
    "hooks",
    "mcp",
]

LABELS = ["claude-code-watch"]


def fetch_newsroom_entries():
    resp = requests.get(NEWSROOM_URL, headers=WEB_HEADERS, timeout=30)
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")
    items = []
    seen = set()

    # Newsroom内のリンクを広めに取得
    for a in soup.select('a[href^="/news/"]'):
        href = a.get("href", "").strip()
        if not href or href == "/news":
            continue

        url = urljoin("https://www.anthropic.com", href)
        title = " ".join(a.get_text(" ", strip=True).split())
        text = title.lower()

        if url in seen:
            continue
        seen.add(url)

        # タイトルが空でもURL末尾で少し判定できるようにする
        url_text = url.lower()
        if not any(k in text or k in url_text for k in KEYWORDS):
            continue

        items.append({
            "source": "anthropic-news",
            "title": title or href.split("/")[-1],
            "url": url,
            "published": "",
            "body": "",
            "unique_key": url,
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
    query = f'repo:{REPOSITORY} in:title,body "{unique_key}" is:issue'
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
    items.extend(fetch_newsroom_entries())
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
