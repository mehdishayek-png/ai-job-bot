import streamlit as st
import json
import os
import re
import uuid
import time
import io
import zipfile
from dotenv import load_dotenv
from datetime import datetime, timedelta

# ============================================
# PAGE CONFIG — MUST BE FIRST
# ============================================

st.set_page_config(
    page_title="JobBot · AI-Powered Job Matching",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ============================================
# CUSTOM CSS — Clean Glassmorphism Design
# ============================================

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap');

/* ============ GLOBAL ============ */
* { margin: 0; padding: 0; box-sizing: border-box; }

.stApp {
    font-family: 'DM Sans', -apple-system, BlinkMacSystemFont, sans-serif;
    background: #f8f9fc;
}

h1, h2, h3, h4, h5, h6,
.stMarkdown h1, .stMarkdown h2, .stMarkdown h3 {
    font-family: 'DM Sans', sans-serif !important;
    font-weight: 700 !important;
    letter-spacing: -0.02em;
    color: #1a1a2e !important;
}

p, li, span, div { color: #3d3d56; }

code, .stCode, pre {
    font-family: 'JetBrains Mono', monospace !important;
}

/* ============ HERO ============ */
.hero {
    background: linear-gradient(135deg, #6c5ce7 0%, #a29bfe 60%, #74b9ff 100%);
    border-radius: 20px;
    padding: 2.5rem 2rem;
    margin-bottom: 1.5rem;
    position: relative;
    overflow: hidden;
    box-shadow: 0 4px 24px rgba(108, 92, 231, 0.2);
}

.hero::before {
    content: '';
    position: absolute;
    top: -40%;
    right: -15%;
    width: 400px;
    height: 400px;
    background: radial-gradient(circle, rgba(255,255,255,0.15) 0%, transparent 70%);
    filter: blur(40px);
}

.hero-content { position: relative; z-index: 1; }

.hero h1 {
    color: #ffffff !important;
    font-size: 2.5rem !important;
    font-weight: 800 !important;
    margin: 0 0 0.4rem 0 !important;
    line-height: 1.1;
}

.hero-subtitle {
    color: rgba(255,255,255,0.85);
    font-size: 1.05rem;
    margin: 0 0 1.2rem 0;
    font-weight: 400;
    line-height: 1.5;
}

.hero-tags {
    display: flex;
    gap: 0.6rem;
    flex-wrap: wrap;
    margin-top: 1rem;
}

.hero-tag {
    background: rgba(255,255,255,0.2);
    backdrop-filter: blur(8px);
    border: 1px solid rgba(255,255,255,0.3);
    color: #fff;
    padding: 0.4rem 0.85rem;
    border-radius: 10px;
    font-size: 0.8rem;
    font-weight: 600;
}

/* ============ STEPPER ============ */
.stepper {
    display: flex;
    justify-content: center;
    align-items: center;
    gap: 0.75rem;
    margin: 1.5rem 0 2rem;
    padding: 1rem;
    background: #fff;
    border: 1px solid #e8e8f0;
    border-radius: 16px;
    box-shadow: 0 1px 4px rgba(0,0,0,0.04);
    flex-wrap: wrap;
}

.step {
    display: flex;
    align-items: center;
    gap: 0.6rem;
    padding: 0.6rem 1rem;
    border-radius: 10px;
    font-size: 0.85rem;
    font-weight: 600;
    color: #6c6c8a;
}

.step-icon {
    width: 32px; height: 32px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 1rem;
}

.step.done { color: #059669; }
.step.done .step-icon {
    background: #059669;
    color: #fff;
    box-shadow: 0 2px 8px rgba(5,150,105,0.25);
}

.step.active {
    color: #6c5ce7;
    background: #f0edff;
}
.step.active .step-icon {
    background: #6c5ce7;
    color: #fff;
    box-shadow: 0 2px 8px rgba(108,92,231,0.3);
    animation: pulse 2s ease-in-out infinite;
}

.step.pending { color: #c0c0d0; }
.step.pending .step-icon {
    background: #f0f0f5;
    border: 2px dashed #d0d0dd;
}

.step-connector {
    width: 40px; height: 2px;
    background: #e0e0ea;
}

@keyframes pulse {
    0%, 100% { transform: scale(1); }
    50% { transform: scale(1.08); }
}

/* ============ GLASS CARD ============ */
.glass-card {
    background: #ffffff;
    border: 1px solid #e8e8f0;
    border-radius: 16px;
    padding: 1.75rem;
    margin-bottom: 1.25rem;
    transition: all 0.2s ease;
    box-shadow: 0 1px 4px rgba(0,0,0,0.04);
}

.glass-card:hover {
    border-color: #d0cfe8;
    box-shadow: 0 4px 16px rgba(108,92,231,0.08);
}

.card-header {
    display: flex;
    align-items: center;
    gap: 0.85rem;
    margin-bottom: 1.25rem;
}

.card-icon {
    width: 42px; height: 42px;
    border-radius: 12px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 1.3rem;
    background: #f0edff;
    border: 1px solid #e0dcf5;
}

.card-title {
    font-size: 1.2rem !important;
    font-weight: 700 !important;
    color: #1a1a2e !important;
    margin: 0 !important;
}

/* ============ FILE UPLOADER ============ */
.stFileUploader section {
    padding: 1.5rem !important;
    background: linear-gradient(135deg, #f8f9fc 0%, #f0edff 100%) !important;
    border: 2px dashed #d0cfe8 !important;
    border-radius: 12px !important;
    transition: all 0.3s ease !important;
}

.stFileUploader section:hover {
    border-color: #6c5ce7 !important;
    background: linear-gradient(135deg, #f0edff 0%, #e8e3ff 100%) !important;
}

/* ============ PROFILE BOX ============ */
.profile-box {
    background: #fff;
    border: 1px solid #e8e8f0;
    border-radius: 14px;
    padding: 1.5rem;
    margin: 1.5rem 0;
    box-shadow: 0 1px 4px rgba(0,0,0,0.04);
}

.profile-name {
    font-size: 1.4rem !important;
    font-weight: 800 !important;
    color: #1a1a2e !important;
    margin: 0 0 0.3rem 0 !important;
}

.profile-headline {
    font-size: 1rem !important;
    color: #6c5ce7 !important;
    font-weight: 600 !important;
    margin-bottom: 0.8rem !important;
}

/* ============ SKILLS ============ */
.skills-container {
    display: flex;
    flex-wrap: wrap;
    gap: 0.6rem;
    margin-top: 0.75rem;
}

.skill-chip {
    background: #f0edff;
    border: 1px solid #e0dcf5;
    color: #6c5ce7;
    padding: 0.4rem 0.85rem;
    border-radius: 8px;
    font-size: 0.82rem;
    font-weight: 600;
    transition: all 0.2s ease;
}

.skill-chip:hover {
    background: #e8e3ff;
    border-color: #d0cfe8;
}

/* ============ STATS ============ */
.stats-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
    gap: 1rem;
    margin: 1.5rem 0 2rem;
}

.stat-card {
    background: #fff;
    border: 1px solid #e8e8f0;
    border-radius: 14px;
    padding: 1.25rem 1rem;
    text-align: center;
    box-shadow: 0 1px 4px rgba(0,0,0,0.04);
    transition: all 0.2s ease;
}

.stat-card:hover {
    border-color: #d0cfe8;
    box-shadow: 0 4px 12px rgba(108,92,231,0.1);
}

.stat-value {
    font-size: 2rem;
    font-weight: 800;
    color: #6c5ce7;
    line-height: 1;
    margin-bottom: 0.3rem;
}

.stat-label {
    color: #8888a0;
    font-size: 0.8rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.04em;
}

/* ============ SCORE BADGES ============ */
.score-badge {
    display: inline-block;
    padding: 0.4rem 1rem;
    border-radius: 10px;
    font-size: 0.95rem;
    font-weight: 700;
    text-align: center;
}

.score-excellent {
    background: #ecfdf5;
    color: #059669;
    border: 1px solid #a7f3d0;
}
.score-good {
    background: #fffbeb;
    color: #d97706;
    border: 1px solid #fde68a;
}
.score-fair {
    background: #f0edff;
    color: #6c5ce7;
    border: 1px solid #e0dcf5;
}

/* ============ SOURCE & DATE BADGES ============ */
.source-badge {
    display: inline-block;
    padding: 0.25rem 0.65rem;
    border-radius: 6px;
    font-size: 0.7rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    background: #eef2ff;
    color: #6366f1;
    border: 1px solid #ddd6fe;
}

.date-badge {
    display: inline-block;
    padding: 0.3rem 0.75rem;
    border-radius: 6px;
    font-size: 0.75rem;
    font-weight: 600;
    background: #f3f4f6;
    color: #6b7280;
    border: 1px solid #e5e7eb;
}

.date-badge.fresh {
    background: #ecfdf5;
    color: #059669;
    border-color: #a7f3d0;
}

.date-badge.recent {
    background: #fed7aa;
    color: #ea580c;
    border-color: #fdba74;
}

/* ============ BUTTONS ============ */
.stButton > button {
    background: #6c5ce7 !important;
    color: white !important;
    border: none !important;
    border-radius: 10px !important;
    padding: 0.65rem 1.25rem !important;
    font-weight: 600 !important;
    font-size: 0.95rem !important;
    transition: all 0.2s ease !important;
    box-shadow: 0 2px 8px rgba(108,92,231,0.2) !important;
}

.stButton > button:hover {
    background: #5b4bd5 !important;
    transform: translateY(-1px) !important;
    box-shadow: 0 4px 12px rgba(108,92,231,0.3) !important;
}

/* ============ APPLY BUTTON - VIBRANT ============ */
div[data-testid="baseButton-secondary"] a {
    background: linear-gradient(135deg, #ff6b35 0%, #ff8555 100%) !important;
    color: white !important;
    border: none !important;
    border-radius: 10px !important;
    padding: 0.65rem 1.25rem !important;
    font-weight: 700 !important;
    font-size: 0.95rem !important;
    box-shadow: 0 4px 12px rgba(255, 107, 53, 0.3) !important;
    text-decoration: none !important;
    display: inline-block !important;
    text-align: center !important;
    transition: all 0.3s ease !important;
}

div[data-testid="baseButton-secondary"] a:hover {
    background: linear-gradient(135deg, #ff5920 0%, #ff7a45 100%) !important;
    transform: translateY(-2px) !important;
    box-shadow: 0 6px 16px rgba(255, 107, 53, 0.4) !important;
}

/* ============ EXPANDERS ============ */
.streamlit-expanderHeader {
    background: #fff !important;
    border: 1px solid #e8e8f0 !important;
    border-radius: 12px !important;
    font-weight: 600 !important;
    color: #1a1a2e !important;
    padding: 0.75rem 1rem !important;
}

/* ============ INPUTS ============ */
.stTextInput > div > div > input,
.stTextArea > div > div > textarea,
.stSelectbox > div > div {
    background: #fff !important;
    border: 1px solid #e0e0ea !important;
    border-radius: 10px !important;
    color: #1a1a2e !important;
}

/* ============ DIVIDER ============ */
.divider {
    height: 1px;
    background: linear-gradient(90deg, transparent 0%, #e0e0ea 50%, transparent 100%);
    margin: 2rem 0;
}

/* ============ COVER LETTER ============ */
.cover-letter-box {
    background: #f8f8fc;
    border: 1px solid #e8e8f0;
    border-radius: 10px;
    padding: 1.25rem;
    margin-top: 0.75rem;
    color: #3d3d56;
    line-height: 1.7;
    font-size: 0.9rem;
}

.cover-letter-label {
    color: #6c5ce7;
    font-weight: 600;
    font-size: 0.85rem;
    margin-bottom: 0.5rem;
}

/* ============ FILTERS ============ */
.filters-box {
    background: #fff;
    border: 1px solid #e8e8f0;
    border-radius: 12px;
    padding: 1rem;
    margin-bottom: 1.5rem;
    display: flex;
    gap: 1rem;
    flex-wrap: wrap;
    align-items: center;
}

.filter-label {
    font-weight: 600;
    color: #3d3d56;
    font-size: 0.9rem;
}

/* ============ SCROLLBAR ============ */
::-webkit-scrollbar { width: 8px; }
::-webkit-scrollbar-track { background: #f0f0f5; }
::-webkit-scrollbar-thumb { background: #d0cfe8; border-radius: 4px; }
::-webkit-scrollbar-thumb:hover { background: #b0afd0; }

/* ============ FOOTER ============ */
.footer {
    text-align: center;
    padding: 1.5rem 1rem;
    margin-top: 3rem;
    color: #999;
    font-size: 0.8rem;
    border-top: 1px solid #e8e8f0;
}
.footer a { color: #6c5ce7; text-decoration: none; font-weight: 600; }
.footer a:hover { color: #5b4bd5; }

/* ============ SIDEBAR ============ */
section[data-testid="stSidebar"] {
    background: #fff;
    border-right: 1px solid #e8e8f0;
}
section[data-testid="stSidebar"] * { color: #3d3d56; }

/* ============ STREAMLIT OVERRIDES ============ */
.stMarkdown, .stMarkdown p, .stCaption, .stText { color: #3d3d56 !important; }
.stAlert p { color: inherit !important; }
label, .stSelectbox label, .stTextInput label, .stTextArea label { color: #3d3d56 !important; }

div[data-testid="stExpander"] details summary span { color: #1a1a2e !important; }
div[data-testid="stExpander"] div[data-testid="stMarkdownContainer"] p { color: #3d3d56 !important; }

.stProgress > div > div > div { background: #6c5ce7 !important; }

a { color: #6c5ce7; text-decoration: none; }
a:hover { color: #5b4bd5; text-decoration: underline; }

.stCodeBlock, pre { background: #f8f8fc !important; color: #3d3d56 !important; }
</style>
""", unsafe_allow_html=True)

# ============================================
# IMPORTS & SETUP
# ============================================

load_dotenv()

import importlib
import sys

_modules_to_reload = [
    "location_utils",
    "job_fetcher",
    "resume_parser",
    "run_auto_apply",
    "cover_letter_generator",
]
for _mod in _modules_to_reload:
    if _mod in sys.modules:
        try:
            importlib.reload(sys.modules[_mod])
        except Exception:
            sys.modules.pop(_mod, None)

try:
    from job_fetcher import fetch_all
    from resume_parser import build_profile
    from run_auto_apply import run_auto_apply_pipeline
    from cover_letter_generator import generate_cover_letter
    from location_utils import get_all_regions, get_region_display_name
except (ImportError, KeyError) as e:
    st.error(f"Missing required module: {e}. Please ensure all files are in the same directory.")
    st.stop()

# ============================================
# SESSION MANAGEMENT
# ============================================

if "session_id" not in st.session_state:
    st.session_state["session_id"] = str(uuid.uuid4())[:8]

SESSION_ID = st.session_state["session_id"]
DATA_DIR = f"data/session_{SESSION_ID}"
os.makedirs(DATA_DIR, exist_ok=True)

PROFILE_FILE = os.path.join(DATA_DIR, "profile.json")
JOBS_FILE = os.path.join(DATA_DIR, "jobs.json")
MATCHES_FILE = os.path.join(DATA_DIR, "matches.json")
CACHE_FILE = os.path.join(DATA_DIR, "semantic_cache.json")
LOG_FILE = os.path.join(DATA_DIR, "pipeline.log")
LETTERS_DIR = os.path.join(DATA_DIR, "cover_letters")

# ============================================
# UTILITY FUNCTIONS
# ============================================

def load_json(filepath):
    """Load JSON file safely"""
    if not os.path.exists(filepath):
        return None
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None

def save_json(filepath, data):
    """Save JSON file safely"""
    os.makedirs(os.path.dirname(filepath) or ".", exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def strip_html(text):
    """Remove HTML tags from text"""
    if not text:
        return ""
    clean = re.sub(r'<[^>]+>', ' ', text)
    clean = re.sub(r'\s+', ' ', clean).strip()
    return clean

def build_zip(letters_dir):
    """Create a ZIP file of all cover letters"""
    zip_buf = io.BytesIO()
    with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as zipf:
        for fname in os.listdir(letters_dir):
            if fname.endswith(".txt"):
                fpath = os.path.join(letters_dir, fname)
                zipf.write(fpath, fname)
    zip_buf.seek(0)
    return zip_buf.getvalue()

def find_cover_letter(company, title):
    """Find cover letter file for a job"""
    if not os.path.exists(LETTERS_DIR):
        return None, None
    
    company_clean = re.sub(r'[^a-zA-Z0-9_\-]', '', company.replace(' ', '_'))
    title_clean = re.sub(r'[^a-zA-Z0-9_\-]', '', title.replace(' ', '_'))
    
    for fname in os.listdir(LETTERS_DIR):
        if fname.endswith(".txt"):
            fname_lower = fname.lower()
            if company_clean.lower() in fname_lower or title_clean.lower() in fname_lower:
                fpath = os.path.join(LETTERS_DIR, fname)
                try:
                    with open(fpath, "r", encoding="utf-8") as f:
                        return f.read(), fname
                except Exception:
                    pass
    return None, None

def parse_job_date(job):
    """Extract and parse job posting date"""
    posted_str = job.get("posted_date", "")
    if posted_str:
        try:
            if isinstance(posted_str, str):
                return datetime.fromisoformat(posted_str.replace("Z", "+00:00"))
            return posted_str
        except:
            pass
    return None

def format_job_date(dt):
    """Format datetime for display with badge class"""
    if not dt:
        return "Date unknown", "date-badge"
    
    if isinstance(dt, str):
        try:
            dt = datetime.fromisoformat(dt.replace("Z", "+00:00"))
        except:
            return "Date unknown", "date-badge"
    
    now = datetime.now(dt.tzinfo) if dt.tzinfo else datetime.now()
    diff = now - dt
    
    if diff.days == 0:
        return "Posted today", "date-badge fresh"
    elif diff.days == 1:
        return "Posted yesterday", "date-badge fresh"
    elif diff.days < 7:
        return f"Posted {diff.days}d ago", "date-badge recent"
    elif diff.days < 30:
        return f"Posted {diff.days // 7}w ago", "date-badge"
    else:
        return dt.strftime("%b %d, %Y"), "date-badge"

# ============================================
# SIDEBAR
# ============================================

with st.sidebar:
    st.markdown("### 🎯 Session Control")
    st.caption(f"Session ID: `{SESSION_ID}`")
    
    if st.button("🔄 Start Fresh Session", use_container_width=True):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st. rerun()
    
    st.markdown("---")
    st.markdown("### 📊 About JobBot")
    st.markdown("""
    **How it works:**
    1. Upload resume → extract skills
    2. Scan 300+ jobs across 6 sources
    3. AI ranks by match quality
    4. Generate cover letters on demand
    """)

# ============================================
# HERO SECTION
# ============================================

st.markdown("""
<div class="hero">
    <div class="hero-content">
        <h1>🚀 JobBot</h1>
        <p class="hero-subtitle">
            AI-powered job matching that actually works. Upload your resume, 
            get matched with opportunities, and generate tailored cover letters.
        </p>
        <div class="hero-tags">
            <span class="hero-tag">🤖 AI Matching</span>
            <span class="hero-tag">📊 6+ Sources</span>
            <span class="hero-tag">🌍 Local + Remote</span>
            <span class="hero-tag">✨ Smart Filters</span>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# ============================================
# PROGRESS STEPPER
# ============================================

profile = load_json(PROFILE_FILE)
matches = load_json(MATCHES_FILE)

step1_status = "done" if profile and profile.get("skills") else "active"
step2_status = "done" if matches else ("active" if step1_status == "done" else "pending")
step3_status = "done" if os.path.exists(LETTERS_DIR) and os.listdir(LETTERS_DIR) else ("active" if step2_status == "done" else "pending")

st.markdown(f"""
<div class="stepper">
    <div class="step {step1_status}">
        <div class="step-icon">📄</div>
        <span>Upload Resume</span>
    </div>
    <div class="step-connector"></div>
    <div class="step {step2_status}">
        <div class="step-icon">🎯</div>
        <span>Match Jobs</span>
    </div>
    <div class="step-connector"></div>
    <div class="step {step3_status}">
        <div class="step-icon">✉️</div>
        <span>Cover Letters</span>
    </div>
</div>
""", unsafe_allow_html=True)

# ============================================
# STEP 1: RESUME UPLOAD & PROFILE
# ============================================

st.markdown('<div class="glass-card">', unsafe_allow_html=True)
st.markdown("""
<div class="card-header">
    <div class="card-icon">📄</div>
    <h2 class="card-title">Step 1: Your Profile</h2>
</div>
""", unsafe_allow_html=True)

col1, col2 = st.columns([2, 1])

with col1:
    uploaded_resume = st.file_uploader(
        "Upload your resume (PDF)",
        type=["pdf"],
        help="We'll extract your skills and experience automatically",
        key="resume_upload"
    )

with col2:
    if uploaded_resume:
        if st.button("🔍 Parse Resume", type="primary", use_container_width=True):
            with st.spinner("Analyzing your resume..."):
                try:
                    resume_path = os.path.join(DATA_DIR, "resume.pdf")
                    with open(resume_path, "wb") as f:
                        f.write(uploaded_resume.getbuffer())
                    
                    existing = load_json(PROFILE_FILE)
                    profile = build_profile(resume_path, PROFILE_FILE)
                    
                    if existing:
                        for field in ["country", "state", "experience", "job_preference"]:
                            if field not in profile and field in existing:
                                profile[field] = existing[field]
                    
                    profile.setdefault("country", "India")
                    profile.setdefault("state", "Any")
                    profile.setdefault("experience", "3–6 years")
                    profile.setdefault("job_preference", "🔀 Both (local + remote)")
                    save_json(PROFILE_FILE, profile)
                    
                    st.success("✅ Resume parsed successfully!")
                    time.sleep(0.5)
                    st.rerun()
                    
                except Exception as e:
                    st.error(f"❌ Error parsing resume: {e}")

# Display current profile
profile = load_json(PROFILE_FILE)

if profile and profile.get("skills"):
    st.markdown("---")
    st.markdown(f"**👤 {profile.get('name', 'Candidate')}**")
    if profile.get('headline'):
        st.caption(profile['headline'])
    
    skills = profile.get("skills", [])
    if skills:
        skills_html = "".join([f'<span class="skill-chip">{s}</span>' for s in skills])
        st.markdown(f'<div class="skills-container">{skills_html}</div>', unsafe_allow_html=True)
        st.caption(f"💡 {len(skills)} skills detected")

    country = profile.get("country", "")
    state = profile.get("state", "")
    if country:
        loc_display = country
        if state and state != "Any":
            loc_display += f" · {state}"
        st.caption(f"📍 {loc_display}")
else:
    st.info("👆 Upload your resume to get started, or create a profile manually below")

# Manual profile editor
with st.expander("✏️ Edit Profile Manually" if profile else "✏️ Create Profile Manually"):
    name_input = st.text_input("Full Name", value=profile.get("name", "") if profile else "")
    headline_input = st.text_input("Professional Headline", value=profile.get("headline", "") if profile else "")
    skills_input = st.text_area(
        "Skills (one per line)", 
        value="\n".join(profile.get("skills", [])) if profile else "",
        height=120,
        help="Enter specific skills - used for matching"
    )

    COUNTRY_OPTIONS = [
        "India", "United States", "United Kingdom", "Canada", "Germany",
        "Australia", "UAE", "Saudi Arabia", "Singapore", "Remote Only",
    ]
    
    current_country = profile.get("country", "India") if profile else "India"
    if current_country not in COUNTRY_OPTIONS:
        COUNTRY_OPTIONS.append(current_country)

    col_c, col_s = st.columns(2)
    with col_c:
        country_input = st.selectbox("📍 Country", options=COUNTRY_OPTIONS)
    with col_s:
        state_input = st.text_input("🏙️ City/State", value=profile.get("state", "Any") if profile else "Any")
    
    col_e, col_p = st.columns(2)
    with col_e:
        exp_input = st.selectbox("📅 Experience", options=["0–1 years", "1–3 years", "3–6 years", "6–10 years", "10+ years"])
    with col_p:
        pref_input = st.selectbox("🎯 Job Preference", options=["🏙️ Local jobs", "🌐 Remote jobs", "🔀 Both"])
    
    if st.button("💾 Save Profile", use_container_width=True):
        skills_list = [s.strip() for s in skills_input.split("\n") if s.strip()]
        if not skills_list and not name_input:
            st.error("⚠️ Please enter at least a name or some skills")
        else:
            existing = load_json(PROFILE_FILE) or {}
            updated_profile = {
                "name": name_input or "Candidate",
                "headline": headline_input,
                "skills": skills_list,
                "country": country_input,
                "state": state_input,
                "experience": exp_input,
                "job_preference": pref_input,
                "industry": existing.get("industry", ""),
                "search_terms": existing.get("search_terms", []),
            }
            save_json(PROFILE_FILE, updated_profile)
            st.success("✅ Profile saved!")
            time.sleep(0.5)
            st.rerun()

st.markdown('</div>', unsafe_allow_html=True)

# ============================================
# STEP 2: JOB MATCHING
# ============================================

st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
st.markdown('<div class="glass-card">', unsafe_allow_html=True)
st.markdown("""
<div class="card-header">
    <div class="card-icon">🎯</div>
    <h2 class="card-title">Step 2: Job Matching</h2>
</div>
""", unsafe_allow_html=True)

profile = load_json(PROFILE_FILE)
profile_ready = bool(profile and profile.get("skills"))

if not profile_ready:
    st.warning("⚠️ Please complete your profile above to unlock job matching")
else:
    with st.expander("ℹ️ How does matching work?"):
        st.markdown("""
        **3-phase matching pipeline:**
        1. **Keyword Extraction** - Extract your skills + related terms
        2. **Local Scoring** - Score all jobs based on keyword overlap
        3. **AI Ranking** - Gemini 2.5 Flash ranks top candidates
        """)
    
    with st.expander("📁 Use Custom Jobs (Optional)"):
        jobs_upload = st.file_uploader("Upload jobs.json", type=["json"])
        if jobs_upload:
            try:
                jobs_data = json.loads(jobs_upload.getvalue())
                save_json(JOBS_FILE, jobs_data)
                st.success(f"✅ Loaded {len(jobs_data)} jobs")
            except Exception as e:
                st.error(f"❌ Invalid JSON: {e}")
    
    if st.session_state.get("_matching_done"):
        st.success("✅ Matching complete! Scroll down to see results.")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🔄 Re-run Matching", use_container_width=True):
                st.session_state.pop("_matching_done", None)
                for fp in [JOBS_FILE, MATCHES_FILE, CACHE_FILE]:
                    if os.path.exists(fp):
                        os.remove(fp)
                st.rerun()
    elif st.session_state.get("_matching_running"):
        st.warning("⏳ Matching in progress... 30-60 seconds")
    else:
        country = profile.get("country", "India")
        st.markdown(f"Ready to find your next role? We'll scan 6+ sources and rank matches using AI (focused on **{country}**).")
        
        if st.button("🚀 Start Job Matching", type="primary", use_container_width=True):
            st.session_state["_matching_running"] = True
            
            status_text = st.empty()
            progress_bar = st.progress(0, text="Starting pipeline...")
            detail_box = st.empty()
            log_lines = []
            
            def progress_callback(msg):
                log_lines.append(msg)
                detail_box.code("\n".join(log_lines[-8:]), language=None)
                progress_bar.progress(min(len(log_lines) / 20, 0.95), text=msg[:70])
            
            try:
                status_text.info("🔍 Scanning 6 sources and running AI matching...")
                
                result = run_auto_apply_pipeline(
                    profile_file=PROFILE_FILE,
                    jobs_file=JOBS_FILE,
                    matches_file=MATCHES_FILE,
                    cache_file=CACHE_FILE,
                    log_file=LOG_FILE,
                    letters_dir=None,
                    progress_callback=progress_callback,
                )
                
                progress_bar.progress(1.0, text="Complete!")
                st.session_state["_matching_done"] = True
                st.session_state.pop("_matching_running", None)
                
                if result and result.get("status") == "success":
                    status_text.success(f"✅ Found {result['matches']} matches!")
                else:
                    status_text.warning("⚠️ No strong matches found. Try broadening your skills.")
                
                time.sleep(1)
                st.rerun()
                
            except Exception as e:
                st.session_state.pop("_matching_running", None)
                status_text.error(f"❌ Error: {e}")

st.markdown('</div>', unsafe_allow_html=True)

# ============================================
# STEP 3: RESULTS WITH FILTERS
# ============================================

matches_data = load_json(MATCHES_FILE)

if isinstance(matches_data, list) and matches_data:
    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
    
    # Stats
    scores = [j.get("match_score", 0) for j in matches_data]
    avg_score = sum(scores) / len(scores) if scores else 0
    max_score = max(scores) if scores else 0
    
    letter_files = []
    if os.path.exists(LETTERS_DIR):
        letter_files = [f for f in os.listdir(LETTERS_DIR) if f.endswith(".txt")]
    
    st.markdown(f"""
    <div class="stats-grid">
        <div class="stat-card">
            <div class="stat-value">{len(matches_data)}</div>
            <div class="stat-label">Total Matches</div>
        </div>
        <div class="stat-card">
            <div class="stat-value">{avg_score:.0f}%</div>
            <div class="stat-label">Avg Score</div>
        </div>
        <div class="stat-card">
            <div class="stat-value">{max_score}%</div>
            <div class="stat-label">Top Score</div>
        </div>
        <div class="stat-card">
            <div class="stat-value">{len(letter_files)}</div>
            <div class="stat-label">Cover Letters</div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    if letter_files:
        col1, col2 = st.columns([3, 1])
        with col1:
            st.markdown(f"### 🎯 Your Top {len(matches_data)} Matches")
        with col2:
            zip_data = build_zip(LETTERS_DIR)
            st.download_button(
                f"📦 {len(letter_files)} Letters",
                data=zip_data,
                file_name="jobbot_letters.zip",
                mime="application/zip",
                use_container_width=True,
            )
    else:
        st.markdown(f"### 🎯 Your Top {len(matches_data)} Matches")
    
    # ============ FILTERS ============
    st.markdown('<div class="filters-box">', unsafe_allow_html=True)
    
    fcol1, fcol2, fcol3, fcol4 = st.columns(4)
    
    with fcol1:
        sort_by = st.selectbox("Sort By", ["Most Recent", "Highest Score", "Lowest Score"], label_visibility="collapsed")
    
    with fcol2:
        min_score_filter = st.slider("Min Score", 0, 100, 0, label_visibility="collapsed")
    
    with fcol3:
        sources = list(set(j.get("source", "Other") for j in matches_data))
        source_filter = st.multiselect("Sources", sources, default=sources, label_visibility="collapsed")
    
    with fcol4:
        days_filter = st.selectbox("Posted Within", ["All Time", "7 days", "30 days"], label_visibility="collapsed")
    
    st.markdown('</div>', unsafe_have_html=True)
    
    # Filter and sort jobs
    filtered_jobs = [j for j in matches_data if j.get("match_score", 0) >= min_score_filter and j.get("source", "Other") in source_filter]
    
    # Date filtering
    if days_filter != "All Time":
        days = 7 if days_filter == "7 days" else 30
        cutoff_date = datetime.now() - timedelta(days=days)
        filtered_jobs = [j for j in filtered_jobs if parse_job_date(j) and parse_job_date(j) > cutoff_date or not parse_job_date(j)]
    
    # Sorting
    if sort_by == "Most Recent":
        filtered_jobs = sorted(filtered_jobs, key=lambda x: parse_job_date(x) or datetime.min, reverse=True)
    elif sort_by == "Highest Score":
        filtered_jobs = sorted(filtered_jobs, key=lambda x: x.get("match_score", 0), reverse=True)
    elif sort_by == "Lowest Score":
        filtered_jobs = sorted(filtered_jobs, key=lambda x: x.get("match_score", 0))
    
    st.caption(f"📊 Showing {len(filtered_jobs)} of {len(matches_data)} matches")
    
    # Job cards
    for i, job in enumerate(filtered_jobs, 1):
        score = job.get("match_score", 0)
        company = job.get("company", "Unknown")
        title = job.get("title", "Unknown")
        source = job.get("source", "")
        summary = strip_html(job.get("summary", ""))[:400]
        
        # Score emoji
        if score >= 75:
            badge_emoji = "🔥"
            badge_class = "score-excellent"
        elif score >= 60:
            badge_emoji = "⭐"
            badge_class = "score-good"
        else:
            badge_emoji = "👍"
            badge_class = "score-fair"
        
        # Post date badge
        job_date = parse_job_date(job)
        date_text, date_class = format_job_date(job_date)
        
        with st.expander(f"#{i} · {badge_emoji} {company} — {title}"):
            col1, col2 = st.columns([3, 1])
            
            with col1:
                st.markdown(f"**{title}**")
                st.markdown(f"🏢 **{company}** · <span class='source-badge'>{source}</span> · <span class='{date_class}'>{date_text}</span>", unsafe_allow_html=True)
                
                job_location = job.get("location", "")
                if not job_location:
                    for tag in job.get("location_tags", []):
                        if tag:
                            job_location = tag
                            break
                
                if job_location:
                    st.caption(f"📍 {job_location}")
                
                if summary:
                    st.write(summary)
            
            with col2:
                st.markdown(
                    f'<div style="text-align:center; margin-bottom:0.5rem;">'
                    f'<span class="score-badge {badge_class}">{score}%</span></div>',
                    unsafe_allow_html=True
                )
                if job.get("apply_url"):
                    st.link_button("🔗 Apply Now", job["apply_url"], use_container_width=True)
                
                letter_content, letter_fname = find_cover_letter(company, title)
                if not letter_content:
                    if st.button("📝 Generate Letter", key=f"gen_{i}", use_container_width=True):
                        with st.spinner("Writing letter..."):
                            try:
                                os.makedirs(LETTERS_DIR, exist_ok=True)
                                profile = load_json(PROFILE_FILE)
                                generate_cover_letter(job, profile, LETTERS_DIR)
                                st.rerun()
                            except Exception as e:
                                st.error(f"Failed: {e}")
            
            letter_content, letter_fname = find_cover_letter(company, title)
            if letter_content:
                st.markdown("---")
                st.markdown('<p class="cover-letter-label">📝 Tailored Cover Letter</p>', unsafe_allow_html=True)
                st.markdown(f'<div class="cover-letter-box">{letter_content}</div>', unsafe_allow_html=True)
                st.download_button("📥 Download", data=letter_content, file_name=letter_fname, key=f"dl_{i}", use_container_width=True)

st.markdown("""
<div class="footer">
    Built with ❤️ using Streamlit & Gemini 2.5 Flash
</div>
""", unsafe_allow_html=True)
