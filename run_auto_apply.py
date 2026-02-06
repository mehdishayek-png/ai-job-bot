import json
import os
import hashlib
import time
import logging
from openai import OpenAI
from dotenv import load_dotenv
from cover_letter_generator import generate_cover_letter

# ============================================
# LOGGING SETUP
# ============================================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ============================================
# LOAD API KEY
# ============================================

load_dotenv()

api_key = os.getenv("OPENROUTER_API_KEY")
if not api_key:
    # Try Streamlit secrets
    try:
        import streamlit as st
        api_key = st.secrets.get("OPENROUTER_API_KEY")
    except (ImportError, KeyError, AttributeError):
        pass

if not api_key:
    raise ValueError(
        "OPENROUTER_API_KEY not found. "
        "Set it in .env file or Streamlit secrets."
    )

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=api_key,
)

# ============================================
# CONFIGURATION
# ============================================

# ============================================
# CONFIG
# ============================================
MODEL = os.getenv("SCORING_MODEL", "google/gemini-2.0-flash-thinking-exp:free")
MATCH_THRESHOLD = int(os.getenv("MATCH_THRESHOLD", "70"))  # Accept 70+ scores
MAX_MATCHES = int(os.getenv("MAX_MATCHES", "30"))  # Show top 30 results
API_RATE_LIMIT = float(os.getenv("API_RATE_LIMIT", "0.3"))  # Faster requests
MAX_LLM_CANDIDATES = int(os.getenv("MAX_LLM_CANDIDATES", "50"))  # Score top 50 jobs
BATCH_SIZE = int(os.getenv("BATCH_SIZE", "5"))  # ✅ Keep at 5
MAX_PER_COMPANY = 3  # ✅ Keep at 3
  # seconds between calls
# ============================================
# UTILITIES
# ============================================

def create_job_id(job: dict) -> str:
    """
    Create unique job ID using multiple fields to avoid collisions.
    """
    unique_str = "|".join([
        job.get("company", "unknown"),
        job.get("title", "unknown"),
        job.get("apply_url", "")[:100],  # Use part of URL for uniqueness
    ])
    return hashlib.md5(unique_str.encode()).hexdigest()[:16]


def profile_hash(profile: dict) -> str:
    """
    Create a unique hash per profile for cache isolation.
    """
    # Only hash the relevant fields
    relevant = {
        "name": profile.get("name", ""),
        "headline": profile.get("headline", ""),
        "skills": sorted(profile.get("skills", []))  # Sort for consistency
    }
    text = json.dumps(relevant, sort_keys=True)
    return hashlib.md5(text.encode()).hexdigest()


def build_safe_profile_text(profile: dict) -> str:
    """
    Build profile text with input validation and sanitization.
    """
    # Validate and sanitize name
    name = str(profile.get("name", "Candidate"))[:100].strip()
    
    # Validate and sanitize headline
    headline = str(profile.get("headline", "Professional"))[:200].strip()
    
    # Validate skills is a list
    skills = profile.get("skills", [])
    if not isinstance(skills, list):
        logger.warning("Skills is not a list, converting to empty list")
        skills = []
    
    # Sanitize skills - limit length and count
    safe_skills = [str(s)[:50].strip() for s in skills if s][:50]
    
    if not safe_skills:
        logger.warning("No valid skills found in profile")
    
    return f"""
Name: {name}
Headline: {headline}

Skills:
{", ".join(safe_skills) if safe_skills else "None specified"}
"""


def deduplicate_jobs(jobs: list) -> list:
    """
    Remove duplicate jobs based on company + title.
    """
    seen = set()
    unique = []
    
    for job in jobs:
        key = (
            job.get("company", "").lower().strip(),
            job.get("title", "").lower().strip()
        )
        
        if key not in seen and key != ("", ""):
            seen.add(key)
            unique.append(job)
        else:
            logger.debug(f"Skipping duplicate job: {key}")
    
    logger.info(f"Deduplicated {len(jobs)} jobs to {len(unique)} unique jobs")
    return unique

# ============================================
# SENIORITY DETECTION
# ============================================

SENIOR_TITLE_WORDS = [
    "lead", "head of", "head,", "director", "vp ", "vice president",
    "principal", "chief", "cto", "coo", "ceo", "cfo",
    "founding", "co-founder", "partner", "svp", "evp",
    "staff ", "distinguished",
]

MID_TITLE_WORDS = [
    "senior", "sr ", "sr.", "manager", "team lead",
]


