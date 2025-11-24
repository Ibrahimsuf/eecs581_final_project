"""
Integration script: use ku_jobs_scraper to get job URLs, fetch each job page,
convert to plain text, parse with JobDescriptionParser (from Keyword.py), and
write a template file per job.

This script intentionally does not modify `ku_jobs_scraper.py`.
"""
from __future__ import annotations
import time
import os
import re
import sys
from typing import Optional

from bs4 import BeautifulSoup

import ku_jobs_scraper as scraper
from Keyword import JobDescriptionParser
import datetime
import argparse


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


def _seconds_until_next_utc_midnight() -> float:
    """Return seconds until the next 00:00:00 UTC from now."""
    now = datetime.datetime.utcnow()
    tomorrow = (now + datetime.timedelta(days=1)).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    return (tomorrow - now).total_seconds()


def schedule_daily_update(output_dir: str = "templates", run_immediately: bool = False) -> None:
    """Run `main()` every day at 00:00 UTC.

    This function blocks and should be run in a persistent process (systemd,
    docker container, or a backgrounded shell job). It will optionally run one
    immediate update when `run_immediately` is True, then wait until the next
    00:00 UTC and run updates daily thereafter.
    """
    if run_immediately:
        try:
            print("Running immediate update before scheduling...")
            main(output_dir=output_dir)
        except Exception as e:
            print(f"Immediate update failed: {e}", file=sys.stderr)

    while True:
        wait = _seconds_until_next_utc_midnight()
        print(f"Sleeping {int(wait)}s until next 00:00 UTC...")
        # Sleep in shorter chunks to be responsive to signals in very long sleeps
        # but keep logic simple here.
        time.sleep(wait)
        try:
            print("Starting scheduled update at 00:00 UTC")
            main(output_dir=output_dir)
        except Exception as e:
            print(f"Scheduled update failed: {e}", file=sys.stderr)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Run the jobs -> templates update. Use --daemon to run daily at 00:00 UTC."
    )
    parser.add_argument("--daemon", action="store_true", help="Run scheduler that updates every day at 00:00 UTC")
    parser.add_argument("--once", action="store_true", help="Run a single update immediately and exit")
    parser.add_argument("--output-dir", default="templates", help="Directory to write templates/database into")
    parser.add_argument("--immediate", action="store_true", help="When used with --daemon run an immediate update before scheduling")
    args = parser.parse_args()

    if args.daemon:
        schedule_daily_update(output_dir=args.output_dir, run_immediately=args.immediate)
    elif args.once:
        raise SystemExit(main(output_dir=args.output_dir))
    else:
        # Default behavior: run one update (keeps backwards compatibility)
        raise SystemExit(main(output_dir=args.output_dir))
