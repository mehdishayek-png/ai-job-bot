import streamlit as st
import json
import os
import re
import uuid
import time
from dotenv import load_dotenv

# ============================================
# PAGE CONFIG — MUST BE FIRST
# ============================================

st.set_page_config(
    page_title="JobBot · AI Job Matcher",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ============================================
# CUSTOM CSS
# ============================================

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:ital,opsz,wght@0,9..40,300;0,9..40,500;0,9..40,700;1,9..40,400&family=JetBrains+Mono:wght@400;500&display=swap');

.stApp {
    font-family: 'DM Sans', sans-serif;
}
h1, h2, h3, .stMarkdown h1, .stMarkdown h2, .stMarkdown h3 {
    font-family: 'DM Sans', sans-serif !important;
    font-weight: 700 !important;
}

/* Hero banner */
.hero-banner {
    background: linear-gradient(135deg, #0f172a 0%, #1e3a5f 50%, #0ea5e9 100%);
    padding: 2.5rem 2rem;
    border-radius: 16px;
    margin-bottom: 1.5rem;
    position: relative;
    overflow: hidden;
}
.hero-banner::before {
    content: '';
    position: absolute;
    top: -50%;
    right: -20%;
    width: 400px;
    height: 400px;
    background: radial-gradient(circle, rgba(14,165,233,0.15) 0%, transparent 70%);
    border-radius: 50%;
}
.hero-banner h1 {
    color: #f0f9ff !important;
    font-size: 2rem !important;
    margin: 0 0 0.3rem 0 !important;
    letter-spacing: -0.02em;
}
.hero-banner p {
    color: #93c5fd;
    font-size: 1rem;
    margin: 0;
}

/* Welcome card */
.welcome-card {
    background: linear-gradient(135deg, #ecfdf5 0%, #f0f9ff 100%);
    border: 1px solid #a7f3d0;
    border-radius: 12px;
    padding: 1.2rem 1.5rem;
    margin-bottom: 1rem;
}
.welcome-card h3 {
    color: #065f46 !important;
    margin: 0 0 0.2rem 0 !important;
    font-size: 1.2rem !important;
}
.welcome-card p {
    color: #047857;
    margin: 0;
    font-size: 0.95rem;
}

/* Section cards */
.section-card {
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 14px;
    padding: 1.5rem;
    margin-bottom: 1rem;
    box-shadow: 0 1px 3px rgba(0,0,0,0.04);
}
.section-card h3 {
    color: #0f172a !important;
    font-size: 1.1rem !important;
    margin-bottom: 0.8rem !important;
}

/* Skill chips */
.skill-chips {
    display: flex;
    flex-wrap: wrap;
    gap: 0.4rem;
    margin-top: 0.5rem;
}
.skill-chip {
    background: #eff6ff;
    color: #1e40af;
    padding: 0.3rem 0.75rem;
    border-radius: 20px;
    font-size: 0.82rem;
    font-weight: 500;
    border: 1px solid #bfdbfe;
    white-space: nowrap;
}

/* Match score badges */
.match-score-high {
    display: inline-block;
    background: #059669;
    color: white;
    padding: 0.25rem 0.7rem;
    border-radius: 8px;
    font-size: 0.85rem;
    font-weight: 700;
}
.match-score-med {
    display: inline-block;
    background: #d97706;
    color: white;
    padding: 0.25rem 0.7rem;
    border-radius: 8px;
    font-size: 0.85rem;
    font-weight: 700;
}

/* Cover letter box */
.cl-box {
    background: #f8fafc;
    border: 1px solid #e2e8f0;
    border-radius: 10px;
    padding: 1rem 1.2rem;
    margin-top: 0.8rem;
    font-size: 0.9rem;
    line-height: 1.6;
    color: #334155;
    white-space: pre-wrap;
}
.cl-label {
    font-size: 0.78rem;
    font-weight: 600;
    color: #64748b;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    margin-bottom: 0.4rem;
}

/* Step indicator */
.step-indicator {
    display: flex;
    justify-content: center;
    gap: 0.5rem;
    margin: 1rem 0 1.5rem 0;
    flex-wrap: wrap;
}
.step-dot {
    display: flex;
    align-items: center;
    gap: 0.4rem;
    padding: 0.4rem 0.9rem;
    border-radius: 20px;
    font-size: 0.82rem;
    font-weight: 500;
}
.step-dot.done {
    background: #ecfdf5;
    color: #059669;
    border: 1px solid #a7f3d0;
}
.step-dot.active {
    background: #eff6ff;
    color: #2563eb;
    border: 1px solid #93c5fd;
}
.step-dot.pending {
    background: #f9fafb;
    color: #9ca3af;
    border: 1px solid #e5e7eb;
}

/* Buttons */
.stButton > button {
    border-radius: 10px !important;
    font-weight: 600 !important;
    padding: 0.5rem 1.2rem !important;
    font-family: 'DM Sans', sans-serif !important;
}
div[data-testid="stExpander"] {
    border: 1px solid #e2e8f0 !important;
    border-radius: 12px !important;
    margin-bottom: 0.5rem !important;
}
</style>
""", unsafe_allow_html=True)

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
        "Go to **App settings → Secrets** and add:\n\n"
        '`OPENROUTER_API_KEY = "your-key-here"`'
    )
    st.stop()

# ============================================
# INTERNAL IMPORTS
# ============================================

from resume_parser import build_profile
from run_auto_apply import run_auto_apply_pipeline

# ============================================
# SESSION ISOLATION
# ============================================

if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())[:8]

SID = st.session_state.session_id
SESSION_DIR = f"data/session_{SID}"
SESSION_OUTPUT_DIR = f"output/session_{SID}"
LETTERS_DIR = os.path.join(SESSION_OUTPUT_DIR, "cover_letters")

for d in [SESSION_DIR, SESSION_OUTPUT_DIR, LETTERS_DIR]:
    os.makedirs(d, exist_ok=True)

PROFILE_FILE = os.path.join(SESSION_DIR, "profile.json")
JOBS_FILE = os.path.join(SESSION_DIR, "jobs.json")
MATCHES_FILE = os.path.join(SESSION_DIR, "matched_jobs.json")
CACHE_FILE = os.path.join(SESSION_DIR, "semantic_cache.json")
LOG_FILE = os.path.join(SESSION_DIR, "run_log.txt")

# ============================================
# HELPERS
# ============================================

def load_json(path):
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
        json.dump(data, f, indent=2, ensure_ascii=False)


def strip_html(text):
    """Remove HTML tags and decode entities for clean display."""
    if not text:
        return ""
    clean = re.sub(r'<[^>]+>', ' ', text)
    clean = clean.replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>')
    clean = clean.replace('&quot;', '"').replace('&#39;', "'").replace('&nbsp;', ' ')
    clean = re.sub(r'\s+', ' ', clean).strip()
    return clean


def sanitize_filename(s, max_length=50):
    """Mirror the sanitize logic from cover_letter_generator."""
    if not s:
        return "unnamed"
    s = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '', s)
    s = re.sub(r'\s+', '_', s)
    s = re.sub(r'_+', '_', s)
    s = s.strip('. ')
    return s[:max_length] if s else "unnamed"


def find_cover_letter(company, title, letters_dir):
    """Find cover letter file matching a job, return (content, filename) or (None, None)."""
    if not os.path.exists(letters_dir):
        return None, None

    # Exact match first (mirrors cover_letter_generator naming)
    expected = f"{sanitize_filename(company)}__{sanitize_filename(title)}.txt"
    path = os.path.join(letters_dir, expected)
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return f.read(), expected
        except Exception:
            pass

    # Fuzzy fallback: match on company + partial title
    sc = sanitize_filename(company).lower()
    st_partial = sanitize_filename(title).lower()[:20]
    for fname in os.listdir(letters_dir):
        if fname.endswith(".txt"):
            fl = fname.lower()
            if sc in fl and st_partial in fl:
                try:
                    with open(os.path.join(letters_dir, fname), "r", encoding="utf-8") as f:
                        return f.read(), fname
                except Exception:
                    pass

    return None, None


# ============================================
# LOAD PROFILE FROM DISK
# ============================================

_disk_profile = load_json(PROFILE_FILE)
if isinstance(_disk_profile, dict) and _disk_profile.get("skills"):
    profile = _disk_profile
else:
    profile = {"name": "", "headline": "", "skills": []}

has_profile = bool(profile.get("skills"))
has_matches = isinstance(load_json(MATCHES_FILE), list) and len(load_json(MATCHES_FILE)) > 0

# ============================================
# HERO BANNER
# ============================================

st.markdown("""
<div class="hero-banner">
    <h1>🎯 JobBot</h1>
    <p>AI-powered job matching · Resume parsing · Auto cover letters</p>
</div>
""", unsafe_allow_html=True)

# ============================================
# WELCOME GREETING
# ============================================

if has_profile and profile.get("name") and profile["name"] != "Candidate":
    st.markdown(f"""
    <div class="welcome-card">
        <h3>Welcome back, {profile["name"]} 👋</h3>
        <p>{profile.get("headline", "")} · {len(profile.get("skills", []))} skills loaded</p>
    </div>
    """, unsafe_allow_html=True)

# ============================================
# PROGRESS INDICATOR
# ============================================

step1_class = "done" if has_profile else "active"
step2_class = "done" if has_profile else "pending"
step3_class = "done" if has_matches else ("active" if has_profile else "pending")
step4_class = "done" if has_matches else "pending"

st.markdown(f"""
<div class="step-indicator">
    <div class="step-dot {step1_class}">{"✓" if has_profile else "1"} Upload Resume</div>
    <div class="step-dot {step2_class}">{"✓" if has_profile else "2"} Profile</div>
    <div class="step-dot {step3_class}">{"✓" if has_matches else "3"} Match Jobs</div>
    <div class="step-dot {step4_class}">{"✓" if has_matches else "4"} Cover Letters</div>
</div>
""", unsafe_allow_html=True)

# ============================================
# SIDEBAR
# ============================================

with st.sidebar:
    st.markdown("### ⚙️ Session")
    st.caption(f"ID: `{SID}`")
    if st.button("🔄 Start Fresh Session"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()
    st.divider()
    st.markdown("### How it works")
    st.markdown(
        "1. **Upload** your resume PDF\n"
        "2. **Review** extracted profile\n"
        "3. **Run matching** against live jobs\n"
        "4. **Read & download** tailored cover letters"
    )

# ============================================
# LAYOUT — two columns for upload + profile
# ============================================

col_left, col_right = st.columns([1, 1], gap="large")

# ============================================
# LEFT: UPLOAD + PARSE
# ============================================

with col_left:
    st.markdown('<div class="section-card"><h3>📄 Resume Upload</h3>', unsafe_allow_html=True)

    uploaded = st.file_uploader(
        "Drop your resume here",
        type=["pdf"],
        label_visibility="collapsed",
        help="PDF format only",
    )

    if uploaded:
        save_path = os.path.join(SESSION_DIR, uploaded.name)

        if st.session_state.get("_uploaded_name") != uploaded.name:
            file_bytes = uploaded.getvalue()
            with open(save_path, "wb") as f:
                f.write(file_bytes)
            st.session_state["_uploaded_name"] = uploaded.name
            st.session_state["_uploaded_path"] = save_path
            st.session_state.pop("_profile_built", None)

        save_path = st.session_state.get("_uploaded_path", save_path)
        st.success(f"📎 {uploaded.name}")

        if not st.session_state.get("_profile_built"):
            if st.button("🧠 Parse Resume & Build Profile", use_container_width=True):
                with st.spinner("Extracting skills, name, and headline…"):
                    try:
                        build_profile(save_path, output_path=PROFILE_FILE)

                        if os.path.exists(PROFILE_FILE):
                            with open(PROFILE_FILE, "r") as f:
                                saved = json.load(f)
                            st.session_state["_profile_built"] = True
                            for k in ("name_input", "headline_input", "skills_input"):
                                st.session_state.pop(k, None)
                            st.success(
                                f"✅ {saved.get('name', 'Profile')} — "
                                f"{len(saved.get('skills', []))} skills found"
                            )
                            time.sleep(0.5)
                            st.rerun()
                        else:
                            st.error("❌ Profile file was not created.")
                    except Exception as e:
                        st.error(f"❌ {e}")
                        st.exception(e)
        else:
            st.info("✅ Resume parsed. Upload a new file to re-parse.")
    else:
        st.caption("Supported: PDF files up to 200 MB")

    st.markdown('</div>', unsafe_allow_html=True)

# ============================================
# RIGHT: PROFILE DISPLAY + EDIT
# ============================================

with col_right:
    st.markdown('<div class="section-card"><h3>👤 Your Profile</h3>', unsafe_allow_html=True)

    if has_profile:
        display_name = profile.get("name", "Candidate")
        display_headline = profile.get("headline", "")

        if display_name and display_name != "Candidate":
            st.markdown(f"**{display_name}**")
        if display_headline:
            st.caption(display_headline)

        skills = profile.get("skills", [])
        if skills:
            chips_html = "".join(f'<span class="skill-chip">{s}</span>' for s in skills)
            st.markdown(f'<div class="skill-chips">{chips_html}</div>', unsafe_allow_html=True)
            st.caption(f"{len(skills)} skills · parsed from resume")
        else:
            st.info("No skills extracted. Add them manually below.")
    else:
        st.markdown(
            '<p style="color:#9ca3af;">No profile yet — upload a resume or fill in manually below.</p>',
            unsafe_allow_html=True,
        )

    st.markdown('</div>', unsafe_allow_html=True)

    with st.expander(
        "✏️ Edit profile manually" if has_profile else "✏️ Create profile manually",
        expanded=not has_profile,
    ):
        name_val = st.text_input("Full Name", key="name_input", placeholder="Your full name")
        headline_input = st.text_input(
            "Professional Headline",
            key="headline_input",
            placeholder="e.g. Customer Success Manager | SaaS",
        )
        skills_input = st.text_area(
            "Skills / Keywords (one per line)",
            height=150,
            key="skills_input",
            placeholder="salesforce\nzendesk\ncustomer success\nsaas\n...",
        )

        if st.button("💾 Save Profile", use_container_width=True):
            skills_list = [s.strip() for s in skills_input.split("\n") if s.strip()]
            if not skills_list and not name_val:
                st.error("❌ Please enter at least a name or some skills")
            else:
                updated = {
                    "name": name_val if name_val else "Candidate",
                    "headline": headline_input,
                    "skills": skills_list,
                }
                save_json(PROFILE_FILE, updated)
                st.success("✅ Saved!")
                for k in ("name_input", "headline_input", "skills_input"):
                    st.session_state.pop(k, None)
                st.session_state.pop("_matching_done", None)
                time.sleep(0.3)
                st.rerun()

# ============================================
# JOB MATCHING SECTION
# ============================================

st.markdown("---")
st.markdown('<div class="section-card"><h3>🚀 Job Matching</h3>', unsafe_allow_html=True)

profile_ready = bool(profile.get("skills") and len(profile.get("skills", [])) > 0)

if not profile_ready:
    st.info("⚠️ Add at least one skill to your profile above to unlock job matching.")
else:
    with st.expander("📁 Upload custom jobs.json (optional)"):
        jobs_upload = st.file_uploader(
            "Upload jobs.json",
            type=["json"],
            key="jobs_upload",
            label_visibility="collapsed",
        )
        if jobs_upload:
            if st.session_state.get("_jobs_uploaded_name") != jobs_upload.name:
                try:
                    jobs_data = json.loads(jobs_upload.getvalue())
                    save_json(JOBS_FILE, jobs_data)
                    st.session_state["_jobs_uploaded_name"] = jobs_upload.name
                    st.success(f"✅ {len(jobs_data)} jobs loaded")
                except Exception as e:
                    st.error(f"Invalid JSON: {e}")

    # Run guards
    if st.session_state.get("_matching_done"):
        st.success("✅ Matching complete — scroll down to see results.")
        if st.button("🔄 Re-run with fresh jobs"):
            st.session_state.pop("_matching_done", None)
            st.session_state.pop("_matching_running", None)
            for fp in [JOBS_FILE, MATCHES_FILE, CACHE_FILE]:
                if os.path.exists(fp):
                    os.remove(fp)
            if os.path.exists(LETTERS_DIR):
                for lf in os.listdir(LETTERS_DIR):
                    os.remove(os.path.join(LETTERS_DIR, lf))
            st.rerun()

    elif st.session_state.get("_matching_running"):
        st.warning("⏳ Pipeline is running — please wait...")

    else:
        st.markdown(
            "Fetches live jobs from **WeWorkRemotely**, **RemoteOK**, "
            "and **Remotive**, then scores each against your profile."
        )
        if st.button("▶ Start Matching", type="primary", use_container_width=True):
            st.session_state["_matching_running"] = True

            status_box = st.empty()
            log_container = st.empty()
            log_lines = []

            def _progress(msg):
                log_lines.append(msg)
                log_container.code("\n".join(log_lines[-20:]), language=None)

            status_box.info("🔍 Fetching jobs and scoring matches... this takes 2–5 min.")

            try:
                result = run_auto_apply_pipeline(
                    profile_file=PROFILE_FILE,
                    jobs_file=JOBS_FILE,
                    matches_file=MATCHES_FILE,
                    cache_file=CACHE_FILE,
                    log_file=LOG_FILE,
                    letters_dir=LETTERS_DIR,
                    progress_callback=_progress,
                )

                st.session_state["_matching_done"] = True
                st.session_state.pop("_matching_running", None)

                if result and result.get("status") == "success":
                    status_box.success(
                        f"✅ {result['matches']} matches from {result['total_scored']} jobs"
                    )
                elif result and result.get("status") == "no_matches":
                    status_box.warning("No strong matches found. Try adding more skills.")
                else:
                    status_box.error(f"Pipeline returned: {result}")

                time.sleep(1)
                st.rerun()

            except Exception as e:
                st.session_state.pop("_matching_running", None)
                status_box.error(f"❌ {e}")
                st.exception(e)

st.markdown('</div>', unsafe_allow_html=True)

# ============================================
# MATCH RESULTS — with embedded cover letters
# ============================================

matches_data = load_json(MATCHES_FILE)

if isinstance(matches_data, list) and matches_data:
    st.markdown("---")
    st.markdown(f"### 📊 Top {len(matches_data)} Matches")
    st.caption("Each match includes the job details, your compatibility score, and a tailored cover letter.")

    for i, job in enumerate(matches_data, 1):
        score = job.get("match_score", 0)
        score_class = "match-score-high" if score >= 85 else "match-score-med"
        company = job.get("company", "Unknown")
        title = job.get("title", "Unknown")
        source = job.get("source", "")

        # Clean summary — strip all HTML
        raw_summary = job.get("summary", "")
        clean_summary = strip_html(raw_summary)
        if len(clean_summary) > 350:
            clean_summary = clean_summary[:350] + "…"

        with st.expander(f"#{i}  ·  {company} — {title}  ({score}%)"):
            # ---- Top row: job info + score badge ----
            c_info, c_score = st.columns([4, 1])

            with c_info:
                st.markdown(f"**{title}**")
                st.caption(f"🏢 {company}  ·  via {source}")
                if clean_summary:
                    st.write(clean_summary)

            with c_score:
                st.markdown(
                    f'<div style="text-align:center; margin-top:0.3rem;">'
                    f'<span class="{score_class}">{score}%</span>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
                if job.get("apply_url"):
                    st.link_button("🔗 Apply", job["apply_url"], use_container_width=True)

            # ---- Cover letter embedded below ----
            cl_content, cl_filename = find_cover_letter(company, title, LETTERS_DIR)

            if cl_content:
                st.markdown("---")
                st.markdown(
                    '<p class="cl-label">📝 Tailored Cover Letter</p>',
                    unsafe_allow_html=True,
                )
                st.markdown(
                    f'<div class="cl-box">{cl_content}</div>',
                    unsafe_allow_html=True,
                )
                # Download button for this cover letter
                st.download_button(
                    "📥 Download Cover Letter",
                    data=cl_content,
                    file_name=cl_filename or f"cover_letter_{i}.txt",
                    mime="text/plain",
                    key=f"dl_cl_{i}",
                    use_container_width=True,
                )

# ============================================
# FOOTER
# ============================================

st.markdown("---")
st.caption(
    "Built with Streamlit · Each session is isolated · "
    "Click **Start Fresh Session** in the sidebar to begin again."
)
