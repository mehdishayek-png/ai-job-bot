import os
import json
import requests
from dotenv import load_dotenv

print("SCRIPT STARTED")
print("JOBBOT BATCH ENGINE STARTED")

# ============================================
# LOAD API KEY - STREAMLIT COMPATIBLE
# ============================================

# Try Streamlit secrets first, then fall back to .env
try:
    import streamlit as st
    API_KEY = st.secrets["OPENROUTER_API_KEY"]
except (ImportError, KeyError, AttributeError):
    load_dotenv()
    API_KEY = os.getenv("OPENROUTER_API_KEY")

if not API_KEY:
    print("ERROR: OPENROUTER_API_KEY not found")
    exit(1)

print("API KEY FOUND")

MODEL = "qwen/qwen-2.5-7b-instruct"
BASE_URL = "https://openrouter.ai/api/v1/chat/completions"

DATA_DIR = "data"
JOBS_DIR = "jobs"
OUTPUT_DIR = "output"

MATCH_PROMPT_FILE = os.path.join(DATA_DIR, "match_prompt.txt")
PROFILE_FILE = os.path.join(DATA_DIR, "profile.json")
COVER_PROMPT_FILE = os.path.join(DATA_DIR, "cover_prompt.txt")

APPLY_THRESHOLD = 70

os.makedirs(OUTPUT_DIR, exist_ok=True)


def call_llm(prompt):
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.2
    }

    try:
        response = requests.post(BASE_URL, headers=headers, json=payload)

        if response.status_code != 200:
            print("API ERROR:", response.text)
            return None

        data = response.json()
        return data["choices"][0]["message"]["content"]
        
    except Exception as e:
        print(f"LLM call failed: {str(e)}")
        return None


# Load base files
with open(MATCH_PROMPT_FILE, "r", encoding="utf-8") as f:
    base_prompt = f.read()

with open(PROFILE_FILE, "r", encoding="utf-8") as f:
    profile_data = f.read()

with open(COVER_PROMPT_FILE, "r", encoding="utf-8") as f:
    cover_template = f.read()


job_files = os.listdir(JOBS_DIR)

if not job_files:
    print("No jobs found in jobs folder.")
    exit(0)


# ======================
# MAIN PIPELINE LOOP
# ======================

for job_file in job_files:

    print("\nProcessing:", job_file)

    job_path = os.path.join(JOBS_DIR, job_file)

    with open(job_path, "r", encoding="utf-8") as f:
        job_text = f.read()

    # ===== MATCHING =====

    match_prompt = base_prompt + "\n\nJOB DESCRIPTION:\n" + job_text
    match_result = call_llm(match_prompt)
    
    if not match_result:
        print("Match call failed - skipping job")
        continue

    match_output_file = os.path.join(
        OUTPUT_DIR,
        job_file.replace(".txt", "_match.json")
    )

    with open(match_output_file, "w", encoding="utf-8") as f:
        f.write(match_result)

    print("Match saved:", match_output_file)

    # ===== FILTERING =====

    try:
        match_json = json.loads(match_result)
        score = int(match_json.get("match_score", 0))
    except:
        print("Invalid match JSON – skipping job.")
        continue

    if score < APPLY_THRESHOLD:
        print(f"Score too low ({score}) – skipping application.")
        continue

    print(f"Score accepted ({score}) – generating cover letter.")

    # ===== COVER LETTER =====

    cover_prompt = cover_template.replace("{{PROFILE}}", profile_data).replace("{{JOB}}", job_text)

    cover_result = call_llm(cover_prompt)
    
    if not cover_result:
        print("Cover letter call failed - skipping")
        continue

    cover_output_file = os.path.join(
        OUTPUT_DIR,
        job_file.replace(".txt", "_cover.txt")
    )

    with open(cover_output_file, "w", encoding="utf-8") as f:
        f.write(cover_result)

    print("Cover letter saved:", cover_output_file)


print("\nBATCH COMPLETE")