def detect_seniority(title: str) -> str:
    """Classify job title seniority: 'senior', 'mid', or 'open'."""
    t = title.lower()
    if any(w in t for w in SENIOR_TITLE_WORDS):
        return "senior"
    if any(w in t for w in MID_TITLE_WORDS):
        return "mid"
    return "open"


def estimate_candidate_years(profile: dict) -> int:
    """Estimate experience from profile headline/skills."""
    headline = (profile.get("headline", "") or "").lower()

    # Look for explicit mention
    import re as _re
    m = _re.search(r'(\d+)\+?\s*(?:years?|yrs?)', headline)
    if m:
        return int(m.group(1))

    # Infer from title words
    if any(w in headline for w in ["intern", "trainee", "fresher", "entry"]):
        return 0
    if any(w in headline for w in ["junior", "associate", "jr "]):
        return 1
    if any(w in headline for w in ["specialist", "analyst", "coordinator", "executive"]):
        return 2
    if any(w in headline for w in ["senior", "sr ", "lead", "manager"]):
        return 5
    if any(w in headline for w in ["director", "head of", "vp "]):
        return 10

    return 2  # Conservative default


# ============================================
# LOCATION CLASSIFICATION
# ============================================

INDIA_SIGNALS = [
    "india", "bangalore", "bengaluru", "mumbai", "delhi",
    "hyderabad", "pune", "chennai", "kolkata", "gurgaon",
    "gurugram", "noida", "jaipur", "ahmedabad", "kochi",
    "chandigarh", "indore", "lucknow", "coimbatore",
]

REMOTE_SIGNALS = [
    "remote", "work from home", "wfh", "anywhere",
    "distributed", "fully remote", "remote-first",
]


def classify_location(job: dict) -> str:
    """Classify job as 'india', 'remote', or 'other'."""
    loc = (job.get("location", "") or "").lower()
    title = job.get("title", "").lower()
    summary = (job.get("summary", "") or "")[:500].lower()
    combined = f"{loc} {title} {summary}"

    if any(s in combined for s in INDIA_SIGNALS):
        return "india"
    if any(s in combined for s in REMOTE_SIGNALS):
        return "remote"
    return "other"


# ============================================
# SEMANTIC SCORING WITH RETRY & RATE LIMITING
# ============================================

def semantic_score(job: dict, profile_text: str, candidate_years: int = 2, max_retries: int = 3) -> int:
    """
    Score match between candidate and job with retry logic and rate limiting.
    Now includes seniority awareness in the prompt.
    """
    # Truncate long job descriptions
    summary = job.get("summary", "")[:2000]
    title = job.get("title", "Unknown")
    location = classify_location(job)

    prompt = f"""Score match between candidate and job from 0-100. Be strict.

Candidate:
{profile_text}
Experience: approximately {candidate_years} years

Job Title: {title}
Job Location: {location}
Job Description:
{summary}

CRITICAL SCORING RULES:
- If the job title contains "Lead", "Director", "VP", "Head of", "Principal", "Staff"
  and the candidate has less than 5 years experience, score 30-50 MAX.
- If the job title contains "Senior" or "Manager" and the candidate has less than
  3 years experience, score 45-60 MAX.
- Seniority mismatch OVERRIDES skill overlap. Wrong level = low score.
- "Specialist", "Associate", "Coordinator", "Executive" roles fit 1-4 years well.
- Strategy/GTM/Revenue Operations Lead roles require 7-10+ years.

LOCATION BONUS:
- If location is "india" or "remote", add +5 to the score.

Return ONLY a number between 0 and 100.
"""

    for attempt in range(max_retries):
        try:
            res = client.chat.completions.create(
                model=MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=0,
                max_tokens=5,
            )

            score_text = res.choices[0].message.content.strip()

            # Extract numeric score safely
            digits = "".join(c for c in score_text if c.isdigit())

            if digits:
                score = max(0, min(100, int(digits)))
                logger.debug(f"Scored job '{job.get('title')}': {score}")
                return score

            logger.warning(f"No numeric score in response: {score_text}")
            return 0

        except Exception as e:
            error_msg = str(e).lower()
            
            # Check for rate limit
            if "rate" in error_msg or "limit" in error_msg:
                wait_time = (2 ** attempt) * 2  # Exponential backoff: 2s, 4s, 8s
                logger.warning(f"Rate limited, waiting {wait_time}s (attempt {attempt + 1}/{max_retries})")
                time.sleep(wait_time)
            elif attempt < max_retries - 1:
                logger.warning(f"Scoring failed (attempt {attempt + 1}/{max_retries}): {e}")
                time.sleep(1)
            else:
                logger.error(f"Semantic scoring failed after {max_retries} attempts: {e}")
                return 0
    
    return 0


