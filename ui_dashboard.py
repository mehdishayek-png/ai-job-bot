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

/* ============ CARDS ============ */
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

/* ============ SKILL CHIPS ============ */
.skills-container {
    display: flex;
    flex-wrap: wrap;
    gap: 0.5rem;
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
}

/* ============ STATS ============ */
.stats-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
    gap: 1rem;
    margin: 1.5rem 0;
}

.stat-card {
    background: #fff;
    border: 1px solid #e8e8f0;
    border-radius: 14px;
    padding: 1.25rem 1rem;
    text-align: center;
    box-shadow: 0 1px 4px rgba(0,0,0,0.04);
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

/* ============ SOURCE BADGES ============ */
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

/* ============ EXPANDERS (job cards) ============ */
.streamlit-expanderHeader {
    background: #fff !important;
    border: 1px solid #e8e8f0 !important;
    border-radius: 12px !important;
    font-weight: 600 !important;
    color: #1a1a2e !important;
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
/* Fix text colors in expanders, markdown, captions */
.stMarkdown, .stMarkdown p, .stCaption, .stText { color: #3d3d56 !important; }
.stAlert p { color: inherit !important; }
label, .stSelectbox label, .stTextInput label, .stTextArea label { color: #3d3d56 !important; }

/* Expander content readability */
div[data-testid="stExpander"] details summary span { color: #1a1a2e !important; }
div[data-testid="stExpander"] div[data-testid="stMarkdownContainer"] p { color: #3d3d56 !important; }

/* Progress bar */
.stProgress > div > div > div { background: #6c5ce7 !important; }

/* Links */
a { color: #6c5ce7; }
a:hover { color: #5b4bd5; }

/* Code blocks in progress */
.stCodeBlock, pre { background: #f8f8fc !important; color: #3d3d56 !important; }
</style>
""", unsafe_allow_html=True)

# ============================================
# IMPORTS & SETUP
# ============================================

load_dotenv()

# ============================================
# MODULE RELOAD — Critical for Streamlit hot-reload
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
    if _mod in sys.modules:
        try:
            importlib.reload(sys.modules[_mod])
        except Exception:
            # Remove corrupted module so fresh import works
            sys.modules.pop(_mod, None)

# Import functions from other modules
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
                    # Preserve user settings from existing profile
                    existing = load_json(PROFILE_FILE)
                    
                    profile = build_profile(resume_path, PROFILE_FILE)
                    
                    # Re-add user-set fields that the parser doesn't know about
                    if existing:
                        for field in ["country", "state", "experience", "job_preference"]:
                            if field not in profile and field in existing:
                                profile[field] = existing[field]
                        # Set defaults if first time
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

    # Experience and job preference
    exp_col1, exp_col2 = st.columns(2)
    with exp_col1:
        EXP_OPTIONS = ["0–1 years", "1–3 years", "3–6 years", "6–10 years", "10+ years"]
        current_exp = profile.get("experience", "3–6 years") if profile else "3–6 years"
        if current_exp not in EXP_OPTIONS:
            current_exp = "3–6 years"
        exp_input = st.selectbox(
            "📅 Years of Experience",
            options=EXP_OPTIONS,
            index=EXP_OPTIONS.index(current_exp),
            help="Used to filter out jobs too senior or too junior for you"
        )
    with exp_col2:
        PREF_OPTIONS = ["🏙️ Local jobs in my city", "🌐 Remote jobs", "🔀 Both (local + remote)"]
        current_pref = profile.get("job_preference", "🔀 Both (local + remote)") if profile else "🔀 Both (local + remote)"
        if current_pref not in PREF_OPTIONS:
            current_pref = "🔀 Both (local + remote)"
        pref_input = st.selectbox(
            "🎯 Job Preference",
            options=PREF_OPTIONS,
            index=PREF_OPTIONS.index(current_pref),
            help="Focus search on local city jobs, remote-only, or both"
        )
    
    if st.button("💾 Save Profile", use_container_width=True):
        skills_list = [s.strip() for s in skills_input.split("\n") if s.strip()]
        if not skills_list and not name_input:
            st.error("⚠️ Please enter at least a name or some skills")
        else:
            # Preserve fields from LLM parsing that user doesn't edit
            existing = load_json(PROFILE_FILE) or {}
            updated_profile = {
                "name": name_input or "Candidate",
                "headline": headline_input,
                "skills": skills_list,
                "country": country_input,
                "state": state_input,
                "experience": exp_input,
                "job_preference": pref_input,
                # Preserve LLM-extracted fields
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
        
        # Check if results are thin and user has a city — offer to expand
        matches_data_check = load_json(MATCHES_FILE)
        match_count = len(matches_data_check) if isinstance(matches_data_check, list) else 0
        user_state = profile.get("state", "Any") if profile else "Any"
        user_country = profile.get("country", "") if profile else ""

        col1, col2 = st.columns(2)
        with col1:
            if st.button("🔄 Re-run Matching (Fresh Jobs)", use_container_width=True):
                st.session_state.pop("_matching_done", None)
                for fp in [JOBS_FILE, MATCHES_FILE, CACHE_FILE]:
                    if os.path.exists(fp):
                        os.remove(fp)
                if os.path.exists(LETTERS_DIR):
                    for lf in os.listdir(LETTERS_DIR):
                        os.remove(os.path.join(LETTERS_DIR, lf))
                st.rerun()
        
        with col2:
            if match_count < 5 and user_state != "Any" and user_country:
                if st.button(f"🌍 Expand to all of {user_country}", type="primary", use_container_width=True):
                    # Widen search: set state to "Any" and re-run
                    profile_data = load_json(PROFILE_FILE)
                    if profile_data:
                        profile_data["state"] = "Any"
                        save_json(PROFILE_FILE, profile_data)
                    st.session_state.pop("_matching_done", None)
                    for fp in [JOBS_FILE, MATCHES_FILE, CACHE_FILE]:
                        if os.path.exists(fp):
                            os.remove(fp)
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
                
                # Job location and experience info
                job_location = job.get("location", "")
                if not job_location:
                    # Try to extract from summary or other fields
                    for tag in job.get("location_tags", []):
                        if tag:
                            job_location = tag
                            break
                
                info_parts = []
                if job_location:
                    info_parts.append(f"📍 {job_location}")
                # Try to extract experience from summary
                import re as _re
                exp_match = _re.search(r'(\d+)\+?\s*(?:to\s*\d+\s*)?(?:years?|yrs?)\s*(?:of\s*)?(?:experience|exp)?', 
                                       job.get("summary", "").lower())
                if exp_match:
                    info_parts.append(f"📅 {exp_match.group(0).strip()}")
                
                if info_parts:
                    st.caption(" · ".join(info_parts))
                
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
