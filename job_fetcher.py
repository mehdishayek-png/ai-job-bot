import feedparser
import json
import os
import requests
from bs4 import BeautifulSoup

# ============================================
# CONFIG
# ============================================

OUTPUT_PATH = "data/jobs.json"
PROFILE_PATH = "data/profile.json"

WWR_RSS = "https://weworkremotely.com/categories/remote-customer-support-jobs.rss"
REMOTEOK_RSS = "https://remoteok.com/remote-jobs.rss"

# ============================================
# LOAD PROFILE KEYWORDS
# ============================================

def load_profile_keywords():

    if not os.path.exists(PROFILE_PATH):
        print("Profile not found — skipping filtering")
        return []

    with open(PROFILE_PATH, "r", encoding="utf-8") as f:
        profile = json.load(f)

    keywords = []

    keywords.extend(profile.get("skills", []))
    keywords.extend(profile.get("tools", []))
    keywords.extend(profile.get("industries", []))
    keywords.extend(profile.get("preferred_roles", []))

    headline = profile.get("headline", "")
    if headline:
        keywords.append(headline)

    keywords = list(set(keywords))

    print(f"Loaded {len(keywords)} targeting keywords")

    return keywords


TARGET_KEYWORDS = load_profile_keywords()

# ============================================
# RELEVANCE FILTER
# ============================================

def is_relevant(job):

    if not TARGET_KEYWORDS:
        return True

    text = (
        job.get("title", "") +
        job.get("summary", "")
    ).lower()

    for kw in TARGET_KEYWORDS:
        if kw.lower() in text:
            return True

    return False

# ============================================
# FETCH — WWR (RSS)
# ============================================

def fetch_weworkremotely():

    print("\nFetching WeWorkRemotely jobs...")

    jobs = []
    feed = feedparser.parse(WWR_RSS)

    for entry in feed.entries:

        job = {
            "title": entry.get("title", ""),
            "company": entry.get("author", "Unknown"),
            "summary": entry.get("summary", ""),
            "apply_url": entry.get("link", ""),
            "source": "WeWorkRemotely"
        }

        if is_relevant(job):
            jobs.append(job)

    print(f"Relevant WWR jobs: {len(jobs)}")

    return jobs

# ============================================
# FETCH — REMOTEOK (RSS)
# ============================================

def fetch_remoteok():

    print("\nFetching RemoteOK jobs...")

    jobs = []
    feed = feedparser.parse(REMOTEOK_RSS)

    for entry in feed.entries:

        job = {
            "title": entry.get("title", ""),
            "company": "RemoteOK",
            "summary": entry.get("summary", ""),
            "apply_url": entry.get("link", ""),
            "source": "RemoteOK"
        }

        if is_relevant(job):
            jobs.append(job)

    print(f"Relevant RemoteOK jobs: {len(jobs)}")

    return jobs

# ============================================
# FETCH — WORKINGNOMADS (HTML SCRAPE)
# ============================================

def fetch_workingnomads():

    print("\nFetching WorkingNomads jobs...")

    url = "https://www.workingnomads.com/jobs"
    headers = {"User-Agent": "Mozilla/5.0"}

    jobs = []

    try:
        res = requests.get(url, headers=headers)
        soup = BeautifulSoup(res.text, "html.parser")

        listings = soup.select(".job-listing")

        for job_html in listings:

            title_el = job_html.select_one("h2")
            company_el = job_html.select_one(".company")
            link_el = job_html.select_one("a")

            job = {
                "title": title_el.text.strip() if title_el else "",
                "company": company_el.text.strip() if company_el else "Unknown",
                "summary": "",
                "apply_url": "https://www.workingnomads.com" + link_el["href"] if link_el else "",
                "source": "WorkingNomads"
            }

            if is_relevant(job):
                jobs.append(job)

    except Exception as e:
        print("WorkingNomads fetch failed:", e)

    print(f"Relevant WorkingNomads jobs: {len(jobs)}")

    return jobs

# ============================================
# FETCH — REMOTIVE (API)
# ============================================

def fetch_remotive():

    print("\nFetching Remotive jobs...")

    url = "https://remotive.com/api/remote-jobs"
    jobs = []

    try:
        res = requests.get(url)
        data = res.json()

        for entry in data["jobs"]:

            job = {
                "title": entry.get("title", ""),
                "company": entry.get("company_name", "Unknown"),
                "summary": entry.get("description", ""),
                "apply_url": entry.get("url", ""),
                "source": "Remotive"
            }

            if is_relevant(job):
                jobs.append(job)

    except Exception as e:
        print("Remotive fetch failed:", e)

    print(f"Relevant Remotive jobs: {len(jobs)}")

    return jobs

# ============================================
# SAVE JOBS
# ============================================

def save_jobs(all_jobs):

    os.makedirs("data", exist_ok=True)

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(all_jobs, f, indent=2)

    print(f"\nSaved → {OUTPUT_PATH}")
    print(f"Total relevant jobs saved: {len(all_jobs)}")

# ============================================
# MAIN
# ============================================

def main():

    print("================================")
    print("SMART JOB FETCHER STARTED")
    print("================================")

    all_jobs = []

    try:
        all_jobs.extend(fetch_weworkremotely())
    except Exception as e:
        print("WWR fetch failed:", e)

    try:
        all_jobs.extend(fetch_remoteok())
    except Exception as e:
        print("RemoteOK fetch failed:", e)

    try:
        all_jobs.extend(fetch_workingnomads())
    except Exception as e:
        print("WorkingNomads fetch failed:", e)

    try:
        all_jobs.extend(fetch_remotive())
    except Exception as e:
        print("Remotive fetch failed:", e)

    save_jobs(all_jobs)

    print("\n================================")
    print("FETCH COMPLETE")
    print("================================")

# ============================================
# RUN
# ============================================

if __name__ == "__main__":
    main()
