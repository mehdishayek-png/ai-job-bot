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
# CUSTOM CSS — Canva-inspired warm, lively design
# ============================================

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=Space+Mono:wght@400;700&display=swap');

:root {
    --primary: #7c3aed;
    --primary-light: #a78bfa;
    --primary-bg: #f5f3ff;
    --primary-border: #ddd6fe;
    --accent-coral: #f43f5e;
    --accent-amber: #f59e0b;
    --accent-emerald: #10b981;
    --accent-sky: #0ea5e9;
    --bg-main: #fafaf9;
    --bg-card: #ffffff;
    --bg-elevated: #f5f5f4;
    --text-primary: #1c1917;
    --text-secondary: #57534e;
    --text-muted: #a8a29e;
    --border: #e7e5e4;
    --border-hover: #d6d3d1;
    --shadow-sm: 0 1px 2px rgba(0,0,0,0.05);
    --shadow-md: 0 4px 12px rgba(0,0,0,0.08);
    --radius-sm: 8px;
    --radius-md: 12px;
    --radius-lg: 16px;
    --radius-xl: 20px;
}

* { margin: 0; padding: 0; box-sizing: border-box; }

.stApp {
    font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif !important;
    background: var(--bg-main) !important;
}

h1, h2, h3, h4, h5, h6,
.stMarkdown h1, .stMarkdown h2, .stMarkdown h3 {
    font-family: 'Plus Jakarta Sans', sans-serif !important;
    font-weight: 800 !important;
    letter-spacing: -0.03em;
    color: var(--text-primary) !important;
}

p, li, span, div {
    color: var(--text-secondary);
    font-family: 'Plus Jakarta Sans', sans-serif !important;
}

code, .stCode, pre { font-family: 'Space Mono', monospace !important; }

