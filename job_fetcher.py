import feedparser
import requests
import json
import os
import time
import logging
from bs4 import BeautifulSoup
from urllib.parse import urlencode, quote_plus

# ============================================
# Import location utilities
# ============================================
from location_utils import extract_location_from_job

# ============================================
# LOGGING SETUP
# ============================================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ============================================
# CONFIGURATION
# ============================================
OUTPUT_DEFAULT = "data/jobs.json"
NETWORK_TIMEOUT = 30  # seconds
MAX_RETRIES = 3
RETRY_DELAY = 2  # seconds

# ============================================
# API KEYS (env or Streamlit secrets)
# ============================================
# JSearch is BEST for jobs (Google Jobs, LinkedIn, Indeed, etc.)
JSEARCH_API_KEY = os.getenv("JSEARCH_API_KEY", "")
# SerperDev is for general web search (not optimized for structured job data)
SERPER_API_KEY = os.getenv("SERPER_API_KEY", "")

if not JSEARCH_API_KEY or not SERPER_API_KEY:
    try:
        import streamlit as _st
        JSEARCH_API_KEY = JSEARCH_API_KEY or _st.secrets.get("JSEARCH_API_KEY", "")
        SERPER_API_KEY = SERPER_API_KEY or _st.secrets.get("SERPER_API_KEY", "")
    except (ImportError, KeyError, AttributeError):
        pass

def strip_html(text: str) -> str:
    """Remove HTML tags and decode entities from text."""
    import re
    if not text:
        return ""
    clean = re.sub(r'<[^>]+>', ' ', text)
    clean = clean.replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>')
    clean = clean.replace('&quot;', '"').replace('&#39;', "'").replace('&nbsp;', ' ')
    clean = re.sub(r'\s+', ' ', clean).strip()
    return clean

def extract_company_from_title(title: str) -> tuple:
    """
    Many RSS feeds encode company in the title as 'Company: Job Title'.
    Returns (company, clean_title).
    """
    if not title:
        return ("Unknown", title)
    if ": " in title:
        parts = title.split(": ", 1)
        if len(parts) == 2 and len(parts[0]) < 60:
            return (parts[0].strip(), parts[1].strip())
    return ("", title)

# ============================================
# JOB SOURCES CONFIGURATION
# ============================================
# --- Remote global boards ---
WWR_FEEDS = [
    "https://weworkremotely.com/categories/remote-programming-jobs.rss",
    "https://weworkremotely.com/categories/remote-design-jobs.rss",
    "https://weworkremotely.com/categories/remote-marketing-jobs.rss",
    "https://weworkremotely.com/categories/remote-customer-support-jobs.rss",
    "https://weworkremotely.com/categories/remote-product-jobs.rss",
    "https://weworkremotely.com/categories/remote-sales-jobs.rss",
]
REMOTEOK = "https://remoteok.com/remote-jobs.rss"
JOBICY = "https://jobicy.com/feed/"

# --- Lever: public JSON API, no auth needed ---
LEVER_COMPANIES = [
    # India-based / India-hiring companies
    "razorpay", "postman", "hasura", "chargebee",
    "browserstack", "clevertap", "druva", "freshworks",
    "zeta-suite", "unacademy", "meesho", "cred",
    # Global companies that hire remote India
    "netflix", "figma", "notion", "stripe", "databricks",
    "cloudflare", "twilio", "datadog", "gitlab",
    "hubspot",
]
LEVER_PER_COMPANY = 20

SERPER_MAX_QUERIES = 10  # Limit for API usage

# Export for run_auto_apply.py
__all__ = ['fetch_all', 'build_serper_queries_from_profile', 'SERPER_MAX_QUERIES']

