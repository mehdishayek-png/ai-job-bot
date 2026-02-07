import requests
import re
import csv
from urllib.parse import urljoin

print("================================")
print("STARTUP EMAIL SCRAPER STARTED")
print("================================")

DOMAINS_FILE = "startup_domains.txt"
OUTPUT_FILE = "startup_contacts.csv"

PAGES_TO_CHECK = [
    "",
    "/careers",
    "/jobs",
    "/work-with-us",
    "/join",
    "/about",
    "/contact"
]

headers = {
    "User-Agent": "Mozilla/5.0"
}

contacts = []


# ---------- EMAIL REGEX ----------
EMAIL_REGEX = r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"


# ---------- Load Domains ----------
with open(DOMAINS_FILE, "r") as f:
    domains = [d.strip() for d in f.readlines() if d.strip()]

print(f"Domains loaded: {len(domains)}\n")


# ---------- Scan Each Domain ----------
for domain in domains:

    print("Scanning:", domain)

    found_email = None

    for page in PAGES_TO_CHECK:

        url = f"https://{domain}{page}"

        try:
            r = requests.get(url, headers=headers, timeout=8)

            if r.status_code != 200:
                continue

            # ---------- Extract emails ----------
            emails = re.findall(EMAIL_REGEX, r.text)

            cleaned_emails = []

            for e in emails:

                e = e.lower().strip()

                # Skip image / asset filenames
                if any(ext in e for ext in [
                    ".png",
                    ".jpg",
                    ".jpeg",
                    ".webp",
                    ".svg",
                    ".gif"
                ]):
                    continue

                # Skip junk / tracking emails
                if any(bad in e for bad in [
                    "example.com",
                    "email.com",
                    "domain.com",
                    "sentry.io",
                    "cloudflare",
                    "amazonaws"
                ]):
                    continue

                # Keep hiring inboxes only
                if any(keyword in e for keyword in [
                    "jobs",
                    "careers",
                    "hr",
                    "talent",
                    "recruit",
                    "people",
                    "hiring"
                ]):
                    cleaned_emails.append(e)

            cleaned_emails = list(set(cleaned_emails))

            if cleaned_emails:
                found_email = cleaned_emails[0]
                print("  Found:", found_email)
                break

        except Exception as e:
            continue

    contacts.append({
        "domain": domain,
        "email": found_email if found_email else "Not found"
    })


# ---------- Save CSV ----------
with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as f:

    writer = csv.DictWriter(f, fieldnames=["domain", "email"])
    writer.writeheader()
    writer.writerows(contacts)

print("\n================================")
print("Scrape complete")
print(f"Saved → {OUTPUT_FILE}")
print("================================")
