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

# Try Streamlit secrets first, then fall back to .env
try:
    import streamlit as st
    api_key = st.secrets.get("OPENROUTER_API_KEY")
except (ImportError, KeyError, AttributeError):
    api_key = os.getenv("OPENROUTER_API_KEY")

if not api_key:
    raise ValueError("OPENROUTER_API_KEY not found in environment or Streamlit secrets")

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=api_key,
)

MODEL = "google/gemini-2.5-flash"

# =========================
# TEXT HELPERS
# =========================

def extract_text(pdf_path):
    """Extract all text from PDF"""
    raw = ""
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            raw += (page.extract_text() or "") + "\n"
    return raw


def extract_name(lines):
    """Extract name from first few lines of resume"""
    # Look in first 5 lines for a name-like pattern
    for line in lines[:5]:
        line = line.strip()
        if not line or len(line) < 3:
            continue
            
        # Skip lines with common resume keywords
        skip_keywords = ['resume', 'cv', 'curriculum', 'vitae', 'contact', 
                        'email', 'phone', 'address', '@', 'http', 'www']
        if any(kw in line.lower() for kw in skip_keywords):
            continue
            
        # Check if it looks like a name (2-4 words, mostly alphabetic)
        words = line.split()
        if 2 <= len(words) <= 4:
            # Allow hyphens and apostrophes in names
            if all(re.match(r"^[A-Za-z\-']+$", w) for w in words):
                return line.title()
    
    return "Candidate"


def extract_headline(lines):
    """Extract professional headline from resume"""
    # Look for headline in lines 2-10
    for i, line in enumerate(lines[1:10], 1):
        line = line.strip()
        
        # Skip contact info
        if "@" in line or "http" in line.lower() or "www" in line.lower():
            continue
        
        # Skip the name line if we can identify it
        if i == 0:
            continue
            
        # Look for title-like patterns (3-15 words)
        words = line.split()
        if 3 <= len(words) <= 15:
            # Should contain some common job title indicators
            title_indicators = ['manager', 'engineer', 'developer', 'analyst', 
                              'specialist', 'consultant', 'director', 'lead',
                              'coordinator', 'associate', 'success', 'support',
                              'operations', 'senior', 'junior', 'staff']
            
            if any(indicator in line.lower() for indicator in title_indicators):
                return line.strip()
            
            # If it has pipes or bullets, it might be a headline
            if '|' in line or '•' in line or '-' in line:
                return line.strip()
    
    return ""

# =========================
# LLM-BASED EXTRACTION (MORE RELIABLE)
# =========================

def extract_profile_with_llm(text):
    """Use LLM to extract name, headline, and skills in one call"""
    
    prompt = f"""Extract the following from this resume and return ONLY valid JSON:

1. name: Full name of the candidate
2. headline: Current job title or professional headline (e.g. "IT Consultant" or "Customer Support Specialist")
3. skills: List of SPECIFIC, MATCHABLE professional skills

SKILLS RULES — this is critical:
- Include specific tools and platforms: "Oracle OMS", "Zendesk", "JIRA", "Salesforce", "SQL"
- Include specific domains: "order management", "marketplace integration", "incident management"  
- Include specific methodologies: "ITIL", "Agile", "SLA management", "root cause analysis"
- Include specific technologies: "SOA Suite", "REST API", "SOAP", "Linux"
- DO NOT include soft skills like "communication", "leadership", "problem solving", "teamwork"
- DO NOT include generic terms like "Microsoft Office", "email", "Google Docs"
- DO NOT include languages spoken like "English", "Hindi"
- Each skill should be something a recruiter would SEARCH FOR in a job posting

Return ONLY a JSON object:
{{"name": "...", "headline": "...", "skills": ["specific skill 1", "specific skill 2", ...]}}

Resume text:
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
        
        # Clean up markdown code blocks if present
        if response_text.startswith("```"):
            response_text = re.sub(r'^```(?:json)?\n?', '', response_text)
            response_text = re.sub(r'\n?```$', '', response_text)
        
        profile_data = json.loads(response_text)
        
        # Validate structure
        if not isinstance(profile_data, dict):
            raise ValueError("Response is not a dictionary")
        
        # Ensure required keys exist
        profile_data.setdefault("name", "Candidate")
        profile_data.setdefault("headline", "")
        profile_data.setdefault("skills", [])
        
        # Ensure skills is a list
        if not isinstance(profile_data["skills"], list):
            profile_data["skills"] = []
        
        # Clean up skills
        profile_data["skills"] = sorted(set([
            s.strip().lower() for s in profile_data["skills"] 
            if isinstance(s, str) and s.strip()
        ]))
        
        return profile_data

    except Exception as e:
        print(f"LLM extraction failed: {e}")
        return None


def extract_skills_llm(text):
    """Fallback: Extract just skills using LLM"""

    prompt = f"""Extract professional skills from this resume.

