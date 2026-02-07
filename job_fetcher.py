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

SERPAPI_KEY = os.getenv("SERPAPI_KEY", "")
if not SERPAPI_KEY:
    try:
        import streamlit as _st
        SERPAPI_KEY = _st.secrets.get("SERPAPI_KEY", "")
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

# --- SerpAPI: Google Jobs search ---
# Free tier = 100 searches/month
# Each query returns ~10 jobs from LinkedIn, Indeed, Naukri, Glassdoor, Instahyre
SERPAPI_MAX_QUERIES = 6  # Cap per run to conserve quota


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
    except Exception as e:
        logger.error(f"Remotive fetch failed: {e}")

    return jobs


# ============================================
# LEVER API — Free public JSON, no auth needed
# ============================================

def fetch_lever_jobs(timeout: int = NETWORK_TIMEOUT) -> list:
    """
    Fetch jobs from Lever's public API for curated companies.
    Endpoint: https://api.lever.co/v0/postings/{company}?mode=json
    No authentication required.
    """
    jobs = []
    companies_hit = 0

    for company in LEVER_COMPANIES:
        try:
            url = f"https://api.lever.co/v0/postings/{company}?mode=json"
            response = requests.get(url, timeout=15, headers={
                'User-Agent': 'JobBot/2.0', 'Accept': 'application/json'
            })

            if response.status_code == 404:
                logger.debug(f"Lever: {company} not found")
                continue
            if response.status_code != 200:
                logger.debug(f"Lever: {company} returned {response.status_code}")
                continue

            postings = response.json()
            if not isinstance(postings, list):
                continue

            count = 0
            for p in postings[:LEVER_PER_COMPANY]:
                try:
                    title = p.get("text", "").strip()
                    desc_plain = p.get("descriptionPlain", "")[:500]
                    apply_url = p.get("hostedUrl", "") or p.get("applyUrl", "")

                    if not title or not apply_url:
                        continue

                    # Lever gives structured category info
                    categories = p.get("categories", {})
                    location = categories.get("location", "")
                    team = categories.get("team", "")

                    # Build company display name
                    display_name = company.replace("-", " ").title()

                    job = {
                        "title": title,
                        "company": display_name,
                        "summary": f"{desc_plain} Location: {location}. Team: {team}".strip(),
                        "apply_url": apply_url,
                        "source": "Lever",
                    }
                    job["location_tags"] = extract_location_from_job(job)
                    jobs.append(job)
                    count += 1
                except Exception:
                    continue

            if count > 0:
                companies_hit += 1
                logger.info(f"Lever: {display_name} → {count} jobs")

            # Small delay to be polite
            time.sleep(0.3)

        except requests.Timeout:
            logger.debug(f"Lever: {company} timed out")
        except Exception as e:
            logger.debug(f"Lever: {company} error: {e}")

    logger.info(f"Lever total: {len(jobs)} jobs from {companies_hit}/{len(LEVER_COMPANIES)} companies")
    return jobs


# ============================================
# SERPAPI — Google Jobs (LinkedIn, Indeed, Naukri, Instahyre, Glassdoor)
# ============================================

