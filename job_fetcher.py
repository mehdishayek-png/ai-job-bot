import feedparser
import requests
import json
import os
import time
import logging

# ============================================
# NEW: Import our location utilities
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


def strip_html(text: str) -> str:
    """Remove HTML tags and decode entities from text."""
    import re
    if not text:
        return ""
    # Remove HTML tags
    clean = re.sub(r'<[^>]+>', ' ', text)
    # Decode common HTML entities
    clean = clean.replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>')
    clean = clean.replace('&quot;', '"').replace('&#39;', "'").replace('&nbsp;', ' ')
    # Collapse whitespace
    clean = re.sub(r'\s+', ' ', clean).strip()
    return clean


def extract_company_from_title(title: str) -> tuple:
    """
    Many RSS feeds encode company in the title as 'Company: Job Title'.
    Returns (company, clean_title).
    """
    if not title:
        return ("Unknown", title)
    # WeWorkRemotely uses "Company: Title" format
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

# Jobicy - High quality remote jobs RSS feed
JOBICY = "https://jobicy.com/feed/"

# Lever - Public JSON API for tech companies (no auth needed)
# Each company has a postings endpoint: https://api.lever.co/v0/postings/{company}
LEVER_COMPANIES = [
    "netflix", "figma", "notion", "stripe", "databricks",
    "cloudflare", "twilio", "datadog", "gitlab",
    "intercom", "hubspot", "zendesk", "freshworks",
    "razorpay", "postman", "hasura", "chargebee",
    "browserstack", "clevertap", "druva",
]
LEVER_PER_COMPANY = 20  # Max jobs per company

# SerpAPI - For Google Jobs search (covers LinkedIn, Indeed, Naukri, Instahyre)
# Free tier: 250 searches/month
SERPAPI_KEY = os.getenv("SERPAPI_KEY", "")
if not SERPAPI_KEY:
    try:
        import streamlit as st
        SERPAPI_KEY = st.secrets.get("SERPAPI_KEY", "")
    except (ImportError, KeyError, AttributeError):
        pass
SERPAPI_QUERIES = [
    # India-focused queries
    {"q": "remote analyst India", "location": "India"},
    {"q": "operations specialist remote India", "location": "India"},
    {"q": "IT consultant remote India", "location": "India"},
    {"q": "data analyst remote India", "location": "India"},
    {"q": "customer success remote India", "location": "India"},
    {"q": "financial analyst remote India", "location": "India"},
]

# ============================================
# RSS PARSING WITH ERROR HANDLING
# ============================================

def parse_rss(url: str, source: str, timeout: int = NETWORK_TIMEOUT, max_retries: int = MAX_RETRIES) -> list:
    """
    Parse RSS feed with proper error handling and retries.
    
    Returns:
        list: List of job dictionaries, or empty list on failure
    """
    jobs = []
    
    for attempt in range(max_retries):
        try:
            logger.info(f"Fetching {source} (attempt {attempt + 1}/{max_retries})")
            
            # Fetch with timeout
            response = requests.get(
                url,
                timeout=timeout,
                headers={
                    'User-Agent': 'JobBot/2.0 (Job Aggregator; +https://github.com/jobbot)',
                    'Accept': 'application/rss+xml, application/xml, text/xml'
                }
            )
            
            # Check HTTP status
            response.raise_for_status()
            
            # Parse RSS
            feed = feedparser.parse(response.content)
            
            # Check for parsing errors
            if feed.bozo:
                logger.warning(f"{source} RSS parsing warning: {feed.bozo_exception}")
                # Continue anyway - feedparser is lenient
            
            # Check if we got any entries
            if not hasattr(feed, 'entries') or not feed.entries:
                logger.warning(f"{source} returned no entries")
                return []
            
            # Extract jobs
            for entry in feed.entries:
                try:
                    raw_title = entry.get("title", "").strip()
                    author = entry.get("author", "").strip()
                    raw_summary = entry.get("summary", "").strip()
                    
                    # Extract company: prefer author, fall back to title parsing
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
                    
                    # ============================================
                    # NEW: Extract location tags from job posting
                    # ============================================
                    job["location_tags"] = extract_location_from_job(job)
                    
                    # Validate required fields
                    if job["title"] and job["apply_url"]:
                        jobs.append(job)
                    else:
                        logger.debug(f"Skipping job with missing title or URL")
                
                except Exception as e:
                    logger.warning(f"Error parsing job entry: {e}")
                    continue
            
            logger.info(f"Successfully fetched {len(jobs)} jobs from {source}")
            return jobs
            
        except requests.Timeout:
            logger.warning(f"{source} request timed out after {timeout}s")
            if attempt < max_retries - 1:
                time.sleep(RETRY_DELAY * (attempt + 1))  # Increasing delay
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
# REMOTIVE API WITH ERROR HANDLING
# ============================================