Rules:
- Return JSON array only
- No duplicates
- Include tools, domains, programming languages, frameworks, soft skills

Resume:
{text[:6000]}

Return format: ["skill1", "skill2", ...]
"""

    try:
        res = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            max_tokens=300,
        )

        response_text = res.choices[0].message.content.strip()
        
        # Clean up markdown code blocks if present
        if response_text.startswith("```"):
            response_text = re.sub(r'^```(?:json)?\n?', '', response_text)
            response_text = re.sub(r'\n?```$', '', response_text)
        
        skills = json.loads(response_text)
        
        if not isinstance(skills, list):
            return []
            
        # Clean and deduplicate
        return sorted(set([
            s.strip().lower() for s in skills 
            if isinstance(s, str) and s.strip()
        ]))

    except Exception as e:
        print(f"Skill extraction failed: {e}")
        return []

# =========================
# MAIN BUILDER
# =========================

def build_profile(pdf_path, output_path):
    """
    Extract profile from PDF resume and save to JSON.
    Uses both rule-based and LLM-based extraction for best results.
    """
    
    # Extract text
    raw_text = extract_text(pdf_path)
    lines = [l.strip() for l in raw_text.split("\n") if l.strip()]
    
    if not lines:
        raise ValueError("Could not extract any text from PDF")
    
    # Try LLM-based extraction first (most reliable)
    profile = extract_profile_with_llm(raw_text)
    
    if profile:
        # LLM extraction succeeded
        print(f"✓ LLM extraction: name={profile.get('name')}, skills={len(profile.get('skills', []))}")
    else:
        # Fall back to rule-based extraction
        print("⚠ LLM extraction failed, using rule-based fallback")
        
        name = extract_name(lines)
        headline = extract_headline(lines)
        skills = extract_skills_llm(raw_text)
        
        profile = {
            "name": name,
            "headline": headline,
            "skills": skills,
        }
    
    # Ensure we have at least some data
    if not profile.get("name") or profile["name"] == "":
        profile["name"] = extract_name(lines) or "Candidate"
    
    if not profile.get("skills") or len(profile["skills"]) == 0:
        raise ValueError("Could not extract any skills from resume. Please try a different resume or enter skills manually.")
    
    # Save to file
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(profile, f, indent=2, ensure_ascii=False)
    
    print(f"✓ Profile saved: {output_path}")
    print(f"  Name: {profile['name']}")
    print(f"  Headline: {profile.get('headline', 'N/A')}")
    print(f"  Skills: {len(profile['skills'])}")
    
    return profile


# =========================
# CLI TEST
# =========================

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python resume_parser.py <resume.pdf>")
        sys.exit(1)
    
    pdf_file = sys.argv[1]
    output_file = "profile.json"
    
    try:
        profile = build_profile(pdf_file, output_file)
        print("\n✅ Success!")
        print(json.dumps(profile, indent=2))
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)
