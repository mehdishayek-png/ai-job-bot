import feedparser
import requests
import json
import os
import time
import logging

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

WWR_FEEDS = [
    "https://weworkremotely.com/categories/remote-programming-jobs.rss",
    "https://weworkremotely.com/categories/remote-design-jobs.rss",
    "https://weworkremotely.com/categories/remote-marketing-jobs.rss",
    "https://weworkremotely.com/categories/remote-customer-support-jobs.rss",
]

REMOTEOK = "https://remoteok.com/remote-jobs.rss"

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
                    'User-Agent': 'JobBot/1.0 (Job Aggregator)',
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
                    job = {
                        "title": entry.get("title", "").strip(),
                        "company": entry.get("author", "Unknown").strip(),
                        "summary": entry.get("summary", "").strip(),
                        "apply_url": entry.get("link", "").strip(),
                        "source": source,
                    }
                    
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
                'User-Agent': 'JobBot/1.0 (Job Aggregator)',
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
                    "summary": (j.get("description", "")[:500]).strip(),  # Truncate description
                    "apply_url": j.get("url", "").strip(),
                    "source": "Remotive",
                }
                
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
        list: All fetched jobs
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
    
    # Save to file
    try:
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(all_jobs, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Jobs saved to {output_path}")
    
    except Exception as e:
        logger.error(f"Failed to save jobs file: {e}")
        raise
    
    return all_jobs


# ============================================
# CLI ENTRY
# ============================================

if __name__ == "__main__":
    import sys
    
    try:
        # Allow custom output path from command line
        output = sys.argv[1] if len(sys.argv) > 1 else OUTPUT_DEFAULT
        
        jobs = fetch_all(output_path=output)
        
        print(f"\n✅ Successfully fetched {len(jobs)} jobs!")
        print(f"Saved to: {output}")
        
        # Show breakdown by source
        sources = {}
        for job in jobs:
            source = job.get("source", "Unknown")
            sources[source] = sources.get(source, 0) + 1
        
        print("\nBreakdown by source:")
        for source, count in sorted(sources.items()):
            print(f"  {source}: {count} jobs")
    
    except Exception as e:
        print(f"\n❌ Error: {e}")
        logger.exception("Job fetching failed")
        sys.exit(1)
