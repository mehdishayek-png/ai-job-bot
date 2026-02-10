"""
RESUME → SMART KEYWORD BUILDER
Expanded semantic detection
"""

import pdfplumber
import json
import re
import os


# -----------------------------
# PATHS
# -----------------------------

RESUME_FILE = "resume/resume.pdf"
OUTPUT_FILE = "data/resume_keywords.json"


# -----------------------------
# TEXT EXTRACTION
# -----------------------------

def extract_text_from_pdf(path):

    if not os.path.exists(path):
        print(f"❌ Resume not found at: {path}")
        return ""

    text = ""

    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"

    return text.lower()


# -----------------------------
# EXPANDED SKILL MAP
# -----------------------------

SKILL_MAP = {

    "customer success": [
        "customer success",
        "client success",
        "customer experience",
        "cx",
    ],

    "support": [
        "support",
        "technical support",
        "customer support",
        "helpdesk",
        "troubleshooting",
    ],

    "onboarding": [
        "onboarding",
        "implementation",
        "go-live",
        "enablement",
    ],

    "account management": [
        "account management",
        "account manager",
        "relationship management",
    ],

    "operations": [
        "operations",
        "product operations",
        "business operations",
    ],

    "crm": [
        "crm",
        "salesforce",
        "hubspot",
    ],

    "saas": [
        "saas",
        "software as a service",
    ],

    "project management": [
        "project management",
        "program management",
        "delivery management",
    ],
}


# -----------------------------
# KEYWORD EXTRACTION
# -----------------------------

def extract_keywords(text):

    found = {}

    for skill, variants in SKILL_MAP.items():

        total = 0

        for variant in variants:
            total += len(re.findall(variant, text))

        if total > 0:
            found[skill] = total

    return found


# -----------------------------
# SAVE
# -----------------------------

def save_keywords(data):

    if not os.path.exists("data"):
        os.makedirs("data")

    with open(OUTPUT_FILE, "w") as f:
        json.dump(data, f, indent=2)


# -----------------------------
# RUN
# -----------------------------

def run():

    print("\n=== BUILDING SMART RESUME KEYWORDS ===\n")

    text = extract_text_from_pdf(RESUME_FILE)

    if not text:
        print("No text extracted.")
        return

    keywords = extract_keywords(text)

    save_keywords(keywords)

    print("Keywords extracted:\n")

    for k, v in keywords.items():
        print(f"{k} → {v}")

    print("\nSaved → data/resume_keywords.json")


if __name__ == "__main__":
    run()
