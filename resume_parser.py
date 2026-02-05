import pdfplumber
import re

# ============================================
# CLEAN TEXT
# ============================================

def clean_text(text):

    text = text.lower()

    # Remove special characters
    text = re.sub(r"[^a-zA-Z0-9\s]", " ", text)

    # Remove extra spaces
    text = re.sub(r"\s+", " ", text)

    return text


# ============================================
# KEYWORD EXTRACTION
# ============================================

def extract_keywords(text):

    keywords_pool = [

        # Customer Success / CX
        "customer success",
        "customer support",
        "customer operations",
        "onboarding",
        "retention",
        "renewals",
        "expansion",

        # Product / Ops
        "product operations",
        "incident management",
        "incident triage",
        "rca",
        "sla",
        "process optimization",
        "workflow automation",
        "stakeholder management",
        "product feedback",
        "beta testing",

        # SaaS / Technical
        "saas",
        "api",
        "sso",
        "identity access management",
        "troubleshooting",
        "automation",

        # Tools
        "zendesk",
        "salesforce",
        "hubspot",
        "intercom",
        "jira",
        "okta",
        "slack",
        "workato",

        # Data / Analytics
        "analytics",
        "predictive analytics"
    ]

    found = []

    for kw in keywords_pool:
        if kw in text:
            found.append(kw)

    return found[:25]   # Cap at 25 keywords


# ============================================
# MAIN PARSER FUNCTION
# ============================================

def parse_resume(file_path):

    text = ""

    # Read PDF
    with pdfplumber.open(file_path) as pdf:

        for page in pdf.pages:
            text += page.extract_text() or ""

    # Clean text
    cleaned = clean_text(text)

    # Extract keywords
    keywords = extract_keywords(cleaned)

    # Build profile
    profile = {
        "name": "Candidate",
        "skills": keywords
    }

    return profile
