#!/usr/bin/env python3
"""
KU Jobs Scraper
"""
from __future__ import annotations

import re
import sys
from time import time
from threading import Lock
from dataclasses import dataclass
from typing import List, Optional, Iterable, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests
from bs4 import BeautifulSoup

# Constants and minimal config
BASE_URL = "https://employment.ku.edu"
LIST_URL = f"{BASE_URL}/jobs"
DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; KUJobsMinimal/1.0)",
    "Accept-Language": "en-US,en;q=0.9",
}

# In-memory detail page cache (timestamped). Process-local.
DETAIL_CACHE: dict[str, dict[str, object]] = {}
CACHE_TTL_SEC = 1800  # 30 minutes
MAX_CACHE_SIZE = 300
_DETAIL_CACHE_LOCK = Lock()

def _get_cached_detail(url: str) -> Optional[str]:
    with _DETAIL_CACHE_LOCK:
        entry = DETAIL_CACHE.get(url)
        if not entry:
            return None
        ts = entry.get("ts", 0)
        if not isinstance(ts, (int, float)) or time() - ts > CACHE_TTL_SEC:
            DETAIL_CACHE.pop(url, None)
            return None
        return entry.get("text") if isinstance(entry.get("text"), str) else None

def _set_cached_detail(url: str, text: str) -> None:
    with _DETAIL_CACHE_LOCK:
        if len(DETAIL_CACHE) >= MAX_CACHE_SIZE:
            # Drop oldest
            oldest = min(DETAIL_CACHE.items(), key=lambda kv: kv[1].get("ts", 0))[0]
            DETAIL_CACHE.pop(oldest, None)
        DETAIL_CACHE[url] = {"text": text, "ts": time()}


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
    skills: Optional[List[str]] = None

    def to_api_format(self) -> dict:
        """Convert to the format expected by app.py"""
        return {
            "id": self.posting_id or f"ku_{hash(self.job_url)}",
            "name": self.title,
            "title": self.title,
            "short_description": f"{self.department} - {self.primary_campus}" if self.department else "KU Job Posting",
            "url": self.job_url,
            "source": "KU Jobs",
            "category": self.category,
            "department": self.department,
            "campus": self.primary_campus,
            "type": self.reg_temp,
            "review_begins": self.review_begins,
            "posted_at": self.review_begins,
            "skills": self.skills or []
        }


# Removed unused norm_space helper


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
                skills=None,
            )
        )
    return rows


def _extract_category_from_url(url: str) -> Optional[str]:
    m = re.search(r"/jobs/(staff|faculty|students)/", url)
    return m.group(1) if m else None


def fetch_detail_and_extract_skills(session: requests.Session, url: str) -> List[str]:
    """Test fetching KU job detail page and extract skills via keyword matching.
    """
    cached = _get_cached_detail(url)
    if cached is None:
        try:
            resp = requests.get(url, headers=DEFAULT_HEADERS, timeout=12)
            resp.raise_for_status()
        except Exception:
            return []
        soup = BeautifulSoup(resp.text, "lxml")
        text_raw = _detail_text(soup)
        _set_cached_detail(url, text_raw)
    else:
        text_raw = cached
    text = text_raw.lower()

    # Curated skill tokens. Keep lowercase; match as whole words where sensible.
    tokens = [
        # languages
        "python", "java", "c++", "c#", "javascript", "typescript", "go", "rust", "ruby", "php", "scala", "r ", " r",
        # web/fe
        "html", "css", "react", "angular", "vue", "node", "node.js", "nodejs", "next.js", "nextjs",
        # data/ai
        "sql", "nosql", "postgres", "mysql", "sqlite", "oracle", "mongodb", "pandas", "numpy", "scikit-learn",
        "tensorflow", "pytorch", "spark", "hadoop", "tableau", "power bi", "excel",
        # devops/cloud
        "aws", "azure", "gcp", "docker", "kubernetes", "linux", "bash", "git", "ci/cd", "jenkins", "terraform",
        # backend/web
        "flask", "django", "fastapi", "graphql", "rest ", " rest", "api",
        # misc
        "matlab", "sas", "snowflake",
    ]

    found: List[str] = []
    for t in tokens:
        # coarse matching: word boundary if simple token; otherwise substring
        tt = t.strip()
        if not tt:
            continue
        if any(ch in tt for ch in ['+', '#', '/', '.', ' ']):
            if tt in text:
                found.append(tt.replace(' ', ' ').replace('.js', ''))
        else:
            if re.search(rf"\b{re.escape(tt)}\b", text):
                found.append(tt)

    # normalize variants
    norm_map = {
        "node": "node.js",
        "nodejs": "node.js",
        "nextjs": "next.js",
        "rest": "rest",
        " r": "r",
        "r ": "r",
    }
    out = []
    for f in found:
        key = norm_map.get(f, f)
        if key not in out:
            out.append(key)
    return out