# ============================================
# RSS PARSING
# ============================================
def parse_rss(url: str, source: str, timeout: int = NETWORK_TIMEOUT, max_retries: int = MAX_RETRIES) -> list:
    """Parse RSS feed with proper error handling and retries."""
    jobs = []
    for attempt in range(max_retries):
        try:
            logger.info(f"Fetching {source} (attempt {attempt + 1}/{max_retries})")
            response = requests.get(
                url, timeout=timeout,
                headers={
                    'User-Agent': 'JobBot/2.0 (Job Aggregator; +https://github.com/jobbot)',
                    'Accept': 'application/rss+xml, application/xml, text/xml'
                }
            )
            response.raise_for_status()
            feed = feedparser.parse(response.content)

            if feed.bozo:
                logger.warning(f"{source} RSS parsing warning: {feed.bozo_exception}")

            if not hasattr(feed, 'entries') or not feed.entries:
                logger.warning(f"{source} returned no entries")
                return []

            for entry in feed.entries:
                try:
                    raw_title = entry.get("title", "").strip()
                    author = entry.get("author", "").strip()
                    raw_summary = entry.get("summary", "").strip()

                    if author and author != "Unknown":
                        company = author
                        title = raw_title
                    else:
                        parsed_company, parsed_title = extract_company_from_title(raw_title)
                        company = parsed_company if parsed_company else "Unknown"
                        title = parsed_title

                    job = {
                        "title": title,
                        "company": company,
                        "summary": strip_html(raw_summary),
                        "apply_url": entry.get("link", "").strip(),
                        "source": source,
                    }
                    job["location_tags"] = extract_location_from_job(job)

                    if job["title"] and job["apply_url"]:
                        jobs.append(job)
                except Exception as e:
                    logger.warning(f"Error parsing job entry: {e}")
                    continue

            logger.info(f"Successfully fetched {len(jobs)} jobs from {source}")
            return jobs

        except requests.Timeout:
            logger.warning(f"{source} request timed out after {timeout}s")
            if attempt < max_retries - 1:
                time.sleep(RETRY_DELAY * (attempt + 1))
            else:
                logger.error(f"{source} failed after {max_retries} timeout attempts")
        except requests.RequestException as e:
            logger.warning(f"{source} request failed: {e}")
            if attempt < max_retries - 1:
                time.sleep(RETRY_DELAY * (attempt + 1))
            else:
                logger.error(f"{source} failed after {max_retries} attempts: {e}")
        except Exception as e:
            logger.error(f"Unexpected error parsing {source}: {e}")
            break

    return jobs

# ============================================
# REMOTIVE API
# ============================================
def fetch_remotive_jobs(timeout: int = NETWORK_TIMEOUT) -> list:
    """Fetch jobs from Remotive API."""
    jobs = []
    url = "https://remotive.com/api/remote-jobs"

    try:
        logger.info("Fetching jobs from Remotive API")
        response = requests.get(url, timeout=timeout, headers={
            'User-Agent': 'JobBot/2.0', 'Accept': 'application/json'
        })
        response.raise_for_status()
        data = response.json()

        if not isinstance(data, dict) or "jobs" not in data:
            raise ValueError("Invalid Remotive response")

        for j in data.get("jobs", []):
            try:
                if not isinstance(j, dict):
                    continue

                job = {
                    "title": j.get("title", "Unknown").strip(),
                    "company": j.get("company_name", "Unknown").strip(),
                    "summary": strip_html((j.get("description", "")[:500]).strip()),
                    "apply_url": j.get("url", "").strip(),
                    "source": "Remotive",
                    "posted_date": j.get("publication_date", ""),
                }
                job["location_tags"] = extract_location_from_job(job)

                if job["title"] and job["apply_url"]:
                    jobs.append(job)
            except Exception:
                continue

        logger.info(f"Successfully fetched {len(jobs)} jobs from Remotive")
        return jobs
    except Exception as e:
        logger.error(f"Remotive API error: {e}")
        return []

