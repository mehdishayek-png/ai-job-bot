import json
import os
import re
import time
from openai import OpenAI
from dotenv import load_dotenv
from cover_letter_generator import generate_cover_letter

# ============================================
# LOAD API KEY - STREAMLIT COMPATIBLE
# ============================================

try:
    import streamlit as st
    api_key = st.secrets.get("OPENROUTER_API_KEY", None)
except (ImportError, KeyError, AttributeError):
    api_key = None

if not api_key:
    load_dotenv()
    api_key = os.getenv("OPENROUTER_API_KEY")

if not api_key:
    error_msg = "❌ OPENROUTER_API_KEY not found"
    try:
        import streamlit as st
        st.error(error_msg)
        st.stop()
    except ImportError:
        raise ValueError(error_msg)

# ============================================
# OPENROUTER CLIENT
# ============================================

MODEL = "mistralai/mistral-7b-instruct"

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=api_key,
)

# ============================================
# DEFAULTS (used only when run from CLI)
# ============================================

DEFAULT_PROFILE_FILE = "data/profile.json"
DEFAULT_JOBS_FILE = "data/jobs.json"
DEFAULT_MATCHES_FILE = "data/matched_jobs.json"
DEFAULT_CACHE_FILE = "data/semantic_cache.json"
DEFAULT_LOG_FILE = "data/run_log.txt"
DEFAULT_LETTERS_DIR = "output/cover_letters"

MATCH_THRESHOLD = 70
MAX_APPLICATIONS = 5
MAX_RETRIES = 3
RETRY_DELAY = 2
API_RATE_LIMIT_DELAY = 0.5

# ============================================
# LOGGER (path set per-run)
# ============================================

_log_file = DEFAULT_LOG_FILE


def log(message):
    print(message)
    try:
        with open(_log_file, "a", encoding="utf-8") as f:
            f.write(message + "\n")
    except Exception:
        pass

# ============================================
# HELPERS
# ============================================

def _load_cache(cache_file):
    if not os.path.exists(cache_file):
        return {}
    try:
        with open(cache_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}

# ============================================
# SEMANTIC SCORING
# ============================================

def semantic_score(job, profile_text, retry_count=0):
    title = job.get("title", "Unknown")
    description = job.get("summary", "")[:500]

    if not description:
        log(f"⚠️ Skipping {title} — no description")
        return 0

    prompt = f"""Rate match between candidate and job from 0–100.

Candidate:
{profile_text}

Job Title: {title}
Job Description:
{description}

Return ONLY a number."""

    try:
        time.sleep(API_RATE_LIMIT_DELAY)
        response = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            max_tokens=5,
            timeout=30,
        )
        score_text = response.choices[0].message.content.strip()
        numbers = re.findall(r"\d+", score_text)
        if numbers:
            return max(0, min(100, int(numbers[0])))
        log(f"⚠️ Non-numeric response for {title}: {score_text}")
        return 0

    except Exception as e:
        error_msg = str(e)
        if retry_count < MAX_RETRIES and (
            "rate_limit" in error_msg.lower() or "timeout" in error_msg.lower()
        ):
            log(f"⚠️ Retry {retry_count+1}/{MAX_RETRIES} for {title}")
            time.sleep(RETRY_DELAY * (retry_count + 1))
            return semantic_score(job, profile_text, retry_count + 1)

        log(f"❌ Scoring API error for {title}: {error_msg}")
        return 0

