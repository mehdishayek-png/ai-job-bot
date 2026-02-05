import json
from openai import OpenAI

# ============================================
# CONFIG
# ============================================

JOBS_FILE = "data/jobs.json"
PROFILE_FILE = "data/profile.json"

MATCH_THRESHOLD = 60
MAX_MATCHES = 10

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key="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"
)

MODEL = "openrouter/auto"

# ============================================
# LOAD DATA
# ============================================

with open(JOBS_FILE, "r", encoding="utf-8") as f:
    jobs = json.load(f)

with open(PROFILE_FILE, "r", encoding="utf-8") as f:
    profile = json.load(f)

# ============================================
# BUILD PROFILE TEXT
# ============================================

profile_text = f"""
Name: {profile.get("name")}
Headline: {profile.get("headline")}

Skills:
{", ".join(profile.get("skills", []))}

Tools:
{", ".join(profile.get("tools", []))}

Industries:
{", ".join(profile.get("industries", []))}

Preferred Roles:
{", ".join(profile.get("preferred_roles", []))}
"""

# ============================================
# SEMANTIC SCORING FUNCTION
# ============================================

def semantic_score(job):

    job_text = f"""
Title: {job.get("title")}

Description:
{job.get("summary")}
"""

    prompt = f"""
You are an AI job matching engine.

Score how well this candidate matches the job from 0–100.

Consider:

- Role alignment
- Skills overlap
- Tools overlap
- Industry relevance
- Career trajectory fit

Return ONLY a number.

CANDIDATE PROFILE:
{profile_text}

JOB:
{job_text}
"""

    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "user", "content": prompt}
        ],
        temperature=0,
        max_tokens=5
    )

    try:
        score = int(response.choices[0].message.content.strip())
    except:
        score = 0

    return score

# ============================================
# SCORE JOBS
# ============================================

scored_jobs = []

print("\nScoring jobs semantically...\n")

for job in jobs:

    score = semantic_score(job)

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

top_jobs = scored_jobs[:MAX_MATCHES]

# ============================================
# OUTPUT
# ============================================

print("\n=== SEMANTIC MATCH RESULTS ===\n")

for job in top_jobs:

    print(f"{job.get('company','Unknown')}: {job['title']}")
    print(f"Match score: {job['match_score']}%")
    print(f"Apply → {job['apply_url']}\n")

print(f"Top matches found: {len(top_jobs)}")
