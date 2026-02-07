import json
import os
from openai import OpenAI
from dotenv import load_dotenv

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

# ============================================
# CONFIG
# ============================================

JOBS_FILE = "data/jobs.json"
PROFILE_FILE = "data/profile.json"

MATCH_THRESHOLD = 60
MAX_MATCHES = 10

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=api_key  # Use validated API key instead of hardcoded one
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

    try:
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
        
    except Exception as e:
        print(f"❌ Scoring failed for {job.get('title')}: {str(e)}")
        return 0

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
