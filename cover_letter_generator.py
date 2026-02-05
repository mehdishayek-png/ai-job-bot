import os
import json
from openai import OpenAI

# ============================================
# CONFIG
# ============================================

OUTPUT_DIR = "output/cover_letters"
CACHE_FILE = "data/cover_letter_cache.json"

OPENROUTER_API_KEY = "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"

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_API_KEY
)

MODEL = "mistralai/mistral-7b-instruct"

os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs("data", exist_ok=True)

# ============================================
# LOAD CACHE
# ============================================

if os.path.exists(CACHE_FILE):

    try:
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            cover_cache = json.load(f)

    except:
        print("⚠️ Cover cache corrupted — resetting")
        cover_cache = {}

else:
    cover_cache = {}

# ============================================
# WORD COUNT
# ============================================

def word_count(text):
    return len(text.split())

# ============================================
# GENERATOR
# ============================================

def generate_cover_letter(job):

    title = job.get("title", "Unknown Role")
    company = job.get("company", "Hiring Team")

    job_id = title + company

    # ============================================
    # CACHE CHECK
    # ============================================

    if job_id in cover_cache:

        print("⚡ Using cached cover letter")

        letter = cover_cache[job_id]

    else:

        print("Generating cover letter...")

        profile_text = """
Customer Operations and Product Operations specialist
with SaaS experience across onboarding, support,
incident triage, and CX tooling like Zendesk and Okta.
"""

        prompt = f"""
Write a concise, human cover letter.

Guidelines:

- 2 short paragraphs
- Under 150 words
- Conversational tone
- No placeholders
- Focus on candidate fit

Candidate:
{profile_text}

Role:
{title}

Company:
{company}
"""

        try:

            response = client.chat.completions.create(
                model=MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                max_tokens=400
            )

            letter = response.choices[0].message.content.strip()

        except Exception as e:

            print(f"❌ API failed → {e}\n")
            return

        if not letter:
            print("❌ Empty response — skipping\n")
            return

        # ---------- HARD CAP 150 ----------

        wc = word_count(letter)

        if wc > 150:

            print(f"⚠️ Length {wc} — trimming to 150")

            words = letter.split()
            letter = " ".join(words[:150])

        # ---------- STORE IN CACHE ----------

        cover_cache[job_id] = letter

        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(cover_cache, f, indent=2)

    # ============================================
    # SAFE FILENAME
    # ============================================

    safe_title = "".join(
        c for c in title if c.isalnum() or c in " _-"
    ).replace(" ", "_")[:80]

    safe_company = "".join(
        c for c in company if c.isalnum() or c in " _-"
    ).replace(" ", "_")[:40]

    file_path = os.path.join(
        OUTPUT_DIR,
        f"{safe_company}__{safe_title}.txt"
    )

    # ============================================
    # SAVE FILE
    # ============================================

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(letter)

    print(f"✅ Saved → {file_path}\n")
