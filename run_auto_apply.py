import json
import os
import subprocess
from openai import OpenAI
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

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

MODEL = "mistralai/mistral-7b-instruct"

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_API_KEY
)

os.makedirs("data", exist_ok=True)

# ============================================
# LOGGER
# ============================================

def log(message):

    print(message)

    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(message + "\n")

# Reset log each run
open(LOG_FILE, "w").close()

# ============================================
# ENSURE JOBS EXIST
# ============================================

if not os.path.exists(JOBS_FILE):

    log("No jobs file found. Running job fetcher...\n")

    subprocess.run(["python", "job_fetcher.py"])

    if not os.path.exists(JOBS_FILE):
        log("Job fetch failed. Exiting.")
        exit()

# ============================================
# LOAD DATA
# ============================================

with open(PROFILE_FILE, "r", encoding="utf-8") as f:
    profile = json.load(f)

with open(JOBS_FILE, "r", encoding="utf-8") as f:
    jobs = json.load(f)

# ============================================
# SAFE CACHE LOAD
# ============================================

semantic_cache = {}

if os.path.exists(CACHE_FILE):

    try:
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

            if isinstance(data, dict):
                semantic_cache = data
            else:
                semantic_cache = {}

    except:
        semantic_cache = {}

# ============================================
# PROFILE TEXT
# ============================================

profile_text = f"""
Name: {profile.get('name')}

Headline: {profile.get('headline')}

Skills:
{", ".join(profile.get('skills', []))}
"""

# ============================================
# SEMANTIC SCORING
# ============================================

def semantic_score(job):

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

# ============================================
# RUN MATCHING
# ============================================

log("\n=== PROFILE DRIVEN AUTO APPLY ===\n")

shortlisted_jobs = jobs

log(f"Shortlisted jobs: {len(shortlisted_jobs)}\n")

scored_jobs = []

log("Scoring jobs semantically...\n")

for i, job in enumerate(shortlisted_jobs, 1):

    job_id = job.get("title", "") + job.get("company", "")

    log(f"[{i}/{len(shortlisted_jobs)}] {job['title']}")

    if job_id in semantic_cache:

        score = semantic_cache[job_id]
        log(f"⚡ Cached score: {score}")

    else:

        try:
            score = semantic_score(job)
            semantic_cache[job_id] = score
            log(f"🧠 API score: {score}")

        except Exception as e:
            log(f"❌ Semantic scoring failed: {e}")
            score = 0

    if score >= MATCH_THRESHOLD:
        job["match_score"] = score
        scored_jobs.append(job)

# ============================================
# SAVE CACHE
# ============================================

with open(CACHE_FILE, "w", encoding="utf-8") as f:
    json.dump(semantic_cache, f, indent=2)

log("\nSemantic cache updated.")

# ============================================
# SORT BEST MATCHES
# ============================================

scored_jobs.sort(
    key=lambda x: x["match_score"],
    reverse=True
)

best_matches = scored_jobs[:MAX_APPLICATIONS]

# ============================================
# SAVE MATCHES
# ============================================

with open(MATCHES_FILE, "w", encoding="utf-8") as f:
    json.dump(best_matches, f, indent=2)

# ============================================
# DISPLAY + COVER LETTERS
# ============================================

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
