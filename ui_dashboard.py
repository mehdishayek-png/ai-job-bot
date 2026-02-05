import streamlit as st
import json
import os
import subprocess

# ============================================
# CONFIG
# ============================================

st.set_page_config(
    page_title="AI Job Application Bot",
    layout="wide"
)

PROFILE_FILE = "data/profile.json"
JOBS_FILE = "data/jobs.json"
MATCHES_FILE = "data/matched_jobs.json"
LOG_FILE = "data/run_log.txt"

os.makedirs("data", exist_ok=True)
os.makedirs("output/cover_letters", exist_ok=True)

# ============================================
# HELPERS
# ============================================

def load_json(path):

    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return {}

    return {}

def save_json(path, data):

    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

profile = load_json(PROFILE_FILE)
jobs = load_json(JOBS_FILE)
matches = load_json(MATCHES_FILE)

# ============================================
# HEADER
# ============================================

st.title("🤖 AI Job Application Bot")
st.caption(
    "Upload resume → Extract profile → Match jobs → Generate cover letters"
)

# ============================================
# RESUME UPLOAD
# ============================================

st.header("📄 Resume Upload")

uploaded = st.file_uploader(
    "Upload your resume (PDF)",
    type=["pdf"]
)

if uploaded:

    save_path = f"data/{uploaded.name}"

    with open(save_path, "wb") as f:
        f.write(uploaded.read())

    st.success("Resume uploaded successfully.")

    if st.button("🧠 Build Profile From Resume"):

        with st.spinner("Parsing resume + extracting skills..."):

            subprocess.run(
                ["python", "resume_parser.py", save_path]
            )

        st.success("Profile built successfully.")

        profile = load_json(PROFILE_FILE)

# ============================================
# EXTRACTION DISPLAY
# ============================================

st.header("🧠 Extraction Results")

if profile:

    col1, col2 = st.columns(2)

    with col1:

        st.subheader("Extracted Skills")

        skills = profile.get("skills", [])

        st.write(f"Total skills: {len(skills)}")

        st.code(
            "\n".join(skills),
            language="text"
        )

    with col2:

        st.subheader("Professional Headline")

        st.write(
            profile.get("headline", "Not detected")
        )

else:

    st.info("Upload a resume to extract profile.")

# ============================================
# EDITABLE PROFILE
# ============================================

st.header("👤 Editable Profile")

if not profile:
    profile = {
        "name": "",
        "headline": "",
        "skills": []
    }

name = st.text_input(
    "Full Name",
    value=profile.get("name", "")
)

headline = st.text_input(
    "Professional Headline",
    value=profile.get("headline", "")
)

skills_text = st.text_area(
    "Skills / Keywords (one per line)",
    value="\n".join(profile.get("skills", [])),
    height=200
)

if st.button("💾 Save Profile"):

    updated = {
        "name": name,
        "headline": headline,
        "skills": [
            s.strip()
            for s in skills_text.split("\n")
            if s.strip()
        ]
    }

    save_json(PROFILE_FILE, updated)

    st.success("Profile saved successfully.")

# ============================================
# RUN MATCHING
# ============================================

st.header("🚀 Run Auto Apply")

if st.button("▶ Run Job Matching"):

    with st.spinner("Running job fetch + semantic matching..."):

        subprocess.run(
            ["python", "run_auto_apply.py"]
        )

    st.success("Matching complete.")

    matches = load_json(MATCHES_FILE)

# ============================================
# SEMANTIC MATCH DISPLAY
# ============================================

st.header("📊 Semantic Match Results")

if matches:

    table_data = []

    for job in matches:

        table_data.append({
            "Company": job.get("company"),
            "Title": job.get("title"),
            "Match %": job.get("match_score"),
            "Source": job.get("source"),
            "Apply": job.get("apply_url")
        })

    st.dataframe(
        table_data,
        use_container_width=True
    )

else:

    st.info("Run matching to see results.")

# ============================================
# COVER LETTER VIEWER
# ============================================

st.header("📝 Generated Cover Letters")

letters_dir = "output/cover_letters"

files = os.listdir(letters_dir)

if files:

    selected = st.selectbox(
        "Select a cover letter",
        files
    )

    with open(
        os.path.join(letters_dir, selected),
        "r",
        encoding="utf-8"
    ) as f:
        content = f.read()

    st.text_area(
        "Preview",
        content,
        height=300
    )

else:

    st.info("No cover letters generated yet.")

# ============================================
# LIVE RUN LOG DISPLAY
# ============================================

st.header("🖥️ Execution Logs")

if os.path.exists(LOG_FILE):

    with open(LOG_FILE, "r", encoding="utf-8") as f:
        logs = f.read()

    st.text_area(
        "Live system output",
        logs,
        height=400
    )

else:

    st.info("No logs available yet.")
