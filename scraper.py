"""
Fetches and parses RBI public notification notices from the live website.

Used by the web API to list circulars and download PDFs for gap analysis.
"""

import hashlib
import os
import re
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

RBI_NOTIFICATIONS_URL = "https://www.rbi.org.in/Scripts/NotificationUser.aspx"
RBI_BASE_URL = "https://www.rbi.org.in"
DOWNLOAD_DIR = os.path.join(os.path.dirname(__file__), "data", "circulars")
SEEN_FILE = os.path.join(os.path.dirname(__file__), "data", "seen_circulars.txt")

DATE_PATTERN = re.compile(
    r"^(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{1,2},\s+\d{4}$",
    re.IGNORECASE,
)

REQUEST_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

os.makedirs(DOWNLOAD_DIR, exist_ok=True)


def _get_seen_ids() -> set:
    if not os.path.exists(SEEN_FILE):
        return set()
    with open(SEEN_FILE, encoding="utf-8") as f:
        return set(line.strip() for line in f if line.strip())


def _mark_seen(circular_id: str):
    os.makedirs(os.path.dirname(SEEN_FILE), exist_ok=True)
    with open(SEEN_FILE, "a", encoding="utf-8") as f:
        f.write(circular_id + "\n")


def _normalize_pdf_url(href: str) -> str:
    if not href:
        return ""
    if href.startswith("http"):
        return href
    return urljoin(RBI_BASE_URL, href)


def _notice_id(pdf_url: str) -> str:
    return hashlib.md5(pdf_url.encode()).hexdigest()


def fetch_rbi_page_html() -> str:
    resp = requests.get(RBI_NOTIFICATIONS_URL, headers=REQUEST_HEADERS, timeout=20)
    resp.raise_for_status()
    return resp.text


def parse_rbi_notices(html: str, limit: int | None = None) -> list[dict]:
    """
    Parses the RBI notifications table into structured notice objects.
    """
    soup = BeautifulSoup(html, "html.parser")
    notices = []
    current_date = None

    for row in soup.find_all("tr"):
        cells = row.find_all("td")
        if not cells:
            continue

        cell_texts = [cell.get_text(" ", strip=True) for cell in cells]
        if cell_texts[0] and DATE_PATTERN.match(cell_texts[0]):
            current_date = cell_texts[0]

        pdf_link = row.find("a", href=re.compile(r"\.pdf$", re.IGNORECASE))
        if not pdf_link:
            continue

        pdf_url = _normalize_pdf_url(pdf_link.get("href", ""))
        if not pdf_url:
            continue

        title = pdf_link.get_text(" ", strip=True)
        if not title:
            title = cell_texts[0] if cell_texts else pdf_url

        file_size = None
        for text in reversed(cell_texts):
            if re.search(r"\bkb\b", text, re.IGNORECASE):
                file_size = text
                break

        notices.append({
            "id": _notice_id(pdf_url),
            "date": current_date,
            "title": title,
            "pdf_url": pdf_url,
            "file_size": file_size,
        })

        if limit and len(notices) >= limit:
            break

    return notices


def fetch_rbi_notices(limit: int = 50) -> list[dict]:
    html = fetch_rbi_page_html()
    return parse_rbi_notices(html, limit=limit)


def inspect_page_structure(limit: int = 10) -> list[dict]:
    notices = fetch_rbi_notices(limit=limit)
    for notice in notices:
        print(notice["date"], "|", notice["title"][:80], "|", notice["pdf_url"])
    return notices


def download_circular(pdf_url: str, circular_id: str | None = None) -> str:
    circular_id = circular_id or _notice_id(pdf_url)
    cached_path = os.path.join(DOWNLOAD_DIR, f"{circular_id}.pdf")
    if os.path.exists(cached_path):
        return cached_path

    resp = requests.get(pdf_url, headers=REQUEST_HEADERS, timeout=30)
    resp.raise_for_status()

    with open(cached_path, "wb") as f:
        f.write(resp.content)

    return cached_path


def check_for_new_circulars(on_new_circular=None) -> list[dict]:
    seen = _get_seen_ids()
    newly_found = []

    for notice in fetch_rbi_notices():
        if notice["id"] in seen:
            continue

        filepath = download_circular(notice["pdf_url"], notice["id"])
        _mark_seen(notice["id"])
        notice["filepath"] = filepath
        newly_found.append(notice)

        if on_new_circular:
            on_new_circular(filepath, notice["title"])

    return newly_found


def start_scheduler(interval_hours: int = 6, on_new_circular=None):
    """
    Starts a background job that polls RBI every `interval_hours`.
    Requires `apscheduler` (pip install apscheduler).
    """
    from apscheduler.schedulers.background import BackgroundScheduler

    scheduler = BackgroundScheduler()
    scheduler.add_job(
        lambda: check_for_new_circulars(on_new_circular=on_new_circular),
        "interval",
        hours=interval_hours,
    )
    scheduler.start()
    return scheduler


if __name__ == "__main__":
    print("Fetching RBI notifications...")
    inspect_page_structure()
