import pdfplumber
import json
import os
import re
from openai import OpenAI
from dotenv import load_dotenv

# =========================
# LOAD API KEY
# =========================

load_dotenv()
client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENROUTER_API_KEY"),
)

MODEL = "mistralai/mistral-7b-instruct"

# =========================
# TEXT HELPERS
# =========================

def extract_text(pdf_path):
    raw = ""
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            raw += (page.extract_text() or "") + "\n"
    return raw


def extract_name(lines):
    for line in lines[:5]:
        words = line.split()
        if 2 <= len(words) <= 4 and all(w.isalpha() for w in words):
            return line.title()
    return "Candidate"


def extract_headline(lines):
    for line in lines[1:8]:
        if "@" in line or "http" in line.lower():
            continue
        if 3 <= len(line.split()) <= 12:
            return line.strip()
    return ""

# =========================
# LLM SKILL EXTRACTION
# =========================

def extract_skills_llm(text):

    prompt = f"""
Extract professional skills from this resume.

Rules:
- Return JSON list only
- No duplicates
- Include tools, domains, programming, soft skills

Resume:
{text[:6000]}
"""

    try:
        res = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            max_tokens=300,
        )

        skills = json.loads(res.choices[0].message.content.strip())
        return sorted(set(skills))

    except Exception:
        return []

# =========================
# MAIN BUILDER
# =========================

def build_profile(pdf_path, output_path):

    raw_text = extract_text(pdf_path)
    lines = [l.strip() for l in raw_text.split("\n") if l.strip()]

    name = extract_name(lines)
    headline = extract_headline(lines)
    skills = extract_skills_llm(raw_text)

    profile = {
        "name": name,
        "headline": headline,
        "skills": skills,
    }

    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    with open(output_path, "w") as f:
        json.dump(profile, f, indent=2)

    return profile
