import feedparser
import requests
import json
import os
import time
import logging

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
NETWORK_TIMEOUT = 30
MAX_RETRIES = 3
RETRY_DELAY = 2

# ============================================
# API KEYS - ROBUST LOADING
# ============================================

def load_api_key(key_name):
    """Load API key from environment or Streamlit secrets"""
    # Try environment first
    key = os.getenv(key_name, "")
    if key:
        return key
    
    # Try Streamlit secrets
    try:
        import streamlit as st
        return st.secrets.get(key_name, "")
    except:
        return ""

# Load all API keys
SERPER_API_KEY = load_api_key("SERPER_API_KEY")
JSEARCH_API_KEY = load_api_key("JSEARCH_API_KEY")
SERPAPI_API_KEY = load_api_key("SERPAPI_API_KEY")

# Log which keys are available
logger.info("API Keys loaded:")
logger.info(f"  SerperDev: {'✓' if SERPER_API_KEY else '✗ MISSING'}")
logger.info(f"  JSearch: {'✓' if JSEARCH_API_KEY else '✗ MISSING'}")
logger.info(f"  SerpAPI: {'✓' if SERPAPI_API_KEY else '✗ MISSING'}")

# ============================================
# HELPER FUNCTIONS
# ============================================

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
    """Extract company from 'Company: Job Title' format"""
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

LEVER_COMPANIES = [
    "razorpay", "postman", "hasura", "chargebee",
    "browserstack", "clevertap", "druva", "freshworks",
    "zeta-suite", "unacademy", "meesho", "cred",
    "netflix", "figma", "notion", "stripe", "databricks",
    "cloudflare", "twilio", "datadog", "gitlab",
    "hubspot",
]
LEVER_PER_COMPANY = 20

# API query limits (balanced across 3 APIs)
SERPER_QUERIES = 4
JSEARCH_QUERIES = 3
SERPAPI_QUERIES = 3

__all__ = ['fetch_all', 'build_queries_from_profile', 'SERPER_QUERIES', 'JSEARCH_QUERIES', 'SERPAPI_QUERIES']


# ============================================
# RSS PARSING
# ============================================