# ============================================
# LEVER API
# ============================================
def fetch_lever_jobs(companies: list = None, max_per_company: int = LEVER_PER_COMPANY) -> list:
    """Fetch jobs from Lever public API."""
    companies = companies or LEVER_COMPANIES
    all_jobs = []
    successful = 0

    logger.info(f"Fetching from {len(companies)} Lever companies")

    for company in companies:
        try:
            url = f"https://api.lever.co/v0/postings/{company}?mode=json"
            response = requests.get(url, timeout=15)

            if response.status_code == 404:
                continue

            response.raise_for_status()
            postings = response.json()

            if not isinstance(postings, list):
                continue

            company_jobs = []
            for posting in postings[:max_per_company]:
                try:
                    if not isinstance(posting, dict):
                        continue

                    location = posting.get("categories", {}).get("location", "")
                    job = {
                        "title": posting.get("text", "").strip(),
                        "company": posting.get("categories", {}).get("team", company).strip(),
                        "summary": strip_html((posting.get("description", "")[:500]).strip()),
                        "apply_url": posting.get("hostedUrl", "").strip(),
                        "source": "Lever",
                        "location": location,
                        "posted_date": str(posting.get("createdAt", "")),
                    }

                    if job["title"] and job["apply_url"]:
                        job["location_tags"] = extract_location_from_job(job)
                        company_jobs.append(job)
                except Exception:
                    continue

            if company_jobs:
                logger.info(f"Lever: {company} → {len(company_jobs)} jobs")
                all_jobs.extend(company_jobs)
                successful += 1
        except Exception as e:
            continue

    logger.info(f"Lever total: {len(all_jobs)} jobs from {successful}/{len(companies)} companies")
    return all_jobs

# ============================================
# JSEARCH API (Replaces SerperDev for Jobs)
# ============================================
def build_serper_queries_from_profile(profile: dict) -> tuple:
    """
    Generate targeted queries from user profile.
    Returns (queries, location) tuple.
    """
    headline = (profile.get("headline", "") or "").strip()
    skills = profile.get("skills", [])
    country = (profile.get("country", "") or "").strip()
    state = (profile.get("state", "") or "").strip()
    search_terms = profile.get("search_terms", [])
    industry = (profile.get("industry", "") or "").strip()

    # Determine if remote-only
    is_remote_only = country.lower() in ("remote only", "remote", "global")

    # Build location string
    location = None
    if not is_remote_only:
        if state and state != "Any":
            location = state.replace("(", "").replace(")", "")
        elif country:
            location = country

    queries = []

    # Priority 1: Search terms (user's preferred job titles)
    if search_terms:
        for term in search_terms[:4]:
            queries.append(term)

    # Priority 2: Headline-based
    if headline:
        queries.append(headline)

    # Priority 3: Industry combinations
    if industry:
        queries.append(f"{industry} jobs")

    # Priority 4: Top 2 skills
    if skills:
        for skill in skills[:2]:
            if len(skill.split()) <= 3:
                queries.append(f"{skill} specialist")

    # Deduplicate and limit
    seen = set()
    unique_queries = []
    for q in queries:
        q_clean = q.strip()
        if q_clean and q_clean.lower() not in seen:
            seen.add(q_clean.lower())
            unique_queries.append(q_clean)

    return unique_queries[:SERPER_MAX_QUERIES], location

