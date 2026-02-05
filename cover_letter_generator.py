import os
import json
from openai import OpenAI
from dotenv import load_dotenv
import datetime

# ============================================
# LOAD ENV (API KEY FIX) - STREAMLIT COMPATIBLE
# ============================================

# Try Streamlit secrets first, then fall back to .env
try:
    import streamlit as st
    api_key = st.secrets["OPENROUTER_API_KEY"]
except (ImportError, KeyError, AttributeError):
    # Fall back to .env for local development
    load_dotenv()
    api_key = os.getenv("OPENROUTER_API_KEY")

# Validate API key is present
if not api_key:
    error_msg = "❌ OPENROUTER_API_KEY not found. Add it to Streamlit secrets or .env file."
    try:
        import streamlit as st
        st.error(error_msg)
        st.stop()
    except ImportError:
        raise ValueError(error_msg)

# ============================================
# CONFIG
# ============================================

OUTPUT_DIR = "output/cover_letters"
CACHE_FILE = "data/cover_letter_cache.json"
LOG_FILE = "logs.txt"

os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs("data", exist_ok=True)

# ============================================
# LOGGER
# ============================================

def log(message):

    with open(LOG_FILE, "a", encoding="utf-8") as f:

        f.write(
            f"{datetime.datetime.now()} → {message}\n"
        )

# ============================================
# SAFE CACHE LOAD
# ============================================

if os.path.exists(CACHE_FILE):

    try:
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            cache = json.load(f)

        if not isinstance(cache, dict):
            cache = {}

    except:
        cache = {}

else:
    cache = {}

# ============================================
# OPENROUTER CLIENT
# ============================================

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=api_key  # Use the validated API key from above
)

MODEL = "mistralai/mistral-7b-instruct"

# ============================================
# GENERATOR
# ============================================

def generate_cover_letter(job, profile_keywords=None):

    title = job.get("title", "Role")
    company = job.get("company", "Hiring Team")
    description = job.get("summary", "")

    job_id = f"{company}_{title}"

    log(f"Generating cover letter → {job_id}")

    # ----------------------------------------
    # CACHE CHECK
    # ----------------------------------------

    if job_id in cache:

        log("Skipped (cached)")
        print("⚡ Cached — skipping")
        return

    # ----------------------------------------
    # PROFILE CONTEXT
    # ----------------------------------------

    skills_text = ", ".join(profile_keywords or [])

    profile_text = f"""
Candidate skills include:
{skills_text}

Background in SaaS support, onboarding,
incident triage, and product operations.
"""

    # ----------------------------------------
    # PROMPT
    # ----------------------------------------

    prompt = f"""
Write a concise, human cover letter.

Rules:

- 2 paragraphs
- 60–76 words total
- Natural tone
- No placeholders
- No fake metrics
- Tailored to job

Candidate:
{profile_text}

Job Title:
{title}

Company:
{company}

Job Description:
{description}
"""

    # ----------------------------------------
    # API CALL WITH ERROR HANDLING
    # ----------------------------------------

    try:

        response = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=200
        )

        letter = response.choices[0].message.content.strip()

    except Exception as e:

        log(f"API ERROR → {str(e)}")
        print(f"❌ API Error: {e}")
        
        # Show error in Streamlit if available
        try:
            import streamlit as st
            st.error(f"Cover Letter API Error: {str(e)}")
        except ImportError:
            pass
            
        return

    # ----------------------------------------
    # WORD COUNT CHECK
    # ----------------------------------------

    words = letter.split()
    word_count = len(words)

    if word_count > 150:
        letter = " ".join(words[:150])

    if word_count < 50:
        log(f"Too short ({word_count}) — skipped")
        print(f"❌ Too short ({word_count})")
        return

    # ----------------------------------------
    # SAVE FILE
    # ----------------------------------------

    safe_title = "".join(
        c for c in title if c.isalnum() or c in " _-"
    ).replace(" ", "_")

    file_path = os.path.join(
        OUTPUT_DIR,
        f"{company}__{safe_title}.txt"
    )

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(letter)

    print(f"📝 Saved → {file_path}")
    log(f"Saved → {file_path}")

    # ----------------------------------------
    # UPDATE CACHE
    # ----------------------------------------

    cache[job_id] = True

    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(cache, f, indent=2)

# ============================================
# TEST RUN BLOCK
# ============================================

if __name__ == "__main__":

    print("Running cover letter generator test...\n")

    sample_job = {
        "title": "Customer Success Manager",
        "company": "TestCorp",
        "summary": "Manage enterprise SaaS customers and onboarding."
    }

    sample_keywords = [
        "customer success",
        "saas",
        "zendesk",
        "automation"
    ]

    generate_cover_letter(sample_job, sample_keywords)
