import json
import os
import time
from openai import OpenAI
from dotenv import load_dotenv
from cover_letter_generator import generate_cover_letter

# ============================================
# CONFIG
# ============================================

PROFILE_FILE = "data/profile.json"
JOBS_FILE = "data/jobs.json"
MATCHES_FILE = "data/matched_jobs.json"
CACHE_FILE = "data/semantic_cache.json"
LOG_FILE = "data/run_log.txt"

MATCH_THRESHOLD = 70
MAX_APPLICATIONS = 5
MAX_RETRIES = 3
RETRY_DELAY = 2  # seconds
API_RATE_LIMIT_DELAY = 0.5  # seconds between API calls

# ============================================
# LOAD API KEY - STREAMLIT COMPATIBLE
# ============================================

# Try Streamlit secrets first, then fall back to .env
try:
    import streamlit as st
    api_key = st.secrets["OPENROUTER_API_KEY"]
except (ImportError, KeyError, AttributeError):
    load_dotenv()
    api_key = os.getenv("OPENROUTER_API_KEY")

# Validate API key
if not api_key:
    error_msg = "❌ OPENROUTER_API_KEY not found"
    try:
        import streamlit as st
        st.error(error_msg)
        st.stop()
    except ImportError:
        raise ValueError(error_msg)

MODEL = "mistralai/mistral-7b-instruct"

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=api_key
)

os.makedirs("data", exist_ok=True)

# ============================================
# LOGGER
# ============================================

def log(message):
    print(message)
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(message + "\n")
    except Exception as e:
        print(f"Logging error: {e}")

# ============================================
# SAFE CACHE LOAD
# ============================================

def load_cache():
    if not os.path.exists(CACHE_FILE):
        return {}

    try:
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, dict):
                return data
            else:
                return {}
    except Exception as e:
        log(f"Cache load error: {e}")
        return {}

# ============================================
# SEMANTIC SCORING WITH RETRY LOGIC
# ============================================

def semantic_score(job, profile_text, retry_count=0):
    """
    Score job match with retry logic and rate limiting
    """
    title = job.get("title", "Unknown")
    description = job.get("summary", "")[:500]  # Limit description length to avoid token issues

    # Skip if no description
    if not description:
        log(f"⚠️ Skipping {title} - no description")
        return 0

    prompt = f"""Rate match between candidate and job from 0–100.

Candidate:
{profile_text}

Job Title:
{title}

Job Description:
{description}

Return ONLY a number."""

    try:
        # Add rate limiting to avoid overwhelming API
        time.sleep(API_RATE_LIMIT_DELAY)
        
        response = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            max_tokens=5,
            timeout=30  # Add timeout to prevent hanging
        )

        score_text = response.choices[0].message.content.strip()
        
        # Parse score more robustly
        try:
            # Extract just the number from response
            import re
            numbers = re.findall(r'\d+', score_text)
            if numbers:
                score = int(numbers[0])
                # Clamp score between 0-100
                return max(0, min(100, score))
            else:
                log(f"⚠️ Non-numeric response for {title}: {score_text}")
                return 0
        except ValueError:
            log(f"⚠️ Could not parse score for {title}: {score_text}")
            return 0
            
    except Exception as e:
        error_msg = str(e)
        
        # Retry logic for transient errors
        if retry_count < MAX_RETRIES:
            if "rate_limit" in error_msg.lower() or "timeout" in error_msg.lower():
                log(f"⚠️ Retry {retry_count + 1}/{MAX_RETRIES} for {title}: {error_msg}")
                time.sleep(RETRY_DELAY * (retry_count + 1))  # Exponential backoff
                return semantic_score(job, profile_text, retry_count + 1)
        
        log(f"❌ Scoring API error for {title}: {error_msg}")
        
        try:
            import streamlit as st
            st.warning(f"Scoring failed for {title}")
        except ImportError:
            pass
            
        return 0

# ============================================
# MAIN RUNNER WITH ROBUST ERROR HANDLING
# ============================================

