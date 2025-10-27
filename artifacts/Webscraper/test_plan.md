# Test Plan: KU Jobs Scraper 

This plan validates Requirement R2 for the minimal scraper in `ku_jobs_scraper.py`.

## Environment
- Python 3.9+ (3.11 used during development)
- Packages installed via `requirements.txt`: `requests`, `beautifulsoup4`, `lxml`
- Network access to https://employment.ku.edu/jobs

## Test Cases

1. Basic run prints header and rows (Happy path)
   - Steps:
     - Run: `src\ku_jobs_scraper.py`
   - Expected:
     - First line is a header: `Title | Category | ID | Department | Campus | Reg/Temp | Review Begins | URL`
     - At least one job row is printed.
     - No Python exceptions.

2. Column structure and ordering
   - Steps:
     - Inspect the first few printed job lines.
   - Expected:
     - Each row has eight pipe-separated fields matching the header order.
     - `Category` values are one of: `faculty`, `staff`, `students`.

3. URL format sanity
   - Steps:
     - Inspect the `URL` field of several rows.
   - Expected:
     - Each `URL` begins with `https://employment.ku.edu/` and points to a detail page.

4. Data variety across categories
   - Steps:
     - Observe multiple lines across the listing output.
   - Expected:
     - At least one row per available category (e.g., faculty, staff, students) appears.

5. Long-field truncation formatting
   - Steps:
     - Identify a job with a long title or department.
   - Expected:
     - Long fields are truncated with ellipses to keep the table aligned; overall formatting remains readable.

6. Table detection resilience (manual inspection)
   - Steps:
     - Review `parse_listings_table` in `ku_jobs_scraper.py`.
   - Expected:
     - Header-based detection is used to find the listings table; if the site changes headers, the function is the single place to adjust.

7. Network failure behavior (negative test)
   - Steps:
     - Temporarily disconnect from the network or use a firewall rule to block the site.
     - Run the script.
   - Expected:
     - A network error may be raised by `requests` and surfaced to the console. Reconnecting and re-running should succeed. (Graceful handling is optional for Sprint 1.)

## Evidence Capture
- Save a representative run to `artifacts\Webscraper\sample_run_output.txt`.
- Cross-check against acceptance criteria in `artifacts\Webscraper\requirement_R2_web_scraper.md`.

## Maintenance Notes
- If the site’s HTML structure changes, update `parse_listings_table` selectors.
- Keep `requirements.txt` in sync if libraries are upgraded.
