"""
Polls RBI's public notifications page for new circulars, downloads any
new PDF, and (optionally) triggers the regtrack pipeline against it.

NOTE: run `inspect_page_structure()` once against the live RBI site to
confirm the CSS selector still matches before relying on this in a demo --
government sites restructure their HTML without notice.
"""

import hashlib
import os
import time

import requests
from bs4 import BeautifulSoup

RBI_NOTIFICATIONS_URL = "https://www.rbi.org.in/Scripts/NotificationUser.aspx"
DOWNLOAD_DIR = os.path.join(os.path.dirname(__file__), "data", "circulars")
SEEN_FILE = os.path.join(os.path.dirname(__file__), "data", "seen_circulars.txt")

os.makedirs(DOWNLOAD_DIR, exist_ok=True)


def _get_seen_ids() -> set:
    if not os.path.exists(SEEN_FILE):
        return set()
    with open(SEEN_FILE) as f:
        return set(line.strip() for line in f if line.strip())


def _mark_seen(circular_id: str):
    with open(SEEN_FILE, "a") as f:
        f.write(circular_id + "\n")


def inspect_page_structure():
    """
    Debug helper -- run manually to print out the first few PDF links
    found, so you can confirm the selector below still matches the
    live page before a demo.
    """
    resp = requests.get(RBI_NOTIFICATIONS_URL, timeout=15)
    soup = BeautifulSoup(resp.text, "html.parser")
    links = soup.select("a[href$='.PDF'], a[href$='.pdf']")
    for link in links[:10]:
        print(link.get("href"), "|", link.text.strip()[:80])
    return links


def check_for_new_circulars(on_new_circular=None) -> list[dict]:
    """
    Checks the RBI notifications page for PDFs not seen before.
    `on_new_circular(filepath, title)` is an optional callback -- wire
    this to `run_regtrack_pipeline` to auto-analyze new circulars as
    they're found.
    """
    resp = requests.get(RBI_NOTIFICATIONS_URL, timeout=15)
    soup = BeautifulSoup(resp.text, "html.parser")

    seen = _get_seen_ids()
    newly_found = []

    for link in soup.select("a[href$='.PDF'], a[href$='.pdf']"):
        pdf_url = link.get("href")
        if not pdf_url:
            continue
        if not pdf_url.startswith("http"):
            pdf_url = "https://www.rbi.org.in" + pdf_url

        circular_id = hashlib.md5(pdf_url.encode()).hexdigest()
        if circular_id in seen:
            continue

        title = link.text.strip() or circular_id
        filepath = _download_pdf(pdf_url, circular_id)
        _mark_seen(circular_id)
        newly_found.append({"id": circular_id, "url": pdf_url, "title": title, "filepath": filepath})

        if on_new_circular:
            on_new_circular(filepath, title)

    return newly_found


def _download_pdf(url: str, circular_id: str) -> str:
    resp = requests.get(url, timeout=15)
    filepath = os.path.join(DOWNLOAD_DIR, f"{circular_id}.pdf")
    with open(filepath, "wb") as f:
        f.write(resp.content)
    return filepath


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
    print("Inspecting RBI notifications page structure...")
    inspect_page_structure()
