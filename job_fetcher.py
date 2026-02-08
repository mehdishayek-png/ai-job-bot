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

SERPER_API_KEY = os.getenv("SERPER_API_KEY", "")
SCRAPINGDOG_API_KEY = os.getenv("SCRAPINGDOG_API_KEY", "")

if not SERPER_API_KEY or not SCRAPINGDOG_API_KEY:
    try:
        import streamlit as _st
        SERPER_API_KEY = SERPER_API_KEY or _st.secrets.get("SERPER_API_KEY", "")
        SCRAPINGDOG_API_KEY = SCRAPINGDOG_API_KEY or _st.secrets.get("SCRAPINGDOG_API_KEY", "")
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

# --- SerperDev: Google JOBS search ---
SERPER_MAX_QUERIES = 12
SERPER_NUM_RESULTS = 100

# --- ScrapingDog: Direct job board scraping ---
# ScrapingDog credits: 1000 free/month on basic plan
# Use as backup when SerperDev hits limits or for additional coverage
SCRAPINGDOG_MAX_SCRAPES = 8  # Conservative to preserve credits
SCRAPINGDOG_ENABLED = True  # Can be toggled

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
# SERPERDEV GOOGLE JOBS API
# ============================================

def build_serper_queries_from_profile(profile: dict) -> tuple:
    """
    Generate targeted SerperDev Google Jobs queries from user profile.
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
    
    # Build location string for Google Jobs API
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
        if headline:
            queries.append(f"{headline} {industry}")
    
    # Priority 4: Top 2 skills
    if skills:
        for skill in skills[:2]:
            if len(skill.split()) <= 3:
                queries.append(f"{skill} specialist")
    
    # Priority 5: Remote variations
    if search_terms:
        queries.append(f"remote {search_terms[0]}")
    
    # Deduplicate and limit
    seen = set()
    unique_queries = []
    for q in queries:
        q_clean = q.strip()
        if q_clean and q_clean.lower() not in seen:
            seen.add(q_clean.lower())
            unique_queries.append(q_clean)
    
    return unique_queries[:SERPER_MAX_QUERIES], location


def fetch_serperdev_jobs(queries: list = None, location: str = None) -> list:
    """
    Fetch ACTUAL JOB POSTINGS from Google Jobs via SerperDev.
    Uses type="jobs" to get real job postings, not search results.
    """
    if not SERPER_API_KEY:
        logger.warning("SerperDev: No API key found, skipping")
        return []
    
    if not queries:
        logger.warning("SerperDev: No queries provided")
        return []
    
    # Convert old format to new if needed
    if queries and isinstance(queries[0], dict):
        query_strings = [q.get("q", "") for q in queries if q.get("q")]
        if queries[0].get("location"):
            location = queries[0]["location"]
    else:
        query_strings = queries
    
    query_strings = query_strings[:SERPER_MAX_QUERIES]
    
    logger.info(f"SerperDev: Fetching jobs for {len(query_strings)} queries (location: {location or 'global'})")
    
    jobs = []
    seen_urls = set()
    searches_used = 0
    
    for query in query_strings:
        if searches_used >= SERPER_MAX_QUERIES:
            logger.info(f"SerperDev: Reached query limit ({SERPER_MAX_QUERIES})")
            break
        
        try:
            logger.info(f"SerperDev Google Jobs: '{query}'" + (f" in {location}" if location else ""))
            
            url = "https://google.serper.dev/search"
            
            payload = {
                "q": query,
                "location": location if location else "India",
                "gl": "in",
                "hl": "en",
                "num": SERPER_NUM_RESULTS,
                "type": "jobs",  # CRITICAL: Gets actual job postings
            }
            
            headers = {
                'X-API-KEY': SERPER_API_KEY,
                'Content-Type': 'application/json'
            }
            
            response = requests.post(url, json=payload, headers=headers, timeout=NETWORK_TIMEOUT)
            searches_used += 1
            
            if response.status_code == 429:
                logger.warning("SerperDev: Rate limit hit, stopping searches")
                break
            elif response.status_code == 403:
                logger.error("SerperDev: Invalid API key or quota exhausted")
                break
            elif response.status_code == 400:
                logger.warning(f"SerperDev: Bad request for query '{query}'")
                continue
            
            response.raise_for_status()
            data = response.json()
            
            job_results = data.get("jobs", [])
            
            if not job_results:
                logger.info(f"SerperDev: No jobs found for '{query}'")
                continue
            
            added = 0
            for result in job_results:
                try:
                    title = result.get("title", "").strip()
                    company_name = result.get("company", {}).get("name", "") if isinstance(result.get("company"), dict) else result.get("company", "Unknown")
                    description = result.get("description", "").strip()
                    link = result.get("link", "").strip()
                    job_location = result.get("location", "")
                    posted_date = result.get("detected_extensions", {}).get("posted_at", "") or result.get("posted_at", "")
                    
                    if not title or not link:
                        continue
                    
                    # Determine source from link
                    source_name = "Google Jobs"
                    if "linkedin.com" in link:
                        source_name = "LinkedIn"
                    elif "naukri.com" in link:
                        source_name = "Naukri"
                    elif "indeed.com" in link:
                        source_name = "Indeed"
                    elif "glassdoor.com" in link:
                        source_name = "Glassdoor"
                    elif "instahyre.com" in link:
                        source_name = "Instahyre"
                    elif "foundit.in" in link:
                        source_name = "Foundit"
                    
                    if link in seen_urls:
                        continue
                    seen_urls.add(link)
                    
                    job = {
                        "title": title,
                        "company": company_name,
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
                    logger.debug(f"Error parsing SerperDev job result: {e}")
                    continue
            
            logger.info(f"SerperDev: '{query}' → {added} jobs")
            
            if searches_used < len(query_strings):
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
# SCRAPINGDOG - DIRECT JOB BOARD SCRAPING
# ============================================

def fetch_scrapingdog_jobs(queries: list = None, location: str = None) -> list:
    """
    Scrape job boards directly using ScrapingDog API.
    
    ScrapingDog provides:
    - Direct scraping of Naukri, Indeed, LinkedIn job pages
    - Bypasses anti-scraping measures
    - Returns clean HTML for parsing
    
    Use cases:
    - Backup when SerperDev hits limits
    - Additional coverage from job boards
    - Get jobs that don't appear in Google Jobs
    
    Credits: 1000 free/month on basic plan
    """
    if not SCRAPINGDOG_API_KEY:
        logger.warning("ScrapingDog: No API key found, skipping")
        return []
    
    if not SCRAPINGDOG_ENABLED:
        logger.info("ScrapingDog: Disabled in config")
        return []
    
    if not queries:
        logger.warning("ScrapingDog: No queries provided")
        return []
    
    logger.info(f"ScrapingDog: Starting direct job board scraping")
    
    jobs = []
    seen_urls = set()
    scrapes_used = 0
    
    # Determine location for URLs
    loc_str = location.lower().replace(" ", "-") if location else "india"
    if "bangalore" in loc_str or "bengaluru" in loc_str:
        loc_str = "bangalore"
    
    # Build target URLs for top queries
    # We'll scrape Naukri and Indeed (most reliable for India)
    target_urls = []
    
    for query in queries[:SCRAPINGDOG_MAX_SCRAPES // 2]:  # Split credits between boards
        # Clean query for URL
        q_clean = query.lower().replace(" ", "-")
        
        # Naukri.com URL
        naukri_url = f"https://www.naukri.com/{q_clean}-jobs-in-{loc_str}"
        target_urls.append(("Naukri", naukri_url, query))
        
        # Indeed.in URL
        indeed_q = quote_plus(query)
        indeed_loc = quote_plus(location if location else "India")
        indeed_url = f"https://in.indeed.com/jobs?q={indeed_q}&l={indeed_loc}"
        target_urls.append(("Indeed", indeed_url, query))
    
    # Limit total scrapes
    target_urls = target_urls[:SCRAPINGDOG_MAX_SCRAPES]
    
    for source, url, query in target_urls:
        if scrapes_used >= SCRAPINGDOG_MAX_SCRAPES:
            logger.info(f"ScrapingDog: Reached scrape limit ({SCRAPINGDOG_MAX_SCRAPES})")
            break
        
        try:
            logger.info(f"ScrapingDog: Scraping {source} for '{query}'")
            
            # Build ScrapingDog API URL
            params = {
                'api_key': SCRAPINGDOG_API_KEY,
                'url': url,
                'dynamic': 'false',  # Static scraping (faster, uses fewer credits)
            }
            
            scrapingdog_url = f"https://api.scrapingdog.com/scrape?{urlencode(params)}"
            
            response = requests.get(scrapingdog_url, timeout=45)
            scrapes_used += 1
            
            if response.status_code == 403:
                logger.error("ScrapingDog: Invalid API key or quota exhausted")
                break
            elif response.status_code == 429:
                logger.warning("ScrapingDog: Rate limit hit")
                break
            elif response.status_code != 200:
                logger.warning(f"ScrapingDog: Failed to scrape {source} (status {response.status_code})")
                continue
            
            # Parse HTML
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Parse based on source
            if source == "Naukri":
                jobs_found = parse_naukri_html(soup, seen_urls)
            elif source == "Indeed":
                jobs_found = parse_indeed_html(soup, seen_urls)
            else:
                jobs_found = []
            
            jobs.extend(jobs_found)
            logger.info(f"ScrapingDog: {source} → {len(jobs_found)} jobs")
            
            # Delay between scrapes
            if scrapes_used < len(target_urls):
                time.sleep(2)
        
        except Exception as e:
            logger.error(f"ScrapingDog: Error scraping {source}: {e}")
            continue
    
    logger.info(f"ScrapingDog total: {len(jobs)} jobs ({scrapes_used} scrapes used of {SCRAPINGDOG_MAX_SCRAPES} max)")
    return jobs


def parse_naukri_html(soup: BeautifulSoup, seen_urls: set) -> list:
    """Parse Naukri.com job listings from HTML."""
    jobs = []
    
    try:
        # Naukri uses article tags with class "jobTuple"
        job_cards = soup.find_all('article', class_='jobTuple')
        
        for card in job_cards[:20]:  # Limit per page
            try:
                # Title
                title_elem = card.find('a', class_='title')
                if not title_elem:
                    continue
                title = title_elem.get_text(strip=True)
                link = "https://www.naukri.com" + title_elem.get('href', '')
                
                if link in seen_urls:
                    continue
                seen_urls.add(link)
                
                # Company
                company_elem = card.find('a', class_='comp-name')
                company = company_elem.get_text(strip=True) if company_elem else "Unknown"
                
                # Location
                location_elem = card.find('li', class_='location')
                location = location_elem.get_text(strip=True) if location_elem else ""
                
                # Experience
                exp_elem = card.find('li', class_='experience')
                experience = exp_elem.get_text(strip=True) if exp_elem else ""
                
                # Description
                desc_elem = card.find('div', class_='job-description')
                description = desc_elem.get_text(strip=True) if desc_elem else ""
                
                # Build job object
                job = {
                    "title": title,
                    "company": company,
                    "summary": f"{description[:400]} Experience: {experience}".strip(),
                    "apply_url": link,
                    "source": "Naukri",
                    "location": location,
                    "posted_date": "",  # Naukri doesn't always show this
                }
                
                job["location_tags"] = extract_location_from_job(job)
                jobs.append(job)
            
            except Exception as e:
                logger.debug(f"Error parsing Naukri job card: {e}")
                continue
    
    except Exception as e:
        logger.error(f"Error parsing Naukri HTML: {e}")
    
    return jobs


def parse_indeed_html(soup: BeautifulSoup, seen_urls: set) -> list:
    """Parse Indeed.in job listings from HTML."""
    jobs = []
    
    try:
        # Indeed uses div tags with class "job_seen_beacon"
        job_cards = soup.find_all('div', class_='job_seen_beacon')
        
        for card in job_cards[:20]:
            try:
                # Title and link
                title_elem = card.find('h2', class_='jobTitle')
                if not title_elem:
                    continue
                
                link_elem = title_elem.find('a')
                if not link_elem:
                    continue
                
                title = title_elem.get_text(strip=True)
                job_id = link_elem.get('data-jk', '')
                link = f"https://in.indeed.com/viewjob?jk={job_id}" if job_id else ""
                
                if not link or link in seen_urls:
                    continue
                seen_urls.add(link)
                
                # Company
                company_elem = card.find('span', class_='companyName')
                company = company_elem.get_text(strip=True) if company_elem else "Unknown"
                
                # Location
                location_elem = card.find('div', class_='companyLocation')
                location = location_elem.get_text(strip=True) if location_elem else ""
                
                # Description
                desc_elem = card.find('div', class_='job-snippet')
                description = desc_elem.get_text(strip=True) if desc_elem else ""
                
                # Posted date
                date_elem = card.find('span', class_='date')
                posted_date = date_elem.get_text(strip=True) if date_elem else ""
                
                # Build job object
                job = {
                    "title": title,
                    "company": company,
                    "summary": description[:500],
                    "apply_url": link,
                    "source": "Indeed",
                    "location": location,
                    "posted_date": posted_date,
                }
                
                job["location_tags"] = extract_location_from_job(job)
                jobs.append(job)
            
            except Exception as e:
                logger.debug(f"Error parsing Indeed job card: {e}")
                continue
    
    except Exception as e:
        logger.error(f"Error parsing Indeed HTML: {e}")
    
    return jobs


# ============================================
# MAIN FETCH FUNCTION
# ============================================

def fetch_all(output_path: str = None, serper_queries: list = None, 
              prioritize_local: bool = False, location: str = None,
              use_scrapingdog: bool = True) -> list:
    """
    Fetch jobs from all sources with multi-layer search strategy.
    
    Search layers (in order):
    1. SerperDev Google Jobs API (primary, fast)
    2. ScrapingDog direct scraping (backup/supplement)
    3. Lever API (tech companies)
    4. Remotive API (curated remote)
    5. RSS feeds (if not prioritizing local)
    
    Args:
        output_path: Path to save jobs JSON file
        serper_queries: Profile-based queries
        prioritize_local: If True, skip large remote-only RSS feeds
        location: User's location for targeted searches
        use_scrapingdog: Enable ScrapingDog as backup (default: True)
    
    Returns:
        list: All fetched jobs with location_tags
    """
    output_path = output_path or OUTPUT_DEFAULT
    all_jobs = []
    source_counts = {}

    logger.info("Starting multi-layer job fetch from all sources")

    if prioritize_local:
        logger.info("Prioritizing local sources: SerperDev → ScrapingDog → Lever")
        
        # Layer 1: SerperDev (primary, fastest)
        try:
            jobs = fetch_serperdev_jobs(queries=serper_queries, location=location)
            all_jobs.extend(jobs)
        except Exception as e:
            logger.error(f"Failed to fetch SerperDev: {e}")
        
        # Layer 2: ScrapingDog (backup/supplement)
        if use_scrapingdog and SCRAPINGDOG_API_KEY:
            try:
                jobs = fetch_scrapingdog_jobs(queries=serper_queries, location=location)
                all_jobs.extend(jobs)
            except Exception as e:
                logger.error(f"Failed to fetch ScrapingDog: {e}")
        
        # Layer 3: Lever (tech companies)
        try:
            jobs = fetch_lever_jobs()
            all_jobs.extend(jobs)
        except Exception as e:
            logger.error(f"Failed to fetch Lever: {e}")
        
        # Layer 4: Remotive (curated remote)
        try:
            jobs = fetch_remotive_jobs()
            all_jobs.extend(jobs)
        except Exception as e:
            logger.error(f"Failed to fetch Remotive: {e}")
        
        logger.info("Skipped large remote-only RSS feeds to favor local sources")

    else:
        # Full fetch including RSS feeds
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

        try:
            jobs = fetch_remotive_jobs()
            all_jobs.extend(jobs)
        except Exception as e:
            logger.error(f"Failed to fetch Remotive: {e}")

        try:
            jobs = fetch_lever_jobs()
            all_jobs.extend(jobs)
        except Exception as e:
            logger.error(f"Failed to fetch Lever: {e}")

        try:
            jobs = fetch_serperdev_jobs(queries=serper_queries, location=location)
            all_jobs.extend(jobs)
        except Exception as e:
            logger.error(f"Failed to fetch SerperDev: {e}")
        
        if use_scrapingdog and SCRAPINGDOG_API_KEY:
            try:
                jobs = fetch_scrapingdog_jobs(queries=serper_queries, location=location)
                all_jobs.extend(jobs)
            except Exception as e:
                logger.error(f"Failed to fetch ScrapingDog: {e}")

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


if __name__ == "__main__":
    import sys

    try:
        output = sys.argv[1] if len(sys.argv) > 1 else OUTPUT_DEFAULT

        test_queries = [
            "Customer Experience Specialist",
            "Technical Support Specialist",
            "SaaS Customer Support",
        ]
        
        jobs = fetch_all(
            output_path=output, 
            serper_queries=test_queries,
            location="Bangalore, India",
            prioritize_local=True,
            use_scrapingdog=True
        )

        print(f"\n✅ Successfully fetched {len(jobs)} unique jobs!")
        print(f"Saved to: {output}")

        sources = {}
        for job in jobs:
            source = job.get("source", "Unknown")
            sources[source] = sources.get(source, 0) + 1
        print("\nBreakdown by source:")
        for source, count in sorted(sources.items(), key=lambda x: -x[1]):
            print(f"  {source}: {count} jobs")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        logger.exception("Job fetching failed")
        sys.exit(1)
