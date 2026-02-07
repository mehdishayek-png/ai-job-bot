"""
Recruiter Finder — Bing Version
Beginner Safe
"""

import requests
from bs4 import BeautifulSoup
import json
import os
import time


# -----------------------------
# CONFIG
# -----------------------------

ROLES = [
    "Recruiter",
    "Technical Recruiter",
    "Hiring Manager",
    "Head of Engineering"
]

OUTPUT_DIR = "data/recruiters"
DELAY = 5

HEADERS = {
    "User-Agent": "Mozilla/5.0"
}


# -----------------------------
# Helpers
# -----------------------------

def ensure_output_dir():
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)


def search_bing(query):

    url = "https://www.bing.com/search"
    params = {"q": query}

    r = requests.get(url, headers=HEADERS, params=params)

    soup = BeautifulSoup(r.text, "html.parser")

    results = []

    for a in soup.select("li.b_algo h2 a"):

        link = a.get("href")

        if "linkedin.com/in" in link:
            results.append(link)

    return results[:5]


# -----------------------------
# Core
# -----------------------------

def find_recruiters(company):

    print(f"\n🔎 Searching recruiters for: {company}")

    people = []

    for role in ROLES:

        query = f'site:linkedin.com/in "{company}" "{role}"'
        print(f"\n   → {query}")

        links = search_bing(query)

        for link in links:
            people.append({
                "company": company,
                "role": role,
                "linkedin_url": link
            })

        print(f"   ⏳ Waiting {DELAY}s...")
        time.sleep(DELAY)

    return people


# -----------------------------
# Save
# -----------------------------

def save(company, people):

    ensure_output_dir()

    filename = f"{OUTPUT_DIR}/{company.replace(' ', '_')}.json"

    with open(filename, "w") as f:
        json.dump(people, f, indent=2)

    print(f"\n💾 Saved → {filename}")


# -----------------------------
# MAIN
# -----------------------------

if __name__ == "__main__":

    print("\n=== Recruiter Finder (Bing) ===\n")

    company = input("Enter company name: ").strip()

    people = find_recruiters(company)

    save(company, people)

    print("\nDone.\n")
