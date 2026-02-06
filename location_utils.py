"""
Location utilities for JobBot - Phase 1
========================================
This file adds location/timezone detection to job postings.

What this does:
- Extracts timezone/region info from job descriptions
- Helps filter jobs by your preferred regions
- Works with existing remote job feeds (no API needed!)
"""

import re
from typing import List

# ============================================
# TIMEZONE/REGION MAPPINGS
# ============================================

# These are keywords we look for in job descriptions to determine location
TIMEZONE_REGIONS = {
    "americas": [
        # North/South America indicators
        "americas", "north america", "south america", "latin america",
        # US/Canada timezones
        "est", "edt", "pst", "pdt", "cst", "cdt", "mst", "mdt",
        "eastern time", "pacific time", "central time", "mountain time",
        # UTC offsets for Americas
        "utc-5", "utc-6", "utc-7", "utc-8", "utc-4",
        # Specific mentions
        "us only", "usa only", "canada only", "north american",
    ],
    
    "europe": [
        # European indicators
        "emea", "europe", "european union", "eu only",
        # European timezones
        "cet", "cest", "gmt", "bst", "wet", "eet",
        "central european", "greenwich mean",
        # UTC offsets for Europe
        "utc+0", "utc+1", "utc+2", "utc+3",
        # Specific mentions
        "uk only", "european hours", "eu hours",
    ],
    
    "asia": [
        # Asia-Pacific indicators
        "apac", "asia pacific", "asia-pacific", "asian",
        # Specific timezones
        "ist", "sgt", "jst", "aest", "hkt",
        "india standard", "singapore time", "japan standard",
        # UTC offsets for Asia
        "utc+5:30", "utc+5", "utc+8", "utc+9", "utc+10",
        # Specific mentions
        "india only", "singapore only", "australia", "new zealand",
    ],
    
    "global": [
        # Universal indicators (can work from anywhere)
        "anywhere", "worldwide", "global", "any timezone", 
        "all timezones", "no timezone restriction", "timezone agnostic",
        "work from anywhere", "fully remote", "location independent",
    ]
}


# ============================================
# LOCATION EXTRACTION
# ============================================

def extract_location_tags(text: str) -> List[str]:
    """
    Extract location/timezone tags from job text (title or description).
    
    This scans the text for timezone or region keywords and returns
    which regions this job is open to.
    
    Args:
        text: Job title or description to scan
        
    Returns:
        List of region tags like ["americas", "europe"] or ["global"]
        
    Examples:
        >>> extract_location_tags("Remote Developer - EST timezone preferred")
        ["americas"]
        
        >>> extract_location_tags("Work from anywhere in the world!")
        ["global"]
        
        >>> extract_location_tags("EMEA or Americas")
        ["europe", "americas"]
    """
    if not text:
        return ["global"]  # Default: assume global if no info
    
    text_lower = text.lower()
    tags = set()
    
    # Check each region's keywords
    for region, keywords in TIMEZONE_REGIONS.items():
        for keyword in keywords:
            if keyword in text_lower:
                tags.add(region)
                break  # Found a match for this region, move to next
    
    # If no location info found, assume it's global (open to all)
    if not tags:
        return ["global"]
    
    return sorted(list(tags))  # Sort for consistency


def extract_location_from_job(job: dict) -> List[str]:
    """
    Extract location tags from a complete job posting.
    
    Checks both the job title and description for location info.
    
    Args:
        job: Job dictionary with "title" and "summary" fields
        
    Returns:
        List of location tags
        
    Example:
        >>> job = {
        ...     "title": "Python Developer",
        ...     "summary": "Remote position. Must be in EST timezone..."
        ... }
        >>> extract_location_from_job(job)
        ["americas"]
    """
    # Combine title and summary for better detection
    title = job.get("title", "")
    summary = job.get("summary", "")
    combined_text = f"{title} {summary}"
    
    return extract_location_tags(combined_text)


