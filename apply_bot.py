from playwright.sync_api import sync_playwright
import time
import os

OUTPUT_DIR = "output"
RESUME_PATH = os.path.abspath("resume/resume.pdf")

# Example job application URL (replace later dynamically)
JOB_URL = input("Paste job application URL: ").strip()

print("Launching browser...")

with sync_playwright() as p:

    browser = p.chromium.launch(
    channel="msedge",
    headless=False
)
    page = browser.new_page()

    print("Opening job page...")
    page.goto(JOB_URL)

    print("\nLOGIN IF REQUIRED")
    print("After login and page fully loads, press ENTER here.")
    input()

    print("Page loaded. Ready for manual review.")

    print("\nNEXT STEPS:")
    print("- Click Easy Apply / Apply button manually")
    print("- When upload resume appears, use this file:")
    print(RESUME_PATH)
    print("- Cover letters are inside output folder")

    print("\nBot is now idle for manual control.")
    input("Press ENTER to close browser when done...")

    browser.close()

print("Session finished.")
