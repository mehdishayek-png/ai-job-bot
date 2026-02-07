import os
import time
from googlesearch import search

print("================================")
print("GOOGLE + LINKEDIN FETCHER STARTED")
print("================================")

OUTPUT_DIR = "jobs"
MAX_RESULTS = 15
RESULTS_PER_QUERY = 10   # Lowered to avoid Google blocks

os.makedirs(OUTPUT_DIR, exist_ok=True)

saved = 0


# ---------- SEARCH QUERIES ----------

QUERIES = [

    "product operations jobs",
    "customer operations jobs",
    "customer success operations",
    "support operations specialist",
    "customer experience operations",
    "SaaS operations specialist",
    "incident management operations",
]


# ---------- FILTER ----------

INCLUDE = [
    "operations",
    "customer",
    "support",
    "success",
    "cx"
]

EXCLUDE = [
    "engineer",
    "developer",
    "frontend",
    "backend",
    "designer",
    "ux",
    "finance",
    "accountant",
    "data scientist"
]


def is_relevant(url):

    url_l = url.lower()

    if any(bad in url_l for bad in EXCLUDE):
        return False

    if not any(good in url_l for good in INCLUDE):
        return False

    return True


# ---------- SAVE ----------

def save_job(url):

    global saved

    filename = f"google_job_{saved+1}.txt"
    path = os.path.join(OUTPUT_DIR, filename)

    content = f"""
Apply URL: {url}
Source: Google / LinkedIn
"""

    with open(path, "w", encoding="utf-8") as f:
        f.write(content)

    saved += 1
    print("Saved:", url)


# ---------- MAIN ----------

for query in QUERIES:

    if saved >= MAX_RESULTS:
        break

    print(f"\nSearching: {query}")

    try:
        results = search(
            query,
            num_results=RESULTS_PER_QUERY
        )

        for url in results:

            if saved >= MAX_RESULTS:
                break

            if not is_relevant(url):
                continue

            save_job(url)

        time.sleep(5)  # Delay between searches

    except Exception as e:
        print("Search failed:", e)


print("\n================================")
print("Jobs saved:", saved)
print("FETCH COMPLETE")
print("================================")
