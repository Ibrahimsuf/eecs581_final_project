import requests
import time

def scrape_remoteok():
    url = "https://remoteok.com/api"
    headers = {"User-Agent": "JobScraperBot/1.0 (+https://yourdomain.com/contact)"}

    print("Title | Category | ID | Department | Campus | Reg/Temp | Review Begins | URL")
    print("-" * 120)

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()

        jobs = response.json()[1:]  # first element is metadata
        for job in jobs:
            title = job.get("position", "")
            category = ", ".join(job.get("tags", []))
            job_id = job.get("id", "")
            department = job.get("company", "")
            campus = job.get("location", "Remote")
            reg_temp = "N/A"
            review_begins = job.get("date", "")
            job_url = job.get("url", "")

            print(f"{title} | {category} | {job_id} | {department} | {campus} | {reg_temp} | {review_begins} | {job_url}")

            time.sleep(0.2)  # polite delay

    except requests.RequestException as e:
        print("error fetching data", e)

scrape_remoteok()