# ============================================
# MAIN PIPELINE — ALL PATHS ARE PARAMETERS
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
    Run the full matching + cover-letter pipeline.

    Every path is a parameter so each Streamlit session
    can use its own isolated directory.
    """
    global _log_file

    profile_file = profile_file or DEFAULT_PROFILE_FILE
    jobs_file = jobs_file or DEFAULT_JOBS_FILE
    matches_file = matches_file or DEFAULT_MATCHES_FILE
    cache_file = cache_file or DEFAULT_CACHE_FILE
    log_file = log_file or DEFAULT_LOG_FILE
    letters_dir = letters_dir or DEFAULT_LETTERS_DIR

    _log_file = log_file
    os.makedirs(os.path.dirname(log_file) or ".", exist_ok=True)

    def progress(msg):
        log(msg)
        if progress_callback:
            try:
                progress_callback(msg)
            except Exception:
                pass

    # Reset log
    try:
        open(log_file, "w").close()
    except Exception:
        pass

    progress("=== PROFILE-DRIVEN AUTO APPLY ===")

    # ---- Validate profile ----
    if not os.path.exists(profile_file):
        progress("❌ Profile file not found. Please create a profile first.")
        return {"status": "error", "message": "No profile"}

    try:
        with open(profile_file, "r", encoding="utf-8") as f:
            profile = json.load(f)
        if not profile.get("skills"):
            progress("❌ Profile has no skills.")
            return {"status": "error", "message": "No skills in profile"}
    except Exception as e:
        progress(f"❌ Failed to load profile: {e}")
        return {"status": "error", "message": str(e)}

    # ---- Fetch jobs if needed (pass session paths!) ----
    if not os.path.exists(jobs_file):
        progress("No jobs file found. Fetching jobs from RSS feeds...")
        try:
            import job_fetcher
            job_fetcher.main(
                output_path=jobs_file,
                profile_path=profile_file,
            )
            progress("Job fetch completed.")
        except Exception as e:
            progress(f"Job fetch error: {e}")

    if not os.path.exists(jobs_file):
        progress("❌ No jobs available. Sources may be temporarily down.")
        return {"status": "error", "message": "No jobs"}

    try:
        with open(jobs_file, "r", encoding="utf-8") as f:
            jobs = json.load(f)
        if not jobs:
            progress("Jobs file is empty — no jobs matched your keywords.")
            return {"status": "error", "message": "Empty jobs file"}
    except Exception as e:
        progress(f"❌ Failed to load jobs: {e}")
        return {"status": "error", "message": str(e)}

    # ---- Build profile text ----
    profile_text = (
        f"Name: {profile.get('name', 'Candidate')}\n"
        f"Headline: {profile.get('headline', 'Professional')}\n"
        f"Skills: {', '.join(profile.get('skills', [])[:15])}"
    )

    semantic_cache = _load_cache(cache_file)
    scored_jobs = []

    progress(f"Scoring {len(jobs)} jobs semantically...")

    # ---- Scoring loop ----
    for i, job in enumerate(jobs, 1):
        try:
            job_id = f"{job.get('company', 'Unknown')}_{job.get('title', 'Unknown')}"
            progress(f"[{i}/{len(jobs)}] {job.get('title', 'Unknown')}")

            if job_id in semantic_cache:
                score = semantic_cache[job_id]
                progress(f"  ⚡ Cached score: {score}")
            else:
                score = semantic_score(job, profile_text)
                semantic_cache[job_id] = score
                progress(f"  🧠 API score: {score}")

            if score >= MATCH_THRESHOLD:
                job["match_score"] = score
                scored_jobs.append(job)
        except Exception as e:
            progress(f"❌ Error processing job {i}: {e}")
            continue

    # ---- Save cache ----
    try:
        os.makedirs(os.path.dirname(cache_file) or ".", exist_ok=True)
        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump(semantic_cache, f, indent=2)
    except Exception as e:
        progress(f"❌ Cache save failed: {e}")

    if not scored_jobs:
        progress(f"❌ No jobs scored above {MATCH_THRESHOLD}%.")
        # Save empty matches so the UI knows we ran
        try:
            with open(matches_file, "w", encoding="utf-8") as f:
                json.dump([], f)
        except Exception:
            pass
        return {"status": "no_matches", "total_scored": len(jobs)}

    # ---- Sort & limit ----
    scored_jobs.sort(key=lambda x: x.get("match_score", 0), reverse=True)
    best_matches = scored_jobs[:MAX_APPLICATIONS]

    try:
        os.makedirs(os.path.dirname(matches_file) or ".", exist_ok=True)
        with open(matches_file, "w", encoding="utf-8") as f:
            json.dump(best_matches, f, indent=2)
    except Exception as e:
        progress(f"❌ Matches save failed: {e}")

    # ---- Generate cover letters (pass session paths!) ----
    progress(f"\n=== GENERATING COVER LETTERS FOR {len(best_matches)} MATCHES ===")

    cl_cache_file = os.path.join(
        os.path.dirname(cache_file), "cover_letter_cache.json"
    )

    for job in best_matches:
        try:
            progress(
                f"  {job.get('company')}: {job.get('title')} "
                f"({job.get('match_score')}%)"
            )
            generate_cover_letter(
                job,
                profile_keywords=profile.get("skills", []),
                output_dir=letters_dir,
                cache_file=cl_cache_file,
            )
        except Exception as e:
            progress(f"  ❌ Cover letter failed: {e}")
            continue

    progress(f"\n✅ Done — {len(best_matches)} matches processed.")
    return {
        "status": "success",
        "matches": len(best_matches),
        "total_scored": len(jobs),
    }

# ============================================
# CLI ENTRY POINT
# ============================================

def main():
    run_auto_apply_pipeline()


if __name__ == "__main__":
    main()
