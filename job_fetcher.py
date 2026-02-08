import feedparser
import requests
import json
import os
import time
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

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
NETWORK_TIMEOUT = 15  # Reduced from 30
MAX_RETRIES = 2  # Reduced from 3
RETRY_DELAY = 1  # Reduced from 2

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
JSEARCH_API_KEY = load_api_key("JSEARCH_API_KEY") or load_api_key("RAPIDAPI_KEY")
SERPAPI_API_KEY = load_api_key("SERPAPI_API_KEY") or load_api_key("SERPAPI_KEY")

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
# JOB SOURCES CONFIGURATION (OPTIMIZED)
# ============================================

# Reduced WWR feeds to most relevant categories
WWR_FEEDS = [
    "https://weworkremotely.com/categories/remote-programming-jobs.rss",
    "https://weworkremotely.com/categories/remote-product-jobs.rss",
]

REMOTEOK = "https://remoteok.com/remote-jobs.rss"
JOBICY = "https://jobicy.com/feed/"
ADZUNA_INDIA = "https://www.adzuna.in/rss"

# REMOVED: Lever companies - too resource intensive
# REMOVED: Himalayas - bloats search

# API query limits (optimized for speed)
SERPER_QUERIES = 0  # Free tier doesn't support /jobs endpoint
JSEARCH_QUERIES = 3  # Reduced from 5
SERPAPI_QUERIES = 3  # Reduced from 4

__all__ = ['fetch_all', 'build_queries_from_profile', 'SERPER_QUERIES', 'JSEARCH_QUERIES', 'SERPAPI_QUERIES']


# ============================================
# RSS PARSING (OPTIMIZED WITH PARALLEL)
# ============================================

def parse_rss(url: str, source: str, timeout: int = NETWORK_TIMEOUT, max_retries: int = MAX_RETRIES) -> list:
    """Parse RSS feed with retries and timeout optimization"""
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
                time.sleep(RETRY_DELAY)
            else:
                logger.error(f"{source} failed after {max_retries} timeout attempts")
        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(RETRY_DELAY)
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
            except Exception as e:
                logger.warning(f"Error parsing Remotive job: {e}")
                continue

        logger.info(f"Remotive: {len(jobs)} jobs fetched")
        return jobs

    except Exception as e:
        logger.error(f"Remotive API error: {e}")
        return []


# ============================================
# QUERY BUILDER
# ============================================

def build_queries_from_profile(profile: dict) -> tuple:
    """Build search queries from user profile"""
    queries = []
    
    search_terms = profile.get("search_terms", [])
    if not search_terms:
        headline = profile.get("headline", "")
        search_terms = [headline] if headline else ["jobs"]
    
    skills = profile.get("skills", [])[:3]
    
    # Use primary search term
    for term in search_terms[:2]:
        queries.append(term)
    
    # Add one skill-enhanced query
    if skills and search_terms:
        queries.append(f"{search_terms[0]} {skills[0]}")
    
    # Location
    location = None
    country = profile.get("country", "")
    state = profile.get("state", "")
    
    if country and country.lower() != "remote only":
        if state and state != country:
            location = f"{state}, {country}"
        else:
            location = country
    
    return queries, location


# ============================================
# JSEARCH API (OPTIMIZED)
# ============================================

def fetch_jsearch_jobs(queries: list, location: str = None, 
                       per_query: int = 10) -> list:
    """Fetch from JSearch API with optimized pagination"""
    if not JSEARCH_API_KEY:
        logger.warning("JSearch API key missing")
        return []
    
    jobs = []
    url = "https://jsearch.p.rapidapi.com/search"
    
    headers = {
        "X-RapidAPI-Key": JSEARCH_API_KEY,
        "X-RapidAPI-Host": "jsearch.p.rapidapi.com"
    }
    
    for query in queries:
        try:
            params = {
                "query": f"{query} {location}" if location else query,
                "num_pages": 1,  # Single page only for speed
                "page": 1,
            }
            
            logger.info(f"JSearch query: {params['query']}")
            response = requests.get(url, headers=headers, params=params, timeout=NETWORK_TIMEOUT)
            response.raise_for_status()
            data = response.json()
            
            for j in data.get("data", [])[:per_query]:
                try:
                    job = {
                        "title": j.get("job_title", "Unknown"),
                        "company": j.get("employer_name", "Unknown"),
                        "summary": strip_html(j.get("job_description", "")[:500]),
                        "apply_url": j.get("job_apply_link") or j.get("job_google_link", ""),
                        "source": "JSearch",
                        "location": j.get("job_city", "") or j.get("job_country", ""),
                        "posted_date": j.get("job_posted_at_datetime_utc", ""),
                    }
                    job["location_tags"] = extract_location_from_job(job)
                    
                    if job["title"] and job["apply_url"]:
                        jobs.append(job)
                except Exception:
                    continue
            
            time.sleep(0.5)  # Reduced delay
            
        except Exception as e:
            logger.warning(f"JSearch error for '{query}': {e}")
    
    logger.info(f"JSearch: {len(jobs)} jobs fetched")
    return jobs


# ============================================
# SERPAPI (OPTIMIZED)
# ============================================

