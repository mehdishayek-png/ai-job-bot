import pdfplumber
import json
import os

# ============================================
# PATHS
# ============================================

PROFILE_PATH = "data/profile.json"

# ============================================
# EXTRACT TEXT
# ============================================

def extract_text(pdf_path):

    text = ""

    with pdfplumber.open(pdf_path) as pdf:

        for page in pdf.pages:
            text += page.extract_text() + "\n"

    return text.lower()

# ============================================
# KEYWORD BUILDER
# ============================================

COMMON_KEYWORDS = [

    "customer success",
    "customer support",
    "saas",
    "zendesk",
    "hubspot",
    "crm",
    "onboarding",
    "technical support",
    "product operations",
    "incident management",
    "workflow automation",
    "cx operations",
    "okta",
    "slack",
    "process optimization"
]

def extract_keywords(text):

    found = []

    for word in COMMON_KEYWORDS:

        if word in text:
            found.append(word)

    return found

# ============================================
# BUILD PROFILE
# ============================================

def build_profile(pdf_path):

    print("Parsing resume...")

    text = extract_text(pdf_path)

    keywords = extract_keywords(text)

    profile = {

        "name": "Candidate",
        "headline": "Auto-generated profile",
        "skills": keywords,
        "tools": keywords,
        "industries": ["SaaS", "Technology"]
    }

    os.makedirs("data", exist_ok=True)

    with open(PROFILE_PATH, "w") as f:
        json.dump(profile, f, indent=2)

    print("Profile built from resume.")
