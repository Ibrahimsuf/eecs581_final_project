# eecs581_final_project

## KU Employment Scraper

This repository includes a Python script that uses BeautifulSoup to scrape job postings from the public KU employment website (employment.ku.edu) and match them against user-provided skills.

### Requirements

- Python 3.9+
- Packages listed in `requirements.txt`

### Setup

Install dependencies:

```powershell
python -m pip install -r requirements.txt
```

If you're using the provided virtual environment in VS Code, the dependencies may already be handled for you.

### Usage

Run the scraper and view results in the console:

```powershell
python ku_jobs_scraper.py
```

The scraper respects the site's robots.txt and only accesses publicly available job pages.

### Output

Each printed row includes the following fields, parsed from the listings page table:

- Title | Category | ID | Department | Campus | Reg/Temp | Review Begins | URL

See a sample in `docs/sprint1/sample_run_output.txt`.

### Sprint 1 Artifacts

See `docs/sprint1/` for:

- `requirement_R2_web_scraper.md` – acceptance criteria and verification steps
- `test_plan.md` – test cases and expected results
- `sample_run_output.txt` – captured example output
