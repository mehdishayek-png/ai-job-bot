import json
import os
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

    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(message + "\n")

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

    except:
        return {}

# ============================================
# SEMANTIC SCORING
# ============================================

def semantic_score(job, profile_text):

    title = job.get("title", "")
    description = job.get("summary", "")

    prompt = f"""
Rate match between candidate and job from 0–100.

Candidate:
{profile_text}

Job Title:
{title}

Job Description:
{description}

Return ONLY a number.
"""

    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            max_tokens=5
        )

        score_text = response.choices[0].message.content.strip()

        try:
            return int(score_text)
        except:
            return 0
            
    except Exception as e:
        log(f"❌ Scoring API error: {str(e)}")
        try:
            import streamlit as st
            st.warning(f"Scoring failed for {job.get('title')}: {str(e)}")
        except ImportError:
            pass
        return 0

# ============================================
# MAIN RUNNER
# ============================================

def main():

    # Reset log file each run
    open(LOG_FILE, "w").close()

    log("\n=== PROFILE DRIVEN AUTO APPLY ===\n")

    # ----------------------------------------
    # ENSURE JOBS EXIST
    # ----------------------------------------

    if not os.path.exists(JOBS_FILE):

        log("No jobs file found. Running job fetcher...\n")

        try:
            # Import and run job_fetcher directly instead of subprocess
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
                st.warning("No jobs found. Job sources may be unavailable or filtered out all results.")
            except ImportError:
                pass
            return

    # ----------------------------------------
    # LOAD DATA
    # ----------------------------------------

    with open(PROFILE_FILE, "r", encoding="utf-8") as f:
        profile = json.load(f)

    with open(JOBS_FILE, "r", encoding="utf-8") as f:
        jobs = json.load(f)

    semantic_cache = load_cache()

    # ----------------------------------------
    # PROFILE TEXT
    # ----------------------------------------

    profile_text = f"""
Name: {profile.get('name')}

Headline: {profile.get('headline')}

Skills:
{", ".join(profile.get('skills', []))}
"""

    shortlisted_jobs = jobs

    log(f"Shortlisted jobs: {len(shortlisted_jobs)}\n")

    scored_jobs = []

    log("Scoring jobs semantically...\n")

    # ----------------------------------------
    # SCORING LOOP
    # ----------------------------------------

    for i, job in enumerate(shortlisted_jobs, 1):

        job_id = job.get("title", "") + job.get("company", "")

        log(f"[{i}/{len(shortlisted_jobs)}] {job['title']}")

        if job_id in semantic_cache:

            score = semantic_cache[job_id]
            log(f"⚡ Cached score: {score}")

        else:

            try:
                score = semantic_score(job, profile_text)
                semantic_cache[job_id] = score
                log(f"🧠 API score: {score}")

            except Exception as e:
                log(f"❌ Semantic scoring failed: {e}")
                score = 0

        if score >= MATCH_THRESHOLD:
            job["match_score"] = score
            scored_jobs.append(job)

    # ----------------------------------------
    # SAVE CACHE
    # ----------------------------------------

    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(semantic_cache, f, indent=2)

    log("\nSemantic cache updated.")

    # ----------------------------------------
    # SORT BEST MATCHES
    # ----------------------------------------

    scored_jobs.sort(
        key=lambda x: x["match_score"],
        reverse=True
    )

    best_matches = scored_jobs[:MAX_APPLICATIONS]

    # ----------------------------------------
    # SAVE MATCHES
    # ----------------------------------------

    with open(MATCHES_FILE, "w", encoding="utf-8") as f:
        json.dump(best_matches, f, indent=2)

    # ----------------------------------------
    # DISPLAY + COVER LETTERS
    # ----------------------------------------

    log("\n=== BEST MATCHES ===\n")

    for job in best_matches:

        log(f"{job.get('company')}: {job.get('title')}")
        log(f"Match score: {job.get('match_score')}%")
        log(f"Apply → {job.get('apply_url')}\n")

        try:
            generate_cover_letter(
                job,
                profile_keywords=profile.get("skills", [])
            )
        except Exception as e:
            log(f"❌ Cover letter failed: {e}")

    log(f"\nBest matches processed: {len(best_matches)}")

# Alias for UI dashboard compatibility
def run_auto_apply_pipeline():
    main()

# ============================================
# ENTRY POINT
# ============================================

if __name__ == "__main__":
    main()
