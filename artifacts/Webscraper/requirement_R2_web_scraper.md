# Requirement R2: KU Jobs Scraper

Purpose: Implement a functional web scraper that fetches job listings from https://employment.ku.edu/jobs and prints core fields in the console.

Scope for Sprint 1:
- Use requests + BeautifulSoup.
- Scrape the main listings page.
- Extract and print for each row: Title, ID, Department, Primary Campus, Reg/Temp, Review Begins, URL, Category.
- Simple run prints to stdout.

## Implementation
- Script: `ku_jobs_scraper.py`
- Libraries: `requests`, `beautifulsoup4` (listed in `requirements.txt`).
- Entry point: `python ku_jobs_scraper.py`

## Acceptance Criteria
- A1. The script runs without errors on a networked machine with Python 3.9+ and required packages installed.
- A2. The script fetches https://employment.ku.edu/jobs and parses job rows.
- A3. For each parsed job row, the script prints a single-line summary with the fields: Title, Category, ID, Department, Primary Campus, Reg/Temp, Review Begins, URL.
- A4. Output includes at least a few Faculty, Staff, and Students entries when available on the site at run time.
- A5. The code is concise and uses requests + BeautifulSoup to parse the page (no browser automation).

## Verification Steps
1) Install dependencies
   - See the repository `README.md` or run:
     - `python -m pip install -r requirements.txt`
2) Run the scraper
   - `python ku_jobs_scraper.py`
3) Observe console output
   - Expect a header row followed by job lines (Title | Category | ID | Department | Primary Campus | Reg/Temp | Review Begins | URL).
   - Compare with the example in `docs/sprint1/sample_run_output.txt` (entries will vary over time; structure should match).

## Evidence
- Sample output captured: `docs/sprint1/sample_run_output.txt`.
- Source file: `ku_jobs_scraper.py`.

## Traceability
- Requirement: R2 — "Develop web scraper for job listings".
- Code: `ku_jobs_scraper.py`.
- Dependency manifest: `requirements.txt`.
- Artifact docs: `docs/sprint1/*`.

## Notes and Constraints
- Real-time job listings change frequently; the exact entries shown may differ between runs.
- If the site’s HTML structure changes (e.g., table headers), minor selector updates in `parse_listings_table` may be required.
- Network timeouts or transient errors can be retried by re-running the script.
