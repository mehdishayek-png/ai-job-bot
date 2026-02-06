"""
Resume Parser v2
================
Extracts 8-12 high-signal skills that carry real weight in job matching.
No more dumping every keyword — only the ones that would actually
appear as requirements in job postings the candidate should target.
"""

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

try:
    import streamlit as st
    api_key = st.secrets.get("OPENROUTER_API_KEY")
except (ImportError, KeyError, AttributeError):
    api_key = os.getenv("OPENROUTER_API_KEY")

if not api_key:
    raise ValueError("OPENROUTER_API_KEY not found")

client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=api_key)
MODEL = "mistralai/mistral-7b-instruct"

# =========================
# TEXT EXTRACTION
# =========================

def extract_text(pdf_path):
    raw = ""
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            raw += (page.extract_text() or "") + "\n"
    return raw


def extract_name(lines):
    for line in lines[:5]:
        line = line.strip()
        if not line or len(line) < 3:
            continue
        skip = ['resume', 'cv', 'curriculum', 'vitae', 'contact',
                'email', 'phone', 'address', '@', 'http', 'www']
        if any(kw in line.lower() for kw in skip):
            continue
        words = line.split()
        if 2 <= len(words) <= 4:
            if all(re.match(r"^[A-Za-z\-']+$", w) for w in words):
                return line.title()
    return "Candidate"


def extract_headline(lines):
    for i, line in enumerate(lines[1:10], 1):
        line = line.strip()
        if "@" in line or "http" in line.lower():
            continue
        words = line.split()
        if 3 <= len(words) <= 15:
            indicators = ['manager', 'engineer', 'developer', 'analyst',
                         'specialist', 'consultant', 'director', 'lead',
                         'coordinator', 'associate', 'success', 'support',
                         'operations', 'senior', 'junior', 'staff', 'head',
                         'vp', 'officer', 'executive']
            if any(ind in line.lower() for ind in indicators):
                return line.strip()
            if '|' in line or '•' in line or '-' in line:
                return line.strip()
    return ""


# =========================
# LLM EXTRACTION — FOCUSED
# =========================

def extract_profile_with_llm(text):
    """
    Extract profile with STRICT 8-12 skill selection.
    Only skills that would appear as job posting requirements.
    """

    prompt = f"""You are an expert recruiter reviewing a resume. Extract the candidate's profile.

RULES FOR SKILLS — THIS IS CRITICAL:
Return exactly 8-12 skills. No more, no less.

Pick ONLY skills that:
1. Would appear as REQUIREMENTS in a job posting the candidate should apply to
2. Are specific enough to differentiate this candidate (not generic like "communication")
3. Represent the candidate's PRIMARY professional value

SKILL PRIORITY ORDER (pick from top categories first):
- Core tools/platforms they use daily (e.g. "Zendesk", "Salesforce", "JIRA")
- Professional domain expertise (e.g. "customer success", "SaaS operations")
- Industry-specific methodologies (e.g. "agile", "six sigma", "NPS management")
- Technical skills ONLY if relevant to their role (e.g. "SQL" for an analyst)

DO NOT INCLUDE:
- Languages spoken (e.g. "hindi", "english", "malayalam")
- Soft skills (e.g. "attention to detail", "communication", "leadership")
- One-off or very niche tools unless they define the role
- Skills that appear in every resume (e.g. "Microsoft Office", "email")
- Company names or job titles as skills
- Hobbies or non-professional skills

EXAMPLE — for a Customer Experience & Operations Leader:
GOOD: ["customer success", "zendesk", "salesforce", "saas", "nps management", "process optimization", "customer onboarding", "churn reduction", "cross-functional coordination", "quality assurance"]
BAD: ["hindi", "attention to detail", "graphic design", "subtitles", "english", "communication", "prime video", "netflix", "brand voice development", "visual communication"]

Return ONLY valid JSON with keys: "name", "headline", "skills"
- "skills" must be exactly 8-12 items
- Lowercase all skills
- No duplicates

Resume text:
{text[:6000]}

JSON:"""

    try:
        res = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            max_tokens=400,
        )

        response_text = res.choices[0].message.content.strip()

        # Clean markdown fences
        if response_text.startswith("```"):
            response_text = re.sub(r'^```(?:json)?\n?', '', response_text)
            response_text = re.sub(r'\n?```$', '', response_text)

        profile_data = json.loads(response_text)

        if not isinstance(profile_data, dict):
            raise ValueError("Not a dict")

        profile_data.setdefault("name", "Candidate")
        profile_data.setdefault("headline", "")
        profile_data.setdefault("skills", [])

        if not isinstance(profile_data["skills"], list):
            profile_data["skills"] = []

        # Clean, deduplicate, enforce limits
        raw_skills = list(dict.fromkeys([
            s.strip().lower() for s in profile_data["skills"]
            if isinstance(s, str) and s.strip() and len(s.strip()) > 2
        ]))

        # Filter out common garbage that LLMs love to include
        garbage = {
            "communication", "communication skills", "teamwork", "team player",
            "problem solving", "problem-solving", "leadership", "time management",
            "microsoft office", "ms office", "email", "english", "hindi",
            "malayalam", "french", "spanish", "german", "arabic", "tamil",
            "telugu", "kannada", "bengali", "urdu", "marathi", "gujarati",
            "attention to detail", "detail-oriented", "detail oriented",
            "adaptability", "creativity", "critical thinking",
            "interpersonal skills", "multitasking", "organizational skills",
            "work ethic", "self-motivated", "fast learner", "hard working",
            "microsoft word", "microsoft excel", "powerpoint", "google docs",
        }
        filtered = [s for s in raw_skills if s not in garbage]

        # Enforce 8-12 range
        if len(filtered) > 12:
            filtered = filtered[:12]

        profile_data["skills"] = filtered
        return profile_data

    except Exception as e:
        print(f"LLM extraction failed: {e}")
        return None


