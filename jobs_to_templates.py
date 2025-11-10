"""
Integration script: use ku_jobs_scraper to get job URLs, fetch each job page,
convert to plain text, parse with JobDescriptionParser (from Keyword.py), and
write a template file per job.

This script intentionally does not modify `ku_jobs_scraper.py`.
"""
from __future__ import annotations

import os
import re
import sys
from typing import Optional

from bs4 import BeautifulSoup

import ku_jobs_scraper as scraper
from Keyword import JobDescriptionParser


def sanitize_filename(s: str, max_len: int = 80) -> str:
    # Replace unsafe chars with underscore and trim
    s = re.sub(r"[^A-Za-z0-9._ -]", "_", s)
    s = s.strip()
    if len(s) > max_len:
        s = s[: max_len - 3].rstrip() + "..."
    return s or "job"


def main(output_dir: str = "templates") -> int:
    os.makedirs(output_dir, exist_ok=True)

    session = scraper.get_session()

    try:
        html = scraper.fetch_html_text(session, scraper.LIST_URL)
    except Exception as e:
        print(f"Error fetching listings page: {e}", file=sys.stderr)
        return 1

    rows = scraper.parse_listings_table(html)
    if not rows:
        print("No job rows returned by scraper.")
        return 2

    db_path = os.path.join(output_dir, "jobs_database.txt")
    # Use the parser with the output_path pointing at the single DB file.
    parser = JobDescriptionParser("", output_path=db_path)

    created = 0
    for r in rows:
        if not r.job_url:
            continue
        try:
            detail_html = scraper.fetch_html_text(session, r.job_url)
        except Exception as e:
            print(f"Failed to fetch {r.job_url}: {e}", file=sys.stderr)
            continue

        # Convert HTML to readable text
        soup = BeautifulSoup(detail_html, "lxml")
        text = soup.get_text(separator="\n")

        info = parser.extract_job_info_from_text(text)

        # Append the parsed job info as a JSON line into the single DB file.
        try:
            parser.append_to_database(info)
            created += 1
        except Exception as e:
            print(f"Failed appending job {r.title or r.posting_id}: {e}", file=sys.stderr)
            continue

    print(f"Appended {created} job entries to {db_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