def fetch_remotive_jobs(timeout: int = NETWORK_TIMEOUT) -> list:
    """
    Fetch jobs from Remotive API with proper error handling.
    
    Returns:
        list: List of job dictionaries, or empty list on failure
    """
    jobs = []
    url = "https://remotive.com/api/remote-jobs"
    
    try:
        logger.info("Fetching jobs from Remotive API")
        
        response = requests.get(
            url,
            timeout=timeout,
            headers={
                'User-Agent': 'JobBot/2.0 (Job Aggregator; +https://github.com/jobbot)',
                'Accept': 'application/json'
            }
        )
        
        # Check HTTP status
        response.raise_for_status()
        
        # Parse JSON
        data = response.json()
        
        # Validate response structure
        if not isinstance(data, dict):
            raise ValueError(f"Expected dict, got {type(data)}")
        
        if "jobs" not in data:
            raise ValueError("Response missing 'jobs' key")
        
        jobs_list = data.get("jobs", [])
        
        if not isinstance(jobs_list, list):
            raise ValueError(f"Expected jobs to be list, got {type(jobs_list)}")
        
        # Extract jobs
        for j in jobs_list:
            try:
                if not isinstance(j, dict):
                    logger.debug(f"Skipping non-dict job entry")
                    continue
                
                job = {
                    "title": j.get("title", "Unknown").strip(),
                    "company": j.get("company_name", "Unknown").strip(),
                    "summary": strip_html((j.get("description", "")[:500]).strip()),
                    "apply_url": j.get("url", "").strip(),
                    "source": "Remotive",
                }
                
                # ============================================
                # NEW: Extract location tags from job posting
                # ============================================
                job["location_tags"] = extract_location_from_job(job)
                
                # Validate required fields
                if job["title"] and job["apply_url"]:
                    jobs.append(job)
                else:
                    logger.debug(f"Skipping job with missing title or URL")
            
            except Exception as e:
                logger.warning(f"Error parsing Remotive job entry: {e}")
                continue
        
        logger.info(f"Successfully fetched {len(jobs)} jobs from Remotive")
        return jobs
        
    except requests.Timeout:
        logger.error(f"Remotive API request timed out after {timeout}s")
        
    except requests.RequestException as e:
        logger.error(f"Remotive API request failed: {e}")
        
    except (ValueError, KeyError) as e:
        logger.error(f"Remotive API response validation failed: {e}")
        
    except Exception as e:
        logger.error(f"Unexpected error fetching Remotive jobs: {e}")
    
    return jobs


# ============================================
# LEVER API — Free public JSON, no auth
# ============================================

def fetch_lever_jobs(timeout: int = NETWORK_TIMEOUT) -> list:
    """
    Fetch jobs from Lever's public API for curated companies.
    Each company endpoint: https://api.lever.co/v0/postings/{company}
    Returns JSON array of postings.
    """
    jobs = []
    for company in LEVER_COMPANIES:
        try:
            url = f"https://api.lever.co/v0/postings/{company}?mode=json"
            response = requests.get(url, timeout=timeout, headers={
                'User-Agent': 'JobBot/2.0',
                'Accept': 'application/json'
            })
            if response.status_code == 404:
                logger.debug(f"Lever: {company} not found (404)")
                continue
            response.raise_for_status()
            postings = response.json()
            if not isinstance(postings, list):
                continue

            count = 0
            for p in postings[:LEVER_PER_COMPANY]:
                try:
                    title = p.get("text", "").strip()
                    location = p.get("categories", {}).get("location", "")
                    team = p.get("categories", {}).get("team", "")
                    desc_plain = p.get("descriptionPlain", "")[:500]
                    apply_url = p.get("hostedUrl", "") or p.get("applyUrl", "")

                    if not title or not apply_url:
                        continue

                    job = {
                        "title": title,
                        "company": company.replace("-", " ").title(),
                        "summary": desc_plain,
                        "apply_url": apply_url,
                        "source": "Lever",
                    }
                    job["location_tags"] = extract_location_from_job(job)
                    jobs.append(job)
                    count += 1
                except Exception:
                    continue

            if count > 0:
                logger.info(f"Lever: {company} → {count} jobs")

        except requests.Timeout:
            logger.debug(f"Lever: {company} timed out")
        except requests.RequestException as e:
            logger.debug(f"Lever: {company} failed: {e}")
        except Exception as e:
            logger.debug(f"Lever: {company} error: {e}")

    logger.info(f"Lever total: {len(jobs)} jobs from {len(LEVER_COMPANIES)} companies")
    return jobs