def extract_skills_fallback(text):
    """Fallback: extract just skills with strict limits."""

    prompt = f"""Extract the 10 most important professional skills from this resume.

RULES:
- Return a JSON array of exactly 10 skills
- Only skills that would appear as REQUIREMENTS in a job posting
- No languages spoken, no soft skills, no generic office tools
- Lowercase

Resume:
{text[:6000]}

Return: ["skill1", "skill2", ...]"""

    try:
        res = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            max_tokens=200,
        )

        response_text = res.choices[0].message.content.strip()
        if response_text.startswith("```"):
            response_text = re.sub(r'^```(?:json)?\n?', '', response_text)
            response_text = re.sub(r'\n?```$', '', response_text)

        skills = json.loads(response_text)
        if not isinstance(skills, list):
            return []

        return list(dict.fromkeys([
            s.strip().lower() for s in skills
            if isinstance(s, str) and s.strip() and len(s.strip()) > 2
        ]))[:12]

    except Exception as e:
        print(f"Skill fallback failed: {e}")
        return []


# =========================
# MAIN BUILDER
# =========================

def build_profile(pdf_path, output_path):
    """Extract focused profile from resume PDF."""

    raw_text = extract_text(pdf_path)
    lines = [l.strip() for l in raw_text.split("\n") if l.strip()]

    if not lines:
        raise ValueError("Could not extract text from PDF")

    # Try LLM extraction
    profile = extract_profile_with_llm(raw_text)

    if profile and profile.get("skills"):
        print(f"✓ LLM: name={profile.get('name')}, skills={len(profile.get('skills', []))}")
    else:
        print("⚠ LLM failed, using fallback")
        name = extract_name(lines)
        headline = extract_headline(lines)
        skills = extract_skills_fallback(raw_text)
        profile = {"name": name, "headline": headline, "skills": skills}

    if not profile.get("name") or profile["name"] == "":
        profile["name"] = extract_name(lines) or "Candidate"

    if not profile.get("skills"):
        raise ValueError("Could not extract skills. Try a different resume or enter manually.")

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(profile, f, indent=2, ensure_ascii=False)

    print(f"✓ Profile saved: {output_path}")
    print(f"  Name: {profile['name']}")
    print(f"  Headline: {profile.get('headline', 'N/A')}")
    print(f"  Skills ({len(profile['skills'])}): {', '.join(profile['skills'])}")

    return profile


# =========================
# CLI
# =========================

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python resume_parser.py <resume.pdf>")
        sys.exit(1)
    try:
        profile = build_profile(sys.argv[1], "profile.json")
        print("\n✅ Success!")
        print(json.dumps(profile, indent=2))
    except Exception as e:
        print(f"\n❌ {e}")
        sys.exit(1)