def build_serpapi_queries(profile: dict) -> list:
    """
    Generate targeted SerpAPI queries from user profile.
    Uses profile['search_terms'], 'country', 'state', and 'job_preference'.
    Returns max SERPAPI_MAX_QUERIES queries.
    """
    headline = (profile.get("headline", "") or "").strip()
    skills = profile.get("skills", [])
    country = (profile.get("country", "") or "India").strip()
    state = (profile.get("state", "") or "").strip()
    search_terms = profile.get("search_terms", [])
    industry = (profile.get("industry", "") or "").strip()
    job_preference = (profile.get("job_preference", "") or "").strip()

    # Determine preference
    prefer_local = "local" in job_preference.lower() or "city" in job_preference.lower()
    prefer_remote = "remote" in job_preference.lower() and "both" not in job_preference.lower()
    prefer_both = "both" in job_preference.lower() or (not prefer_local and not prefer_remote)

    # For "Remote Only" country, always remote
    is_remote_only = country.lower() in ("remote only", "remote", "global", "")
    if is_remote_only:
        prefer_remote = True
        prefer_local = False
        prefer_both = False

    loc_tag = "" if is_remote_only else country
    serpapi_location = None if is_remote_only else country

    # Extract city name from state
    city = ""
    if state and state != "Any":
        import re
        city_match = re.search(r'\(([^)]+)\)', state)
        if city_match:
            city = city_match.group(1).split("/")[0].strip()
        else:
            city = state

    queries = []

    # Use LLM-extracted search_terms first (these are the best queries)
    for term in search_terms[:3]:
        if prefer_local and city:
            queries.append({"q": f"{term} {city}", "location": serpapi_location})
        elif prefer_remote:
            queries.append({"q": f"{term} remote"})
        else:  # both
            if city:
                queries.append({"q": f"{term} {city}", "location": serpapi_location})
            if len(queries) < SERPAPI_MAX_QUERIES:
                queries.append({"q": f"{term} remote"})

    # If search_terms didn't fill up, use headline
    if len(queries) < SERPAPI_MAX_QUERIES and headline:
        if prefer_local and city:
            queries.append({"q": f"{headline} jobs {city}", "location": serpapi_location})
        elif prefer_remote:
            queries.append({"q": f"{headline} remote jobs"})
        else:
            if city and len(queries) < SERPAPI_MAX_QUERIES:
                queries.append({"q": f"{headline} jobs {city}", "location": serpapi_location})
            if loc_tag and len(queries) < SERPAPI_MAX_QUERIES:
                queries.append({"q": f"{headline} jobs {loc_tag}", "location": serpapi_location})

    # If still room, add industry + location query
    if len(queries) < SERPAPI_MAX_QUERIES and industry:
        if city:
            queries.append({"q": f"{industry} operations jobs {city}", "location": serpapi_location})
        elif loc_tag:
            queries.append({"q": f"{industry} jobs {loc_tag}", "location": serpapi_location})

    # Fill remaining with skill-based queries
    multi_word = [s for s in skills if " " in s and len(s) > 5][:3]
    for skill in multi_word:
        if len(queries) >= SERPAPI_MAX_QUERIES:
            break
        q = {"q": f"{skill} jobs"}
        if prefer_local and city:
            q["q"] = f"{skill} jobs {city}"
            q["location"] = serpapi_location
        elif loc_tag and not prefer_remote:
            q["q"] = f"{skill} jobs {loc_tag}"
            q["location"] = serpapi_location
        else:
            q["q"] = f"{skill} remote jobs"
        queries.append(q)

    # Deduplicate by query text
    seen = set()
    unique_queries = []
    for q in queries:
        key = q["q"].lower()
        if key not in seen:
            seen.add(key)
            unique_queries.append(q)

    return unique_queries[:SERPAPI_MAX_QUERIES]


