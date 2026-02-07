import os
import re

JOBS_DIR = "jobs"

print("================================")
print("EMAIL SCANNER STARTED")
print("================================")

email_pattern = r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]+"

total_emails = 0

for file in os.listdir(JOBS_DIR):

    path = os.path.join(JOBS_DIR, file)

    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    emails = re.findall(email_pattern, content)

    if emails:
        print(f"\n{file}")
        for e in emails:
            print("  →", e)
            total_emails += 1

print("\n================================")
print("Total emails found:", total_emails)
print("SCAN COMPLETE")
print("================================")
