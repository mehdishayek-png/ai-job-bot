import json
import os
import hashlib
from openai import OpenAI
from dotenv import load_dotenv
from cover_letter_generator import generate_cover_letter

load_dotenv()

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENROUTER_API_KEY"),
)

MODEL = "mistralai/mistral-7b-instruct"
MATCH_THRESHOLD = 70
MAX_MATCHES = 5


def profile_hash(profile):
    text = json.dumps(profile, sort_keys=True)
    return hashlib.md5(text.encode()).hexdigest()


def semantic_score(job, profile_text):

    prompt = f"""
Score match 0–100.

Candidate:
{profile_text}

Job:
{job["title"]}
{job["summary"]}

Return number only.
"""

    res = client.chat.completions.create(
        model=MODEL,
        messages=[{"role":"user","content":prompt}],
        temperature=0,
        max_tokens=5,
    )

    try:
        return int(res.choices[0].message.content.strip())
    except:
        return 0


def run_pipeline(profile_file, jobs_file, session_dir):

    with open(profile_file) as f:
        profile = json.load(f)

    with open(jobs_file) as f:
        jobs = json.load(f)

    p_hash = profile_hash(profile)

    cache_file = os.path.join(session_dir,"semantic_cache.json")
    cache = {}

    if os.path.exists(cache_file):
        cache = json.load(open(cache_file))

    profile_text = f"""
Name: {profile['name']}
Headline: {profile['headline']}
Skills: {', '.join(profile['skills'])}
"""

    matches = []

    for job in jobs:

        key = f"{p_hash}_{job['company']}_{job['title']}"

        if key in cache:
            score = cache[key]
        else:
            score = semantic_score(job, profile_text)
            cache[key] = score

        if score >= MATCH_THRESHOLD:
            job["match_score"] = score
            matches.append(job)

    matches.sort(key=lambda x:x["match_score"],reverse=True)
    matches = matches[:MAX_MATCHES]

    json.dump(cache, open(cache_file,"w"), indent=2)

    letters_dir = os.path.join(session_dir,"letters")
    os.makedirs(letters_dir,exist_ok=True)

    for job in matches:
        generate_cover_letter(job, profile, letters_dir)

    return matches