def _detail_text(soup: BeautifulSoup) -> str:
    # Try common content wrappers; fallback to all readable text
    selectors = [
        "main",
        "article",
        ".[role='main']",
        ".region-content",
        ".field--name-body",
        ".node__content",
    ]
    for sel in selectors:
        el = soup.select_one(sel)
        if el:
            return el.get_text(separator=" ", strip=True)
    return soup.get_text(separator=" ", strip=True)


def _extract_given_skills_from_text(text: str, given: List[str]) -> List[str]:
    text = text.lower()
    found: List[str] = []
    for raw in given:
        s = str(raw).strip().lower()
        if not s:
            continue
        # Accept simple variants: node ↔ node.js, ts ↔ typescript, js ↔ javascript
        variants = {s}
        if s in {"node", "nodejs", "node.js"}:
            variants.update({"node", "nodejs", "node.js"})
        if s in {"js", "javascript"}:
            variants.update({"js", "javascript"})
        if s in {"ts", "typescript"}:
            variants.update({"ts", "typescript"})
        if s in {"py", "python"}:
            variants.update({"py", "python"})
        if s in {"sql"}:
            variants.update({"sql"})

        matched = False
        for v in variants:
            if any(ch in v for ch in ['+', '#', '/', '.', ' ']):
                if v in text:
                    matched = True
                    break
            else:
                if re.search(rf"\b{re.escape(v)}\b", text):
                    matched = True
                    break
        if matched:
            # preserve the original input form in output where possible
            if raw not in found:
                found.append(raw)
    return found


def enrich_rows_with_skills(
    session: requests.Session,
    rows: Iterable[JobRow],
    limit: Optional[int] = None,
    input_skills: Optional[List[str]] = None,
    max_workers: int = 8,
) -> None:
    """Mutates rows to populate .skills by scraping the detail page.
    """
    selected: List[JobRow] = []
    for r in rows:
        if limit is not None and len(selected) >= limit:
            break
        selected.append(r)

    def worker(row: JobRow) -> Tuple[JobRow, List[str]]:
        try:
            cached = _get_cached_detail(row.job_url)
            if cached is None:
                resp = requests.get(row.job_url, headers=DEFAULT_HEADERS, timeout=12)
                resp.raise_for_status()
                soup = BeautifulSoup(resp.text, "lxml")
                text_raw = _detail_text(soup)
                _set_cached_detail(row.job_url, text_raw)
            else:
                text_raw = cached
            if input_skills:
                skills = _extract_given_skills_from_text(text_raw, input_skills)
            else:
                # token extraction will handle caching internally too
                skills = fetch_detail_and_extract_skills(session, row.job_url)
            return row, skills
        except Exception:
            return row, []

    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        futures = [ex.submit(worker, r) for r in selected]
        for fut in as_completed(futures):
            row, skills = fut.result()
            row.skills = skills


def filter_rows_by_input_skills(
    session: requests.Session,
    rows: Iterable[JobRow],
    input_skills: List[str],
    limit: Optional[int] = None,
    max_workers: int = 8,
) -> List[JobRow]:
    """Return only rows whose detail page text contains at least one input skill.
    """
    selected: List[JobRow] = []
    for r in rows:
        if limit is not None and len(selected) >= limit:
            break
        selected.append(r)

    def worker(row: JobRow) -> Tuple[JobRow, bool]:
        try:
            cached = _get_cached_detail(row.job_url)
            if cached is None:
                resp = requests.get(row.job_url, headers=DEFAULT_HEADERS, timeout=12)
                resp.raise_for_status()
                soup = BeautifulSoup(resp.text, "lxml")
                text_raw = _detail_text(soup)
                _set_cached_detail(row.job_url, text_raw)
            else:
                text_raw = cached
            matched = bool(_extract_given_skills_from_text(text_raw, input_skills))
            return row, matched
        except Exception:
            return row, False

    kept: List[JobRow] = []
    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        futures = [ex.submit(worker, r) for r in selected]
        for fut in as_completed(futures):
            row, matched = fut.result()
            if matched:
                kept.append(row)
    return kept

