import streamlit as st
import json
import os
import re
import uuid
import time
import io
import zipfile
from dotenv import load_dotenv

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
# CUSTOM CSS — 2026 Glassmorphism + Modern Design
# ============================================

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap');

/* ============ GLOBAL RESET ============ */
* {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}

.stApp {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    background: linear-gradient(135deg, #0f0c29 0%, #302b63 50%, #24243e 100%);
    background-attachment: fixed;
}

h1, h2, h3, h4, h5, h6,
.stMarkdown h1, .stMarkdown h2, .stMarkdown h3 {
    font-family: 'Inter', sans-serif !important;
    font-weight: 700 !important;
    letter-spacing: -0.03em;
}

code, .stCode, pre {
    font-family: 'JetBrains Mono', monospace !important;
}

/* ============ GLASSMORPHISM FOUNDATION ============ */
.glass {
    background: rgba(255, 255, 255, 0.05);
    backdrop-filter: blur(20px) saturate(180%);
    -webkit-backdrop-filter: blur(20px) saturate(180%);
    border: 1px solid rgba(255, 255, 255, 0.1);
    box-shadow: 0 8px 32px 0 rgba(31, 38, 135, 0.37);
}

.glass-strong {
    background: rgba(255, 255, 255, 0.08);
    backdrop-filter: blur(25px) saturate(200%);
    -webkit-backdrop-filter: blur(25px) saturate(200%);
    border: 1px solid rgba(255, 255, 255, 0.15);
    box-shadow: 0 12px 40px 0 rgba(31, 38, 135, 0.45);
}

/* ============ HERO SECTION ============ */
.hero {
    background: linear-gradient(135deg, rgba(139, 92, 246, 0.1) 0%, rgba(59, 130, 246, 0.1) 100%);
    backdrop-filter: blur(20px) saturate(180%);
    -webkit-backdrop-filter: blur(20px) saturate(180%);
    border: 1px solid rgba(139, 92, 246, 0.2);
    border-radius: 24px;
    padding: 3rem 2.5rem;
    margin-bottom: 2rem;
    position: relative;
    overflow: hidden;
    box-shadow: 
        0 8px 32px 0 rgba(139, 92, 246, 0.2),
        inset 0 1px 0 0 rgba(255, 255, 255, 0.1);
}

.hero::before {
    content: '';
    position: absolute;
    top: -50%;
    right: -20%;
    width: 600px;
    height: 600px;
    background: radial-gradient(circle, rgba(139, 92, 246, 0.2) 0%, transparent 70%);
    filter: blur(60px);
    animation: float 8s ease-in-out infinite;
}

.hero::after {
    content: '';
    position: absolute;
    bottom: -30%;
    left: -10%;
    width: 500px;
    height: 500px;
    background: radial-gradient(circle, rgba(59, 130, 246, 0.15) 0%, transparent 70%);
    filter: blur(60px);
    animation: float 10s ease-in-out infinite reverse;
}

@keyframes float {
    0%, 100% { transform: translate(0, 0) scale(1); }
    50% { transform: translate(30px, -20px) scale(1.1); }
}

.hero-content {
    position: relative;
    z-index: 1;
}

.hero h1 {
    color: #ffffff !important;
    font-size: 3rem !important;
    font-weight: 800 !important;
    margin: 0 0 0.5rem 0 !important;
    background: linear-gradient(135deg, #ffffff 0%, #a78bfa 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    line-height: 1.1;
}

.hero-subtitle {
    color: rgba(255, 255, 255, 0.7);
    font-size: 1.15rem;
    margin: 0 0 1.5rem 0;
    font-weight: 400;
    line-height: 1.6;
}

.hero-tags {
    display: flex;
    gap: 0.75rem;
    flex-wrap: wrap;
    margin-top: 1.5rem;
}

.hero-tag {
    background: rgba(139, 92, 246, 0.15);
    backdrop-filter: blur(10px);
    border: 1px solid rgba(139, 92, 246, 0.3);
    color: #c4b5fd;
    padding: 0.5rem 1rem;
    border-radius: 12px;
    font-size: 0.85rem;
    font-weight: 600;
    letter-spacing: 0.02em;
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.hero-tag:hover {
    background: rgba(139, 92, 246, 0.25);
    border-color: rgba(139, 92, 246, 0.5);
    transform: translateY(-2px);
}

/* ============ STEPPER PROGRESS ============ */
.stepper {
    display: flex;
    justify-content: center;
    align-items: center;
    gap: 1rem;
    margin: 2rem 0 2.5rem;
    padding: 1.5rem;
    background: rgba(255, 255, 255, 0.03);
    backdrop-filter: blur(15px);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 20px;
}

.step {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    padding: 0.75rem 1.25rem;
    border-radius: 12px;
    font-size: 0.9rem;
    font-weight: 600;
    transition: all 0.3s ease;
}

.step-icon {
    width: 36px;
    height: 36px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 1.1rem;
    transition: all 0.3s ease;
}

.step.done {
    color: #6ee7b7;
}

.step.done .step-icon {
    background: linear-gradient(135deg, #059669 0%, #10b981 100%);
    box-shadow: 0 4px 15px rgba(16, 185, 129, 0.4);
}

.step.active {
    color: #c4b5fd;
    background: rgba(139, 92, 246, 0.1);
}

.step.active .step-icon {
    background: linear-gradient(135deg, #7c3aed 0%, #8b5cf6 100%);
    box-shadow: 0 4px 15px rgba(139, 92, 246, 0.5);
    animation: pulse 2s ease-in-out infinite;
}

.step.pending {
    color: rgba(255, 255, 255, 0.3);
}

.step.pending .step-icon {
    background: rgba(255, 255, 255, 0.05);
    border: 2px dashed rgba(255, 255, 255, 0.15);
}

.step-connector {
    width: 60px;
    height: 2px;
    background: linear-gradient(90deg, 
        rgba(255, 255, 255, 0.2) 0%, 
        rgba(255, 255, 255, 0.05) 100%
    );
}

@keyframes pulse {
    0%, 100% { transform: scale(1); opacity: 1; }
    50% { transform: scale(1.05); opacity: 0.9; }
}

/* ============ GLASS CARDS ============ */
.glass-card {
    background: rgba(255, 255, 255, 0.04);
    backdrop-filter: blur(20px) saturate(180%);
    -webkit-backdrop-filter: blur(20px) saturate(180%);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 20px;
    padding: 2rem;
    margin-bottom: 1.5rem;
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    box-shadow: 0 8px 32px 0 rgba(31, 38, 135, 0.2);
}

.glass-card:hover {
    border-color: rgba(139, 92, 246, 0.3);
    box-shadow: 0 12px 40px 0 rgba(139, 92, 246, 0.3);
    transform: translateY(-2px);
}

.card-header {
    display: flex;
    align-items: center;
    gap: 1rem;
    margin-bottom: 1.5rem;
}

.card-icon {
    width: 48px;
    height: 48px;
    border-radius: 14px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 1.5rem;
    background: rgba(139, 92, 246, 0.15);
    border: 1px solid rgba(139, 92, 246, 0.3);
}

.card-title {
    font-size: 1.35rem !important;
    font-weight: 700 !important;
    color: #ffffff !important;
    margin: 0 !important;
}

/* ============ SKILL CHIPS ============ */
.skills-container {
    display: flex;
    flex-wrap: wrap;
    gap: 0.6rem;
    margin-top: 1rem;
}

.skill-chip {
    background: rgba(139, 92, 246, 0.12);
    backdrop-filter: blur(10px);
    border: 1px solid rgba(139, 92, 246, 0.25);
    color: #c4b5fd;
    padding: 0.5rem 1rem;
    border-radius: 10px;
    font-size: 0.85rem;
    font-weight: 600;
    transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
    cursor: default;
}

.skill-chip:hover {
    background: rgba(139, 92, 246, 0.2);
    border-color: rgba(139, 92, 246, 0.4);
    transform: translateY(-2px);
    box-shadow: 0 4px 12px rgba(139, 92, 246, 0.3);
}

/* ============ STATS DASHBOARD ============ */
.stats-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 1.25rem;
    margin: 2rem 0;
}

.stat-card {
    background: rgba(255, 255, 255, 0.05);
    backdrop-filter: blur(15px);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 18px;
    padding: 1.75rem 1.5rem;
    text-align: center;
    transition: all 0.3s ease;
}

.stat-card:hover {
    background: rgba(255, 255, 255, 0.08);
    border-color: rgba(139, 92, 246, 0.3);
    transform: translateY(-3px);
    box-shadow: 0 8px 24px rgba(139, 92, 246, 0.2);
}

.stat-value {
    font-size: 2.5rem;
    font-weight: 800;
    background: linear-gradient(135deg, #8b5cf6 0%, #3b82f6 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    line-height: 1;
    margin-bottom: 0.5rem;
}

.stat-label {
    color: rgba(255, 255, 255, 0.6);
    font-size: 0.9rem;
    font-weight: 500;
    text-transform: uppercase;
    letter-spacing: 0.05em;
}

/* ============ SCORE BADGES ============ */
.score-badge {
    display: inline-block;
    padding: 0.5rem 1.25rem;
    border-radius: 12px;
    font-size: 1rem;
    font-weight: 700;
    letter-spacing: 0.02em;
    text-align: center;
    box-shadow: 0 4px 15px rgba(0, 0, 0, 0.2);
}

.score-excellent {
    background: linear-gradient(135deg, #059669 0%, #10b981 100%);
    color: #ffffff;
    box-shadow: 0 4px 15px rgba(16, 185, 129, 0.4);
}

.score-good {
    background: linear-gradient(135deg, #d97706 0%, #f59e0b 100%);
    color: #ffffff;
    box-shadow: 0 4px 15px rgba(245, 158, 11, 0.4);
}

.score-fair {
    background: linear-gradient(135deg, #7c3aed 0%, #8b5cf6 100%);
    color: #ffffff;
    box-shadow: 0 4px 15px rgba(139, 92, 246, 0.4);
}

/* ============ SOURCE BADGES ============ */
.source-badge {
    display: inline-block;
    padding: 0.35rem 0.85rem;
    border-radius: 8px;
    font-size: 0.75rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    background: rgba(59, 130, 246, 0.15);
    color: #60a5fa;
    border: 1px solid rgba(59, 130, 246, 0.3);
}

/* ============ BUTTONS ============ */
.stButton > button {
    background: linear-gradient(135deg, #7c3aed 0%, #8b5cf6 100%) !important;
    color: white !important;
    border: none !important;
    border-radius: 12px !important;
    padding: 0.75rem 1.5rem !important;
    font-weight: 600 !important;
    font-size: 1rem !important;
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
    box-shadow: 0 4px 15px rgba(139, 92, 246, 0.3) !important;
}

.stButton > button:hover {
    background: linear-gradient(135deg, #6d28d9 0%, #7c3aed 100%) !important;
    transform: translateY(-2px) !important;
    box-shadow: 0 6px 20px rgba(139, 92, 246, 0.4) !important;
}

/* ============ DIVIDER ============ */
.divider {
    height: 1px;
    background: linear-gradient(90deg, 
        transparent 0%, 
        rgba(139, 92, 246, 0.3) 50%, 
        transparent 100%
    );
    margin: 2.5rem 0;
}

/* ============ COVER LETTER DISPLAY ============ */
.cover-letter-box {
    background: rgba(255, 255, 255, 0.03);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 12px;
    padding: 1.5rem;
    margin-top: 1rem;
    color: rgba(255, 255, 255, 0.85);
    line-height: 1.8;
    font-size: 0.95rem;
}

.cover-letter-label {
    color: #c4b5fd;
    font-weight: 600;
    font-size: 0.9rem;
    margin-bottom: 0.75rem;
    display: flex;
    align-items: center;
    gap: 0.5rem;
}

/* ============ SCROLLBAR ============ */
::-webkit-scrollbar {
    width: 10px;
    height: 10px;
}

::-webkit-scrollbar-track {
    background: rgba(255, 255, 255, 0.02);
}

::-webkit-scrollbar-thumb {
    background: rgba(139, 92, 246, 0.3);
    border-radius: 5px;
}

::-webkit-scrollbar-thumb:hover {
    background: rgba(139, 92, 246, 0.5);
}

/* ============ FOOTER ============ */
.footer {
    text-align: center;
    padding: 2rem 1rem;
    margin-top: 4rem;
    color: rgba(255, 255, 255, 0.4);
    font-size: 0.85rem;
    border-top: 1px solid rgba(255, 255, 255, 0.05);
}

.footer a {
    color: #8b5cf6;
    text-decoration: none;
    font-weight: 600;
}

.footer a:hover {
    color: #a78bfa;
}
</style>
""", unsafe_allow_html=True)

# ============================================
# IMPORTS & SETUP
# ============================================

load_dotenv()

# ============================================
# MODULE RELOAD — Critical for Streamlit hot-reload
# Without this, Streamlit caches old module versions
# and new code (like Lever/SerpAPI) never runs
# ============================================
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
    try:
        if _mod in sys.modules:
            importlib.reload(sys.modules[_mod])
    except Exception:
        # First load or dependency not ready — safe to skip
        pass

# Import functions from other modules
try:
    from job_fetcher import fetch_all
    from resume_parser import build_profile
    from run_auto_apply import run_auto_apply_pipeline
    from cover_letter_generator import generate_cover_letter
    from location_utils import get_all_regions, get_region_display_name
except ImportError as e:
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
    
    # Sanitize search terms
    company_clean = re.sub(r'[^a-zA-Z0-9_\-]', '', company.replace(' ', '_'))
    title_clean = re.sub(r'[^a-zA-Z0-9_\-]', '', title.replace(' ', '_'))
    
    # Try to find matching file
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

# ============================================
# SIDEBAR - SESSION CONTROL
# ============================================

with st.sidebar:
    st.markdown("### 🎯 Session Control")
    st.caption(f"Session ID: `{SESSION_ID}`")
    
    if st.button("🔄 Start Fresh Session", use_container_width=True):
        # Clear session state
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()
    
    st.markdown("---")
    st.markdown("### 📊 About JobBot")
    st.markdown("""
    **How it works:**
    1. **Skills-based matching** - Extracts skills from your resume
    2. **Keyword filtering** - Finds relevant jobs (300+ sources)
    3. **AI ranking** - Gemini scores top candidates
    4. **Smart matching** - Considers seniority & diversity
    """)
    
    st.markdown("---")
    st.markdown("### 🔍 Job Sources")
    st.markdown("""
    - WeWorkRemotely (6 categories)
    - RemoteOK
    - Jobicy
    - Remotive
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
            get matched with remote opportunities, and generate tailored cover letters in minutes.
        </p>
        <div class="hero-tags">
            <span class="hero-tag">🤖 Gemini 2.5 Flash</span>
            <span class="hero-tag">📊 Skills-Based Matching</span>
            <span class="hero-tag">🌍 300+ Jobs Daily</span>
            <span class="hero-tag">✨ Smart Deduplication</span>
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
        <span>Generate Letters</span>
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
        help="We'll extract your skills, experience, and headline automatically",
        key="resume_upload"
    )

with col2:
    if uploaded_resume:
        if st.button("🔍 Parse Resume", type="primary", use_container_width=True):
            with st.spinner("Analyzing your resume..."):
                try:
                    # Save uploaded file
                    resume_path = os.path.join(DATA_DIR, "resume.pdf")
                    with open(resume_path, "wb") as f:
                        f.write(uploaded_resume.getbuffer())
                    
                    # Parse resume
                    # Preserve country from existing profile
                    existing = load_json(PROFILE_FILE)
                    existing_country = existing.get("country", "India") if existing else "India"
                    
                    profile = build_profile(resume_path, PROFILE_FILE)
                    
                    # Re-add country to the saved profile
                    if "country" not in profile:
                        profile["country"] = existing_country
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
        st.caption(f"💡 {len(skills)} skills detected - used for keyword matching")

    # Display location preferences
    country = profile.get("country", "")
    state = profile.get("state", "")
    if country:
        loc_display = country
        if state and state != "Any":
            loc_display += f" · {state}"
        st.caption(f"📍 {loc_display}")
    if profile.get("location_preferences"):
        prefs = profile["location_preferences"]
        pref_names = []
        name_map = {"americas": "Americas", "europe": "Europe", "asia": "Asia-Pacific", "global": "Global"}
        for p in prefs:
            pref_names.append(name_map.get(p, p.title()))
        st.caption(f"📍 Regions: {', '.join(pref_names)}")
else:
    st.info("👆 Upload your resume to get started, or create a profile manually below")

# Manual profile editing
with st.expander("✏️ Edit Profile Manually" if profile else "✏️ Create Profile Manually"):
    name_input = st.text_input("Full Name", value=profile.get("name", "") if profile else "")
    headline_input = st.text_input("Professional Headline", value=profile.get("headline", "") if profile else "")
    skills_input = st.text_area(
        "Skills (one per line)", 
        value="\n".join(profile.get("skills", [])) if profile else "",
        height=150,
        help="Enter specific skills, tools, and technologies - these are used for matching"
    )

    # Location selectors — country + state/city
    COUNTRY_OPTIONS = [
        "India", "United States", "United Kingdom", "Canada", "Germany",
        "Australia", "UAE", "Saudi Arabia", "Singapore", "Netherlands",
        "France", "Ireland", "Israel", "Brazil", "Remote Only",
    ]
    STATE_OPTIONS = {
        "India": [
            "Any", "Karnataka (Bangalore)", "Maharashtra (Mumbai/Pune)", "Delhi NCR",
            "Telangana (Hyderabad)", "Tamil Nadu (Chennai)", "West Bengal (Kolkata)",
            "Gujarat (Ahmedabad)", "Rajasthan (Jaipur)", "Uttar Pradesh (Noida/Lucknow)",
            "Kerala (Kochi)", "Haryana (Gurgaon)",
        ],
        "United States": [
            "Any", "California", "New York", "Texas", "Washington",
            "Massachusetts", "Illinois", "Florida", "Georgia", "Colorado",
            "Virginia", "Pennsylvania",
        ],
        "United Kingdom": ["Any", "London", "Manchester", "Edinburgh", "Birmingham", "Bristol"],
        "Canada": ["Any", "Ontario (Toronto)", "British Columbia (Vancouver)", "Quebec (Montreal)", "Alberta"],
        "Germany": ["Any", "Berlin", "Munich", "Hamburg", "Frankfurt"],
        "Australia": ["Any", "New South Wales (Sydney)", "Victoria (Melbourne)", "Queensland"],
        "UAE": ["Any", "Dubai", "Abu Dhabi", "Sharjah"],
        "Saudi Arabia": ["Any", "Riyadh", "Jeddah", "Dammam"],
    }

    current_country = profile.get("country", "India") if profile else "India"
    if current_country not in COUNTRY_OPTIONS:
        COUNTRY_OPTIONS.append(current_country)

    loc_col1, loc_col2 = st.columns(2)
    with loc_col1:
        country_input = st.selectbox(
            "📍 Country",
            options=COUNTRY_OPTIONS,
            index=COUNTRY_OPTIONS.index(current_country) if current_country in COUNTRY_OPTIONS else 0,
            help="We'll prioritize jobs in your country"
        )
    with loc_col2:
        state_list = STATE_OPTIONS.get(country_input, ["Any"])
        current_state = profile.get("state", "Any") if profile else "Any"
        if current_state not in state_list:
            current_state = "Any"
        state_input = st.selectbox(
            "🏙️ State / City",
            options=state_list,
            index=state_list.index(current_state) if current_state in state_list else 0,
            help="Refines search queries for more local results"
        )
    
    if st.button("💾 Save Profile", use_container_width=True):
        skills_list = [s.strip() for s in skills_input.split("\n") if s.strip()]
        if not skills_list and not name_input:
            st.error("⚠️ Please enter at least a name or some skills")
        else:
            updated_profile = {
                "name": name_input or "Candidate",
                "headline": headline_input,
                "skills": skills_list,
                "country": country_input,
                "state": state_input,
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
    # Explain matching process
    with st.expander("ℹ️ How does matching work?"):
        st.markdown("""
        **JobBot uses a 3-phase matching system:**
        
        1. **Keyword Extraction** - We extract skills from your resume + expand them with related terms
        2. **Local Scoring** - All jobs are scored locally based on keyword overlap (fast, no API calls)
        3. **AI Ranking** - Top 30-50 candidates sent to Gemini 2.5 Flash for final scoring
        
        **What we match on:**
        - ✅ Your **skills** (primary signal - exact matches + variants)
        - ✅ Your **headline** (job title/role context)
        - ✅ Domain terms extracted from both
        
        **What we filter:**
        - ❌ Non-English jobs
        - ❌ Jobs too senior for your experience
        - ❌ Duplicate postings across sources
        """)
    
    # Optional: Upload custom jobs
    with st.expander("📁 Use Custom Jobs (Optional)"):
        jobs_upload = st.file_uploader(
            "Upload jobs.json",
            type=["json"],
            help="Upload your own jobs.json file instead of fetching from job boards"
        )
        if jobs_upload:
            try:
                jobs_data = json.loads(jobs_upload.getvalue())
                save_json(JOBS_FILE, jobs_data)
                st.success(f"✅ Loaded {len(jobs_data)} jobs from file")
            except Exception as e:
                st.error(f"❌ Invalid JSON file: {e}")
    
    # Run matching
    if st.session_state.get("_matching_done"):
        st.success("✅ Matching complete! Scroll down to see your matches.")
        if st.button("🔄 Re-run Matching (Fresh Jobs)", use_container_width=True):
            # Clear all matching data
            st.session_state.pop("_matching_done", None)
            for fp in [JOBS_FILE, MATCHES_FILE, CACHE_FILE]:
                if os.path.exists(fp):
                    os.remove(fp)
            if os.path.exists(LETTERS_DIR):
                for lf in os.listdir(LETTERS_DIR):
                    os.remove(os.path.join(LETTERS_DIR, lf))
            st.rerun()
    
    elif st.session_state.get("_matching_running"):
        st.warning("⏳ Matching in progress... This may take 30-60 seconds.")
    
    else:
        country = profile.get("country", "India")
        st.markdown(f"""
        **Ready to find your next role?**
        
        We'll scan **6 sources** — WeWorkRemotely, RemoteOK, Remotive, Lever, 
        and **Google Jobs** (LinkedIn, Indeed, Naukri) focused on **{country}** — 
        then rank the best matches using AI.
        """)
        
        if st.button("🚀 Start Job Matching", type="primary", use_container_width=True):
            st.session_state["_matching_running"] = True
            
            # Progress UI
            status_text = st.empty()
            progress_bar = st.progress(0, text="Starting pipeline...")
            detail_box = st.empty()
            log_lines = []

            # Progress stages for the bar
            stage_pct = {
                "Starting pipeline": 0,
                "Fetching jobs": 5,
                "WeWorkRemotely": 10,
                "RemoteOK": 15,
                "Remotive": 20,
                "Lever": 30,
                "Google Jobs": 40,
                "SerpAPI": 40,
                "Loaded": 50,
                "Location filter": 55,
                "Matching against": 60,
                "Phase 1": 65,
                "Batch 1": 70,
                "Batch 2": 78,
                "Batch 3": 85,
                "Batch 4": 90,
                "Threshold": 95,
                "Done": 100,
            }
            
            def progress_callback(msg):
                log_lines.append(msg)
                detail_box.code("\n".join(log_lines[-8:]), language=None)
                # Update progress bar based on message content
                pct = 0
                for keyword, p in stage_pct.items():
                    if keyword.lower() in msg.lower():
                        pct = p
                # Always advance at least to current max
                current = getattr(progress_callback, '_max_pct', 0)
                pct = max(pct, current)
                progress_callback._max_pct = pct
                progress_bar.progress(min(pct, 100) / 100, text=msg[:80])
            
            progress_callback._max_pct = 0
            
            try:
                status_text.info("🔍 Scanning 6 job sources and running AI matching...")
                
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
                    status_text.success(f"✅ Found {result['matches']} matches from {result['total_scored']} jobs!")
                elif result and result.get("status") == "no_matches":
                    status_text.warning("⚠️ No strong matches found. Try broadening your skills or check back later.")
                else:
                    status_text.error(f"❌ Pipeline error: {result}")
                
                time.sleep(1)
                st.rerun()
                
            except Exception as e:
                st.session_state.pop("_matching_running", None)
                progress_bar.progress(1.0, text="Error")
                status_text.error(f"❌ Error: {e}")
                st.exception(e)

st.markdown('</div>', unsafe_allow_html=True)

# ============================================
# STEP 3: MATCH RESULTS & COVER LETTERS
# ============================================

matches_data = load_json(MATCHES_FILE)

if isinstance(matches_data, list) and matches_data:
    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
    
    # Stats
    scores = [j.get("match_score", 0) for j in matches_data]
    avg_score = sum(scores) / len(scores) if scores else 0
    max_score = max(scores) if scores else 0
    min_score = min(scores) if scores else 0
    
    sources = {}
    for j in matches_data:
        src = j.get("source", "Other")
        sources[src] = sources.get(src, 0) + 1
    
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
    
    # Download all letters ZIP (if any exist)
    letter_files = []
    if os.path.exists(LETTERS_DIR):
        letter_files = [f for f in os.listdir(LETTERS_DIR) if f.endswith(".txt")]
    
    if letter_files:
        col1, col2 = st.columns([3, 1])
        with col1:
            st.markdown(f"### 🎯 Your Top {len(matches_data)} Matches")
        with col2:
            zip_data = build_zip(LETTERS_DIR)
            st.download_button(
                f"📦 Download {len(letter_files)} Letters",
                data=zip_data,
                file_name="jobbot_cover_letters.zip",
                mime="application/zip",
                use_container_width=True,
            )
    else:
        st.markdown(f"### 🎯 Your Top {len(matches_data)} Matches")
        st.caption("💡 Click 'Generate Letter' on any job to create a tailored cover letter")
    
    # Job cards
    for i, job in enumerate(matches_data, 1):
        score = job.get("match_score", 0)
        company = job.get("company", "Unknown")
        title = job.get("title", "Unknown")
        source = job.get("source", "")
        summary = strip_html(job.get("summary", ""))[:400]
        
        # Score badge
        if score >= 75:
            badge_emoji = "🔥"
            badge_class = "score-excellent"
        elif score >= 60:
            badge_emoji = "⭐"
            badge_class = "score-good"
        else:
            badge_emoji = "👍"
            badge_class = "score-fair"
        
        with st.expander(f"#{i} · {badge_emoji} {company} — {title} ({score}%)"):
            col1, col2 = st.columns([3, 1])
            
            with col1:
                st.markdown(f"**{title}**")
                st.markdown(f"🏢 **{company}** · <span class='source-badge'>{source}</span>", unsafe_allow_html=True)
                if summary:
                    st.write(summary)
            
            with col2:
                st.markdown(
                    f'<div style="text-align:center; margin-bottom:0.5rem;">'
                    f'<span class="score-badge {badge_class}">{score}%</span>'
                    f'</div>',
                    unsafe_allow_html=True
                )
                if job.get("apply_url"):
                    st.link_button("🔗 Apply Now", job["apply_url"], use_container_width=True)
                
                # Per-job cover letter button
                letter_content, letter_fname = find_cover_letter(company, title)
                if not letter_content:
                    if st.button("📝 Generate Letter", key=f"gen_{i}", use_container_width=True):
                        with st.spinner("Writing cover letter..."):
                            try:
                                os.makedirs(LETTERS_DIR, exist_ok=True)
                                profile = load_json(PROFILE_FILE)
                                generate_cover_letter(job, profile, LETTERS_DIR)
                                st.rerun()
                            except Exception as e:
                                st.error(f"Failed: {e}")
            
            # Show cover letter if it exists
            letter_content, letter_fname = find_cover_letter(company, title)
            if letter_content:
                st.markdown("---")
                st.markdown('<p class="cover-letter-label">📝 Tailored Cover Letter</p>', unsafe_allow_html=True)
                st.markdown(f'<div class="cover-letter-box">{letter_content}</div>', unsafe_allow_html=True)
                st.download_button(
                    "📥 Download Letter",
                    data=letter_content,
                    file_name=letter_fname or f"cover_letter_{i}.txt",
                    mime="text/plain",
                    key=f"dl_{i}",
                    use_container_width=True,
                )

# ============================================
# FOOTER
# ============================================

st.markdown("""
<div class="footer">
    Built with ❤️ using Streamlit & Gemini 2.5 Flash<br>
    <a href="https://github.com" target="_blank">View on GitHub</a> · 
    <a href="#" onclick="alert('Feature coming soon!')">Report Bug</a>
</div>
""", unsafe_allow_html=True)
