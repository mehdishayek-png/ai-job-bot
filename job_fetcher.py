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
# MAIN FETCH FUNCTION
# ============================================

def fetch_all(output_path: str = None) -> list:
    """
    Fetch jobs from all sources and save to JSON.
    
    Args:
        output_path: Path to save jobs JSON file
        
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
