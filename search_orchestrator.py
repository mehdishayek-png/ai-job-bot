"""
Search Orchestration Engine
============================
Multi-provider search with intelligent fallback and cost management.

Provider Priority:
1. Serper.dev (Primary) - Fast, reliable, generous limits
2. SerpAPI (Fallback) - Limited credits, use sparingly
3. Free RSS/API sources (Always on) - No cost

Features:
- Smart provider selection based on quota
- Automatic failover on errors
- Query deduplication
- Result normalization
- Pagination support
"""

import os
import time
import logging
import hashlib
import json
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
import requests

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ============================================
# API KEYS
# ============================================

def get_api_key(key_name: str) -> Optional[str]:
    """Get API key from env or Streamlit secrets"""
    key = os.getenv(key_name, "")
    if not key:
        try:
            import streamlit as st
            key = st.secrets.get(key_name, "")
        except (ImportError, KeyError, AttributeError):
            pass
    return key if key else None

SERPER_API_KEY = get_api_key("SERPER_API_KEY")
SERPAPI_KEY = get_api_key("SERPAPI_KEY")

# ============================================
# QUOTA MANAGEMENT
# ============================================

class QuotaManager:
    """Track API usage to avoid overspending"""
    
    def __init__(self, quota_file: str = "data/search_quota.json"):
        self.quota_file = quota_file
        self.quotas = self._load_quotas()
    
    def _load_quotas(self) -> dict:
        """Load quota tracking data"""
        if os.path.exists(self.quota_file):
            try:
                with open(self.quota_file, "r") as f:
                    return json.load(f)
            except Exception:
                pass
        
        # Default quotas (reset monthly)
        return {
            "serper": {
                "limit": 2500,  # Serper.dev free tier
                "used": 0,
                "reset_date": self._get_next_month()
            },
            "serpapi": {
                "limit": 100,  # SerpAPI free tier
                "used": 0,
                "reset_date": self._get_next_month()
            }
        }
    
    def _get_next_month(self) -> str:
        """Get first day of next month as ISO string"""
        today = datetime.now()
        if today.month == 12:
            next_month = datetime(today.year + 1, 1, 1)
        else:
            next_month = datetime(today.year, today.month + 1, 1)
        return next_month.isoformat()
    
    def _save_quotas(self):
        """Persist quota data"""
        try:
            os.makedirs(os.path.dirname(self.quota_file) or ".", exist_ok=True)
            with open(self.quota_file, "w") as f:
                json.dump(self.quotas, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save quotas: {e}")
    
    def _check_reset(self, provider: str):
        """Reset quota if we've passed the reset date"""
        reset_date = datetime.fromisoformat(self.quotas[provider]["reset_date"])
        if datetime.now() >= reset_date:
            logger.info(f"{provider} quota reset (new month)")
            self.quotas[provider]["used"] = 0
            self.quotas[provider]["reset_date"] = self._get_next_month()
            self._save_quotas()
    
    def has_quota(self, provider: str) -> bool:
        """Check if provider has remaining quota"""
        self._check_reset(provider)
        quota = self.quotas.get(provider, {})
        used = quota.get("used", 0)
        limit = quota.get("limit", 0)
        return used < limit
    
    def increment(self, provider: str, count: int = 1):
        """Increment usage counter"""
        if provider in self.quotas:
            self.quotas[provider]["used"] += count
            self._save_quotas()
            logger.info(f"{provider}: {self.quotas[provider]['used']}/{self.quotas[provider]['limit']} searches used")
    
    def get_remaining(self, provider: str) -> int:
        """Get remaining quota"""
        self._check_reset(provider)
        quota = self.quotas.get(provider, {})
        return max(0, quota.get("limit", 0) - quota.get("used", 0))

# Global quota manager instance
quota_manager = QuotaManager()

# ============================================
# SEARCH PROVIDERS
# ============================================

def search_serper(query: str, location: str = None, num_results: int = 10) -> List[Dict]:
    """
    Search using Serper.dev Google Jobs API
    
    Serper advantages:
    - 2,500 free searches/month
    - Fast response times
    - Clean JSON structure
    - Good job board coverage
    """
    if not SERPER_API_KEY:
        logger.warning("Serper API key not found")
        return []
    
    if not quota_manager.has_quota("serper"):
        logger.warning("Serper quota exhausted")
        return []
    
    url = "https://google.serper.dev/search"
    
    # Build search query
    search_query = query
    if location and location.lower() not in ["remote", "remote only"]:
        search_query = f"{query} {location}"
    
    payload = {
        "q": search_query,
        "gl": "us",  # Can be customized based on user location
        "hl": "en",
        "num": num_results,
        "type": "search"  # Use regular search, not just jobs (more sources)
    }
    
    headers = {
        "X-API-KEY": SERPER_API_KEY,
        "Content-Type": "application/json"
    }
    
    try:
        logger.info(f"Serper search: '{search_query}'")
        response = requests.post(url, json=payload, headers=headers, timeout=15)
        response.raise_for_status()
        data = response.json()
        
        quota_manager.increment("serper")
        
        jobs = []
        
        # Parse organic results (job listings appear here)
        for result in data.get("organic", [])[:num_results]:
            # Check if this looks like a job posting
            title = result.get("title", "")
            link = result.get("link", "")
            snippet = result.get("snippet", "")
            
            # Extract company from title if present (format: "Company - Job Title")
            company = "Unknown"
            job_title = title
            
            if " - " in title:
                parts = title.split(" - ", 1)
                if len(parts) == 2 and len(parts[0]) < 60:
                    company = parts[0].strip()
                    job_title = parts[1].strip()
            elif " | " in title:
                parts = title.split(" | ", 1)
                if len(parts) == 2 and len(parts[0]) < 60:
                    company = parts[0].strip()
                    job_title = parts[1].strip()
            
            jobs.append({
                "title": job_title,
                "company": company,
                "summary": snippet,
                "apply_url": link,
                "source": "Google Jobs (Serper)",
                "posted_date": None  # Serper doesn't provide this
            })
        
        logger.info(f"Serper returned {len(jobs)} results")
        return jobs
    
    except requests.RequestException as e:
        logger.error(f"Serper API error: {e}")
        return []
    except Exception as e:
        logger.error(f"Serper processing error: {e}")
        return []


def search_serpapi(query: str, location: str = None, num_results: int = 10) -> List[Dict]:
    """
    Search using SerpAPI (fallback only)
    
    SerpAPI provides:
    - Direct access to Google Jobs
    - 100 free searches/month
    - Structured job data
    """
    if not SERPAPI_KEY:
        logger.warning("SerpAPI key not found")
        return []
    
    if not quota_manager.has_quota("serpapi"):
        logger.warning("SerpAPI quota exhausted")
        return []
    
    url = "https://serpapi.com/search"
    
    params = {
        "engine": "google_jobs",
        "q": query,
        "api_key": SERPAPI_KEY,
        "num": min(num_results, 10),  # SerpAPI max is 10
        "hl": "en"
    }
    
    if location and location.lower() not in ["remote", "remote only"]:
        params["location"] = location
    
    try:
        logger.info(f"SerpAPI search: '{query}' (location: {location})")
        response = requests.get(url, params=params, timeout=20)
        response.raise_for_status()
        data = response.json()
        
        quota_manager.increment("serpapi")
        
        jobs = []
        job_results = data.get("jobs_results", [])
        
        for job in job_results[:num_results]:
            # Parse posted date if available
            posted_date = None
            if "detected_extensions" in job:
                posted_at = job["detected_extensions"].get("posted_at")
                if posted_at:
                    posted_date = _parse_posted_date(posted_at)
            
            jobs.append({
                "title": job.get("title", "Unknown"),
                "company": job.get("company_name", "Unknown"),
                "summary": job.get("description", "")[:500],
                "apply_url": job.get("related_links", [{}])[0].get("link", ""),
                "source": f"Google Jobs ({job.get('via', 'SerpAPI')})",
                "posted_date": posted_date
            })
        
        logger.info(f"SerpAPI returned {len(jobs)} results")
        return jobs
    
    except requests.RequestException as e:
        logger.error(f"SerpAPI error: {e}")
        return []
    except Exception as e:
        logger.error(f"SerpAPI processing error: {e}")
        return []


def _parse_posted_date(posted_str: str) -> Optional[str]:
    """
    Parse 'posted X days ago' into ISO date
    
    Returns ISO date string or None
    """
    try:
        posted_str = posted_str.lower()
        
        if "today" in posted_str or "just posted" in posted_str:
            return datetime.now().isoformat()
        
        if "yesterday" in posted_str:
            return (datetime.now() - timedelta(days=1)).isoformat()
        
        # Extract number of hours/days/weeks ago
        import re
        match = re.search(r'(\d+)\s*(hour|day|week|month)s?\s*ago', posted_str)
        if match:
            number = int(match.group(1))
            unit = match.group(2)
            
            if unit == "hour":
                delta = timedelta(hours=number)
            elif unit == "day":
                delta = timedelta(days=number)
            elif unit == "week":
                delta = timedelta(weeks=number)
            elif unit == "month":
                delta = timedelta(days=number * 30)
            else:
                return None
            
            return (datetime.now() - delta).isoformat()
    
    except Exception:
        pass
    
    return None

# ============================================
# SEARCH ORCHESTRATION
# ============================================

def deduplicate_jobs(jobs: List[Dict]) -> List[Dict]:
    """Remove duplicate jobs based on URL and title similarity"""
    seen_urls = set()
    seen_titles = set()
    unique = []
    
    for job in jobs:
        url = job.get("apply_url", "")
        title = job.get("title", "").lower()
        company = job.get("company", "").lower()
        
        # Create a signature for this job
        signature = f"{company}:{title}"
        
        # Skip if we've seen this URL or very similar title+company
        if url and url in seen_urls:
            continue
        if signature in seen_titles:
            continue
        
        if url:
            seen_urls.add(url)
        seen_titles.add(signature)
        unique.append(job)
    
    return unique


def multi_search(queries: List[Dict], max_results_per_query: int = 10) -> List[Dict]:
    """
    Execute multiple search queries with intelligent provider selection
    
    Args:
        queries: List of query dicts with keys: q, location (optional)
        max_results_per_query: Max results per query
    
    Returns:
        Deduplicated list of all results
    
    Strategy:
    1. Try Serper first (primary, generous quota)
    2. Fall back to SerpAPI if Serper fails or quota exhausted
    3. Deduplicate and return all results
    """
    all_jobs = []
    
    for i, query_config in enumerate(queries, 1):
        query = query_config.get("q", "")
        location = query_config.get("location")
        
        if not query:
            continue
        
        logger.info(f"Query {i}/{len(queries)}: '{query}' (location: {location})")
        
        jobs = []
        
        # Try Serper first
        if SERPER_API_KEY and quota_manager.has_quota("serper"):
            jobs = search_serper(query, location, max_results_per_query)
            
            if jobs:
                logger.info(f"Serper success: {len(jobs)} jobs")
            else:
                logger.warning("Serper returned no results, trying fallback")
        
        # Fallback to SerpAPI if Serper failed or no quota
        if not jobs and SERPAPI_KEY and quota_manager.has_quota("serpapi"):
            logger.info("Using SerpAPI fallback")
            jobs = search_serpapi(query, location, max_results_per_query)
            
            if jobs:
                logger.info(f"SerpAPI fallback success: {len(jobs)} jobs")
        
        if not jobs:
            logger.warning(f"No results from any provider for: {query}")
        
        all_jobs.extend(jobs)
        
        # Rate limiting between queries
        if i < len(queries):
            time.sleep(0.5)
    
    # Deduplicate across all queries
    unique_jobs = deduplicate_jobs(all_jobs)
    
    logger.info(f"Total: {len(unique_jobs)} unique jobs from {len(all_jobs)} raw results")
    
    return unique_jobs


def get_provider_status() -> Dict[str, Dict]:
    """Get status of all search providers for UI display"""
    return {
        "serper": {
            "available": bool(SERPER_API_KEY),
            "remaining": quota_manager.get_remaining("serper") if SERPER_API_KEY else 0,
            "limit": quota_manager.quotas.get("serper", {}).get("limit", 0)
        },
        "serpapi": {
            "available": bool(SERPAPI_KEY),
            "remaining": quota_manager.get_remaining("serpapi") if SERPAPI_KEY else 0,
            "limit": quota_manager.quotas.get("serpapi", {}).get("limit", 0)
        }
    }


# ============================================
# QUERY GENERATION
# ============================================

def generate_search_queries(profile: Dict, max_queries: int = 8) -> List[Dict]:
    """
    Generate diverse search queries from profile
    
    Strategy:
    - Use search_terms from profile (user's preferred job titles)
    - Add location context
    - Combine with key skills for specificity
    """
    queries = []
    
    # Get user's search terms (preferred job titles)
    search_terms = profile.get("search_terms", [])
    if not search_terms:
        # Fallback: use headline or industry
        headline = profile.get("headline", "")
        if headline:
            search_terms = [headline]
        else:
            search_terms = [profile.get("industry", "jobs")]
    
    # Get location
    country = profile.get("country", "")
    location = country if country and country.lower() != "remote only" else None
    
    # Get top skills for query variation
    skills = profile.get("skills", [])[:5]
    
    # Generate base queries from search terms
    for term in search_terms[:3]:  # Limit to 3 primary terms
        queries.append({"q": term, "location": location})
    
    # Add skill-enhanced queries for variety
    if skills and len(queries) < max_queries:
        for skill in skills[:2]:
            for term in search_terms[:1]:
                if len(queries) >= max_queries:
                    break
                queries.append({
                    "q": f"{term} {skill}",
                    "location": location
                })
    
    # Add remote-specific query if user is remote
    if country and country.lower() == "remote only" and len(queries) < max_queries:
        for term in search_terms[:1]:
            queries.append({
                "q": f"{term} remote",
                "location": None
            })
    
    return queries[:max_queries]


# ============================================
# TESTING
# ============================================

if __name__ == "__main__":
    # Test the orchestrator
    test_profile = {
        "search_terms": ["Business Operations Manager", "Operations Lead"],
        "country": "India",
        "skills": ["fintech", "payment operations", "vendor management"]
    }
    
    print("=== Search Provider Status ===")
    status = get_provider_status()
    for provider, info in status.items():
        print(f"{provider}: {'✓' if info['available'] else '✗'} "
              f"({info['remaining']}/{info['limit']} remaining)")
    
    print("\n=== Generating Queries ===")
    queries = generate_search_queries(test_profile, max_queries=4)
    for i, q in enumerate(queries, 1):
        print(f"{i}. {q['q']} (location: {q.get('location', 'global')})")
    
    print("\n=== Running Search ===")
    results = multi_search(queries, max_results_per_query=5)
    
    print(f"\n=== Results: {len(results)} jobs ===")
    for job in results[:3]:
        print(f"- [{job['source']}] {job['company']}: {job['title']}")
