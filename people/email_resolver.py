"""
Email Resolver
--------------
Turns recruiter LinkedIn URLs
into possible email addresses.
"""

import json
import os


# -----------------------------
# CONFIG
# -----------------------------

INPUT_DIR = "data/recruiters"
OUTPUT_DIR = "data/recruiter_emails"

EMAIL_PATTERNS = [
    "{first}@{domain}",
    "{first}.{last}@{domain}",
    "{f}{last}@{domain}",
    "{first}{last}@{domain}"
]


# -----------------------------
# Helpers
# -----------------------------

def ensure_output_dir():
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)


def extract_name_from_url(url):
    """
    Example:
    linkedin.com/in/john-smith-123

    → John Smith
    """

    slug = url.split("/in/")[-1]
    slug = slug.split("?")[0]
    slug = slug.replace("-", " ")

    parts = slug.split()

    if len(parts) >= 2:
        first = parts[0]
        last = parts[1]
    else:
        first = parts[0]
        last = ""

    return first.lower(), last.lower()


def generate_emails(first, last, domain):

    f = first[0] if first else ""

    emails = []

    for pattern in EMAIL_PATTERNS:
        email = pattern.format(
            first=first,
            last=last,
            f=f,
            domain=domain
        )
        emails.append(email)

    return emails


# -----------------------------
# Core
# -----------------------------

def process_file(file):

    company = file.replace(".json", "")
    domain = input(f"Enter domain for {company}: ").strip()

    path = os.path.join(INPUT_DIR, file)

    with open(path, "r") as f:
        people = json.load(f)

    output = []

    for person in people:

        url = person["linkedin_url"]

        first, last = extract_name_from_url(url)

        emails = generate_emails(first, last, domain)

        output.append({
            "name": f"{first} {last}",
            "emails": emails,
            "linkedin": url
        })

    return company, output


# -----------------------------
# Runner
# -----------------------------

def run():

    ensure_output_dir()

    files = os.listdir(INPUT_DIR)

    for file in files:

        if not file.endswith(".json"):
            continue

        company, data = process_file(file)

        out_path = f"{OUTPUT_DIR}/{company}.json"

        with open(out_path, "w") as f:
            json.dump(data, f, indent=2)

        print(f"Saved → {out_path}")


# -----------------------------
# CLI
# -----------------------------

if __name__ == "__main__":
    run()