# ============================================
# SERPAPI — Google Jobs (covers LinkedIn, Indeed, Naukri, Instahyre)
# ============================================

def fetch_serpapi_jobs(queries: list = None, timeout: int = NETWORK_TIMEOUT) -> list:
    """
    Fetch jobs from SerpAPI Google Jobs search.
    Free tier: 250 searches/month.
    Each search returns ~10 jobs, so 6 queries = ~60 jobs.
    """
    if not SERPAPI_KEY:
        logger.info("SerpAPI: No API key set (SERPAPI_KEY), skipping")
        return []

    queries = queries or SERPAPI_QUERIES
    jobs = []
    searches_used = 0

    for query_config in queries:
        try:
            params = {
                "engine": "google_jobs",
                "q": query_config["q"],
                "api_key": SERPAPI_KEY,
                "hl": "en",
            }
            if "location" in query_config:
                params["location"] = query_config["location"]

            response = requests.get(
                "https://serpapi.com/search",
                params=params,
                timeout=timeout,
                headers={'User-Agent': 'JobBot/2.0'}
            )
            searches_used += 1

            if response.status_code == 401:
                logger.error("SerpAPI: Invalid API key")
                break
            if response.status_code == 429:
                logger.warning("SerpAPI: Rate limit reached, stopping")
                break

            response.raise_for_status()
            data = response.json()

            job_results = data.get("jobs_results", [])
            for jr in job_results:
                try:
                    title = jr.get("title", "").strip()
                    company = jr.get("company_name", "Unknown").strip()
                    description = jr.get("description", "")[:500]
                    location = jr.get("location", "")

                    # Get apply link (SerpAPI provides multiple)
                    apply_url = ""
                    apply_options = jr.get("apply_options", [])
                    if apply_options:
                        apply_url = apply_options[0].get("link", "")
                    if not apply_url:
                        apply_url = jr.get("share_link", "") or jr.get("job_id", "")

                    if not title:
                        continue

                    # Detect source from apply_options
                    source_name = "Google Jobs"
                    if apply_options:
                        via = apply_options[0].get("title", "").lower()
                        if "linkedin" in via:
                            source_name = "LinkedIn"
                        elif "indeed" in via:
                            source_name = "Indeed"
                        elif "naukri" in via:
                            source_name = "Naukri"
                        elif "instahyre" in via:
                            source_name = "Instahyre"

                    job = {
                        "title": title,
                        "company": company,
                        "summary": description,
                        "apply_url": apply_url,
                        "source": source_name,
                    }
                    job["location_tags"] = extract_location_from_job(job)
                    jobs.append(job)
                except Exception:
                    continue

            logger.info(f"SerpAPI: '{query_config['q']}' → {len(job_results)} results")

            # Small delay between searches to be nice
            if searches_used < len(queries):
                time.sleep(0.5)

        except requests.Timeout:
            logger.warning(f"SerpAPI: Query timed out: {query_config['q']}")
        except requests.RequestException as e:
            logger.warning(f"SerpAPI: Request failed: {e}")
        except Exception as e:
            logger.error(f"SerpAPI: Unexpected error: {e}")

    logger.info(f"SerpAPI total: {len(jobs)} jobs ({searches_used} searches used)")
    return jobs


# ============================================
# MAIN FETCH FUNCTION
# ============================================