def fetch_jsearch_jobs(queries: list = None, location: str = None) -> list:
    """
    Fetch jobs from Google Jobs, LinkedIn, Indeed, Glassdoor via JSearch API (RapidAPI).
    This is the RELIABLE way to get aggregated jobs (SerperDev doesn't support this well).
    """
    if not JSEARCH_API_KEY:
        logger.warning("JSearch: No API key found (add JSEARCH_API_KEY to .env or secrets), skipping")
        return []

    if not queries:
        logger.warning("JSearch: No queries provided")
        return []

    # Standardize queries
    query_strings = []
    if queries and isinstance(queries[0], dict):
        query_strings = [q.get("q", "") for q in queries if q.get("q")]
        if queries[0].get("location"):
            location = queries[0]["location"]
    else:
        query_strings = queries

    # RapidAPI Free Tier = 100 requests/month. 
    # We limit to 5 queries per run to be safe.
    query_strings = query_strings[:5]

    logger.info(f"JSearch: Fetching jobs for {len(query_strings)} queries (location: {location or 'India'})")

    jobs = []
    seen_urls = set()
    searches_used = 0

    url = "https://jsearch.p.rapidapi.com/search"

    headers = {
        "X-RapidAPI-Key": JSEARCH_API_KEY,
        "X-RapidAPI-Host": "jsearch.p.rapidapi.com"
    }

    for query in query_strings:
        if searches_used >= 5:
            logger.info("JSearch: Reached query limit for this run")
            break

        try:
            logger.info(f"JSearch: '{query}' in {location or 'India'}")

            querystring = {
                "query": f"{query} in {location or 'India'}",
                "page": "1",
                "num_pages": "1", 
                "date_posted": "week" # Get fresh jobs
            }

            response = requests.get(url, headers=headers, params=querystring, timeout=NETWORK_TIMEOUT)
            searches_used += 1

            if response.status_code == 429:
                logger.warning("JSearch: Rate limit hit")
                break
            elif response.status_code == 403:
                logger.error("JSearch: Invalid API key")
                break

            response.raise_for_status()
            data = response.json()

            job_results = data.get("data", [])

            if not job_results:
                logger.info(f"JSearch: No jobs found for '{query}'")
                continue

            added = 0
            for result in job_results:
                try:
                    title = result.get("job_title", "").strip()
                    company = result.get("employer_name", "Unknown").strip()
                    description = result.get("job_description", "").strip()

                    # Try getting apply link, fallback to google link
                    link = result.get("job_apply_link")
                    if not link:
                         link = result.get("job_google_link", "")

                    # Build location string
                    loc_parts = []
                    if result.get("job_city"): loc_parts.append(result.get("job_city"))
                    if result.get("job_state"): loc_parts.append(result.get("job_state"))
                    if result.get("job_country"): loc_parts.append(result.get("job_country"))
                    job_location = ", ".join(loc_parts)

                    posted_date = result.get("job_posted_at_datetime_utc", "")

                    if not title or not link:
                        continue

                    # Determine source
                    source_name = "Google Jobs" # Default
                    link_lower = link.lower()
                    if "linkedin.com" in link_lower: source_name = "LinkedIn"
                    elif "naukri.com" in link_lower: source_name = "Naukri"
                    elif "indeed.com" in link_lower: source_name = "Indeed"
                    elif "glassdoor.com" in link_lower: source_name = "Glassdoor"
                    elif "foundit.in" in link_lower: source_name = "Foundit"
                    elif "instahyre.com" in link_lower: source_name = "Instahyre"

                    if link in seen_urls:
                        continue
                    seen_urls.add(link)

                    job = {
                        "title": title,
                        "company": company,
                        "summary": strip_html(description[:500]),
                        "apply_url": link,
                        "source": source_name,
                        "location": job_location,
                        "posted_date": posted_date,
                    }
                    job["location_tags"] = extract_location_from_job(job)
                    jobs.append(job)
                    added += 1

                except Exception as e:
                    logger.debug(f"Error parsing JSearch result: {e}")
                    continue

            logger.info(f"JSearch: '{query}' → {added} jobs")
            time.sleep(1) # Be nice to API

        except requests.Timeout:
            logger.warning(f"JSearch: Timeout for '{query}'")
        except requests.RequestException as e:
            logger.warning(f"JSearch: Request failed: {e}")
        except Exception as e:
            logger.error(f"JSearch: Unexpected error: {e}")

    logger.info(f"JSearch total: {len(jobs)} unique jobs")
    return jobs

