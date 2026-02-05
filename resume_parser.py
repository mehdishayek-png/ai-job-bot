import pdfplumber
import json
import os
import re

# ============================================
# CONFIG
# ============================================

OUTPUT_PATH = "data/profile.json"

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
    "integrations"
]

# ============================================
# TEXT CLEANER
# ============================================

def clean_text(text):
    text = text.lower()
    text = re.sub(r"\n", " ", text)
    text = re.sub(r"[^a-zA-Z0-9\s]", "", text)
    return text


# ============================================
# KEYWORD EXTRACTOR
# ============================================

def extract_keywords(text):

    keywords_found = []

    for skill in COMMON_SKILLS:
        if skill in text:
            keywords_found.append(skill)

    return list(set(keywords_found))


# ============================================
# MAIN BUILDER (UI EXPECTS THIS)
# ============================================

def build_profile(pdf_path):

    print("\nParsing resume...")

    if not os.path.exists(pdf_path):
        print("Resume file not found.")
        return

    full_text = ""

    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            full_text += page.extract_text() or ""

    cleaned = clean_text(full_text)

    keywords = extract_keywords(cleaned)

    profile = {
        "name": "Candidate",
        "skills": keywords
    }

    os.makedirs("data", exist_ok=True)

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(profile, f, indent=2)

    print("\nProfile built successfully.")
    print(f"Skills extracted: {len(keywords)}")
    print(f"Saved → {OUTPUT_PATH}")


# ============================================
# TEST RUN
# ============================================

if __name__ == "__main__":

    sample_path = "resume/resume.pdf"

    build_profile(sample_path)