def fetch_serpapi_jobs(queries: list = None, timeout: int = NETWORK_TIMEOUT) -> list:
    """
    Fetch jobs from SerpAPI Google Jobs search.
    Google Jobs aggregates: LinkedIn, Indeed, Naukri, Instahyre, Glassdoor, etc.
    Free tier: 100 searches/month.
    """
    if not SERPAPI_KEY:
        logger.info("SerpAPI: No API key set (SERPAPI_KEY env var), skipping")
        return []

    if not queries:
        logger.info("SerpAPI: No queries provided, skipping")
        return []

    jobs = []
    seen_titles = set()  # Dedup within SerpAPI results
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

            logger.info(f"SerpAPI: Searching '{query_config['q']}'")

            response = requests.get(
                "https://serpapi.com/search",
                params=params,
                timeout=timeout,
                headers={'User-Agent': 'JobBot/2.0'}
            )
            searches_used += 1

            if response.status_code == 401:
                logger.error("SerpAPI: Invalid API key — check SERPAPI_KEY")
                break
            if response.status_code == 429:
                logger.warning("SerpAPI: Rate limit / quota exhausted, stopping")
                break
            if response.status_code != 200:
                logger.warning(f"SerpAPI: HTTP {response.status_code} for '{query_config['q']}'")
                continue

            data = response.json()

            # Check for error in response body
            if "error" in data:
                logger.warning(f"SerpAPI error: {data['error']}")
                if "Invalid API key" in str(data.get("error", "")):
                    break
                continue

            job_results = data.get("jobs_results", [])
            added = 0

            for jr in job_results:
                try:
                    title = jr.get("title", "").strip()
                    company = jr.get("company_name", "Unknown").strip()
                    description = jr.get("description", "")[:500]
                    location = jr.get("location", "")

                    if not title:
                        continue

                    # Dedup by title+company
                    dedup_key = f"{title.lower()}|{company.lower()}"
                    if dedup_key in seen_titles:
                        continue
                    seen_titles.add(dedup_key)

                    # Get apply link
                    apply_url = ""
                    apply_options = jr.get("apply_options", [])
                    if apply_options and isinstance(apply_options, list):
                        apply_url = apply_options[0].get("link", "")
                    if not apply_url:
                        apply_url = jr.get("share_link", "")
                    if not apply_url:
                        # Use Google's job link as fallback
                        job_id = jr.get("job_id", "")
                        if job_id:
                            apply_url = f"https://www.google.com/search?q={job_id}&ibp=htl;jobs"

                    # Detect original source from apply_options
                    source_name = "Google Jobs"
                    if apply_options and isinstance(apply_options, list):
                        via = apply_options[0].get("title", "").lower()
                        if "linkedin" in via:
                            source_name = "LinkedIn"
                        elif "indeed" in via:
                            source_name = "Indeed"
                        elif "naukri" in via:
                            source_name = "Naukri"
                        elif "instahyre" in via:
                            source_name = "Instahyre"
                        elif "glassdoor" in via:
                            source_name = "Glassdoor"
                        elif "foundit" in via or "monster" in via:
                            source_name = "Foundit"

                    job = {
                        "title": title,
                        "company": company,
                        "summary": f"{description} Location: {location}".strip(),
                        "apply_url": apply_url,
                        "source": source_name,
                    }
                    job["location_tags"] = extract_location_from_job(job)
                    jobs.append(job)
                    added += 1
                except Exception:
                    continue

            logger.info(f"SerpAPI: '{query_config['q']}' → {added} new jobs ({len(job_results)} results)")

            # Delay between queries
            if searches_used < len(queries):
                time.sleep(1.0)

        except requests.Timeout:
            logger.warning(f"SerpAPI: Timed out for '{query_config.get('q', '?')}'")
        except requests.RequestException as e:
            logger.warning(f"SerpAPI: Request failed: {e}")
        except Exception as e:
            logger.error(f"SerpAPI: Unexpected error: {e}")

    logger.info(f"SerpAPI total: {len(jobs)} unique jobs ({searches_used} searches used of {SERPAPI_MAX_QUERIES} max)")
    return jobs


# ============================================
# MAIN FETCH FUNCTION
# ============================================

def fetch_all(output_path: str = None, serpapi_queries: list = None) -> list:
    """
    Fetch jobs from all sources and save to JSON.

    Sources:
    1. WeWorkRemotely (RSS) — remote global
    2. RemoteOK (RSS) — remote global
    3. Jobicy (RSS) — remote global
    4. Remotive (API) — remote curated
    5. Lever (API) — tech companies (India + global)
    6. SerpAPI (API) — Google Jobs → LinkedIn, Indeed, Naukri, Instahyre

    Args:
        output_path: Path to save jobs JSON file
        serpapi_queries: Profile-based queries for SerpAPI (from run_auto_apply)

    Returns:
        list: All fetched jobs with location_tags
    """
    output_path = output_path or OUTPUT_DEFAULT
    all_jobs = []
    source_counts = {}

    logger.info("Starting job fetch from all sources")

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

    # ---- 6. SerpAPI → Google Jobs (LinkedIn, Indeed, Naukri, etc.) ----
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

        # For CLI testing, use default SerpAPI queries
        test_queries = [
            {"q": "remote analyst India", "location": "India"},
            {"q": "customer support specialist remote India", "location": "India"},
        ]
        jobs = fetch_all(output_path=output, serpapi_queries=test_queries)

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
