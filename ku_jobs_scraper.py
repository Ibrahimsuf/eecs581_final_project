#!/usr/bin/env python3
"""
KU Jobs Scraper

Purpose: Scrape https://employment.ku.edu/jobs using requests + BeautifulSoup
and extract core job fields from the listings page.

Feature :
- Scrape the main listings page
- Parse and print basic attributes per job row: title, ID, department,
    primary campus, reg/temp, review begins, URL, category
- Added later: skill filtering, no deep page fetch, no CSV/JSON export
"""
from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from typing import List, Optional

import requests
from bs4 import BeautifulSoup, Tag

# Constants and minimal config
BASE_URL = "https://employment.ku.edu"
LIST_URL = f"{BASE_URL}/jobs"
DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; KUJobsMinimal/1.0)",
    "Accept-Language": "en-US,en;q=0.9",
}


@dataclass
class JobRow:
    title: str
    job_url: str
    posting_id: Optional[str]
    department: Optional[str]
    primary_campus: Optional[str]
    reg_temp: Optional[str]
    review_begins: Optional[str]
    category: Optional[str]


def norm_space(s: Optional[str]) -> Optional[str]:
    if s is None:
        return None
    return re.sub(r"\s+", " ", s).strip()


def get_session(timeout: int = 20) -> requests.Session:
    s = requests.Session()
    # Simple retry/backoff omitted to keep within minimal scope
    s.headers.update(DEFAULT_HEADERS)

    # Attach default timeout via wrapper
    original_request = s.request

    def wrapped(method, url, **kwargs):
        if "timeout" not in kwargs:
            kwargs["timeout"] = timeout
        return original_request(method, url, **kwargs)

    s.request = wrapped  # type: ignore[assignment]
    return s


def fetch_html_text(session: requests.Session, url: str) -> str:
    resp = session.get(url)
    resp.raise_for_status()
    return resp.text


def parse_listings_table(html: str) -> List[JobRow]:
    soup = BeautifulSoup(html, "lxml")
    # Try to find a table with expected headers
    header_labels = [
        "Posting Title",
        "ID",
        "Department",
        "Primary Campus",
        "Reg/Temp",
        "Review Begins",
    ]
    target_table = None
    for tbl in soup.find_all("table"):
        thead = tbl.find("thead")
        header_text = ""
        if thead and thead.find("tr"):
            header_text = " ".join([th.get_text(strip=True) for th in thead.find("tr").find_all("th")])
        else:
            first_row = tbl.find("tr")
            if first_row:
                header_text = " ".join([cell.get_text(strip=True) for cell in first_row.find_all(["th", "td"])])
        if header_text and all(h in header_text for h in header_labels):
            target_table = tbl
            break

    rows: List[JobRow] = []
    if not target_table:
        # Fallback: parse links that look like job postings
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if href.startswith("/jobs/") and re.search(r"/jobs/(staff|faculty|students)/", href):
                title = a.get_text(strip=True)
                url = href if href.startswith("http") else f"{BASE_URL.rstrip('/')}{href}"
                rows.append(
                    JobRow(
                        title=title,
                        job_url=url,
                        posting_id=None,
                        department=None,
                        primary_campus=None,
                        reg_temp=None,
                        review_begins=None,
                        category=_extract_category_from_url(url),
                    )
                )
        return rows

    tbody = target_table.find("tbody") or target_table
    for tr in tbody.find_all("tr"):
        cells = tr.find_all(["td", "th"])
        if not cells:
            continue
        title_cell = cells[0]
        link = title_cell.find("a", href=True)
        if not link:
            continue
        title = re.sub(r"^\[\*\*Internal Only\*\*\]\s*", "", link.get_text(strip=True), flags=re.I)
        href = link["href"]
        url = href if href.startswith("http") else f"{BASE_URL.rstrip('/')}{href}"
        posting_id = cells[1].get_text(strip=True) if len(cells) > 1 else None
        department = cells[2].get_text(strip=True) if len(cells) > 2 else None
        primary_campus = cells[3].get_text(strip=True) if len(cells) > 3 else None
        reg_temp = cells[4].get_text(strip=True) if len(cells) > 4 else None
        review_begins = cells[5].get_text(strip=True) if len(cells) > 5 else None

        rows.append(
            JobRow(
                title=title,
                job_url=url,
                posting_id=posting_id or None,
                department=department or None,
                primary_campus=primary_campus or None,
                reg_temp=reg_temp or None,
                review_begins=review_begins or None,
                category=_extract_category_from_url(url),
            )
        )
    return rows


def _extract_category_from_url(url: str) -> Optional[str]:
    m = re.search(r"/jobs/(staff|faculty|students)/", url)
    return m.group(1) if m else None


def print_console(rows: List[JobRow], max_width: Optional[int] = None) -> None:
    """Print rows in a readable table.

    No global line truncation is applied so full URLs are shown.
    Title/Department/Campus are shortened for readability. Set max_width
    to an integer to enable global truncation if desired.
    """
    headers = ["Title", "Category", "ID", "Department", "Campus", "Reg/Temp", "Review Begins", "URL"]
    header_line = " | ".join(headers)
    print(header_line)
    sep_len = max(len(header_line), 120)
    print("-" * sep_len)
    for r in rows:
        cols = [
            (r.title or "")[:40],
            r.category or "",
            r.posting_id or "",
            (r.department or "")[:24],
            (r.primary_campus or "")[:24],
            r.reg_temp or "",
            r.review_begins or "",
            r.job_url,
        ]
        line = " | ".join(cols)
        if max_width is not None and len(line) > max_width:
            line = line[: max_width - 3] + "..."
        print(line)


def main() -> int:
    session = get_session()
    try:
        html = fetch_html_text(session, LIST_URL)
    except Exception as e:
        print(f"Error fetching list page: {e}", file=sys.stderr)
        return 1

    jobs = parse_listings_table(html)
    if not jobs:
        print("No jobs parsed from list page. The page structure may have changed.", file=sys.stderr)
        return 2

    print_console(jobs)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
