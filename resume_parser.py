"""
Resume Parser v3
================
Extracts:
  - 8-12 high-signal SKILLS (tools, platforms, methodologies)
  - 5-8 ROLE KEYWORDS (function-level terms like "incident management",
    "customer support", "ticket triage" that describe WHAT you do)

The role_keywords are critical for matching: a job saying "manage customer
escalations" should match someone who does "incident triage" even if the
exact phrase never appears in either.
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
# LLM EXTRACTION
# =========================

def extract_profile_with_llm(text):
    prompt = f"""You are an expert recruiter. Extract this candidate's profile.

Return JSON with FIVE keys: "name", "headline", "skills", "role_keywords", "experience_years"

=== EXPERIENCE_YEARS (integer) ===
Estimate total years of professional experience from work history dates.
Count from earliest job start year to present. Internships count as 0.5 years.
Return an integer. If unsure, estimate conservatively (round down).

=== SKILLS (8-12 items) ===
Specific tools, platforms, and methodologies that would appear as REQUIREMENTS in job postings.

Pick ONLY:
- Core tools/platforms: "Zendesk", "Salesforce", "Okta", "JIRA", "Workato"
- Domain expertise: "SaaS operations", "identity access management"
- Methodologies: "incident management", "root cause analysis", "SLA management"

DO NOT include:
- Languages spoken (hindi, english, etc.)
- Soft skills (communication, leadership, attention to detail)
- Generic tools (Microsoft Office, email, Google Docs)
- Company names as skills (Netflix, OpenAI, etc.)

=== ROLE KEYWORDS (5-8 items) ===
These describe the FUNCTION the candidate performs — the type of work, not the tools.
These are critical because job postings often describe the same work using different words.

Examples of good role_keywords:
- "customer support", "customer experience", "customer success"
- "incident triage", "ticket escalation", "issue resolution"
- "technical troubleshooting", "enterprise support"
- "stakeholder communication", "cross-functional coordination"
- "process documentation", "SOP development"
- "account management", "client onboarding"
- "QA testing", "beta testing", "product feedback"

Think: if a recruiter searched for candidates, what job FUNCTIONS would they search?

=== FORMAT ===
Return ONLY valid JSON:
{{"name": "...", "headline": "...", "skills": ["8-12 items"], "role_keywords": ["5-8 items"], "experience_years": 3}}
All lowercase. No duplicates.

Resume:
{text[:6000]}

JSON:"""

    try:
        res = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            max_tokens=500,
        )

        response_text = res.choices[0].message.content.strip()
        if response_text.startswith("```"):
            response_text = re.sub(r'^```(?:json)?\n?', '', response_text)
            response_text = re.sub(r'\n?```$', '', response_text)

        data = json.loads(response_text)
        if not isinstance(data, dict):
            raise ValueError("Not a dict")

        data.setdefault("name", "Candidate")
        data.setdefault("headline", "")
        data.setdefault("skills", [])
        data.setdefault("role_keywords", [])
        data.setdefault("experience_years", 2)

        # Clean skills
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

        skills = list(dict.fromkeys([
            s.strip().lower() for s in data["skills"]
            if isinstance(s, str) and s.strip() and len(s.strip()) > 2
            and s.strip().lower() not in garbage
        ]))[:12]

        role_kw = list(dict.fromkeys([
            s.strip().lower() for s in data["role_keywords"]
            if isinstance(s, str) and s.strip() and len(s.strip()) > 2
            and s.strip().lower() not in garbage
        ]))[:8]

        data["skills"] = skills
        data["role_keywords"] = role_kw
        return data

    except Exception as e:
        print(f"LLM extraction failed: {e}")
        return None


def extract_skills_fallback(text):
    prompt = f"""Extract the 10 most important professional skills from this resume.
Only skills that would appear as REQUIREMENTS in a job posting.
No languages, soft skills, or generic tools. Lowercase. JSON array only.

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
    raw_text = extract_text(pdf_path)
    lines = [l.strip() for l in raw_text.split("\n") if l.strip()]

    if not lines:
        raise ValueError("Could not extract text from PDF")

    profile = extract_profile_with_llm(raw_text)

    if profile and profile.get("skills"):
        print(f"✓ LLM: name={profile.get('name')}, skills={len(profile.get('skills', []))}, role_kw={len(profile.get('role_keywords', []))}")
    else:
        print("⚠ LLM failed, using fallback")
        name = extract_name(lines)
        headline = extract_headline(lines)
        skills = extract_skills_fallback(raw_text)
        profile = {"name": name, "headline": headline, "skills": skills, "role_keywords": []}

    if not profile.get("name") or profile["name"] == "":
        profile["name"] = extract_name(lines) or "Candidate"

    if not profile.get("skills"):
        raise ValueError("Could not extract skills. Try a different resume or enter manually.")

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(profile, f, indent=2, ensure_ascii=False)

    print(f"✓ Saved: {output_path}")
    print(f"  Name: {profile['name']}")
    print(f"  Headline: {profile.get('headline', 'N/A')}")
    print(f"  Skills ({len(profile['skills'])}): {', '.join(profile['skills'])}")
    print(f"  Role KW ({len(profile.get('role_keywords', []))}): {', '.join(profile.get('role_keywords', []))}")

    return profile


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