/* ============ HERO ============ */
.hero {
    background: linear-gradient(135deg, #7c3aed 0%, #a78bfa 35%, #f43f5e 100%);
    border-radius: var(--radius-xl); padding: 2.8rem 2.2rem;
    margin-bottom: 1.5rem; position: relative; overflow: hidden;
    box-shadow: 0 8px 32px rgba(124,58,237,0.25);
}
.hero::before {
    content: ''; position: absolute; top: -50%; right: -20%;
    width: 500px; height: 500px;
    background: radial-gradient(circle, rgba(255,255,255,0.12) 0%, transparent 70%);
    filter: blur(60px);
}
.hero::after {
    content: ''; position: absolute; bottom: -30%; left: -10%;
    width: 300px; height: 300px;
    background: radial-gradient(circle, rgba(244,63,94,0.2) 0%, transparent 60%);
    filter: blur(40px);
}
.hero-content { position: relative; z-index: 1; }
.hero h1 { color: #ffffff !important; font-size: 2.6rem !important; font-weight: 800 !important; margin: 0 0 0.5rem 0 !important; line-height: 1.1; }
.hero-subtitle { color: rgba(255,255,255,0.9); font-size: 1.05rem; margin: 0 0 1.4rem 0; font-weight: 500; line-height: 1.6; max-width: 600px; }
.hero-tags { display: flex; gap: 0.6rem; flex-wrap: wrap; margin-top: 1rem; }
.hero-tag { background: rgba(255,255,255,0.18); backdrop-filter: blur(12px); border: 1px solid rgba(255,255,255,0.25); color: #fff; padding: 0.45rem 0.9rem; border-radius: var(--radius-sm); font-size: 0.78rem; font-weight: 600; }

/* ============ STEPPER ============ */
.stepper { display: flex; justify-content: center; align-items: center; gap: 0.75rem; margin: 1.5rem 0 2rem; padding: 1rem 1.5rem; background: var(--bg-card); border: 1px solid var(--border); border-radius: var(--radius-lg); box-shadow: var(--shadow-sm); }
.step { display: flex; align-items: center; gap: 0.6rem; padding: 0.6rem 1rem; border-radius: var(--radius-md); font-size: 0.85rem; font-weight: 600; color: var(--text-muted); }
.step-icon { width: 34px; height: 34px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 1rem; }
.step.done { color: var(--accent-emerald); }
.step.done .step-icon { background: var(--accent-emerald); color: #fff; box-shadow: 0 2px 8px rgba(16,185,129,0.3); }
.step.active { color: var(--primary); background: var(--primary-bg); }
.step.active .step-icon { background: var(--primary); color: #fff; box-shadow: 0 2px 8px rgba(124,58,237,0.35); animation: pulse 2s ease-in-out infinite; }
.step.pending { color: var(--text-muted); }
.step.pending .step-icon { background: var(--bg-elevated); border: 2px dashed var(--border); }
.step-connector { width: 40px; height: 2px; background: var(--border); }
@keyframes pulse { 0%, 100% { transform: scale(1); } 50% { transform: scale(1.1); } }

/* ============ CARDS ============ */
.glass-card { background: var(--bg-card); border: 1px solid var(--border); border-radius: var(--radius-xl); padding: 1.75rem; margin-bottom: 1.25rem; box-shadow: var(--shadow-sm); }
.glass-card:hover { border-color: var(--border-hover); box-shadow: var(--shadow-md); }
.card-header { display: flex; align-items: center; gap: 0.85rem; margin-bottom: 1.25rem; }
.card-icon { width: 44px; height: 44px; border-radius: var(--radius-md); display: flex; align-items: center; justify-content: center; font-size: 1.3rem; background: var(--primary-bg); border: 1px solid var(--primary-border); }
.card-title { font-size: 1.2rem !important; font-weight: 800 !important; color: var(--text-primary) !important; margin: 0 !important; }

/* ============ SKILL CHIPS ============ */
.skills-container { display: flex; flex-wrap: wrap; gap: 0.45rem; margin-top: 0.75rem; }
.skill-chip { padding: 0.35rem 0.75rem; border-radius: 100px; font-size: 0.78rem; font-weight: 600; }
.skill-chip:nth-child(5n+1) { background: #f5f3ff; color: #7c3aed; border: 1px solid #ddd6fe; }
.skill-chip:nth-child(5n+2) { background: #fef2f2; color: #ef4444; border: 1px solid #fecaca; }
.skill-chip:nth-child(5n+3) { background: #ecfdf5; color: #059669; border: 1px solid #a7f3d0; }
.skill-chip:nth-child(5n+4) { background: #fff7ed; color: #ea580c; border: 1px solid #fed7aa; }
.skill-chip:nth-child(5n+5) { background: #f0f9ff; color: #0284c7; border: 1px solid #bae6fd; }

/* ============ STATS ============ */
.stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 0.75rem; margin: 1.5rem 0; }
.stat-card { background: var(--bg-card); border: 1px solid var(--border); border-radius: var(--radius-lg); padding: 1.25rem 1rem; text-align: center; box-shadow: var(--shadow-sm); }
.stat-card:hover { box-shadow: var(--shadow-md); transform: translateY(-2px); }
.stat-value { font-size: 2rem; font-weight: 800; line-height: 1; margin-bottom: 0.35rem; }
.stat-value.purple { color: var(--primary); }
.stat-value.coral { color: var(--accent-coral); }
.stat-value.emerald { color: var(--accent-emerald); }
.stat-value.amber { color: var(--accent-amber); }
.stat-label { color: var(--text-muted); font-size: 0.75rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.06em; }

/* ============ BADGES ============ */
.score-badge { display: inline-block; padding: 0.45rem 1.1rem; border-radius: 100px; font-size: 0.95rem; font-weight: 700; font-family: 'Space Mono', monospace !important; }
.score-excellent { background: linear-gradient(135deg, #ecfdf5, #d1fae5); color: #059669; border: 1px solid #a7f3d0; }
.score-good { background: linear-gradient(135deg, #fffbeb, #fef3c7); color: #d97706; border: 1px solid #fde68a; }
.score-fair { background: linear-gradient(135deg, #f5f3ff, #ede9fe); color: #7c3aed; border: 1px solid #ddd6fe; }
.source-badge { display: inline-block; padding: 0.2rem 0.6rem; border-radius: 100px; font-size: 0.65rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em; background: var(--bg-elevated); color: var(--text-secondary); border: 1px solid var(--border); }
.timestamp-badge { display: inline-flex; align-items: center; gap: 0.3rem; padding: 0.2rem 0.6rem; border-radius: 100px; font-size: 0.65rem; font-weight: 700; letter-spacing: 0.04em; }
.timestamp-fresh { background: #ecfdf5; color: #059669; border: 1px solid #a7f3d0; }
.timestamp-recent { background: #fff7ed; color: #ea580c; border: 1px solid #fed7aa; }
.timestamp-older { background: var(--bg-elevated); color: var(--text-muted); border: 1px solid var(--border); }
.pin-badge { display: inline-flex; align-items: center; gap: 0.25rem; padding: 0.2rem 0.6rem; border-radius: 100px; font-size: 0.65rem; font-weight: 700; background: #fef2f2; color: #ef4444; border: 1px solid #fecaca; }

/* ============ BUTTONS ============ */
.stButton > button { background: var(--primary) !important; color: white !important; border: none !important; border-radius: var(--radius-md) !important; padding: 0.65rem 1.25rem !important; font-weight: 700 !important; font-size: 0.9rem !important; font-family: 'Plus Jakarta Sans', sans-serif !important; box-shadow: 0 2px 8px rgba(124,58,237,0.2) !important; }
.stButton > button:hover { background: #6d28d9 !important; transform: translateY(-1px) !important; box-shadow: 0 4px 16px rgba(124,58,237,0.3) !important; }

/* ============ EXPANDERS ============ */
div[data-testid="stExpander"] { border: 1px solid var(--border) !important; border-radius: var(--radius-md) !important; background: var(--bg-card) !important; box-shadow: var(--shadow-sm) !important; margin-bottom: 0.5rem !important; }
div[data-testid="stExpander"]:hover { border-color: var(--primary-border) !important; box-shadow: var(--shadow-md) !important; }

/* ============ INPUTS — CRITICAL: visible text + cursor ============ */
.stTextInput > div > div > input,
.stTextArea > div > div > textarea {
    background: var(--bg-card) !important; border: 1.5px solid var(--border) !important;
    border-radius: var(--radius-md) !important; color: var(--text-primary) !important;
    font-family: 'Plus Jakarta Sans', sans-serif !important; font-size: 0.9rem !important;
    font-weight: 500 !important; padding: 0.65rem 0.85rem !important;
    caret-color: var(--primary) !important; -webkit-text-fill-color: var(--text-primary) !important;
}
.stTextInput > div > div > input:focus,
.stTextArea > div > div > textarea:focus {
    border-color: var(--primary) !important; box-shadow: 0 0 0 3px rgba(124,58,237,0.12) !important; outline: none !important;
}
.stTextInput > div > div > input::placeholder,
.stTextArea > div > div > textarea::placeholder {
    color: var(--text-muted) !important; -webkit-text-fill-color: var(--text-muted) !important; opacity: 1 !important;
}

.stSelectbox > div > div, .stMultiSelect > div > div { background: var(--bg-card) !important; border: 1.5px solid var(--border) !important; border-radius: var(--radius-md) !important; }
.stSelectbox > div > div:focus-within, .stMultiSelect > div > div:focus-within { border-color: var(--primary) !important; box-shadow: 0 0 0 3px rgba(124,58,237,0.12) !important; }
.stSelectbox [data-baseweb="select"] span, .stMultiSelect [data-baseweb="select"] span { color: var(--text-primary) !important; -webkit-text-fill-color: var(--text-primary) !important; font-weight: 500 !important; }

label, .stSelectbox label, .stTextInput label, .stTextArea label, .stMultiSelect label, .stFileUploader label { color: var(--text-primary) !important; font-weight: 600 !important; font-size: 0.85rem !important; }

.stFileUploader > div { border: 2px dashed var(--border) !important; border-radius: var(--radius-md) !important; background: var(--bg-elevated) !important; }

/* ============ MISC ============ */
.divider { height: 1px; background: linear-gradient(90deg, transparent, var(--border), transparent); margin: 2rem 0; }
.cover-letter-box { background: var(--bg-elevated); border: 1px solid var(--border); border-radius: var(--radius-md); padding: 1.25rem; margin-top: 0.75rem; color: var(--text-secondary); line-height: 1.75; font-size: 0.88rem; }
.cover-letter-label { color: var(--primary); font-weight: 700; font-size: 0.82rem; text-transform: uppercase; letter-spacing: 0.04em; }
::-webkit-scrollbar { width: 6px; } ::-webkit-scrollbar-thumb { background: var(--border); border-radius: 3px; }
.footer { text-align: center; padding: 2rem 1rem; margin-top: 3rem; color: var(--text-muted); font-size: 0.78rem; border-top: 1px solid var(--border); }
.footer a { color: var(--primary); text-decoration: none; font-weight: 700; }

section[data-testid="stSidebar"] { background: var(--bg-card); border-right: 1px solid var(--border); }
section[data-testid="stSidebar"] * { color: var(--text-secondary); }
.stMarkdown, .stMarkdown p, .stCaption, .stText { color: var(--text-secondary) !important; }
.stMarkdown strong, .stMarkdown b { color: var(--text-primary) !important; }
.stAlert p { color: inherit !important; }
div[data-testid="stExpander"] details summary span { color: var(--text-primary) !important; font-weight: 600 !important; }
div[data-testid="stExpander"] div[data-testid="stMarkdownContainer"] p { color: var(--text-secondary) !important; }
.stProgress > div > div > div { background: var(--primary) !important; }
a { color: var(--primary); } a:hover { color: #6d28d9; }
.stCodeBlock, pre { background: var(--bg-elevated) !important; color: var(--text-primary) !important; border: 1px solid var(--border) !important; }
</style>
""", unsafe_allow_html=True)

# ============================================
# IMPORTS & SETUP
# ============================================
load_dotenv()
import importlib, sys

for _mod in ["location_utils", "job_fetcher", "resume_parser", "run_auto_apply", "cover_letter_generator"]:
    if _mod in sys.modules:
        try: importlib.reload(sys.modules[_mod])
        except Exception: sys.modules.pop(_mod, None)

try:
    from job_fetcher import fetch_all
    from resume_parser import build_profile
    from run_auto_apply import run_auto_apply_pipeline
    from cover_letter_generator import generate_cover_letter
    from location_utils import get_all_regions, get_region_display_name
except (ImportError, KeyError) as e:
    st.error(f"Missing module: {e}. Ensure all files are in the same directory.")
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
# COUNTRY / STATE DATA (comprehensive)
# ============================================
COUNTRY_OPTIONS = [
    "India", "United States", "United Kingdom", "Canada", "Germany",
    "Australia", "UAE", "Saudi Arabia", "Singapore", "Netherlands",
    "France", "Ireland", "Israel", "Brazil", "Japan", "South Korea",
    "Philippines", "Indonesia", "Malaysia", "Mexico", "Remote Only",
]

STATE_OPTIONS = {
    "India": ["Any", "Karnataka (Bangalore)", "Maharashtra (Mumbai/Pune)", "Delhi NCR",
              "Telangana (Hyderabad)", "Tamil Nadu (Chennai)", "West Bengal (Kolkata)",
              "Gujarat (Ahmedabad)", "Rajasthan (Jaipur)", "Uttar Pradesh (Noida/Lucknow)",
              "Kerala (Kochi)", "Haryana (Gurgaon)"],
    "United States": ["Any", "California", "New York", "Texas", "Washington",
                      "Massachusetts", "Illinois", "Florida", "Georgia", "Colorado"],
    "United Kingdom": ["Any", "London", "Manchester", "Edinburgh", "Birmingham", "Bristol"],
    "Canada": ["Any", "Ontario (Toronto)", "British Columbia (Vancouver)", "Quebec (Montreal)", "Alberta (Calgary)"],
    "Germany": ["Any", "Berlin", "Munich", "Hamburg", "Frankfurt"],
    "Australia": ["Any", "New South Wales (Sydney)", "Victoria (Melbourne)", "Queensland (Brisbane)"],
    "UAE": ["Any", "Dubai", "Abu Dhabi", "Sharjah"],
    "Saudi Arabia": ["Any", "Riyadh", "Jeddah", "Dammam"],
    "Singapore": ["Any"], "Netherlands": ["Any", "Amsterdam", "Rotterdam"],
    "France": ["Any", "Paris", "Lyon"], "Ireland": ["Any", "Dublin", "Cork"],
    "Israel": ["Any", "Tel Aviv", "Jerusalem"], "Brazil": ["Any", "São Paulo", "Rio de Janeiro"],
    "Japan": ["Any", "Tokyo", "Osaka"], "South Korea": ["Any", "Seoul", "Busan"],
    "Philippines": ["Any", "Metro Manila", "Cebu"], "Indonesia": ["Any", "Jakarta"],
    "Malaysia": ["Any", "Kuala Lumpur", "Penang"], "Mexico": ["Any", "Mexico City", "Guadalajara"],
    "Remote Only": ["Any"],
}

# ============================================
# UTILITY FUNCTIONS
# ============================================
def load_json(fp):
    if not os.path.exists(fp): return None
    try:
        with open(fp, "r", encoding="utf-8") as f: return json.load(f)
    except Exception: return None

def save_json(fp, data):
    os.makedirs(os.path.dirname(fp) or ".", exist_ok=True)
    with open(fp, "w", encoding="utf-8") as f: json.dump(data, f, indent=2, ensure_ascii=False)

def strip_html(text):
    if not text: return ""
    return re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ', text)).strip()

def build_zip(d):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for f in os.listdir(d):
            if f.endswith(".txt"): z.write(os.path.join(d, f), f)
    buf.seek(0); return buf.getvalue()

def find_cover_letter(company, title):
    if not os.path.exists(LETTERS_DIR): return None, None
    cc = re.sub(r'[^a-zA-Z0-9_\-]', '', company.replace(' ', '_')).lower()
    tc = re.sub(r'[^a-zA-Z0-9_\-]', '', title.replace(' ', '_')).lower()
    for fn in os.listdir(LETTERS_DIR):
        if fn.endswith(".txt") and (cc in fn.lower() or tc in fn.lower()):
            try:
                with open(os.path.join(LETTERS_DIR, fn), "r", encoding="utf-8") as f: return f.read(), fn
            except Exception: pass
    return None, None

def parse_job_timestamp(job):
    posted = job.get("posted_date") or ""
    if posted:
        try: return datetime.fromisoformat(posted.replace("Z", "+00:00"))
        except Exception: pass
    combined = f"{job.get('summary', '')} {job.get('title', '')}".lower()
    if "just posted" in combined or "just now" in combined: return datetime.now()
    m = re.search(r'(\d+)\s*(hour|day|week|month)s?\s*ago', combined)
    if m:
        n, u = int(m.group(1)), m.group(2)
        d = {"hour": timedelta(hours=n), "day": timedelta(days=n), "week": timedelta(weeks=n), "month": timedelta(days=n*30)}
        return datetime.now() - d.get(u, timedelta())
    return None

def format_timestamp(dt):
    if not dt: return None, None, "timestamp-older"
    diff = datetime.now() - dt
    s = diff.total_seconds()
    if s < 3600: return "Just now", dt.strftime("%b %d"), "timestamp-fresh"
    if s < 86400: return f"{int(s//3600)}h ago", dt.strftime("%b %d"), "timestamp-fresh"
    if diff.days < 3: return f"{diff.days}d ago", dt.strftime("%b %d"), "timestamp-fresh"
    if diff.days < 7: return f"{diff.days}d ago", dt.strftime("%b %d"), "timestamp-recent"
    if diff.days < 30: return f"{diff.days//7}w ago", dt.strftime("%b %d"), "timestamp-recent"
    return f"{diff.days//30}mo ago", dt.strftime("%b %d"), "timestamp-older"

# Pin management
def get_pinned(): return st.session_state.get("_pinned_jobs", set())
def toggle_pin(k):
    p = st.session_state.get("_pinned_jobs", set())
    p.symmetric_difference_update({k})
    st.session_state["_pinned_jobs"] = p
def job_key(j): return f"{j.get('company','')}__{j.get('title','')}__{j.get('apply_url','')[:50]}"

# ============================================
# SIDEBAR
# ============================================
with st.sidebar:
    st.markdown("### ⚡ Session")
    st.caption(f"ID: `{SESSION_ID}`")
    if st.button("🔄 Start Fresh", use_container_width=True):
        for key in list(st.session_state.keys()): del st.session_state[key]
        st.rerun()
    st.markdown("---")
    st.markdown("### 🧠 How It Works")
    st.markdown("**1.** Upload resume → AI extracts skills\n\n**2.** Scans 6+ job sources\n\n**3.** AI ranks best matches\n\n**4.** Generate cover letters")
    st.markdown("---")
    st.markdown("### 📡 Sources")
    for s in ["Google Jobs (LinkedIn, Indeed, Naukri...)", "Lever (50+ companies)", "Remotive", "WeWorkRemotely", "RemoteOK", "Jobicy"]:
        st.caption(f"• {s}")

# ============================================
# HERO
# ============================================
st.markdown("""
<div class="hero"><div class="hero-content">
    <h1>🚀 JobBot</h1>
    <p class="hero-subtitle">Upload your resume, get matched with the right opportunities, and generate tailored cover letters — all powered by AI.</p>
    <div class="hero-tags">
        <span class="hero-tag">🤖 AI Matching</span>
        <span class="hero-tag">📊 6+ Sources</span>
        <span class="hero-tag">🌍 Local + Remote</span>
        <span class="hero-tag">✉️ Cover Letters</span>
    </div>
</div></div>
""", unsafe_allow_html=True)

# ============================================
# STEPPER
# ============================================
profile = load_json(PROFILE_FILE)
matches = load_json(MATCHES_FILE)
s1 = "done" if profile and profile.get("skills") else "active"
s2 = "done" if matches else ("active" if s1 == "done" else "pending")
s3 = "done" if os.path.exists(LETTERS_DIR) and os.listdir(LETTERS_DIR) else ("active" if s2 == "done" else "pending")
st.markdown(f"""
<div class="stepper">
    <div class="step {s1}"><div class="step-icon">📄</div><span>Your Profile</span></div>
    <div class="step-connector"></div>
    <div class="step {s2}"><div class="step-icon">🎯</div><span>Find Jobs</span></div>
    <div class="step-connector"></div>
    <div class="step {s3}"><div class="step-icon">✉️</div><span>Apply</span></div>
</div>
""", unsafe_allow_html=True)

# ============================================
# STEP 1: PROFILE
# ============================================
st.markdown('<div class="glass-card">', unsafe_allow_html=True)
st.markdown('<div class="card-header"><div class="card-icon">📄</div><h2 class="card-title">Step 1: Your Profile</h2></div>', unsafe_allow_html=True)

col1, col2 = st.columns([2, 1])
with col1:
    uploaded_resume = st.file_uploader("Upload your resume (PDF)", type=["pdf"], help="We'll extract your skills automatically", key="resume_upload")
with col2:
    if uploaded_resume:
        if st.button("🔍 Parse Resume", type="primary", use_container_width=True):
            with st.spinner("Analyzing your resume with AI..."):
                try:
                    rp = os.path.join(DATA_DIR, "resume.pdf")
                    with open(rp, "wb") as f: f.write(uploaded_resume.getbuffer())
                    existing = load_json(PROFILE_FILE)
                    profile = build_profile(rp, PROFILE_FILE)
                    if existing:
                        for fld in ["country", "state", "experience", "job_preference"]:
                            if fld not in profile and fld in existing: profile[fld] = existing[fld]
                    profile.setdefault("country", "")
                    profile.setdefault("state", "Any")
                    profile.setdefault("experience", "3–6 years")
                    profile.setdefault("job_preference", "🔀 Both (local + remote)")
                    save_json(PROFILE_FILE, profile)
                    st.success("✅ Resume parsed!")
                    time.sleep(0.5); st.rerun()
                except Exception as e: st.error(f"❌ Error: {e}")

profile = load_json(PROFILE_FILE)
if profile and profile.get("skills"):
    st.markdown("---")
    st.markdown(f"**👤 {profile.get('name', 'Candidate')}**")
    if profile.get('headline'): st.caption(profile['headline'])
    skills = profile.get("skills", [])
    if skills:
        st.markdown(f'<div class="skills-container">{"".join(f"""<span class="skill-chip">{s}</span>""" for s in skills)}</div>', unsafe_allow_html=True)
        st.caption(f"💡 {len(skills)} skills detected — used for keyword matching")
    country = profile.get("country", "")
    state = profile.get("state", "")
    if country and country != "Remote Only":
        st.caption(f"📍 {country}" + (f" · {state}" if state and state != "Any" else ""))
    elif country == "Remote Only": st.caption("🌐 Remote Only")
else:
    st.info("👆 Upload your resume to get started, or create a profile manually below")

# Manual edit
with st.expander("✏️ Edit Profile Manually" if profile else "✏️ Create Profile Manually"):
    name_input = st.text_input("Full Name", value=profile.get("name", "") if profile else "", placeholder="e.g. Jane Doe")
    headline_input = st.text_input("Professional Headline", value=profile.get("headline", "") if profile else "", placeholder="e.g. Customer Experience Specialist")
    skills_input = st.text_area("Skills (one per line)", value="\n".join(profile.get("skills", [])) if profile else "", height=150, placeholder="customer experience\nSalesforce\nSaaS operations")

    lc1, lc2 = st.columns(2)
    with lc1:
        cc = profile.get("country", "") if profile else ""
        co = list(COUNTRY_OPTIONS)
        if cc and cc not in co: co.append(cc)
        country_input = st.selectbox("📍 Country", options=["— Select Country —"] + co,
            index=(co.index(cc) + 1) if cc in co else 0,
            help="We'll prioritize local job listings for your country")
        if country_input == "— Select Country —": country_input = ""
    with lc2:
        sl = STATE_OPTIONS.get(country_input, ["Any"])
        cs = profile.get("state", "Any") if profile else "Any"
        if cs not in sl: cs = "Any"
        state_input = st.selectbox("🏙️ State / City", options=sl, index=sl.index(cs) if cs in sl else 0)

    ec1, ec2 = st.columns(2)
    with ec1:
        EXP = ["0–1 years", "1–3 years", "3–6 years", "6–10 years", "10+ years"]
        ce = profile.get("experience", "3–6 years") if profile else "3–6 years"
        if ce not in EXP: ce = "3–6 years"
        exp_input = st.selectbox("📅 Experience", options=EXP, index=EXP.index(ce))
    with ec2:
        PREFS = ["🏙️ Local jobs in my city", "🌐 Remote jobs", "🔀 Both (local + remote)"]
        cp = profile.get("job_preference", "🔀 Both (local + remote)") if profile else "🔀 Both (local + remote)"
        if cp not in PREFS: cp = "🔀 Both (local + remote)"
        pref_input = st.selectbox("🎯 Job Preference", options=PREFS, index=PREFS.index(cp))

    if st.button("💾 Save Profile", use_container_width=True):
        sk = [s.strip() for s in skills_input.split("\n") if s.strip()]
        if not sk and not name_input: st.error("⚠️ Enter at least a name or skills")
        else:
            ex = load_json(PROFILE_FILE) or {}
            save_json(PROFILE_FILE, {"name": name_input or "Candidate", "headline": headline_input,
                "skills": sk, "country": country_input, "state": state_input,
                "experience": exp_input, "job_preference": pref_input,
                "industry": ex.get("industry", ""), "search_terms": ex.get("search_terms", [])})
            st.success("✅ Profile saved!"); time.sleep(0.5); st.rerun()

st.markdown('</div>', unsafe_allow_html=True)

# ============================================
# STEP 2: JOB MATCHING
# ============================================
st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
st.markdown('<div class="glass-card">', unsafe_allow_html=True)
st.markdown('<div class="card-header"><div class="card-icon">🎯</div><h2 class="card-title">Step 2: Find Your Matches</h2></div>', unsafe_allow_html=True)

profile = load_json(PROFILE_FILE)
profile_ready = bool(profile and profile.get("skills"))

if not profile_ready:
    st.warning("⚠️ Complete your profile above to unlock job matching")
else:
    with st.expander("ℹ️ How does matching work?"):
        st.markdown("**3-phase matching:** Keyword Extraction → Local Scoring → AI Ranking (Gemini 2.5 Flash)\n\n**Sources:** Google Jobs (LinkedIn, Indeed, Naukri, Glassdoor), Lever (50+ companies), Remotive, WeWorkRemotely, RemoteOK, Jobicy")

    with st.expander("📁 Upload Custom Jobs (Optional)"):
        jobs_upload = st.file_uploader("Upload jobs.json", type=["json"], help="Use your own jobs file")
        if jobs_upload:
            try:
                jd = json.loads(jobs_upload.getvalue()); save_json(JOBS_FILE, jd)
                st.success(f"✅ Loaded {len(jd)} jobs")
            except Exception as e: st.error(f"❌ Invalid JSON: {e}")

    if st.session_state.get("_matching_done"):
        st.success("✅ Matching complete! Scroll down to see your results.")
        mdc = load_json(MATCHES_FILE)
        mc = len(mdc) if isinstance(mdc, list) else 0
        us = profile.get("state", "Any") if profile else "Any"
        uc = profile.get("country", "") if profile else ""

        c1, c2 = st.columns(2)
        with c1:
            if st.button("🔄 Re-run (Fresh Jobs)", use_container_width=True):
                st.session_state.pop("_matching_done", None); st.session_state.pop("_pinned_jobs", None)
                for fp in [JOBS_FILE, MATCHES_FILE, CACHE_FILE]:
                    if os.path.exists(fp): os.remove(fp)
                if os.path.exists(LETTERS_DIR):
                    for lf in os.listdir(LETTERS_DIR): os.remove(os.path.join(LETTERS_DIR, lf))
                st.rerun()
        with c2:
            if mc < 5 and us != "Any" and uc:
                if st.button(f"🌍 Expand to all of {uc}", type="primary", use_container_width=True):
                    pd = load_json(PROFILE_FILE)
                    if pd: pd["state"] = "Any"; save_json(PROFILE_FILE, pd)
                    st.session_state.pop("_matching_done", None)
                    for fp in [JOBS_FILE, MATCHES_FILE, CACHE_FILE]:
                        if os.path.exists(fp): os.remove(fp)
                    st.rerun()

    elif st.session_state.get("_matching_running"):
        st.warning("⏳ Matching in progress... usually 30-60 seconds.")
    else:
        # Dynamic description based on user's actual location — no hardcoded "India"
        country = profile.get("country", "")
        state = profile.get("state", "")
        pref = profile.get("job_preference", "")
        if country and country != "Remote Only":
            loc_d = f"**{state + ', ' if state and state != 'Any' else ''}{country}**"
        elif country == "Remote Only":
            loc_d = "**remote opportunities worldwide**"
        else:
            loc_d = "**relevant regions**"

        st.markdown(f"We'll scan **6+ sources** focused on {loc_d}, then rank the best matches using AI.")

        if st.button("🚀 Start Job Matching", type="primary", use_container_width=True):
            st.session_state["_matching_running"] = True
            status_text = st.empty()
            progress_bar = st.progress(0, text="Starting pipeline...")
            detail_box = st.empty()
            log_lines = []
            stage_pct = {"Starting pipeline": 0, "Fetching jobs": 5, "Remotive": 20,
                "Lever": 30, "Google Jobs": 40, "SerpAPI": 40, "Loaded": 50,
                "Location filter": 55, "Matching against": 60, "Phase 1": 65,
                "Batch 1": 70, "Batch 2": 78, "Batch 3": 85, "Threshold": 95, "Done": 100}

            def progress_callback(msg):
                log_lines.append(msg)
                detail_box.code("\n".join(log_lines[-8:]), language=None)
                pct = max((p for k, p in stage_pct.items() if k.lower() in msg.lower()), default=0)
                pct = max(pct, getattr(progress_callback, '_max_pct', 0))
                progress_callback._max_pct = pct
                progress_bar.progress(min(pct, 100) / 100, text=msg[:80])
            progress_callback._max_pct = 0

            try:
                status_text.info("🔍 Scanning job sources and running AI matching...")
                result = run_auto_apply_pipeline(
                    profile_file=PROFILE_FILE, jobs_file=JOBS_FILE, matches_file=MATCHES_FILE,
                    cache_file=CACHE_FILE, log_file=LOG_FILE, letters_dir=None,
                    progress_callback=progress_callback)
                progress_bar.progress(1.0, text="Complete!")
                st.session_state["_matching_done"] = True
                st.session_state.pop("_matching_running", None)
                if result and result.get("status") == "success":
                    status_text.success(f"✅ Found {result['matches']} matches from {result['total_scored']} jobs!")
                elif result and result.get("status") == "no_matches":
                    status_text.warning("⚠️ No strong matches. Try broadening skills.")
                else: status_text.error(f"❌ Pipeline error: {result}")
                time.sleep(1); st.rerun()
            except Exception as e:
                st.session_state.pop("_matching_running", None)
                progress_bar.progress(1.0, text="Error")
                status_text.error(f"❌ Error: {e}"); st.exception(e)

st.markdown('</div>', unsafe_allow_html=True)

# ============================================
# STEP 3: RESULTS (sorted by recency, with pins)
# ============================================
matches_data = load_json(MATCHES_FILE)

if isinstance(matches_data, list) and matches_data:
    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)

    # Parse timestamps for sorting
    for j in matches_data:
        j["_parsed_ts"] = parse_job_timestamp(j)

    pinned = get_pinned()

    # Sort: pinned first, then by timestamp (newest first), then by score
    def sort_key(j):
        ts = j.get("_parsed_ts")
        return (0, -ts.timestamp()) if ts else (1, -j.get("match_score", 0))

    pj = sorted([j for j in matches_data if job_key(j) in pinned], key=sort_key)
    uj = sorted([j for j in matches_data if job_key(j) not in pinned], key=sort_key)
    sorted_matches = pj + uj

    scores = [j.get("match_score", 0) for j in matches_data]
    avg_s = sum(scores) / len(scores) if scores else 0

    lf = []
    if os.path.exists(LETTERS_DIR):
        lf = [f for f in os.listdir(LETTERS_DIR) if f.endswith(".txt")]

    st.markdown(f"""
    <div class="stats-grid">
        <div class="stat-card"><div class="stat-value purple">{len(matches_data)}</div><div class="stat-label">Matches</div></div>
        <div class="stat-card"><div class="stat-value coral">{avg_s:.0f}%</div><div class="stat-label">Avg Score</div></div>
        <div class="stat-card"><div class="stat-value emerald">{max(scores)}%</div><div class="stat-label">Top Score</div></div>
        <div class="stat-card"><div class="stat-value amber">{len(lf)}</div><div class="stat-label">Letters</div></div>
    </div>
    """, unsafe_allow_html=True)

    if lf:
        zc1, zc2 = st.columns([3, 1])
        with zc1: st.markdown(f"### 🎯 Your Top {len(matches_data)} Matches")
        with zc2:
            st.download_button(f"📦 Download {len(lf)} Letters", data=build_zip(LETTERS_DIR),
                file_name="jobbot_cover_letters.zip", mime="application/zip", use_container_width=True)
    else:
        st.markdown(f"### 🎯 Your Top {len(matches_data)} Matches")
        st.caption("💡 Click 'Generate Letter' on any job to create a cover letter.")

    if pinned:
        st.caption(f"📌 {len(pj)} pinned shown first · Sorted newest → oldest")
    else:
        st.caption("Sorted newest → oldest · Pin jobs to keep them at the top")

    # Job cards
    for i, j in enumerate(sorted_matches, 1):
        sc = j.get("match_score", 0)
        co = j.get("company", "Unknown")
        ti = j.get("title", "Unknown")
        src = j.get("source", "")
        sm = strip_html(j.get("summary", ""))[:400]
        jk = job_key(j)
        ip = jk in pinned

        ts_text, ts_full, ts_css = format_timestamp(j.get("_parsed_ts"))
        be = "🔥" if sc >= 75 else ("⭐" if sc >= 60 else "👍")

        pm = "📌 " if ip else ""
        tm = f" · {ts_text}" if ts_text else ""
        label = f"{pm}#{i} · {be} {co} — {ti} ({sc}%){tm}"

        with st.expander(label):
            c1, c2 = st.columns([3, 1])
            with c1:
                st.markdown(f"**{ti}**")
                ih = f"🏢 **{co}**"
                if src: ih += f" · <span class='source-badge'>{src}</span>"
                if ts_text: ih += f" · <span class='timestamp-badge {ts_css}'>🕐 {ts_text}</span>"
                if ip: ih += " · <span class='pin-badge'>📌 Pinned</span>"
                st.markdown(ih, unsafe_allow_html=True)

                jl = j.get("location", "")
                if not jl:
                    for t in j.get("location_tags", []):
                        if t: jl = t; break
                parts = []
                if jl: parts.append(f"📍 {jl}")
                em = re.search(r'(\d+)\+?\s*(?:to\s*\d+\s*)?(?:years?|yrs?)\s*(?:of\s*)?(?:experience|exp)?', j.get("summary", "").lower())
                if em: parts.append(f"📅 {em.group(0).strip()}")
                if parts: st.caption(" · ".join(parts))
                if sm: st.write(sm)

            with c2:
                bc = "score-excellent" if sc >= 75 else ("score-good" if sc >= 60 else "score-fair")
                st.markdown(f'<div style="text-align:center;margin-bottom:0.5rem;"><span class="score-badge {bc}">{sc}%</span></div>', unsafe_allow_html=True)
                if j.get("apply_url"):
                    st.link_button("🔗 Apply Now", j["apply_url"], use_container_width=True)
                if st.button("📌 Unpin" if ip else "📌 Pin", key=f"pin_{i}", use_container_width=True):
                    toggle_pin(jk); st.rerun()
                lc, ln = find_cover_letter(co, ti)
                if not lc:
                    if st.button("📝 Letter", key=f"gen_{i}", use_container_width=True):
                        with st.spinner("Writing..."):
                            try:
                                os.makedirs(LETTERS_DIR, exist_ok=True)
                                generate_cover_letter(j, load_json(PROFILE_FILE), LETTERS_DIR)
                                st.rerun()
                            except Exception as e: st.error(f"Failed: {e}")

            lc, ln = find_cover_letter(co, ti)
            if lc:
                st.markdown("---")
                st.markdown('<p class="cover-letter-label">📝 Tailored Cover Letter</p>', unsafe_allow_html=True)
                st.markdown(f'<div class="cover-letter-box">{lc}</div>', unsafe_allow_html=True)
                st.download_button("📥 Download", data=lc, file_name=ln or f"letter_{i}.txt",
                    mime="text/plain", key=f"dl_{i}", use_container_width=True)

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
