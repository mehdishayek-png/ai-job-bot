from resume_parser import parse_resume

# ============================================
# TEST FILE PATH
# ============================================

pdf_path = "resume/resume.pdf"

print("\nRunning parser test...\n")

profile = parse_resume(pdf_path)

print("=== KEYWORDS EXTRACTED ===\n")

for skill in profile["skills"]:
    print("-", skill)
