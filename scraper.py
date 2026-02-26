"""
scraper.py — Scrapes WatchDNA.com and builds the knowledge base.
Run manually or automatically via GitHub Actions daily cron.
"""

import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import json
import os
from datetime import datetime, timezone

BASE_URL = os.environ.get("SHOPIFY_URL", "https://watchdna.com")
MAX_PAGES = 80
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; WatchDNAChatbot/1.0)"}

# Priority pages to always scrape first
PRIORITY_PATHS = [
    "/",
    "/pages/brands-dna",
    "/pages/our-vision",
    "/pages/watchmaking101",
    "/pages/watch-aficionados",
    "/pages/worldwatchday",
    "/pages/redbar",
    "/collections/watches",
    "/collections/accessories",
    "/tools/storelocator/directory",
    "/pages/media-directory",
    "/pages/contributors",
    "/pages/groups",
    "/pages/platforms",
    "/pages/committee",
    "/pages/dailyroutine",
    "/pages/1fortheplanet",
    "/pages/b1g1-business-for-good",
    "/pages/watchesandwonders",
    "/pages/windupwatchfair",
    "/pages/dubai-watch-week",
    "/pages/jck",
    "/blogs/press",
    "/blogs/watch_enthusiast",
]


def get_text(soup: BeautifulSoup) -> str:
    for tag in soup(["script", "style", "noscript", "svg", "header", "footer", "nav"]):
        tag.decompose()
    return " ".join(soup.get_text(separator=" ").split())


def scrape_site(base_url: str) -> list[dict]:
    visited = set()
    domain = urlparse(base_url).netloc

    # Start with priority pages, then crawl others
    to_visit = [base_url + p for p in PRIORITY_PATHS]
    pages = []

    while to_visit and len(visited) < MAX_PAGES:
        url = to_visit.pop(0)
        # Normalize URL
        url = url.split("#")[0].split("?")[0].rstrip("/") or base_url
        if url in visited:
            continue
        visited.add(url)

        try:
            resp = requests.get(url, headers=HEADERS, timeout=12)
            if resp.status_code != 200:
                print(f"  ✗ {url} (status {resp.status_code})")
                continue
            if "text/html" not in resp.headers.get("Content-Type", ""):
                continue

            soup = BeautifulSoup(resp.text, "html.parser")
            text = get_text(soup)
            title = soup.title.string.strip() if soup.title else url

            if len(text) > 150:
                pages.append({"url": url, "title": title, "content": text[:3500]})
                print(f"  ✓ [{len(pages)}] {title[:60]} ({len(text)} chars)")

            # Collect more links from same domain
            for a in soup.find_all("a", href=True):
                href = urljoin(base_url, a["href"]).split("#")[0].split("?")[0]
                if urlparse(href).netloc == domain and href not in visited and href not in to_visit:
                    to_visit.append(href)

        except Exception as e:
            print(f"  ✗ {url}: {e}")

    return pages


def main():
    print(f"Starting WatchDNA scrape: {BASE_URL}")
    print(f"Time: {datetime.now(timezone.utc).isoformat()}\n")

    pages = scrape_site(BASE_URL)
    print(f"\n✅ Scraped {len(pages)} pages total.")

    output = {
        "scraped_at": datetime.now(timezone.utc).isoformat(),
        "base_url": BASE_URL,
        "page_count": len(pages),
        "pages": pages,
    }

    with open("knowledge_base.json", "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print("Saved to knowledge_base.json ✓")


if __name__ == "__main__":
    main()
