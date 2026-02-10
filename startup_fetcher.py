import requests
import os

print("================================")
print("STARTUP DOMAIN FETCHER STARTED")
print("================================")

OUTPUT_FILE = "startup_domains.txt"

domains = set()

# ---------- SOURCE 1 — Static Startup List ----------
STATIC_DOMAINS = [
    "notion.so",
    "airtable.com",
    "brex.com",
    "deel.com",
    "remote.com",
    "rippling.com",
    "clickup.com",
    "loom.com",
    "webflow.com",
    "zapier.com",
    "intercom.com",
    "freshworks.com",
    "gusto.com",
    "figma.com",
    "canva.com",
    "stripe.com",
    "wise.com",
    "pitch.com",
    "monday.com",
    "hubstaff.com",
    "close.com",
    "apollo.io",
    "clearbit.com",
    "attio.com",
    "retool.com",
    "supabase.com",
    "railway.app",
    "render.com",
    "fly.io",
    "vercel.com"
]

print("\nLoading static startup list...")
domains.update(STATIC_DOMAINS)


# ---------- SOURCE 2 — YC Companies (Public JSON) ----------
print("\nFetching YC companies...")

YC_URL = "https://yc-oss.github.io/api/batches/all.json"

try:
    r = requests.get(YC_URL, timeout=15)

    if r.status_code == 200:

        data = r.json()

        for company in data:

            website = company.get("website")

            if website and "." in website:
                domain = website.replace("https://", "").replace("http://", "").split("/")[0]
                domains.add(domain)

        print("YC domains added")

    else:
        print("YC fetch failed")

except Exception as e:
    print("YC fetch error:", e)


# ---------- SAVE ----------
domains = sorted(domains)

with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    for d in domains:
        f.write(d + "\n")

print("\n================================")
print("Domains saved:", len(domains))
print(f"Saved → {OUTPUT_FILE}")
print("================================")