# ============================================
# LOCATION FILTERING
# ============================================

def location_matches(job_tags: List[str], user_preferences: List[str]) -> bool:
    """
    Check if a job's location matches user's preferences.
    
    Rules:
    - If job or user has "global", it matches everything
    - Otherwise, there must be at least one region in common
    
    Args:
        job_tags: Location tags from the job (e.g., ["americas", "europe"])
        user_preferences: User's preferred regions (e.g., ["americas"])
        
    Returns:
        True if the job matches user's location preferences
        
    Examples:
        >>> location_matches(["global"], ["americas"])
        True  # Global jobs match everyone
        
        >>> location_matches(["americas"], ["americas", "europe"])
        True  # Americas is in user's preferences
        
        >>> location_matches(["asia"], ["americas"])
        False  # No overlap
    """
    # Global matches everything
    if "global" in job_tags or "global" in user_preferences:
        return True
    
    # Check if there's any overlap between job and user preferences
    job_set = set(job_tags)
    user_set = set(user_preferences)
    return bool(job_set & user_set)  # True if intersection is not empty


def filter_jobs_by_location(jobs: List[dict], user_preferences: List[str]) -> List[dict]:
    """
    Filter a list of jobs to only those matching user's location preferences.
    
    Args:
        jobs: List of job dictionaries
        user_preferences: List of preferred regions (e.g., ["americas", "europe"])
        
    Returns:
        Filtered list of jobs
        
    Example:
        >>> jobs = [
        ...     {"title": "Dev", "location_tags": ["americas"]},
        ...     {"title": "Designer", "location_tags": ["asia"]},
        ... ]
        >>> filter_jobs_by_location(jobs, ["americas"])
        [{"title": "Dev", "location_tags": ["americas"]}]
    """
    # If user wants global or didn't specify, return all jobs
    if not user_preferences or "global" in user_preferences:
        return jobs
    
    filtered = []
    for job in jobs:
        job_tags = job.get("location_tags", ["global"])
        if location_matches(job_tags, user_preferences):
            filtered.append(job)
    
    return filtered


# ============================================
# UTILITY FUNCTIONS
# ============================================

def get_region_display_name(region_code: str) -> str:
    """
    Convert region code to friendly display name.
    
    Args:
        region_code: Region code like "americas"
        
    Returns:
        Display name like "Americas"
    """
    display_names = {
        "americas": "Americas (North & South America)",
        "europe": "Europe (EMEA)",
        "asia": "Asia-Pacific",
        "global": "Global (Anywhere)",
    }
    return display_names.get(region_code, region_code.title())


def get_all_regions() -> List[str]:
    """
    Get list of all supported region codes.
    
    Returns:
        ["americas", "europe", "asia", "global"]
    """
    return ["americas", "europe", "asia", "global"]


# ============================================
# TESTING
# ============================================

if __name__ == "__main__":
    # Test the location extraction
    test_cases = [
        "Remote Developer - Must be in EST timezone",
        "Fully remote - work from anywhere!",
        "EMEA only - CET timezone",
        "Looking for someone in APAC region",
        "US or Europe preferred",
        "No timezone requirements",
    ]
    
    print("Testing location extraction:\n")
    for text in test_cases:
        tags = extract_location_tags(text)
        print(f"Text: {text}")
        print(f"Tags: {tags}\n")
    
    # Test filtering
    jobs = [
        {"title": "Job 1", "location_tags": ["americas"]},
        {"title": "Job 2", "location_tags": ["europe"]},
        {"title": "Job 3", "location_tags": ["global"]},
        {"title": "Job 4", "location_tags": ["asia"]},
    ]
    
    print("\nTesting job filtering:")
    print(f"User prefers: americas")
    filtered = filter_jobs_by_location(jobs, ["americas"])
    print(f"Matches: {[j['title'] for j in filtered]}")
