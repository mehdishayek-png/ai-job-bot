import smtplib
import os
from email.message import EmailMessage

EMAIL = os.getenv("JOBBOT_EMAIL")
PASSWORD = os.getenv("JOBBOT_EMAIL_PASS")

if not EMAIL or not PASSWORD:
    print("ERROR: Email credentials missing")
    exit(1)

print("Email credentials loaded")

TO_EMAIL = input("Recipient hiring email: ").strip()
SUBJECT = input("Email subject: ").strip()

COVER_FILE = input("Cover letter file path: ").strip()
RESUME_FILE = input("Resume PDF file path: ").strip()

with open(COVER_FILE, "r", encoding="utf-8") as f:
    body = f.read()

msg = EmailMessage()
msg["From"] = EMAIL
msg["To"] = TO_EMAIL
msg["Subject"] = SUBJECT
msg.set_content(body)

with open(RESUME_FILE, "rb") as f:
    resume_data = f.read()

msg.add_attachment(
    resume_data,
    maintype="application",
    subtype="pdf",
    filename="Resume.pdf"
)

print("Connecting to Gmail SMTP...")

with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
    smtp.login(EMAIL, PASSWORD)
    smtp.send_message(msg)

print("APPLICATION EMAIL SENT SUCCESSFULLY")
