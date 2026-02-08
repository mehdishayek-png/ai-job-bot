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
NETWORK_TIMEOUT = 30  # seconds
MAX_RETRIES = 3
RETRY_DELAY = 2  # seconds

# ============================================
# API KEYS (env or Streamlit secrets)
# ============================================

SERPER_API_KEY = os.getenv("SERPER_API_KEY", "")
if not SERPER_API_KEY:
    try:
        import streamlit as _st
        SERPER_API_KEY = _st.secrets.get("SERPER_API_KEY", "")
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
# Companies with India presence / remote-friendly
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

# --- SerperDev: Google Jobs search ---
# Free tier = 2500 searches/month (much more generous!)
# Strategy: Use more searches per run for better quality and quantity
SERPER_MAX_QUERIES = 15  # Increased from 6 to 15 (still conservative with 2500/month)
SERPER_NUM_RESULTS = 50  # Request 50 results per query (SerperDev supports up to 100)

# Export for run_auto_apply.py
__all__ = ['fetch_all', 'build_serper_queries_from_profile', 'SERPER_MAX_QUERIES']


# ============================================
# RSS PARSING WITH ERROR HANDLING
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

                    job = {
                        "title": posting.get("text", "").strip(),
                        "company": posting.get("categories", {}).get("team", company).strip(),
                        "summary": strip_html((posting.get("description", "")[:500]).strip()),
                        "apply_url": posting.get("hostedUrl", "").strip(),
                        "source": "Lever",
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
# SERPERDEV API (GOOGLE JOBS SEARCH)
# ============================================

def build_serper_queries_from_profile(profile: dict) -> tuple:
    """
    Generate targeted SerperDev queries from user profile.
    Returns (queries, location) tuple.
    
    With 2500 searches/month, we can be more generous and strategic:
    - More diverse queries (up to 15)
    - Location-specific optimizations
    - Industry and seniority variations
    """
    headline = (profile.get("headline", "") or "").strip()
    skills = profile.get("skills", [])
    country = (profile.get("country", "") or "").strip()
    state = (profile.get("state", "") or "").strip()
    search_terms = profile.get("search_terms", [])
    industry = (profile.get("industry", "") or "").strip()
    job_preference = (profile.get("job_preference", "") or "").strip()
    
    # Determine preference
    prefer_local = "local" in job_preference.lower() or "city" in job_preference.lower()
    prefer_remote = "remote" in job_preference.lower() and "both" not in job_preference.lower()
    is_remote_only = country.lower() in ("remote only", "remote", "global")
    
    # Build location string
    location = None if is_remote_only else country
    loc_tag = ""
    if not is_remote_only:
        if state and state != "Any":
            loc_tag = state
        elif country:
            loc_tag = country
    
    queries = []
    
    # Priority 1: Search terms (user's preferred job titles)
    if search_terms:
        for term in search_terms[:5]:  # Top 5 search terms
            if loc_tag:
                queries.append(f"{term} {loc_tag}")
            else:
                queries.append(term)
    
    # Priority 2: Headline-based queries
    if headline:
        if loc_tag:
            queries.append(f"{headline} {loc_tag}")
        queries.append(f"{headline} jobs")
    
    # Priority 3: Industry + location
    if industry and loc_tag:
        queries.append(f"{industry} jobs {loc_tag}")
    
    # Priority 4: Top skills + location
    if skills and loc_tag:
        top_skills = skills[:3]
        for skill in top_skills:
            queries.append(f"{skill} {loc_tag}")
    
    # Priority 5: Remote variations (if applicable)
    if prefer_remote or not prefer_local:
        if search_terms:
            queries.append(f"remote {search_terms[0]}")
        if headline:
            queries.append(f"remote {headline}")
    
    # Priority 6: Entry-level/junior variations for less experienced candidates
    experience = profile.get("experience", "")
    if experience and ("0–1" in experience or "1–3" in experience):
        if search_terms:
            queries.append(f"{search_terms[0]} entry level OR junior")
    
    # Deduplicate and limit
    seen = set()
    unique_queries = []
    for q in queries:
        q_clean = q.strip()
        if q_clean and q_clean not in seen:
            seen.add(q_clean)
            unique_queries.append(q_clean)
    
    return unique_queries[:SERPER_MAX_QUERIES], location


def build_serper_queries(profile_queries: list, location: str = None) -> list:
    """
    Build optimized SerperDev search queries from profile data.
    Legacy function for compatibility with old code.
    
    Args:
        profile_queries: Base queries from profile (job titles, search terms)
        location: User's location (city, state, country)
        
    Returns:
        List of query strings optimized for SerperDev
    """
    queries = []
    
    # If we have specific location, prioritize location-based queries
    if location:
        # Direct location queries (highest priority)
        for pq in profile_queries[:5]:  # Top 5 profile queries
            queries.append(f"{pq} {location}")
        
        # Add location-specific variations
        if "india" in location.lower() or "bangalore" in location.lower():
            # India-specific job boards
            for pq in profile_queries[:3]:
                queries.append(f"{pq} site:naukri.com OR site:linkedin.com/jobs India")
        
        # Remote jobs that accept the location
        if profile_queries:
            queries.append(f"remote {profile_queries[0]} {location}")
    
    # General queries (no location filter)
    for pq in profile_queries[:8]:  # Expand to 8 general queries
        queries.append(pq)
    
    # Add industry-specific variations
    if len(profile_queries) > 0:
        base_query = profile_queries[0]
        queries.append(f"{base_query} entry level OR junior OR associate")
        queries.append(f"{base_query} remote OR work from home")
    
    # Limit to SERPER_MAX_QUERIES
    return queries[:SERPER_MAX_QUERIES]


def fetch_serperdev_jobs(queries: list = None, location: str = None) -> list:
    """
    Fetch jobs from Google Jobs via SerperDev API.
    
    SerperDev advantages over SerpAPI:
    - 2500 free searches/month (vs 100)
    - Better JSON structure
    - More reliable results
    - Up to 100 results per query
    
    Args:
        queries: List of search query dicts with 'q' and optional 'location'
        location: Default location if not specified in query
        
    Returns:
        List of job dictionaries
    """
    if not SERPER_API_KEY:
        logger.warning("SerperDev: No API key found, skipping")
        return []
    
    if not queries:
        logger.warning("SerperDev: No queries provided")
        return []
    
    # Convert old format to new if needed
    if queries and isinstance(queries[0], dict):
        # Old format from run_auto_apply: [{"q": "...", "location": "..."}]
        query_strings = [q.get("q", "") for q in queries if q.get("q")]
        if queries[0].get("location"):
            location = queries[0]["location"]
    else:
        # New format: ["query1", "query2", ...]
        query_strings = queries
    
    # Build optimized queries
    optimized_queries = build_serper_queries(query_strings, location)
    
    logger.info(f"SerperDev: Using {len(optimized_queries)} optimized queries (limit: {SERPER_MAX_QUERIES})")
    
    jobs = []
    seen_urls = set()
    searches_used = 0
    
    for query in optimized_queries:
        if searches_used >= SERPER_MAX_QUERIES:
            logger.info(f"SerperDev: Reached query limit ({SERPER_MAX_QUERIES})")
            break
        
        try:
            logger.info(f"SerperDev: Searching '{query}'")
            
            # SerperDev API request
            url = "https://google.serper.dev/search"
            
            payload = {
                "q": query,
                "gl": "in" if not location or "india" in location.lower() else "us",  # Country
                "hl": "en",  # Language
                "num": SERPER_NUM_RESULTS,  # Results per query
                "type": "search",  # Can also use "jobs" for dedicated job search
            }
            
            headers = {
                'X-API-KEY': SERPER_API_KEY,
                'Content-Type': 'application/json'
            }
            
            response = requests.post(
                url,
                json=payload,
                headers=headers,
                timeout=NETWORK_TIMEOUT
            )
            
            searches_used += 1
            
            # Check for errors
            if response.status_code == 429:
                logger.warning("SerperDev: Rate limit hit, stopping searches")
                break
            elif response.status_code == 403:
                logger.error("SerperDev: Invalid API key or quota exhausted")
                break
            
            response.raise_for_status()
            data = response.json()
            
            # Parse results
            # SerperDev can return organic results or dedicated job results
            results = []
            
            # Try job-specific results first
            if "jobs" in data:
                results = data["jobs"]
            # Fall back to organic results
            elif "organic" in data:
                results = data["organic"]
            
            added = 0
            for result in results:
                try:
                    # Extract job details
                    title = result.get("title", "").strip()
                    link = result.get("link", "").strip()
                    snippet = result.get("snippet", "").strip()
                    
                    # For job-specific results, SerperDev provides extra fields
                    company_name = result.get("company", {}).get("name", "") if isinstance(result.get("company"), dict) else result.get("company", "")
                    job_location = result.get("location", "")
                    
                    # Determine source from link
                    source_name = "SerperDev"
                    if "linkedin.com" in link:
                        source_name = "LinkedIn"
                    elif "naukri.com" in link:
                        source_name = "Naukri"
                    elif "indeed.com" in link:
                        source_name = "Indeed"
                    elif "glassdoor.com" in link:
                        source_name = "Glassdoor"
                    
                    # Skip duplicates
                    if link in seen_urls:
                        continue
                    seen_urls.add(link)
                    
                    # Build job object
                    job = {
                        "title": title,
                        "company": company_name or "Unknown",
                        "summary": f"{snippet} {job_location}".strip(),
                        "apply_url": link,
                        "source": source_name,
                    }
                    
                    job["location_tags"] = extract_location_from_job(job)
                    
                    if job["title"] and job["apply_url"]:
                        jobs.append(job)
                        added += 1
                
                except Exception as e:
                    logger.debug(f"Error parsing SerperDev result: {e}")
                    continue
            
            logger.info(f"SerperDev: '{query}' → {added} new jobs ({len(results)} total results)")
            
            # Small delay between queries to be respectful
            if searches_used < len(optimized_queries):
                time.sleep(0.5)
        
        except requests.Timeout:
            logger.warning(f"SerperDev: Timeout for '{query}'")
        except requests.RequestException as e:
            logger.warning(f"SerperDev: Request failed: {e}")
        except Exception as e:
            logger.error(f"SerperDev: Unexpected error: {e}")
    
    logger.info(f"SerperDev total: {len(jobs)} unique jobs ({searches_used} searches used of {SERPER_MAX_QUERIES} max)")
    return jobs


# ============================================
# MAIN FETCH FUNCTION
# ============================================

def fetch_all(output_path: str = None, serper_queries: list = None, prioritize_local: bool = False, location: str = None) -> list:
    """
    Fetch jobs from all sources and save to JSON.

    Sources:
    1. WeWorkRemotely (RSS) — remote global
    2. RemoteOK (RSS) — remote global
    3. Jobicy (RSS) — remote global
    4. Remotive (API) — remote curated
    5. Lever (API) — tech companies (India + global)
    6. SerperDev (API) — Google search results (LinkedIn, Indeed, Naukri, etc.)

    Args:
        output_path: Path to save jobs JSON file
        serper_queries: Profile-based queries for SerperDev (from run_auto_apply)
        prioritize_local: If True, fetch local sources first and skip large remote feeds
        location: User's location for targeted searches

    Returns:
        list: All fetched jobs with location_tags
    """
    output_path = output_path or OUTPUT_DEFAULT
    all_jobs = []
    source_counts = {}

    logger.info("Starting job fetch from all sources")

    # If the caller requests local prioritization (e.g., user selected a city),
    # fetch SerperDev (Google Jobs / Indeed / Naukri) first and avoid bulk remote
    # boards to increase the relative share of localized results.
    if prioritize_local:
        logger.info("Prioritizing local sources: running SerperDev and Lever first, skipping large remote-only feeds")
        
        # 1. SerperDev (targeted local searches)
        try:
            jobs = fetch_serperdev_jobs(queries=serper_queries, location=location)
            all_jobs.extend(jobs)
        except Exception as e:
            logger.error(f"Failed to fetch SerperDev: {e}")

        # 2. Lever (targeted companies, many with India presence)
        try:
            jobs = fetch_lever_jobs()
            all_jobs.extend(jobs)
        except Exception as e:
            logger.error(f"Failed to fetch Lever: {e}")

        # 3. Optionally include Remotive (smaller remote curated set)
        try:
            jobs = fetch_remotive_jobs()
            all_jobs.extend(jobs)
        except Exception as e:
            logger.error(f"Failed to fetch Remotive: {e}")

        # Skip large global remote RSS feeds (WeWorkRemotely / RemoteOK / Jobicy)
        logger.info("Skipped WeWorkRemotely / RemoteOK / Jobicy feeds to favour local sources")

    else:
        # ---- 1. WeWorkRemotely (RSS feeds) ----
        for feed_url in WWR_FEEDS:
            try:
                jobs = parse_rss(feed_url, "WeWorkRemotely")
                all_jobs.extend(jobs)
            except Exception as e:
                logger.error(f"Failed to fetch {feed_url}: {e}")

        # ---- 2. RemoteOK (RSS) ----
        try:
            jobs = parse_rss(REMOTEOK, "RemoteOK")
            all_jobs.extend(jobs)
        except Exception as e:
            logger.error(f"Failed to fetch RemoteOK: {e}")

        # ---- 3. Jobicy (RSS) ----
        try:
            jobs = parse_rss(JOBICY, "Jobicy")
            all_jobs.extend(jobs)
        except Exception as e:
            logger.error(f"Failed to fetch Jobicy: {e}")

        # ---- 4. Remotive (API) ----
        try:
            jobs = fetch_remotive_jobs()
            all_jobs.extend(jobs)
        except Exception as e:
            logger.error(f"Failed to fetch Remotive: {e}")

        # ---- 5. Lever (public API, no auth) ----
        try:
            jobs = fetch_lever_jobs()
            all_jobs.extend(jobs)
        except Exception as e:
            logger.error(f"Failed to fetch Lever: {e}")

        # ---- 6. SerperDev → Google search results ----
        try:
            jobs = fetch_serperdev_jobs(queries=serper_queries, location=location)
            all_jobs.extend(jobs)
        except Exception as e:
            logger.error(f"Failed to fetch SerperDev: {e}")

    # Check if we got any jobs
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

    # Log location distribution
    location_stats = {}
    for job in all_jobs:
        for tag in job.get("location_tags", ["global"]):
            location_stats[tag] = location_stats.get(tag, 0) + 1
    logger.info("Location distribution:")
    for region, count in sorted(location_stats.items()):
        logger.info(f"  {region}: {count} jobs")

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
        output = sys.argv[1] if len(sys.argv) > 1 else OUTPUT_DEFAULT

        # For CLI testing, use improved SerperDev queries
        test_queries = [
            "Financial Analyst Bangalore",
            "Deal Advisory Consultant India",
            "remote analyst jobs India",
        ]
        
        jobs = fetch_all(
            output_path=output, 
            serper_queries=test_queries,
            location="Bangalore, India",
            prioritize_local=True
        )

        print(f"\n✅ Successfully fetched {len(jobs)} unique jobs!")
        print(f"Saved to: {output}")

        sources = {}
        for job in jobs:
            source = job.get("source", "Unknown")
            sources[source] = sources.get(source, 0) + 1
        print("\nBreakdown by source:")
        for source, count in sorted(sources.items()):
            print(f"  {source}: {count} jobs")

        locations = {}
        for job in jobs:
            for tag in job.get("location_tags", ["unknown"]):
                locations[tag] = locations.get(tag, 0) + 1
        print("\nBreakdown by location/region:")
        for location, count in sorted(locations.items()):
            print(f"  {location}: {count} jobs")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        logger.exception("Job fetching failed")
        sys.exit(1)
