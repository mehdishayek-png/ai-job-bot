import os
import json
from openai import OpenAI
from dotenv import load_dotenv
import datetime

# ============================================
# LOAD ENV (API KEY) - STREAMLIT COMPATIBLE
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
    error_msg = "❌ OPENROUTER_API_KEY not found. Add it to Streamlit secrets or .env file."
    try:
        import streamlit as st
        st.error(error_msg)
        st.stop()
    except ImportError:
        raise ValueError(error_msg)

# ============================================
# DEFAULTS (used only when run from CLI)
# ============================================

DEFAULT_OUTPUT_DIR = "output/cover_letters"
DEFAULT_CACHE_FILE = "data/cover_letter_cache.json"
LOG_FILE = "logs.txt"

# ============================================
# OPENROUTER CLIENT
# ============================================

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=api_key,
)

MODEL = "mistralai/mistral-7b-instruct"

# ============================================
# LOGGER
# ============================================

def log(message):
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"{datetime.datetime.now()} → {message}\n")
    except Exception:
        pass

# ============================================
# CACHE HELPERS — loaded fresh per call, NOT at import
# ============================================

def _load_cache(cache_file):
    """Load cache from disk each time to avoid shared module-level state."""
    if not os.path.exists(cache_file):
        return {}
    try:
        with open(cache_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _save_cache(cache, cache_file):
    os.makedirs(os.path.dirname(cache_file) or ".", exist_ok=True)
    with open(cache_file, "w", encoding="utf-8") as f:
        json.dump(cache, f, indent=2)

# ============================================
# GENERATOR — all paths are parameters
# ============================================

def generate_cover_letter(
    job,
    profile_keywords=None,
    output_dir=None,
    cache_file=None,
):
    """
    Generate a cover letter for a single job.

    All file paths are parameters so each Streamlit session
    can point to its own isolated directory.
    """
    output_dir = output_dir or DEFAULT_OUTPUT_DIR
    cache_file = cache_file or DEFAULT_CACHE_FILE

    os.makedirs(output_dir, exist_ok=True)

    title = job.get("title", "Role")
    company = job.get("company", "Hiring Team")
    description = job.get("summary", "")
    job_id = f"{company}_{title}"

    log(f"Generating cover letter → {job_id}")

    # ---- Cache check (loaded fresh each call) ----
    cache = _load_cache(cache_file)
    if job_id in cache:
        log("Skipped (cached)")
        return cache[job_id]

    # ---- Profile context ----
    skills_text = ", ".join(profile_keywords or [])
    profile_text = (
        f"Candidate skills include: {skills_text}\n"
        "Background in SaaS support, onboarding, incident triage, "
        "and product operations."
    )

    # ---- Prompt ----
    prompt = f"""Write a concise, human cover letter.

Rules:
- 2 paragraphs
- 60–76 words total
- Natural tone
- No placeholders
- No fake metrics
- Tailored to job

Candidate:
{profile_text}

Job Title: {title}
Company: {company}
Job Description:
{description}
"""

    # ---- API call ----
    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=200,
        )
        letter = response.choices[0].message.content.strip()
    except Exception as e:
        log(f"API ERROR → {e}")
        try:
            import streamlit as st
            st.error(f"Cover Letter API Error: {e}")
        except ImportError:
            pass
        return None

    # ---- Word count guard ----
    words = letter.split()
    if len(words) > 150:
        letter = " ".join(words[:150])
    if len(words) < 50:
        log(f"Too short ({len(words)}) — skipped")
        return None

    # ---- Save file ----
    safe_title = "".join(
        c for c in title if c.isalnum() or c in " _-"
    ).replace(" ", "_")
    file_path = os.path.join(output_dir, f"{company}__{safe_title}.txt")

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(letter)

    log(f"Saved → {file_path}")

    # ---- Update cache ----
    cache[job_id] = file_path
    _save_cache(cache, cache_file)

    return file_path

# ============================================
# TEST RUN
# ============================================

if __name__ == "__main__":
    sample_job = {
        "title": "Customer Success Manager",
        "company": "TestCorp",
        "summary": "Manage enterprise SaaS customers and onboarding.",
    }
    result = generate_cover_letter(
        sample_job,
        profile_keywords=["customer success", "saas", "zendesk", "automation"],
    )
    print(f"Result: {result}")
