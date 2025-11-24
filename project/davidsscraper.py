import requests
import time
from datetime import datetime

def scrape_remoteok():
    url = "https://remoteok.com/api"
    headers = {"User-Agent": "JobScraperBot/1.0 (+https://yourdomain.com/contact)"}

    print("Title | Category | ID | Department | Campus | Reg/Temp | Review Begins | URL")
    print("-" * 120)

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()

        jobs = response.json()[1:]  # first element is metadata
        api_jobs = []
        for job in jobs:
            title = job.get("position", "")
            category = ", ".join(job.get("tags", []))
            job_id = job.get("id", "")
            department = job.get("company", "")
            campus = job.get("location", "Remote")
            reg_temp = "N/A"
            review_begins = job.get("date", "")
            job_url = job.get("url", "")

            # print(f"{title} | {category} | {job_id} | {department} | {campus} | {reg_temp} | {review_begins} | {job_url}")

            # convert to API dict format
            api_job = {
                "id": f"remote_{job_id}",
                "name": title,
                "title": title,
                "short_description": f"Remote position at {department}",
                "url": job_url,
                "source": "RemoteOK",
                "company": department,
                "location": campus,
                "date": review_begins,
                "posted_at": _normalize_date_string(review_begins),
                "skills": job.get("tags", [])
            }

            # adding break condition bc 100 jobs is a lot
            api_jobs.append(api_job)
            if len(api_jobs) >= 10:
                break

            time.sleep(0.2)  # polite delay

        return api_jobs

    except requests.RequestException as e:
        print("error fetching data", e)
        return []

def _normalize_date_string(s):
    if not s:
        return None
    try:
        dt = datetime.fromisoformat(str(s).replace('Z', '+00:00'))
        return dt.strftime('%Y-%m-%d')
    except Exception:
        return str(s)

# scrape_remoteok()