# ============================================
# CORE PIPELINE
# ============================================

def run_pipeline(
    profile_file: str,
    jobs_file: str,
    session_dir: str,
    letters_dir: str = None,
    progress_callback=None
) -> list:
    """
    Main job matching pipeline with proper error handling.
    """
    
    # ---- Load profile ----
    if not os.path.exists(profile_file):
        raise FileNotFoundError(f"Profile file not found: {profile_file}")

    with open(profile_file, "r", encoding="utf-8") as f:
        profile = json.load(f)
    
    logger.info(f"Loaded profile: {profile.get('name', 'Unknown')}")

    # ---- Fetch jobs if not present ----
    if not os.path.exists(jobs_file):
        logger.info("Jobs file not found, fetching from sources...")
        if progress_callback:
            progress_callback("Fetching jobs from remote sources...")
        
        from job_fetcher import fetch_all
        try:
            fetch_all(output_path=jobs_file)
            logger.info(f"Jobs fetched and saved to {jobs_file}")
        except Exception as e:
            logger.error(f"Failed to fetch jobs: {e}")
            raise RuntimeError(f"Could not fetch jobs: {e}")

    # ---- Load jobs ----
    with open(jobs_file, "r", encoding="utf-8") as f:
        jobs = json.load(f)

    if not jobs:
        logger.warning("No jobs found")
        return []
    
    logger.info(f"Loaded {len(jobs)} jobs")

    # ---- Deduplicate jobs ----
    jobs = deduplicate_jobs(jobs)

    # ---- Estimate candidate experience ----
    candidate_years = estimate_candidate_years(profile)
    logger.info(f"Estimated experience: ~{candidate_years} years")
    if progress_callback:
        progress_callback(f"Estimated experience: ~{candidate_years} years")

    # ---- Pre-filter: seniority + location ----
    filtered_jobs = []
    stats = {"too_senior": 0, "wrong_location": 0, "passed": 0}

    for job in jobs:
        title = job.get("title", "")
        loc = classify_location(job)

        # Kill senior roles for junior candidates
        if candidate_years < 3 and detect_seniority(title) == "senior":
            stats["too_senior"] += 1
            continue

        # Deprioritize non-India/non-Remote (but don't kill — these sources are mostly remote)
        # WeWorkRemotely, RemoteOK, Remotive are all remote job boards
        # so most jobs should classify as 'remote' anyway
        job["_location"] = loc
        filtered_jobs.append(job)
        stats["passed"] += 1

    logger.info(f"Pre-filter: {len(jobs)} → {stats['passed']} "
                f"(killed {stats['too_senior']} too-senior)")
    if progress_callback:
        progress_callback(f"Pre-filter: {len(jobs)} → {stats['passed']} jobs "
                         f"({stats['too_senior']} too senior removed)")

    jobs = filtered_jobs

    # ---- Profile hash for cache isolation ----
    p_hash = profile_hash(profile)
    logger.info(f"Profile hash: {p_hash}")

    # ---- Load cache ----
    cache_file = os.path.join(session_dir, "semantic_cache.json")
    cache = {}

    if os.path.exists(cache_file):
        try:
            # Safety check: limit cache file size
            if os.path.getsize(cache_file) > 10 * 1024 * 1024:  # 10MB
                logger.warning("Cache file too large, resetting")
            else:
                with open(cache_file, "r", encoding="utf-8") as f:
                    cache = json.load(f)
                logger.info(f"Loaded cache with {len(cache)} entries")
        except Exception as e:
            logger.warning(f"Failed to load cache: {e}")
            cache = {}

    # ---- Build profile text ----
    profile_text = build_safe_profile_text(profile)

    # ---- Score jobs ----
    matches = []
    total_jobs = len(jobs)
    cache_hits = 0
    
    if progress_callback:
        progress_callback(f"Scoring {total_jobs} jobs...")

    for idx, job in enumerate(jobs, 1):
        # Progress update every 10 jobs
        if progress_callback and idx % 10 == 0:
            progress_callback(
                f"Scoring jobs... {idx}/{total_jobs} ({idx*100//total_jobs}%) - "
                f"{len(matches)} matches found"
            )

        # Create unique job ID
        job_id = create_job_id(job)
        cache_key = f"{p_hash}_{job_id}"

        # Check cache first
        if cache_key in cache:
            score = cache[cache_key]
            cache_hits += 1
        else:
            # Score with rate limiting
            score = semantic_score(job, profile_text, candidate_years=candidate_years)
            cache[cache_key] = score
            
            # Rate limit between API calls
            time.sleep(API_RATE_LIMIT)

        # Add to matches if above threshold
        if score >= MATCH_THRESHOLD:
            # Create copy to avoid mutation
            matched_job = job.copy()
            matched_job["match_score"] = score
            matches.append(matched_job)

    logger.info(f"Scoring complete: {len(matches)} matches from {total_jobs} jobs")
    logger.info(f"Cache hit rate: {cache_hits}/{total_jobs} ({cache_hits*100//total_jobs if total_jobs > 0 else 0}%)")

    # ---- Sort and limit matches ----
    matches.sort(key=lambda x: x["match_score"], reverse=True)

    # ---- Enforce company diversity (max 3 per company) ----
    MAX_PER_COMPANY = 3
    company_count = {}
    diverse_matches = []
    for m in matches:
        co = m.get("company", "Unknown").lower().strip()
        company_count[co] = company_count.get(co, 0) + 1
        if company_count[co] <= MAX_PER_COMPANY:
            diverse_matches.append(m)
    matches = diverse_matches

    matches = matches[:MAX_MATCHES]
    
    logger.info(f"Top {len(matches)} matches selected")

    # ---- Save cache ----
    os.makedirs(session_dir, exist_ok=True)

    try:
        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump(cache, f, indent=2, ensure_ascii=False)
        logger.info(f"Cache saved with {len(cache)} entries")
    except Exception as e:
        logger.error(f"Failed to save cache: {e}")

    # ---- Generate cover letters ----
    if not letters_dir:
        letters_dir = os.path.join(session_dir, "cover_letters")
    os.makedirs(letters_dir, exist_ok=True)

    if progress_callback:
        progress_callback(f"Generating {len(matches)} cover letters...")

    for job in matches:
        try:
            generate_cover_letter(job, profile, letters_dir)
        except Exception as e:
            logger.error(f"Cover letter generation failed for {job.get('title')}: {e}")

    return matches, total_jobs  # Return both matches and total count


