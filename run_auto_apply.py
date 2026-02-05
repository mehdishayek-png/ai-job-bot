import json
import os
from cover_letter_generator import generate_cover_letter
from openai import OpenAI

# ============================================
# CONFIG
# ============================================

MATCH_THRESHOLD = 40
MAX_APPLICATIONS = 15

JOBS_FILE = "data/jobs.json"
CACHE_FILE = "data/semantic_cache.json"

OPENROUTER_API_KEY = "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"   # keep your real key

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_API_KEY
)

MODEL = "openrouter/auto"

# ============================================
# LOAD JOBS
# ============================================

if not os.path.exists(JOBS_FILE):
    print("No jobs file found.")
    exit()

with open(JOBS_FILE, "r", encoding="utf-8") as f:
    jobs = json.load(f)

print("\n=== PROFILE DRIVEN AUTO APPLY ===\n")

# ============================================
# LOAD / INIT SEMANTIC CACHE (SAFE)
# ============================================

os.makedirs("data", exist_ok=True)

semantic_cache = {}

if os.path.exists(CACHE_FILE):

    try:
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            semantic_cache = json.load(f)

    except json.JSONDecodeError:
        print("⚠️ Cache file empty/corrupted — resetting...")
        semantic_cache = {}

# ============================================
# PROFILE TEXT (FOR SCORING)
# ============================================

profile_text = """
Customer Operations and Product Operations specialist
with SaaS experience across onboarding, support,
incident triage, workflow automation, and CX tooling
like Zendesk, Okta, and Slack.
"""

# ============================================
# SEMANTIC SCORING FUNCTION
# ============================================

def semantic_score(job):

    prompt = f"""
Score how well this candidate matches the job from 0–100.

Candidate:
{profile_text}

Job Title:
{job.get("title")}

Job Description:
{job.get("summary")}

Respond ONLY with a number.
"""

    response = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
        max_tokens=5
    )

    try:
        score = int(response.choices[0].message.content.strip())
    except:
        score = 0

    return score

# ============================================
# SHORTLIST JOBS (basic filter)
# ============================================

shortlisted_jobs = jobs   # using all jobs for now

print(f"Shortlisted jobs: {len(shortlisted_jobs)}\n")

# ============================================
# SEMANTIC SCORING + CACHE
# ============================================

scored_jobs = []

print("Scoring jobs semantically...\n")

for i, job in enumerate(shortlisted_jobs, 1):

    job_id = job.get("title", "") + job.get("company", "")

    print(f"[{i}/{len(shortlisted_jobs)}] {job['title']}")

    # ---------- CACHE CHECK ----------

    if job_id in semantic_cache:

        score = semantic_cache[job_id]
        print(f"⚡ Cached score: {score}")

    else:

        score = semantic_score(job)
        semantic_cache[job_id] = score

        print(f"🧠 API score: {score}")

    # ---------- MATCH FILTER ----------

    if score >= MATCH_THRESHOLD:
        job["match_score"] = score
        scored_jobs.append(job)

# ============================================
# SORT BEST MATCHES
# ============================================

scored_jobs.sort(
    key=lambda x: x["match_score"],
    reverse=True
)

top_jobs = scored_jobs[:MAX_APPLICATIONS]

print("\n=== BEST MATCHES ===\n")

for job in top_jobs:

    print(f"{job['company']}: {job['title']}")
    print(f"Match score: {job['match_score']}%")
    print(f"Apply → {job['apply_url']}\n")

    # ---------- GENERATE COVER LETTER ----------

    generate_cover_letter(job)

# ============================================
# SAVE CACHE
# ============================================

with open(CACHE_FILE, "w", encoding="utf-8") as f:
    json.dump(semantic_cache, f, indent=2)

print("\nSemantic cache updated.")

print(f"\nBest matches processed: {len(top_jobs)}")
