import feedparser
import json
import os
import requests
from bs4 import BeautifulSoup

# ============================================
# CONFIG
# ============================================

DEFAULT_OUTPUT_PATH = "data/jobs.json"
DEFAULT_PROFILE_PATH = "data/profile.json"

WWR_RSS = "https://weworkremotely.com/categories/remote-customer-support-jobs.rss"
REMOTEOK_RSS = "https://remoteok.com/remote-jobs.rss"

# ============================================
# LOAD PROFILE KEYWORDS — now a function call, not module-level
# ============================================

def load_profile_keywords(profile_path=None):
    """Load targeting keywords from a profile file.
    
    Accepts a path parameter so each session can point
    to its own profile.
    """
    profile_path = profile_path or DEFAULT_PROFILE_PATH

    if not os.path.exists(profile_path):
        print("Profile not found — skipping filtering")
        return []

    try:
        with open(profile_path, "r", encoding="utf-8") as f:
            profile = json.load(f)
    except Exception as e:
        print(f"Profile load error: {e}")
        return []

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

# ============================================
# RELEVANCE FILTER — keywords passed as argument
# ============================================

def is_relevant(job, target_keywords):
    if not target_keywords:
        return True

    text = (
        job.get("title", "") + " " +
        job.get("summary", "")
    ).lower()

    for kw in target_keywords:
        if kw.lower() in text:
            return True

    return False

# ============================================
# FETCH — WWR (RSS)
# ============================================

def fetch_weworkremotely(target_keywords):
    print("\nFetching WeWorkRemotely jobs...")
    jobs = []

    try:
        feed = feedparser.parse(WWR_RSS)

        for entry in feed.entries:
            job = {
                "title": entry.get("title", ""),
                "company": entry.get("author", "Unknown"),
                "summary": entry.get("summary", ""),
                "apply_url": entry.get("link", ""),
                "source": "WeWorkRemotely",
            }
            if is_relevant(job, target_keywords):
                jobs.append(job)
    except Exception as e:
        print(f"WWR fetch failed: {e}")

    print(f"Relevant WWR jobs: {len(jobs)}")
    return jobs

# ============================================
# FETCH — REMOTEOK (RSS)
# ============================================

def fetch_remoteok(target_keywords):
    print("\nFetching RemoteOK jobs...")
    jobs = []

    try:
        feed = feedparser.parse(REMOTEOK_RSS)

        for entry in feed.entries:
            job = {
                "title": entry.get("title", ""),
                "company": "RemoteOK",
                "summary": entry.get("summary", ""),
                "apply_url": entry.get("link", ""),
                "source": "RemoteOK",
            }
            if is_relevant(job, target_keywords):
                jobs.append(job)
    except Exception as e:
        print(f"RemoteOK fetch failed: {e}")

    print(f"Relevant RemoteOK jobs: {len(jobs)}")
    return jobs

# ============================================
# FETCH — WORKINGNOMADS (HTML SCRAPE)
# ============================================

def fetch_workingnomads(target_keywords):
    print("\nFetching WorkingNomads jobs...")

    url = "https://www.workingnomads.com/jobs"
    headers = {"User-Agent": "Mozilla/5.0"}
    jobs = []

    try:
        res = requests.get(url, headers=headers, timeout=15)
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
                "apply_url": (
                    "https://www.workingnomads.com" + link_el["href"]
                    if link_el and link_el.get("href")
                    else ""
                ),
                "source": "WorkingNomads",
            }
            if is_relevant(job, target_keywords):
                jobs.append(job)

    except Exception as e:
        print(f"WorkingNomads fetch failed: {e}")

    print(f"Relevant WorkingNomads jobs: {len(jobs)}")
    return jobs

# ============================================
# FETCH — REMOTIVE (API)
# ============================================

def fetch_remotive(target_keywords):
    print("\nFetching Remotive jobs...")
    jobs = []

    try:
        res = requests.get("https://remotive.com/api/remote-jobs", timeout=15)
        data = res.json()

        for entry in data.get("jobs", []):
            job = {
                "title": entry.get("title", ""),
                "company": entry.get("company_name", "Unknown"),
                "summary": entry.get("description", "")[:500],  # limit size
                "apply_url": entry.get("url", ""),
                "source": "Remotive",
            }
            if is_relevant(job, target_keywords):
                jobs.append(job)

    except Exception as e:
        print(f"Remotive fetch failed: {e}")

    print(f"Relevant Remotive jobs: {len(jobs)}")
    return jobs

# ============================================
# SAVE JOBS — path is a parameter
# ============================================

def save_jobs(all_jobs, output_path=None):
    output_path = output_path or DEFAULT_OUTPUT_PATH
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(all_jobs, f, indent=2)

    print(f"\nSaved → {output_path}")
    print(f"Total relevant jobs saved: {len(all_jobs)}")

# ============================================
# MAIN — accepts session-scoped paths
# ============================================

def main(output_path=None, profile_path=None):
    """
    Fetch jobs from all sources, filter by profile keywords,
    and save to output_path.

    Both paths are parameters so the dashboard can pass
    session-specific directories.
    """
    output_path = output_path or DEFAULT_OUTPUT_PATH
    profile_path = profile_path or DEFAULT_PROFILE_PATH

    print("================================")
    print("SMART JOB FETCHER STARTED")
    print("================================")

    target_keywords = load_profile_keywords(profile_path)

    all_jobs = []

    try:
        all_jobs.extend(fetch_weworkremotely(target_keywords))
    except Exception as e:
        print(f"WWR fetch failed: {e}")

    try:
        all_jobs.extend(fetch_remoteok(target_keywords))
    except Exception as e:
        print(f"RemoteOK fetch failed: {e}")

    try:
        all_jobs.extend(fetch_workingnomads(target_keywords))
    except Exception as e:
        print(f"WorkingNomads fetch failed: {e}")

    try:
        all_jobs.extend(fetch_remotive(target_keywords))
    except Exception as e:
        print(f"Remotive fetch failed: {e}")

    save_jobs(all_jobs, output_path)

    print("\n================================")
    print("FETCH COMPLETE")
    print("================================")

    return all_jobs

# ============================================
# RUN
# ============================================

if __name__ == "__main__":
    main()