def fetch_serpapi_jobs(queries: list, location: str = None, 
                       per_query: int = 10) -> list:
    """Fetch from SerpAPI with optimized settings"""
    if not SERPAPI_API_KEY:
        logger.warning("SerpAPI key missing")
        return []
    
    jobs = []
    
    for query in queries:
        try:
            params = {
                "engine": "google_jobs",
                "q": f"{query} {location}" if location else query,
                "api_key": SERPAPI_API_KEY,
                "num": per_query,
            }
            
            if location:
                params["location"] = location
            
            logger.info(f"SerpAPI query: {params['q']}")
            response = requests.get(
                "https://serpapi.com/search",
                params=params,
                timeout=NETWORK_TIMEOUT
            )
            response.raise_for_status()
            data = response.json()
            
            for j in data.get("jobs_results", []):
                try:
                    title = j.get("title", "Unknown")
                    company = j.get("company_name", "Unknown")
                    description = j.get("description", "")
                    link = j.get("share_url") or j.get("related_links", [{}])[0].get("link", "")
                    job_location = j.get("location", "")
                    
                    source = "SerpAPI (Google Jobs)"
                    
                    job = {
                        "title": title,
                        "company": company,
                        "summary": strip_html(description[:500]),
                        "apply_url": link,
                        "source": source,
                        "location": job_location,
                    }
                    job["location_tags"] = extract_location_from_job(job)
                    
                    if job["title"] and job["apply_url"]:
                        jobs.append(job)

                except Exception:
                    continue

            time.sleep(0.5)  # Reduced delay

        except Exception as e:
            logger.warning(f"SerpAPI error for '{query}': {e}")

    logger.info(f"SerpAPI: {len(jobs)} jobs fetched")
    return jobs


# ============================================
# PARALLEL RSS FETCHING
# ============================================

def fetch_rss_parallel(feeds: list) -> list:
    """Fetch multiple RSS feeds in parallel"""
    all_jobs = []
    
    with ThreadPoolExecutor(max_workers=4) as executor:
        future_to_feed = {
            executor.submit(parse_rss, feed_url, feed_name): (feed_url, feed_name)
            for feed_url, feed_name in feeds
        }
        
        for future in as_completed(future_to_feed):
            try:
                jobs = future.result(timeout=20)
                all_jobs.extend(jobs)
            except Exception as e:
                feed_url, feed_name = future_to_feed[future]
                logger.error(f"Failed to fetch {feed_name}: {e}")
    
    return all_jobs


# ============================================
# MAIN ORCHESTRATOR (OPTIMIZED)
# ============================================

def fetch_all(output_path: str = None, profile: dict = None, 
              prioritize_local: bool = False) -> list:
    """
    Optimized job fetching - targets 1-2 minute runtime
    
    Key optimizations:
    - REMOVED: Lever companies (too slow)
    - REMOVED: Himalayas (bloats results)
    - Parallel RSS fetching
    - Reduced API queries
    - Lower timeouts and retries
    - Streamlined RSS feeds
    """
    output_path = output_path or OUTPUT_DEFAULT
    all_jobs = []

    logger.info("Starting OPTIMIZED job fetch")

    # Generate queries from profile
    if profile:
        queries, location = build_queries_from_profile(profile)
        logger.info(f"Generated {len(queries)} queries, location: {location or 'None'}")
    else:
        queries = []
        location = None

    # Layer 1: API sources (parallel where possible)
    if queries:
        jsearch_queries = queries[:JSEARCH_QUERIES]
        serpapi_queries = queries[:SERPAPI_QUERIES]

        logger.info(f"API split: JSearch={len(jsearch_queries)}, SerpAPI={len(serpapi_queries)}")

        # JSearch
        try:
            jobs = fetch_jsearch_jobs(jsearch_queries, location)
            all_jobs.extend(jobs)
        except Exception as e:
            logger.error(f"JSearch failed: {e}")

        # SerpAPI
        try:
            jobs = fetch_serpapi_jobs(serpapi_queries, location)
            all_jobs.extend(jobs)
        except Exception as e:
            logger.error(f"SerpAPI failed: {e}")

    # Layer 2: Remotive (fast API)
    try:
        jobs = fetch_remotive_jobs()
        all_jobs.extend(jobs)
    except Exception as e:
        logger.error(f"Remotive failed: {e}")

    # Layer 3: RSS feeds (PARALLEL for speed)
    logger.info("Fetching RSS feeds in parallel")
    
    # Build feed list based on prioritization
    feeds_to_fetch = []
    
    if prioritize_local:
        # Limit WWR when prioritizing local
        for feed_url in WWR_FEEDS[:1]:  # Just programming
            feeds_to_fetch.append((feed_url, "WeWorkRemotely"))
    else:
        # All WWR feeds for remote-first
        for feed_url in WWR_FEEDS:
            feeds_to_fetch.append((feed_url, "WeWorkRemotely"))
    
    # Always fetch these
    feeds_to_fetch.extend([
        (JOBICY, "Jobicy"),
        (ADZUNA_INDIA, "Adzuna India"),
    ])
    
    # Conditionally fetch RemoteOK
    if not prioritize_local or len(all_jobs) < 60:
        feeds_to_fetch.append((REMOTEOK, "RemoteOK"))
    
    # Fetch all RSS in parallel
    rss_jobs = fetch_rss_parallel(feeds_to_fetch)
    all_jobs.extend(rss_jobs)

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
