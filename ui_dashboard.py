import streamlit as st
import json
import os
import uuid
from dotenv import load_dotenv

# ============================================
# PAGE CONFIG — MUST BE THE VERY FIRST st.* CALL
# ============================================

st.set_page_config(page_title="AI Job Application Bot", layout="wide")

# ============================================
# LOAD API KEY
# ============================================

try:
    api_key = st.secrets["OPENROUTER_API_KEY"]
except (KeyError, AttributeError):
    load_dotenv()
    api_key = os.getenv("OPENROUTER_API_KEY")

if not api_key:
    st.error("❌ OPENROUTER_API_KEY not found!")
    st.markdown(
        """
**How to add secrets on Streamlit Cloud:**
1. Go to your app settings → **Secrets**
2. Add: `OPENROUTER_API_KEY = "your-key-here"`
"""
    )
    st.stop()

# ============================================
# INTERNAL IMPORTS (after key validation)
# ============================================

from resume_parser import build_profile
from run_auto_apply import run_auto_apply_pipeline

# ============================================
# SESSION ISOLATION — unique dirs per browser tab
# ============================================

if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())[:8]

SID = st.session_state.session_id
SESSION_DIR = f"data/session_{SID}"
SESSION_OUTPUT_DIR = f"output/session_{SID}"
LETTERS_DIR = os.path.join(SESSION_OUTPUT_DIR, "cover_letters")

for d in [SESSION_DIR, SESSION_OUTPUT_DIR, LETTERS_DIR]:
    os.makedirs(d, exist_ok=True)

# Paths scoped to this session
PROFILE_FILE = os.path.join(SESSION_DIR, "profile.json")
JOBS_FILE = os.path.join(SESSION_DIR, "jobs.json")
MATCHES_FILE = os.path.join(SESSION_DIR, "matched_jobs.json")
CACHE_FILE = os.path.join(SESSION_DIR, "semantic_cache.json")
LOG_FILE = os.path.join(SESSION_DIR, "run_log.txt")

# ============================================
# HELPERS
# ============================================

def load_json(path):
    """Load JSON file, return {} or [] depending on content, or {} if missing."""
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_json(path, data):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

# ============================================
# HEADER
# ============================================

st.title("🤖 AI Job Application Bot")
st.caption("Upload resume → Extract profile → Match jobs → Generate cover letters")

