import pdfplumber
import json
import os
import re

# ============================================
# CONFIG
# ============================================

OUTPUT_PATH = "data/profile.json"  # default; overridden by build_profile() param

COMMON_SKILLS = [
    "customer success",
    "customer support",
    "technical support",
    "product operations",
    "incident management",
    "troubleshooting",
    "automation",
    "process optimization",
    "stakeholder management",
    "onboarding",
    "saas",
    "crm",
    "zendesk",
    "salesforce",
    "hubspot",
    "okta",
    "slack",
    "workato",
    "analytics",
    "predictive analytics",
    "data analysis",
    "project management",
    "agile",
    "scrum",
    "api",
    "integrations",
    "jira",
    "confluence",
    "notion",
    "intercom",
    "freshdesk",
    "python",
    "sql",
    "excel",
    "power bi",
    "tableau",
    "google sheets",
    "zapier",
    "communication",
    "team leadership",
    "training",
    "documentation",
    "sla",
    "kpi",
    "nps",
    "retention",
    "churn",
    "upsell",
    "renewal",
    "b2b",
    "b2c",
    "enterprise",
    "smb",
    "remote",
]

# Common headline-like section headers to skip when guessing the name
_SKIP_WORDS = {
    "resume", "cv", "curriculum", "vitae", "objective",
    "summary", "experience", "education", "skills",
    "contact", "phone", "email", "address", "linkedin",
    "portfolio", "references", "http", "www", "@",
}

# ============================================
# TEXT CLEANER
# ============================================

def clean_text(text):
    text = text.lower()
    text = re.sub(r"\n", " ", text)
    text = re.sub(r"[^a-zA-Z0-9\s]", "", text)
    return text

# ============================================
# NAME EXTRACTOR
# ============================================

def extract_name(raw_text):
    """
    Attempt to pull the candidate's name from the first
    few non-empty lines of the PDF (typically the biggest
    text at the top of a resume).
    """
    lines = [l.strip() for l in raw_text.split("\n") if l.strip()]

    for line in lines[:5]:
        lower = line.lower()
        # Skip lines that look like section headers, emails, URLs
        if any(w in lower for w in _SKIP_WORDS):
            continue
        # Skip lines that are mostly digits (phone numbers)
        if sum(c.isdigit() for c in line) > len(line) * 0.4:
            continue
        # A plausible name is 2-4 short words, all alpha
        words = line.split()
        if 2 <= len(words) <= 4 and all(w.isalpha() for w in words):
            return line.title()

    return "Candidate"

# ============================================
# HEADLINE EXTRACTOR
# ============================================

def extract_headline(raw_text):
    """
    Look for a short professional tagline right after the name,
    e.g. "Customer Success Manager | SaaS Specialist"
    """
    lines = [l.strip() for l in raw_text.split("\n") if l.strip()]

    for line in lines[1:6]:  # skip first line (usually name)
        lower = line.lower()
        # Skip emails, phone numbers, URLs
        if "@" in line or "http" in lower or "www" in lower:
            continue
        if sum(c.isdigit() for c in line) > len(line) * 0.4:
            continue
        # A headline is typically 3-10 words
        words = line.split()
        if 3 <= len(words) <= 12:
            # Check it contains at least one role-like keyword
            role_hints = [
                "manager", "engineer", "specialist", "analyst",
                "lead", "director", "coordinator", "consultant",
                "support", "success", "operations", "developer",
                "associate", "executive", "administrator", "architect",
            ]
            if any(h in lower for h in role_hints):
                return line.strip()

    return ""

# ============================================
# KEYWORD EXTRACTOR
# ============================================

def extract_keywords(text):
    keywords_found = []
    for skill in COMMON_SKILLS:
        if skill in text:
            keywords_found.append(skill)
    return sorted(set(keywords_found))

# ============================================
# MAIN BUILDER
# ============================================

def build_profile(pdf_path, output_path=None):
    """
    Parse a resume PDF, extract name/headline/skills,
    and save to output_path.

    Parameters
    ----------
    pdf_path    : str – path to the uploaded PDF
    output_path : str – where to save profile.json
                        (defaults to module-level OUTPUT_PATH)
    """
    output_path = output_path or OUTPUT_PATH

    print(f"\nParsing resume → {pdf_path}")

    if not os.path.exists(pdf_path):
        print("Resume file not found.")
        return

    raw_text = ""
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            raw_text += (page.extract_text() or "") + "\n"

    if not raw_text.strip():
        print("❌ Could not extract any text from PDF.")
        return

    cleaned = clean_text(raw_text)
    keywords = extract_keywords(cleaned)
    name = extract_name(raw_text)
    headline = extract_headline(raw_text)

    profile = {
        "name": name,
        "headline": headline,
        "skills": keywords,
    }

    # Use the directory from output_path, not hardcoded "data"
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(profile, f, indent=2)

    print(f"\n✅ Profile built successfully.")
    print(f"   Name:     {name}")
    print(f"   Headline: {headline or '(not detected)'}")
    print(f"   Skills:   {len(keywords)} extracted")
    print(f"   Saved →   {output_path}")

# ============================================
# TEST RUN
# ============================================

if __name__ == "__main__":
    sample_path = "resume/resume.pdf"
    build_profile(sample_path)