# ============================================
# COMPATIBILITY WRAPPER (FOR STREAMLIT UI)
# ============================================

def run_auto_apply_pipeline(
    profile_file=None,
    jobs_file=None,
    matches_file=None,
    cache_file=None,
    log_file=None,
    letters_dir=None,
    progress_callback=None,
):
    """
    Wrapper to maintain compatibility with Streamlit dashboard.
    """

    try:
        if progress_callback:
            progress_callback("Loading profile and jobs...")

        session_dir = os.path.dirname(profile_file)

        matches, total_scored = run_pipeline(
            profile_file=profile_file,
            jobs_file=jobs_file,
            session_dir=session_dir,
            letters_dir=letters_dir,
            progress_callback=progress_callback,
        )

        # ---- Save matches if UI expects file ----
        if matches_file:
            os.makedirs(os.path.dirname(matches_file) or ".", exist_ok=True)
            with open(matches_file, "w", encoding="utf-8") as f:
                json.dump(matches, f, indent=2, ensure_ascii=False)

        if progress_callback:
            progress_callback(f"Done - {len(matches)} matches found from {total_scored} jobs.")

        return {
            "status": "success",
            "matches": len(matches),
            "total_scored": total_scored,
        }

    except Exception as e:
        logger.exception("Pipeline error")
        
        if progress_callback:
            progress_callback(f"Pipeline error: {e}")

        return {
            "status": "error",
            "message": str(e),
        }


# ============================================
# CLI ENTRY (FOR TESTING)
# ============================================

if __name__ == "__main__":
    import sys
    
    # Simple CLI test
    if len(sys.argv) < 3:
        print("Usage: python run_auto_apply.py <profile.json> <jobs.json>")
        sys.exit(1)

    test_profile = sys.argv[1]
    test_jobs = sys.argv[2]
    session_dir = "data/test_session"

    try:
        matches, total = run_pipeline(
            profile_file=test_profile,
            jobs_file=test_jobs,
            session_dir=session_dir,
        )

        print(f"\n✅ Success!")
        print(f"Matches found: {len(matches)} from {total} jobs")
        
        for i, job in enumerate(matches, 1):
            print(f"{i}. {job['company']} - {job['title']} ({job['match_score']}%)")
    
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)