def fetch_all(output_path: str = None, serpapi_queries: list = None) -> list:
    """
    Fetch jobs from all sources and save to JSON.
    
    Args:
        output_path: Path to save jobs JSON file
        serpapi_queries: Optional custom SerpAPI queries based on user profile
        
    Returns:
        list: All fetched jobs (now with location_tags!)
    """
    output_path = output_path or OUTPUT_DEFAULT
    all_jobs = []
    
    logger.info("Starting job fetch from all sources")
    
    # Fetch from WeWorkRemotely feeds
    for feed_url in WWR_FEEDS:
        try:
            jobs = parse_rss(feed_url, "WeWorkRemotely")
            all_jobs.extend(jobs)
        except Exception as e:
            logger.error(f"Failed to fetch {feed_url}: {e}")
            # Continue with other sources
    
    # Fetch from RemoteOK
    try:
        jobs = parse_rss(REMOTEOK, "RemoteOK")
        all_jobs.extend(jobs)
    except Exception as e:
        logger.error(f"Failed to fetch RemoteOK: {e}")
    
    # Fetch from Jobicy
    try:
        jobs = parse_rss(JOBICY, "Jobicy")
        all_jobs.extend(jobs)
    except Exception as e:
        logger.error(f"Failed to fetch Jobicy: {e}")
    
    # Fetch from Remotive API
    try:
        jobs = fetch_remotive_jobs()
        all_jobs.extend(jobs)
    except Exception as e:
        logger.error(f"Failed to fetch Remotive: {e}")

    # Fetch from Lever (tech companies)
    try:
        jobs = fetch_lever_jobs()
        all_jobs.extend(jobs)
    except Exception as e:
        logger.error(f"Failed to fetch Lever: {e}")

    # Fetch from SerpAPI (Google Jobs → LinkedIn, Indeed, Naukri, Instahyre)
    try:
        jobs = fetch_serpapi_jobs(queries=serpapi_queries)
        all_jobs.extend(jobs)
    except Exception as e:
        logger.error(f"Failed to fetch SerpAPI: {e}")
    
    # Check if we got any jobs
    if not all_jobs:
        logger.error("Failed to fetch jobs from any source!")
        raise RuntimeError(
            "Could not fetch jobs from any source. "
            "Check your internet connection and try again."
        )
    
    logger.info(f"Total jobs fetched: {len(all_jobs)}")
    
    # ============================================
    # NEW: Log location distribution
    # ============================================
    location_stats = {}
    for job in all_jobs:
        for tag in job.get("location_tags", ["global"]):
            location_stats[tag] = location_stats.get(tag, 0) + 1
    
    logger.info("Location distribution:")
    for region, count in sorted(location_stats.items()):
        logger.info(f"  {region}: {count} jobs")
    
    # Deduplicate jobs based on URL (some jobs may appear on multiple boards)
    seen_urls = set()
    unique_jobs = []
    for job in all_jobs:
        url = job.get("apply_url", "")
        if url and url not in seen_urls:
            seen_urls.add(url)
            unique_jobs.append(job)
        elif not url:
            # Keep jobs without URLs (shouldn't happen but be defensive)
            unique_jobs.append(job)
    
    logger.info(f"Unique jobs after deduplication: {len(unique_jobs)} (removed {len(all_jobs) - len(unique_jobs)} duplicates)")
    
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


# ============================================
# CLI ENTRY
# ============================================

if __name__ == "__main__":
    import sys
    
    try:
        # Allow custom output path from command line
        output = sys.argv[1] if len(sys.argv) > 1 else OUTPUT_DEFAULT
        
        jobs = fetch_all(output_path=output)
        
        print(f"\n✅ Successfully fetched {len(jobs)} unique jobs!")
        print(f"Saved to: {output}")
        
        # Show breakdown by source
        sources = {}
        for job in jobs:
            source = job.get("source", "Unknown")
            sources[source] = sources.get(source, 0) + 1
        
        print("\nBreakdown by source:")
        for source, count in sorted(sources.items()):
            print(f"  {source}: {count} jobs")
        
        # ============================================
        # NEW: Show breakdown by location
        # ============================================
        print("\nBreakdown by location/region:")
        locations = {}
        for job in jobs:
            for tag in job.get("location_tags", ["unknown"]):
                locations[tag] = locations.get(tag, 0) + 1
        
        for location, count in sorted(locations.items()):
            print(f"  {location}: {count} jobs")
    
    except Exception as e:
        print(f"\n❌ Error: {e}")
        logger.exception("Job fetching failed")
        sys.exit(1)
