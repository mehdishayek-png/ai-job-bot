import streamlit as st
import os
import json

from resume_parser import parse_resume

# ============================================
# CONFIG
# ============================================

PROFILE_PATH = "data/profile.json"
UPLOAD_PATH = "data/uploaded_resume.pdf"

os.makedirs("data", exist_ok=True)

# ============================================
# UI HEADER
# ============================================

st.set_page_config(page_title="AI Job Bot", layout="wide")

st.title("🤖 AI Job Application Bot")

st.markdown(
"""
Upload your resume → Build profile → Auto-match jobs → Generate cover letters.
"""
)

# ============================================
# RESUME UPLOAD
# ============================================

st.header("📄 Resume Upload")

uploaded_file = st.file_uploader(
    "Upload your resume (PDF)",
    type=["pdf"]
)

if uploaded_file:

    # Save uploaded resume
    with open(UPLOAD_PATH, "wb") as f:
        f.write(uploaded_file.read())

    st.success("Resume uploaded successfully.")

    # ----------------------------------------
    # PARSE RESUME
    # ----------------------------------------

    if st.button("Build Profile from Resume"):

        with st.spinner("Parsing resume..."):

            profile = parse_resume(UPLOAD_PATH)

            with open(PROFILE_PATH, "w", encoding="utf-8") as f:
                json.dump(profile, f, indent=2)

        st.success("Profile built successfully.")

        st.subheader("Extracted Keywords")

        for skill in profile.get("skills", []):
            st.write("•", skill)

# ============================================
# PROFILE VIEWER
# ============================================

st.header("👤 Current Profile")

if os.path.exists(PROFILE_PATH):

    with open(PROFILE_PATH, "r", encoding="utf-8") as f:
        profile = json.load(f)

    st.json(profile)

else:
    st.info("No profile found. Upload resume first.")

# ============================================
# RUN AUTO APPLY
# ============================================

st.header("🚀 Run Auto Apply")

if st.button("Run Job Matching"):

    with st.spinner("Running matcher..."):
        os.system("python run_auto_apply.py")

    st.success("Matching complete. Check terminal + outputs.")

