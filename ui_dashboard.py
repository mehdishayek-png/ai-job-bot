import streamlit as st
import json
import os
from dotenv import load_dotenv

# ============================================
# LOAD API KEY EARLY - STREAMLIT COMPATIBLE
# ============================================

# Try Streamlit secrets first, then fall back to .env
try:
    api_key = st.secrets["OPENROUTER_API_KEY"]
    st.success("✅ API key loaded from Streamlit secrets")
except (KeyError, AttributeError):
    load_dotenv()
    api_key = os.getenv("OPENROUTER_API_KEY")
    if api_key:
        st.info("✅ API key loaded from .env file")

# Validate API key exists
if not api_key:
    st.error("❌ OPENROUTER_API_KEY not found!")
    st.info("Please add your API key to Streamlit Cloud secrets")
    st.markdown("""
    **How to add secrets:**
    1. Go to your app settings in Streamlit Cloud
    2. Navigate to "Secrets" section
    3. Add: `OPENROUTER_API_KEY = "your-key-here"`
    """)
    st.stop()

# Internal imports (after API key validation)
from resume_parser import build_profile

# Import run_auto_apply but handle if it fails
try:
    from run_auto_apply import main as run_auto_apply_pipeline
except Exception as e:
    st.warning(f"Auto-apply module import warning: {str(e)}")
    run_auto_apply_pipeline = None

# ============================================
# CONFIG
# ============================================

st.set_page_config(
    page_title="AI Job Application Bot",
    layout="wide"
)

PROFILE_FILE = "data/profile.json"
MATCHES_FILE = "data/matched_jobs.json"
LETTERS_DIR = "output/cover_letters"

os.makedirs("data", exist_ok=True)
os.makedirs(LETTERS_DIR, exist_ok=True)

# ============================================
# HELPERS
# ============================================

def load_json(path):
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            st.warning(f"Failed to load {path}: {str(e)}")
            return {}
    return {}

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

profile = load_json(PROFILE_FILE)

if uploaded:

    save_path = f"data/{uploaded.name}"

    with open(save_path, "wb") as f:
        f.write(uploaded.read())

    st.success("Resume uploaded successfully.")

    if st.button("🧠 Build Profile From Resume"):

        with st.spinner("Parsing resume..."):

            try:
                build_profile(save_path)
                st.success("✅ Profile built successfully!")
                profile = load_json(PROFILE_FILE)
                
            except Exception as e:
                st.error(f"❌ Profile building failed: {str(e)}")
                st.exception(e)

# ============================================
# EXTRACTION RESULTS
# ============================================

st.header("🧠 Extraction Results")

if profile and profile.get("skills"):

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Extracted Skills")
        st.write(f"Total skills: {len(profile.get('skills', []))}")

        if profile.get("skills"):
            for skill in profile.get("skills", []):
                st.write(f"• {skill}")

    with col2:
        st.subheader("Professional Headline")
        headline = profile.get("headline", "Not detected")
        if headline and headline != "Not detected":
            st.write(headline)
        else:
            st.info("No headline detected - you can add one below")

else:
    st.info("📤 Upload and parse a resume to see extracted information")

# ============================================
# EDITABLE PROFILE
# ============================================

st.header("👤 Editable Profile")

if not profile:
    profile = {"name": "", "skills": [], "headline": ""}

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
    height=200,
    help="Add skills that match the jobs you're targeting"
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

    with open(PROFILE_FILE, "w", encoding="utf-8") as f:
        json.dump(updated, f, indent=2)

    st.success("✅ Profile saved successfully!")
    st.rerun()

# ============================================
# RUN AUTO APPLY
# ============================================

st.header("🚀 Run Auto Apply")

if not profile or not profile.get("skills"):
    st.warning("⚠️ Please create a profile first before running job matching")
else:
    if st.button("▶ Run Job Matching"):

        if run_auto_apply_pipeline is None:
            st.error("❌ Auto-apply module not available")
        else:
            with st.spinner("Running job matching pipeline..."):

                try:
                    # Create a progress container
                    progress_container = st.empty()
                    
                    progress_container.info("🔍 Fetching jobs...")
                    run_auto_apply_pipeline()
                    
                    progress_container.success("✅ Matching complete!")
                    st.rerun()
                    
                except Exception as e:
                    st.error(f"❌ Pipeline failed: {str(e)}")
                    st.exception(e)

# ============================================
# MATCH RESULTS
# ============================================

matches = load_json(MATCHES_FILE)

st.header("📊 Semantic Match Results")

if matches:

    st.success(f"Found {len(matches)} matching jobs!")

    for i, job in enumerate(matches, 1):
        
        with st.expander(f"#{i} - {job.get('company')} - {job.get('title')} ({job.get('match_score')}%)"):
            st.write(f"**Company:** {job.get('company')}")
            st.write(f"**Title:** {job.get('title')}")
            st.write(f"**Match Score:** {job.get('match_score')}%")
            st.write(f"**Source:** {job.get('source')}")
            
            if job.get('summary'):
                st.write(f"**Description:** {job.get('summary')[:200]}...")
            
            if job.get('apply_url'):
                st.link_button("Apply Now", job.get('apply_url'))

else:
    st.info("Run matching to see results here")

# ============================================
# COVER LETTER VIEWER
# ============================================

st.header("📝 Generated Cover Letters")

if os.path.exists(LETTERS_DIR):

    files = [f for f in os.listdir(LETTERS_DIR) if f.endswith('.txt')]

    if files:

        st.success(f"Generated {len(files)} cover letters")

        selected = st.selectbox(
            "Select a cover letter to view",
            files
        )

        if selected:
            try:
                with open(
                    os.path.join(LETTERS_DIR, selected),
                    "r",
                    encoding="utf-8"
                ) as f:
                    content = f.read()

                st.text_area(
                    "Cover Letter Preview",
                    content,
                    height=300
                )
                
                # Add download button
                st.download_button(
                    label="📥 Download Cover Letter",
                    data=content,
                    file_name=selected,
                    mime="text/plain"
                )
                
            except Exception as e:
                st.error(f"Failed to load cover letter: {str(e)}")

    else:
        st.info("No cover letters generated yet. Run matching to generate them!")

else:
    st.info("No cover letters directory found")

# ============================================
# FOOTER
# ============================================

st.divider()
st.caption("💡 Tip: Check your Streamlit Cloud logs if you encounter any errors")