# ============================================
# FETCH ALL
# ============================================
def fetch_all(output_path: str = None, serper_queries: list = None,
              prioritize_local: bool = False, location: str = None) -> list:
    """
    Fetch jobs from all sources.
    """
    output_path = output_path or OUTPUT_DEFAULT
    all_jobs = []
    source_counts = {}

    logger.info("Starting multi-layer job fetch from all sources")

    if prioritize_local:
        logger.info("Prioritizing local sources first, then fetching global sources")

    # Layer 1: JSearch (The RELIABLE Google Jobs/LinkedIn aggregator)
    # This replaces the broken SerperDev implementation
    try:
        # Note: We pass serper_queries here as they are just list of strings/dicts
        jobs = fetch_jsearch_jobs(queries=serper_queries, location=location)
        all_jobs.extend(jobs)
    except Exception as e:
        logger.error(f"Failed to fetch JSearch: {e}")

    # Layer 2: Lever (tech companies)
    try:
        jobs = fetch_lever_jobs()
        all_jobs.extend(jobs)
    except Exception as e:
        logger.error(f"Failed to fetch Lever: {e}")

    # Layer 3: Remotive (curated remote)
    try:
        jobs = fetch_remotive_jobs()
        all_jobs.extend(jobs)
    except Exception as e:
        logger.error(f"Failed to fetch Remotive: {e}")

    # Layer 4: RSS FEEDS
    logger.info("Fetching RSS feeds (will reorder local jobs to top later)")

    for feed_url in WWR_FEEDS:
        try:
            jobs = parse_rss(feed_url, "WeWorkRemotely")
            all_jobs.extend(jobs)
        except Exception as e:
            logger.error(f"Failed to fetch {feed_url}: {e}")

    try:
        jobs = parse_rss(REMOTEOK, "RemoteOK")
        all_jobs.extend(jobs)
    except Exception as e:
        logger.error(f"Failed to fetch RemoteOK: {e}")

    try:
        jobs = parse_rss(JOBICY, "Jobicy")
        all_jobs.extend(jobs)
    except Exception as e:
        logger.error(f"Failed to fetch Jobicy: {e}")

    if not all_jobs:
        logger.error("Failed to fetch jobs from any source!")
        raise RuntimeError(
            "Could not fetch jobs from any source. "
            "Check your internet connection and try again."
        )

    logger.info(f"Total jobs fetched: {len(all_jobs)}")

    # Log source breakdown
    for job in all_jobs:
        src = job.get("source", "Unknown")
        source_counts[src] = source_counts.get(src, 0) + 1

    logger.info("Source breakdown:")
    for src, count in sorted(source_counts.items(), key=lambda x: -x[1]):
        logger.info(f"  {src}: {count}")

    # Deduplicate jobs based on URL
    seen_urls = set()
    unique_jobs = []
    for job in all_jobs:
        url = job.get("apply_url", "")
        if url and url not in seen_urls:
            seen_urls.add(url)
            unique_jobs.append(job)
        elif not url:
            unique_jobs.append(job)

    logger.info(f"Unique jobs after deduplication: {len(unique_jobs)}")

    # Save to file
    try:
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(unique_jobs, f, indent=2, ensure_ascii=False)
        logger.info(f"Jobs saved to {output_path}")
    except Exception as e:
        logger.error(f"Failed to save jobs file: {e}")
        raise

    return unique_jobs

if __name__ == "__main__":
    import sys
    try:
        output = sys.argv[1] if len(sys.argv) > 1 else OUTPUT_DEFAULT
        test_queries = [
            "Customer Experience Specialist",
            "Technical Support Specialist"
        ]

        jobs = fetch_all(
            output_path=output,
            serper_queries=test_queries,
            location="Bangalore, India",
            prioritize_local=True
        )

        print(f"\n✅ Successfully fetched {len(jobs)} unique jobs!")
        print(f"Saved to: {output}")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        logger.exception("Job fetching failed")
        sys.exit(1)
