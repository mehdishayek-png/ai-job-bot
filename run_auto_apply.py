import json
import os
import hashlib
from openai import OpenAI
from dotenv import load_dotenv
from cover_letter_generator import generate_cover_letter

# ============================================
# LOAD API KEY
# ============================================

load_dotenv()

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENROUTER_API_KEY"),
)

MODEL = "mistralai/mistral-7b-instruct"

MATCH_THRESHOLD = 70
MAX_MATCHES = 5

# ============================================
# PROFILE HASH (for cache isolation)
# ============================================

def profile_hash(profile: dict) -> str:
    """
    Create a unique hash per profile so semantic
    scores never leak across users or resumes.
    """
    text = json.dumps(profile, sort_keys=True)
    return hashlib.md5(text.encode()).hexdigest()


# ============================================
# SEMANTIC SCORING
# ============================================

def semantic_score(job: dict, profile_text: str) -> int:

    prompt = f"""
Score match between candidate and job from 0–100.

Candidate:
{profile_text}

Job Title: {job.get("title")}
Job Description:
{job.get("summary")}

Return ONLY a number.
"""

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
            return max(0, min(100, int(digits)))

        return 0

    except Exception as e:
        print(f"Semantic scoring failed: {e}")
        return 0


# ============================================
# CORE PIPELINE (NEW ARCHITECTURE)
# ============================================

def run_pipeline(profile_file: str, jobs_file: str, session_dir: str):

    # ---- Load profile ----
    if not os.path.exists(profile_file):
        raise FileNotFoundError("Profile file missing")

    with open(profile_file, "r", encoding="utf-8") as f:
        profile = json.load(f)

    # ---- Load jobs ----
    if not os.path.exists(jobs_file):
        raise FileNotFoundError("Jobs file missing")

    with open(jobs_file, "r", encoding="utf-8") as f:
        jobs = json.load(f)

    if not jobs:
        return []

    # ---- Profile hash for cache isolation ----
    p_hash = profile_hash(profile)

    cache_file = os.path.join(session_dir, "semantic_cache.json")
    cache = {}

    if os.path.exists(cache_file):
        try:
            with open(cache_file, "r") as f:
                cache = json.load(f)
        except Exception:
            cache = {}

    # ---- Build profile text ----
    profile_text = f"""
Name: {profile.get("name","Candidate")}
Headline: {profile.get("headline","Professional")}

Skills:
{", ".join(profile.get("skills", []))}
"""

    matches = []

    # ---- Score jobs ----
    for job in jobs:

        job_id = f"{job.get('company')}_{job.get('title')}"
        cache_key = f"{p_hash}_{job_id}"

        if cache_key in cache:
            score = cache[cache_key]
        else:
            score = semantic_score(job, profile_text)
            cache[cache_key] = score

        if score >= MATCH_THRESHOLD:
            job["match_score"] = score
            matches.append(job)

    # ---- Sort + limit ----
    matches.sort(key=lambda x: x["match_score"], reverse=True)
    matches = matches[:MAX_MATCHES]

    # ---- Save cache ----
    os.makedirs(session_dir, exist_ok=True)

    with open(cache_file, "w") as f:
        json.dump(cache, f, indent=2)

    # ---- Generate cover letters ----
    letters_dir = os.path.join(session_dir, "cover_letters")
    os.makedirs(letters_dir, exist_ok=True)

    for job in matches:
        try:
            generate_cover_letter(job, profile, letters_dir)
        except Exception as e:
            print(f"Cover letter failed: {e}")

    return matches


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
    Wrapper to maintain compatibility with the
    existing Streamlit dashboard.

    The UI still calls this function name,
    so we forward execution to the new pipeline.
    """

    try:
        if progress_callback:
            progress_callback("Loading profile + jobs…")

        session_dir = os.path.dirname(profile_file)

        matches = run_pipeline(
            profile_file=profile_file,
            jobs_file=jobs_file,
            session_dir=session_dir,
        )

        # ---- Save matches if UI expects file ----
        if matches_file:
            os.makedirs(os.path.dirname(matches_file), exist_ok=True)
            with open(matches_file, "w") as f:
                json.dump(matches, f, indent=2)

        if progress_callback:
            progress_callback(f"Done — {len(matches)} matches found.")

        return {
            "status": "success",
            "matches": len(matches),
            "total_scored": len(matches),
        }

    except Exception as e:

        if progress_callback:
            progress_callback(f"Pipeline error: {e}")

        return {
            "status": "error",
            "message": str(e),
        }


# ============================================
# CLI ENTRY (OPTIONAL TEST)
# ============================================

if __name__ == "__main__":

    test_profile = "data/profile.json"
    test_jobs = "data/jobs.json"
    session_dir = "data/test_session"

    results = run_pipeline(
        profile_file=test_profile,
        jobs_file=test_jobs,
        session_dir=session_dir,
    )

    print(f"Matches found: {len(results)}")