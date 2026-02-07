import json
from cover_letter_generator import generate_cover_letter

# ============================================
# CONFIG
# ============================================

JOBS_FILE = "data/jobs.json"
MAX_TEST = 999   # change if you want to cap

# ============================================
# LOAD JOBS
# ============================================

with open(JOBS_FILE, "r", encoding="utf-8") as f:
    jobs = json.load(f)

print("\n=== COVER LETTER STRESS TEST ===\n")

count = 0

for job in jobs:

    if count >= MAX_TEST:
        break

    print(f"[{count+1}] {job.get('title')}")

    generate_cover_letter(job)

    count += 1

print(f"\nTotal letters generated: {count}")