def main():
    """
    Main pipeline with comprehensive error handling
    """
    try:
        # Reset log file each run
        open(LOG_FILE, "w").close()
    except Exception as e:
        print(f"Could not reset log file: {e}")

    log("\n=== PROFILE DRIVEN AUTO APPLY ===\n")

    # ----------------------------------------
    # VALIDATE PROFILE EXISTS
    # ----------------------------------------
    
    if not os.path.exists(PROFILE_FILE):
        error_msg = "❌ Profile file not found. Please create a profile first."
        log(error_msg)
        try:
            import streamlit as st
            st.error(error_msg)
        except ImportError:
            pass
        return

    # ----------------------------------------
    # ENSURE JOBS EXIST
    # ----------------------------------------

    if not os.path.exists(JOBS_FILE):
        log("No jobs file found. Running job fetcher...\n")

        try:
            import job_fetcher
            job_fetcher.main()
            log("Job fetcher completed.\n")
        except Exception as e:
            log(f"Job fetcher error: {str(e)}\n")
            try:
                import streamlit as st
                st.error(f"Job fetching failed: {str(e)}")
            except ImportError:
                pass

        if not os.path.exists(JOBS_FILE):
            log("Job fetch failed. Exiting.")
            try:
                import streamlit as st
                st.warning("No jobs found. Job sources may be temporarily unavailable. Please try again later.")
            except ImportError:
                pass
            return

    # ----------------------------------------
    # LOAD DATA WITH VALIDATION
    # ----------------------------------------

    try:
        with open(PROFILE_FILE, "r", encoding="utf-8") as f:
            profile = json.load(f)
            
        if not profile.get("skills"):
            error_msg = "❌ Profile has no skills. Please add skills to your profile."
            log(error_msg)
            try:
                import streamlit as st
                st.error(error_msg)
            except ImportError:
                pass
            return
            
    except Exception as e:
        log(f"❌ Failed to load profile: {e}")
        return

    try:
        with open(JOBS_FILE, "r", encoding="utf-8") as f:
            jobs = json.load(f)
            
        if not jobs or len(jobs) == 0:
            log("No jobs available in jobs file.")
            try:
                import streamlit as st
                st.info("No jobs found. The job sources might be empty or all jobs were filtered out.")
            except ImportError:
                pass
            return
            
    except Exception as e:
        log(f"❌ Failed to load jobs: {e}")
        return

    semantic_cache = load_cache()

    # ----------------------------------------
    # BUILD PROFILE TEXT
    # ----------------------------------------

    profile_text = f"""Name: {profile.get('name', 'Candidate')}
Headline: {profile.get('headline', 'Professional')}
Skills: {", ".join(profile.get('skills', [])[:15])}"""  # Limit skills to avoid token issues

    shortlisted_jobs = jobs
    log(f"Shortlisted jobs: {len(shortlisted_jobs)}\n")

    scored_jobs = []
    log("Scoring jobs semantically...\n")

    # ----------------------------------------
    # SCORING LOOP WITH PROGRESS TRACKING
    # ----------------------------------------

    for i, job in enumerate(shortlisted_jobs, 1):
        try:
            job_id = f"{job.get('company', 'Unknown')}_{job.get('title', 'Unknown')}"
            
            log(f"[{i}/{len(shortlisted_jobs)}] {job.get('title', 'Unknown')}")

            # Check cache first
            if job_id in semantic_cache:
                score = semantic_cache[job_id]
                log(f"⚡ Cached score: {score}")
            else:
                # Score with retry logic
                score = semantic_score(job, profile_text)
                semantic_cache[job_id] = score
                log(f"🧠 API score: {score}")

            # Add to results if meets threshold
            if score >= MATCH_THRESHOLD:
                job["match_score"] = score
                scored_jobs.append(job)
                
        except Exception as e:
            log(f"❌ Error processing job {i}: {e}")
            continue  # Skip this job and continue

    # ----------------------------------------
    # SAVE CACHE (even if incomplete)
    # ----------------------------------------

    try:
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(semantic_cache, f, indent=2)
        log("\nSemantic cache updated.")
    except Exception as e:
        log(f"❌ Failed to save cache: {e}")

    # ----------------------------------------
    # HANDLE NO MATCHES
    # ----------------------------------------
    
    if not scored_jobs:
        log("\n❌ No jobs met the match threshold.")
        try:
            import streamlit as st
            st.warning(f"No jobs scored above {MATCH_THRESHOLD}%. Try lowering your skill requirements or check back later for new postings.")
        except ImportError:
            pass
        return

    # ----------------------------------------
    # SORT BEST MATCHES
    # ----------------------------------------

    scored_jobs.sort(key=lambda x: x.get("match_score", 0), reverse=True)
    best_matches = scored_jobs[:MAX_APPLICATIONS]

    # ----------------------------------------
    # SAVE MATCHES
    # ----------------------------------------

    try:
        with open(MATCHES_FILE, "w", encoding="utf-8") as f:
            json.dump(best_matches, f, indent=2)
    except Exception as e:
        log(f"❌ Failed to save matches: {e}")

    # ----------------------------------------
    # GENERATE COVER LETTERS
    # ----------------------------------------

    log("\n=== BEST MATCHES ===\n")

    for job in best_matches:
        try:
            log(f"{job.get('company', 'Unknown')}: {job.get('title', 'Unknown')}")
            log(f"Match score: {job.get('match_score')}%")
            log(f"Apply → {job.get('apply_url', 'N/A')}\n")

            generate_cover_letter(
                job,
                profile_keywords=profile.get("skills", [])
            )
        except Exception as e:
            log(f"❌ Cover letter failed for {job.get('title')}: {e}")
            continue

    log(f"\n✅ Best matches processed: {len(best_matches)}")

# Alias for UI dashboard compatibility
def run_auto_apply_pipeline():
    main()

# ============================================
# ENTRY POINT
# ============================================

if __name__ == "__main__":
    main()
