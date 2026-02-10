"""
RESUME → KEYWORD BUILDER
Reads resume from /resume folder
Portable keyword extraction
"""

import pdfplumber
import json
import re
import os


# -----------------------------
# FILE PATHS
# -----------------------------

RESUME_FILE = "resume/resume.pdf"
OUTPUT_FILE = "data/resume_keywords.json"


# -----------------------------
# EXTRACT TEXT
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
# SKILL DETECTION
# -----------------------------

COMMON_SKILLS = [
    "customer success",
    "customer support",
    "technical support",
    "onboarding",
    "implementation",
    "account management",
    "client success",
    "crm",
    "salesforce",
    "hubspot",
    "product operations",
    "operations",
    "program management",
    "project management",
    "saas",
    "support",
]


def extract_keywords(text):

    found = {}

    for skill in COMMON_SKILLS:

        count = len(re.findall(skill, text))

        if count > 0:
            found[skill] = count

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

    print("\n=== BUILDING RESUME KEYWORDS ===\n")

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