def parse_rss(url: str, source: str, timeout: int = NETWORK_TIMEOUT, max_retries: int = MAX_RETRIES) -> list:
    """Parse RSS feed with retries"""
    jobs = []

    for attempt in range(max_retries):
        try:
            logger.info(f"Fetching {source} (attempt {attempt + 1}/{max_retries})")

            response = requests.get(
                url, timeout=timeout,
                headers={
                    'User-Agent': 'JobBot/2.0',
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
            if attempt < max_retries - 1:
                time.sleep(RETRY_DELAY * (attempt + 1))
            else:
                logger.error(f"{source} failed after {max_retries} timeout attempts")
        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(RETRY_DELAY * (attempt + 1))
            else:
                logger.error(f"{source} failed: {e}")
                break

    return jobs


# ============================================
# REMOTIVE API
# ============================================

def fetch_remotive_jobs(timeout: int = NETWORK_TIMEOUT) -> list:
    """Fetch jobs from Remotive API"""
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
    """Fetch jobs from Lever public API"""
    companies = companies or LEVER_COMPANIES
    all_jobs = []
    successful = 0

    logger.info(f"Fetching from {len(companies)} Lever companies")

    for company in companies:
        try:
            url = f"https://api.lever.co/v0/postings/{company}"
            response = requests.get(url, timeout=10)

            if response.status_code == 404:
                continue

            response.raise_for_status()
            postings = response.json()

            if not isinstance(postings, list):
                continue

            company_jobs = 0
            for p in postings[:max_per_company]:
                try:
                    if not isinstance(p, dict):
                        continue

                    job = {
                        "title": p.get("text", "Unknown").strip(),
                        "company": company.replace("-", " ").title(),
                        "summary": strip_html((p.get("description", "") or p.get("descriptionPlain", ""))[:500]),
                        "apply_url": p.get("applyUrl") or p.get("hostedUrl", ""),
                        "source": "Lever",
                        "location": ", ".join(p.get("categories", {}).get("location", [])),
                        "posted_date": p.get("createdAt", ""),
                    }
                    job["location_tags"] = extract_location_from_job(job)

                    if job["title"] and job["apply_url"]:
                        all_jobs.append(job)
                        company_jobs += 1
                except Exception:
                    continue

            if company_jobs > 0:
                logger.info(f"Lever: {company} → {company_jobs} jobs")
                successful += 1

            time.sleep(0.3)

        except Exception:
            continue

    logger.info(f"Lever total: {len(all_jobs)} jobs from {successful}/{len(companies)} companies")
    return all_jobs


# ============================================
# QUERY BUILDER
# ============================================

def build_queries_from_profile(profile: dict) -> tuple:
    """Generate queries from profile. Returns (queries, location)"""
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

    # Priority 1: Search terms
    if search_terms:
        for term in search_terms[:5]:
            queries.append(term)

    # Priority 2: Headline
    if headline:
        queries.append(headline)

    # Priority 3: Industry
    if industry and len(queries) < 8:
        queries.append(f"{industry} jobs")

    # Priority 4: Top skills
    if skills and len(queries) < 10:
        for skill in skills[:2]:
            if len(skill.split()) <= 3:
                queries.append(f"{skill} specialist")

    # Deduplicate
    seen = set()
    unique_queries = []
    for q in queries:
        q_clean = q.strip()
        if q_clean and q_clean.lower() not in seen:
            seen.add(q_clean.lower())
            unique_queries.append(q_clean)

    return unique_queries[:10], location


# ============================================
# SERPERDEV (GOOGLE JOBS)
# ============================================

def fetch_serperdev_jobs(queries: list, location: str = None) -> list:
    """Fetch jobs from SerperDev /jobs endpoint"""
    if not SERPER_API_KEY:
        logger.warning("SerperDev: No API key found")
        return []

    if not queries:
        return []

    queries = queries[:SERPER_QUERIES]
    logger.info(f"SerperDev: Fetching {len(queries)} queries (location: {location or 'India'})")

    jobs = []
    seen_urls = set()

    for query in queries:
        try:
            logger.info(f"SerperDev: '{query}'")

            url = "https://google.serper.dev/jobs"
            payload = {
                "q": query,
                "location": location or "India",
                "num": 50,
            }
            headers = {
                'X-API-KEY': SERPER_API_KEY,
                'Content-Type': 'application/json'
            }

            response = requests.post(url, json=payload, headers=headers, timeout=20)

            if response.status_code in [429, 403]:
                logger.warning(f"SerperDev: HTTP {response.status_code}")
                break

            response.raise_for_status()
            data = response.json()

            for result in data.get("jobs", []):
                try:
                    title = result.get("title", "").strip()
                    
                    company_raw = result.get("company", "Unknown")
                    if isinstance(company_raw, dict):
                        company = company_raw.get("name", "Unknown")
                    else:
                        company = str(company_raw) if company_raw else "Unknown"

                    description = result.get("description", "").strip()
                    link = result.get("link", "").strip()
                    job_location = result.get("location", "")

                    if not title or not link or link in seen_urls:
                        continue
                    seen_urls.add(link)

                    # Determine source from URL
                    source = "Google Jobs"
                    link_lower = link.lower()
                    if "linkedin.com" in link_lower:
                        source = "LinkedIn"
                    elif "naukri.com" in link_lower:
                        source = "Naukri"
                    elif "indeed.com" in link_lower:
                        source = "Indeed"

                    job = {
                        "title": title,
                        "company": company,
                        "summary": strip_html(description[:500]),
                        "apply_url": link,
                        "source": source,
                        "location": job_location,
                    }
                    job["location_tags"] = extract_location_from_job(job)
                    jobs.append(job)

                except Exception:
                    continue

            time.sleep(0.5)

        except Exception as e:
            logger.warning(f"SerperDev error for '{query}': {e}")

    logger.info(f"SerperDev: {len(jobs)} jobs fetched")
    return jobs


# ============================================
# JSEARCH (RAPIDAPI)
# ============================================

def fetch_jsearch_jobs(queries: list, location: str = None) -> list:
    """Fetch jobs from JSearch API"""
    if not JSEARCH_API_KEY:
        logger.warning("JSearch: No API key found")
        return []

    if not queries:
        return []

    queries = queries[:JSEARCH_QUERIES]
    logger.info(f"JSearch: Fetching {len(queries)} queries (location: {location or 'India'})")

    jobs = []
    seen_urls = set()

    url = "https://jsearch.p.rapidapi.com/search"
    headers = {
        "X-RapidAPI-Key": JSEARCH_API_KEY,
        "X-RapidAPI-Host": "jsearch.p.rapidapi.com"
    }

    for query in queries:
        try:
            logger.info(f"JSearch: '{query}'")

            params = {
                "query": f"{query} in {location or 'India'}",
                "page": "1",
                "num_pages": "1",
                "date_posted": "month"
            }

            response = requests.get(url, headers=headers, params=params, timeout=20)

            if response.status_code in [429, 403]:
                logger.warning(f"JSearch: HTTP {response.status_code}")
                break

            response.raise_for_status()
            data = response.json()

            for result in data.get("data", []):
                try:
                    title = result.get("job_title", "").strip()
                    company = result.get("employer_name", "Unknown").strip()
                    description = result.get("job_description", "").strip()

                    link = result.get("job_apply_link") or result.get("job_google_link", "")

                    if not title or not link or link in seen_urls:
                        continue
                    seen_urls.add(link)

                    # Build location
                    loc_parts = []
                    if result.get("job_city"):
                        loc_parts.append(result["job_city"])
                    if result.get("job_state"):
                        loc_parts.append(result["job_state"])
                    job_location = ", ".join(loc_parts)

                    # Determine source
                    source = "Google Jobs"
                    link_lower = link.lower()
                    if "linkedin.com" in link_lower:
                        source = "LinkedIn"
                    elif "naukri.com" in link_lower:
                        source = "Naukri"
                    elif "indeed.com" in link_lower:
                        source = "Indeed"

                    job = {
                        "title": title,
                        "company": company,
                        "summary": strip_html(description[:500]),
                        "apply_url": link,
                        "source": source,
                        "location": job_location,
                    }
                    job["location_tags"] = extract_location_from_job(job)
                    jobs.append(job)

                except Exception:
                    continue

            time.sleep(1.0)

        except Exception as e:
            logger.warning(f"JSearch error for '{query}': {e}")

    logger.info(f"JSearch: {len(jobs)} jobs fetched")
    return jobs


# ============================================
# SERPAPI (GOOGLE JOBS)
# ============================================

def fetch_serpapi_jobs(queries: list, location: str = None) -> list:
    """Fetch jobs from SerpAPI"""
    if not SERPAPI_API_KEY:
        logger.warning("SerpAPI: No API key found")
        return []

    if not queries:
        return []

    queries = queries[:SERPAPI_QUERIES]
    logger.info(f"SerpAPI: Fetching {len(queries)} queries (location: {location or 'India'})")

    jobs = []
    seen_urls = set()

    for query in queries:
        try:
            logger.info(f"SerpAPI: '{query}'")

            url = "https://serpapi.com/search"
            params = {
                'engine': 'google_jobs',
                'q': query,
                'location': location or 'India',
                'api_key': SERPAPI_API_KEY,
            }

            response = requests.get(url, params=params, timeout=30)

            if response.status_code in [429, 403]:
                logger.warning(f"SerpAPI: HTTP {response.status_code}")
                break

            response.raise_for_status()
            data = response.json()

            for result in data.get('jobs_results', []):
                try:
                    title = result.get('title', '').strip()
                    company = result.get('company_name', 'Unknown').strip()
                    description = result.get('description', '').strip()
                    link = result.get('apply_link') or result.get('share_link', '')
                    job_location = result.get('location', '')

                    if not title or not link or link in seen_urls:
                        continue
                    seen_urls.add(link)

                    # Determine source
                    source = "Google Jobs"
                    link_lower = link.lower()
                    if "linkedin.com" in link_lower:
                        source = "LinkedIn"
                    elif "naukri.com" in link_lower:
                        source = "Naukri"
                    elif "indeed.com" in link_lower:
                        source = "Indeed"

                    job = {
                        "title": title,
                        "company": company,
                        "summary": strip_html(description[:500]),
                        "apply_url": link,
                        "source": source,
                        "location": job_location,
                    }
                    job["location_tags"] = extract_location_from_job(job)
                    jobs.append(job)

                except Exception:
                    continue

            time.sleep(1.0)

        except Exception as e:
            logger.warning(f"SerpAPI error for '{query}': {e}")

    logger.info(f"SerpAPI: {len(jobs)} jobs fetched")
    return jobs


# ============================================
# MAIN ORCHESTRATOR
# ============================================

def fetch_all(output_path: str = None, profile: dict = None, 
              prioritize_local: bool = False) -> list:
    """
    Fetch jobs from all sources with 3-API balance
    
    Strategy:
    1. SerperDev: 4 queries (best for local)
    2. JSearch: 3 queries (good aggregation)
    3. SerpAPI: 3 queries (reliable fallback)
    4. Lever + Remotive (free APIs)
    5. RSS feeds (bulk free sources)
    """
    output_path = output_path or OUTPUT_DEFAULT
    all_jobs = []

    logger.info("Starting job fetch from all sources")

    # Generate queries from profile
    if profile:
        queries, location = build_queries_from_profile(profile)
        logger.info(f"Generated {len(queries)} queries, location: {location or 'None'}")
    else:
        queries = []
        location = None

    # Split queries across 3 APIs
    if queries:
        serper_queries = queries[:SERPER_QUERIES]
        jsearch_queries = queries[SERPER_QUERIES:SERPER_QUERIES+JSEARCH_QUERIES]
        serpapi_queries = queries[SERPER_QUERIES+JSEARCH_QUERIES:SERPER_QUERIES+JSEARCH_QUERIES+SERPAPI_QUERIES]

        logger.info(f"API split: SerperDev={len(serper_queries)}, JSearch={len(jsearch_queries)}, SerpAPI={len(serpapi_queries)}")

        # Layer 1: SerperDev (primary)
        try:
            jobs = fetch_serperdev_jobs(serper_queries, location)
            all_jobs.extend(jobs)
        except Exception as e:
            logger.error(f"SerperDev failed: {e}")

        # Layer 2: JSearch (secondary)
        try:
            jobs = fetch_jsearch_jobs(jsearch_queries, location)
            all_jobs.extend(jobs)
        except Exception as e:
            logger.error(f"JSearch failed: {e}")

        # Layer 3: SerpAPI (fallback)
        try:
            jobs = fetch_serpapi_jobs(serpapi_queries, location)
            all_jobs.extend(jobs)
        except Exception as e:
            logger.error(f"SerpAPI failed: {e}")

    # Layer 4: Lever
    try:
        jobs = fetch_lever_jobs()
        all_jobs.extend(jobs)
    except Exception as e:
        logger.error(f"Lever failed: {e}")

    # Layer 5: Remotive
    try:
        jobs = fetch_remotive_jobs()
        all_jobs.extend(jobs)
    except Exception as e:
        logger.error(f"Remotive failed: {e}")

    # Layer 6: RSS feeds
    logger.info("Fetching RSS feeds")

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
        logger.error(f"RemoteOK failed: {e}")

    try:
        jobs = parse_rss(JOBICY, "Jobicy")
        all_jobs.extend(jobs)
    except Exception as e:
        logger.error(f"Jobicy failed: {e}")

    # Error check
    if not all_jobs:
        logger.error("No jobs fetched from any source!")
        raise RuntimeError("Could not fetch jobs. Check API keys and internet connection.")

    logger.info(f"Total jobs fetched: {len(all_jobs)}")

    # Count by source
    sources = {}
    for job in all_jobs:
        src = job.get("source", "Unknown")
        sources[src] = sources.get(src, 0) + 1

    logger.info("Source breakdown:")
    for src, count in sorted(sources.items(), key=lambda x: -x[1]):
        logger.info(f"  {src}: {count}")

    # Deduplicate
    seen_urls = set()
    unique_jobs = []
    for job in all_jobs:
        url = job.get("apply_url", "")
        if url and url not in seen_urls:
            seen_urls.add(url)
            unique_jobs.append(job)
        elif not url:
            unique_jobs.append(job)

    logger.info(f"Unique jobs after dedup: {len(unique_jobs)} (removed {len(all_jobs) - len(unique_jobs)})")

    # Save
    try:
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(unique_jobs, f, indent=2, ensure_ascii=False)
        logger.info(f"Jobs saved to {output_path}")
    except Exception as e:
        logger.error(f"Failed to save jobs: {e}")
        raise

    return unique_jobs


# ============================================
# CLI ENTRY
# ============================================

if __name__ == "__main__":
    import sys

    try:
        output = sys.argv[1] if len(sys.argv) > 1 else OUTPUT_DEFAULT

        # Test with sample queries
        test_profile = {
            "search_terms": ["software engineer", "data analyst"],
            "headline": "Software Engineer",
            "skills": ["python", "javascript"],
            "state": "Karnataka (Bangalore)",
            "country": "India"
        }

        jobs = fetch_all(output_path=output, profile=test_profile)

        print(f"\n✅ Fetched {len(jobs)} jobs!")
        print(f"Saved to: {output}")

        sources = {}
        for job in jobs:
            source = job.get("source", "Unknown")
            sources[source] = sources.get(source, 0) + 1

        print("\nBreakdown:")
        for source, count in sorted(sources.items(), key=lambda x: -x[1]):
            print(f"  {source}: {count}")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