with st.sidebar:
    st.caption(f"Session: `{SID}`")
    if st.button("🔄 Start New Session"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()

# ============================================
# LOAD PROFILE — always read fresh from disk
# ============================================

_disk_profile = load_json(PROFILE_FILE)
if isinstance(_disk_profile, dict) and _disk_profile.get("skills"):
    profile = _disk_profile
else:
    profile = {"name": "", "headline": "", "skills": []}

# ============================================
# RESUME UPLOAD
# ============================================

st.header("📄 Resume Upload")

uploaded = st.file_uploader("Upload your resume (PDF)", type=["pdf"])

if uploaded:
    save_path = os.path.join(SESSION_DIR, uploaded.name)
    with open(save_path, "wb") as f:
        f.write(uploaded.read())
    st.success("Resume uploaded successfully.")

    if st.button("🧠 Build Profile From Resume"):
        with st.spinner("Parsing resume…"):
            try:
                build_profile(save_path, output_path=PROFILE_FILE)
                st.success("✅ Profile built!")

                # ===================================================
                # FIX: Clear widget keys so text_input/text_area
                # pick up the NEW profile values on rerun.
                # Without this, Streamlit ignores value= because
                # the old value is cached in session_state[key].
                # ===================================================
                for k in ("name_input", "headline_input", "skills_input"):
                    st.session_state.pop(k, None)

                st.rerun()
            except Exception as e:
                st.error(f"❌ Profile building failed: {e}")
                st.exception(e)

# ============================================
# EXTRACTION RESULTS
# ============================================

st.header("🧠 Extraction Results")

if profile.get("skills"):
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Extracted Skills")
        st.write(f"**{len(profile['skills'])}** skills detected")
        for skill in profile["skills"]:
            st.write(f"• {skill}")
    with col2:
        st.subheader("Professional Headline")
        headline = profile.get("headline", "")
        st.write(headline if headline else "_No headline detected — add one below._")
else:
    st.info("📤 Upload and parse a resume to see extracted information.")

# ============================================
# EDITABLE PROFILE
# ============================================

st.header("👤 Editable Profile")

name = st.text_input(
    "Full Name",
    value=profile.get("name", ""),
    key="name_input",
)
headline_val = st.text_input(
    "Professional Headline",
    value=profile.get("headline", ""),
    key="headline_input",
)
skills_text = st.text_area(
    "Skills / Keywords (one per line)",
    value="\n".join(profile.get("skills", [])),
    height=200,
    help="Add skills that match the jobs you're targeting",
    key="skills_input",
)

if st.button("💾 Save Profile"):
    updated = {
        "name": name,
        "headline": headline_val,
        "skills": [s.strip() for s in skills_text.split("\n") if s.strip()],
    }
    save_json(PROFILE_FILE, updated)
    st.success("✅ Profile saved!")

    # Clear widget keys so rerun reads fresh values
    for k in ("name_input", "headline_input", "skills_input"):
        st.session_state.pop(k, None)

    st.rerun()

# ============================================
# RUN AUTO APPLY
# ============================================

st.header("🚀 Run Auto Apply")

if not profile.get("skills"):
    st.warning("⚠️ Please create a profile with skills before running job matching.")
else:
    # Optional custom jobs upload
    st.markdown("_Optionally upload a custom `jobs.json`, or we'll fetch from RSS feeds._")
    jobs_upload = st.file_uploader("Upload jobs.json (optional)", type=["json"], key="jobs_upload")

    if jobs_upload:
        try:
            jobs_data = json.loads(jobs_upload.read())
            save_json(JOBS_FILE, jobs_data)
            st.success(f"Loaded {len(jobs_data)} jobs from upload.")
        except Exception as e:
            st.error(f"Invalid JSON: {e}")

    if st.button("▶ Run Job Matching"):
        status_box = st.empty()
        log_expander = st.expander("📋 Live log", expanded=True)
        log_lines = []

        def _progress(msg):
            log_lines.append(msg)
            with log_expander:
                st.text("\n".join(log_lines[-30:]))

        status_box.info("🔍 Running matching pipeline…")

        try:
            # ===================================================
            # FIX: Pass all session paths as FUNCTION PARAMETERS.
            # No monkey-patching of module globals needed.
            # ===================================================
            result = run_auto_apply_pipeline(
                profile_file=PROFILE_FILE,
                jobs_file=JOBS_FILE,
                matches_file=MATCHES_FILE,
                cache_file=CACHE_FILE,
                log_file=LOG_FILE,
                letters_dir=LETTERS_DIR,
                progress_callback=_progress,
            )

            if result and result.get("status") == "success":
                status_box.success(
                    f"✅ Done — {result['matches']} matches "
                    f"out of {result['total_scored']} jobs scored."
                )
            elif result and result.get("status") == "no_matches":
                status_box.warning(
                    "No jobs met the match threshold. "
                    "Try broadening your skills or uploading different jobs."
                )
            else:
                status_box.error(f"Pipeline returned: {result}")

            st.rerun()
        except Exception as e:
            status_box.error(f"❌ Pipeline failed: {e}")
            st.exception(e)

# ============================================
# MATCH RESULTS
# ============================================

matches = load_json(MATCHES_FILE)

st.header("📊 Semantic Match Results")

if isinstance(matches, list) and matches:
    st.success(f"Found **{len(matches)}** matching jobs!")

    for i, job in enumerate(matches, 1):
        label = (
            f"#{i}  —  {job.get('company', '?')}  ·  "
            f"{job.get('title', '?')}  ({job.get('match_score', '?')}%)"
        )
        with st.expander(label):
            st.write(f"**Company:** {job.get('company')}")
            st.write(f"**Title:** {job.get('title')}")
            st.write(f"**Match Score:** {job.get('match_score')}%")
            st.write(f"**Source:** {job.get('source', 'N/A')}")
            if job.get("summary"):
                st.write(f"**Description:** {job['summary'][:300]}…")
            if job.get("apply_url"):
                st.link_button("🔗 Apply Now", job["apply_url"])
else:
    st.info("Run matching to see results here.")

# ============================================
# COVER LETTER VIEWER
# ============================================

st.header("📝 Generated Cover Letters")

if os.path.exists(LETTERS_DIR):
    files = sorted(f for f in os.listdir(LETTERS_DIR) if f.endswith(".txt"))

    if files:
        st.success(f"Generated **{len(files)}** cover letters")

        selected = st.selectbox("Select a cover letter to view", files)
        if selected:
            try:
                content = open(
                    os.path.join(LETTERS_DIR, selected), "r", encoding="utf-8"
                ).read()
                st.text_area("Cover Letter Preview", content, height=300)
                st.download_button(
                    "📥 Download",
                    data=content,
                    file_name=selected,
                    mime="text/plain",
                )
            except Exception as e:
                st.error(f"Failed to load: {e}")
    else:
        st.info("No cover letters yet. Run matching first!")
else:
    st.info("No cover letters directory found.")

# ============================================
# FOOTER
# ============================================

st.divider()
st.caption(
    "💡 Each session is isolated — click **Start New Session** "
    "in the sidebar to begin fresh."
)
