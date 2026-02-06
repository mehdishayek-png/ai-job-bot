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
    page_title="JobBot · Your AI Job Hunter",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ============================================
# CUSTOM CSS — warm, energetic design
# ============================================

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:ital,opsz,wght@0,9..40,300;0,9..40,400;0,9..40,500;0,9..40,600;0,9..40,700;0,9..40,800;1,9..40,400&family=Space+Mono:wght@400;700&display=swap');

/* ---- Reset & Global ---- */
.stApp {
    font-family: 'DM Sans', sans-serif;
}
h1, h2, h3, h4,
.stMarkdown h1, .stMarkdown h2, .stMarkdown h3 {
    font-family: 'DM Sans', sans-serif !important;
    font-weight: 700 !important;
}
code, .stCode, pre {
    font-family: 'Space Mono', monospace !important;
}

/* ---- Hero with floating orbs ---- */
.hero {
    background: linear-gradient(135deg, #1a1a2e 0%, #16213e 25%, #0f3460 50%, #1a1a2e 100%);
    padding: 2.4rem 2rem 1.8rem;
    border-radius: 24px;
    margin-bottom: 1.2rem;
    position: relative;
    overflow: hidden;
    border: 1px solid rgba(255,255,255,0.06);
}
.hero::before {
    content: '';
    position: absolute;
    top: -50%;
    right: -20%;
    width: 60%;
    height: 200%;
    background: radial-gradient(ellipse, rgba(232, 121, 59, 0.15) 0%, transparent 70%);
    pointer-events: none;
    animation: orbFloat 8s ease-in-out infinite;
}
.hero::after {
    content: '';
    position: absolute;
    bottom: -30%;
    left: -10%;
    width: 50%;
    height: 160%;
    background: radial-gradient(ellipse, rgba(99, 102, 241, 0.1) 0%, transparent 70%);
    pointer-events: none;
    animation: orbFloat 10s ease-in-out infinite reverse;
}
@keyframes orbFloat {
    0%, 100% { transform: translate(0, 0) scale(1); }
    50% { transform: translate(20px, -15px) scale(1.05); }
}
.hero-content { position: relative; z-index: 1; }
.hero h1 {
    color: #ffffff !important;
    font-size: 2.4rem !important;
    font-weight: 800 !important;
    margin: 0 0 0.2rem 0 !important;
    letter-spacing: -0.04em;
    line-height: 1.1;
}
.hero h1 .accent { color: #e8793b; }
.hero p {
    color: rgba(255,255,255,0.5);
    font-size: 0.9rem;
    margin: 0;
    font-weight: 400;
    letter-spacing: 0.01em;
}
.hero .tag-row {
    display: flex;
    gap: 0.5rem;
    margin-top: 0.9rem;
    flex-wrap: wrap;
}
.hero .tag {
    background: rgba(255,255,255,0.06);
    border: 1px solid rgba(255,255,255,0.08);
    color: rgba(255,255,255,0.55);
    padding: 0.25rem 0.65rem;
    border-radius: 8px;
    font-size: 0.72rem;
    font-weight: 500;
    letter-spacing: 0.02em;
    text-transform: uppercase;
}

/* ---- Welcome banner ---- */
.welcome {
    background: linear-gradient(135deg, rgba(232,121,59,0.08), rgba(232,121,59,0.02));
    border: 1px solid rgba(232,121,59,0.15);
    border-radius: 16px;
    padding: 1rem 1.3rem;
    margin-bottom: 1.2rem;
    display: flex;
    align-items: center;
    gap: 1rem;
}
.welcome-emoji {
    font-size: 1.8rem;
    line-height: 1;
}
.welcome h3 {
    color: #e8793b !important;
    margin: 0 0 0.1rem 0 !important;
    font-size: 1.05rem !important;
    font-weight: 700 !important;
}
.welcome p {
    color: rgba(232,121,59,0.7);
    margin: 0;
    font-size: 0.82rem;
    font-weight: 400;
}

/* ---- Cards ---- */
.card {
    background: rgba(255,255,255,0.02);
    border: 1px solid rgba(255,255,255,0.07);
    border-radius: 18px;
    padding: 1.4rem;
    margin-bottom: 1rem;
    transition: border-color 0.2s;
}
.card:hover {
    border-color: rgba(232,121,59,0.2);
}
.card h3 {
    font-size: 1rem !important;
    font-weight: 700 !important;
    margin-bottom: 0.8rem !important;
    letter-spacing: -0.02em;
}
.card-icon {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 32px;
    height: 32px;
    border-radius: 10px;
    font-size: 1rem;
    margin-right: 0.5rem;
    vertical-align: middle;
}
.card-icon.upload { background: rgba(99,102,241,0.12); }
.card-icon.profile { background: rgba(232,121,59,0.12); }
.card-icon.match { background: rgba(16,185,129,0.12); }

/* ---- Skill chips ---- */
.chips { display: flex; flex-wrap: wrap; gap: 0.35rem; margin-top: 0.6rem; }
.chip {
    background: rgba(232,121,59,0.08);
    color: #e8a76a;
    padding: 0.25rem 0.65rem;
    border-radius: 8px;
    font-size: 0.75rem;
    font-weight: 500;
    border: 1px solid rgba(232,121,59,0.12);
    white-space: nowrap;
    transition: all 0.15s;
}
.chip:hover {
    background: rgba(232,121,59,0.16);
    transform: translateY(-1px);
}

/* ---- Progress stepper ---- */
.stepper {
    display: flex;
    justify-content: center;
    align-items: center;
    gap: 0;
    margin: 0.6rem 0 1.5rem;
}
.step {
    display: flex;
    align-items: center;
    gap: 0.4rem;
    padding: 0.35rem 0.75rem;
    font-size: 0.76rem;
    font-weight: 600;
    letter-spacing: 0.01em;
}
.step-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    flex-shrink: 0;
}
.step.done .step-dot { background: #10b981; box-shadow: 0 0 8px rgba(16,185,129,0.4); }
.step.done { color: #6ee7b7; }
.step.on .step-dot { background: #e8793b; box-shadow: 0 0 8px rgba(232,121,59,0.4); animation: pulse 2s ease infinite; }
.step.on { color: #e8a76a; }
.step.wait .step-dot { background: rgba(255,255,255,0.15); }
.step.wait { color: rgba(255,255,255,0.25); }
.step-line {
    width: 28px;
    height: 1px;
    background: rgba(255,255,255,0.1);
    flex-shrink: 0;
}
@keyframes pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.5; }
}

/* ---- Score badges ---- */
.score-hi {
    display: inline-block; background: linear-gradient(135deg,#059669,#10b981);
    color: #fff; padding: 0.3rem 0.75rem; border-radius: 10px;
    font-size: 0.88rem; font-weight: 700; letter-spacing: 0.02em;
    box-shadow: 0 2px 8px rgba(16,185,129,0.3);
}
.score-md {
    display: inline-block; background: linear-gradient(135deg,#d97706,#f59e0b);
    color: #fff; padding: 0.3rem 0.75rem; border-radius: 10px;
    font-size: 0.88rem; font-weight: 700;
    box-shadow: 0 2px 8px rgba(245,158,11,0.3);
}
.score-lo {
    display: inline-block; background: rgba(255,255,255,0.08);
    color: rgba(255,255,255,0.6); padding: 0.3rem 0.75rem; border-radius: 10px;
    font-size: 0.88rem; font-weight: 700;
    border: 1px solid rgba(255,255,255,0.1);
}

/* ---- Source badges ---- */
.src-badge {
    display: inline-block;
    padding: 0.18rem 0.5rem;
    border-radius: 6px;
    font-size: 0.68rem;
    font-weight: 600;
    letter-spacing: 0.03em;
    text-transform: uppercase;
}
.src-wwr  { background: rgba(129,140,248,0.12); color: #a5b4fc; border: 1px solid rgba(129,140,248,0.15); }
.src-rok  { background: rgba(251,113,133,0.12); color: #fda4af; border: 1px solid rgba(251,113,133,0.15); }
.src-rem  { background: rgba(56,189,248,0.12); color: #7dd3fc; border: 1px solid rgba(56,189,248,0.15); }
.src-other{ background: rgba(255,255,255,0.04); color: rgba(255,255,255,0.4); border: 1px solid rgba(255,255,255,0.06); }

/* ---- Cover letter box ---- */
.cl-wrap {
    background: rgba(255,255,255,0.02);
    border: 1px solid rgba(255,255,255,0.06);
    border-radius: 12px;
    padding: 1rem 1.3rem;
    margin-top: 0.6rem;
    line-height: 1.7;
    font-size: 0.86rem;
    color: rgba(255,255,255,0.72);
    white-space: pre-wrap;
}
.cl-label {
    font-size: 0.7rem;
    font-weight: 700;
    color: rgba(255,255,255,0.3);
    text-transform: uppercase;
    letter-spacing: 0.08em;
    margin-bottom: 0.4rem;
}

/* ---- Stats row ---- */
.stats-row {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 0.7rem;
    margin-bottom: 1.2rem;
}
.stat-card {
    background: rgba(255,255,255,0.02);
    border: 1px solid rgba(255,255,255,0.06);
    border-radius: 14px;
    padding: 1rem 0.8rem;
    text-align: center;
    transition: border-color 0.2s;
}
.stat-card:hover { border-color: rgba(232,121,59,0.2); }
.stat-card .num {
    font-size: 1.7rem;
    font-weight: 800;
    letter-spacing: -0.03em;
    background: linear-gradient(135deg, #e8793b, #f59e0b);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
}
.stat-card .lbl {
    font-size: 0.68rem;
    font-weight: 600;
    color: rgba(255,255,255,0.35);
    text-transform: uppercase;
    letter-spacing: 0.06em;
    margin-top: 0.15rem;
}

/* ---- Buttons ---- */
.stButton > button {
    border-radius: 12px !important;
    font-weight: 600 !important;
    font-family: 'DM Sans', sans-serif !important;
    padding: 0.55rem 1.3rem !important;
    transition: all 0.15s !important;
}
.stButton > button:hover {
    transform: translateY(-1px) !important;
}

/* ---- Expanders ---- */
div[data-testid="stExpander"] {
    border: 1px solid rgba(255,255,255,0.07) !important;
    border-radius: 14px !important;
    margin-bottom: 0.5rem !important;
    transition: border-color 0.2s !important;
}
div[data-testid="stExpander"]:hover {
    border-color: rgba(255,255,255,0.12) !important;
}
div[data-testid="stExpander"] summary {
    font-weight: 600 !important;
}

/* ---- Divider ---- */
.soft-divider {
    height: 1px;
    background: linear-gradient(90deg, transparent, rgba(255,255,255,0.06), transparent);
    margin: 1.2rem 0;
}

/* ---- Footer ---- */
.footer {
    text-align: center;
    padding: 1.5rem 0 0.5rem;
    font-size: 0.75rem;
    color: rgba(255,255,255,0.2);
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

# Clear stale module cache (Streamlit hot-reload can cause KeyError)
import importlib
import sys
for mod_name in ["resume_parser", "run_auto_apply", "cover_letter_generator", "job_fetcher"]:
    if mod_name in sys.modules:
        importlib.reload(sys.modules[mod_name])

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
    if not text:
        return ""
    clean = re.sub(r'<[^>]+>', ' ', text)
    clean = clean.replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>')
    clean = clean.replace('&quot;', '"').replace('&#39;', "'").replace('&nbsp;', ' ')
    clean = re.sub(r'\s+', ' ', clean).strip()
    return clean


def sanitize_filename(s, max_length=50):
    if not s:
        return "unnamed"
    s = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '', s)
    s = re.sub(r'\s+', '_', s)
    s = re.sub(r'_+', '_', s)
    s = s.strip('. ')
    return s[:max_length] if s else "unnamed"


def find_cover_letter(company, title):
    if not os.path.exists(LETTERS_DIR):
        return None, None
    expected = f"{sanitize_filename(company)}__{sanitize_filename(title)}.txt"
    path = os.path.join(LETTERS_DIR, expected)
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return f.read(), expected
        except Exception:
            pass
    sc = sanitize_filename(company).lower()
    st_part = sanitize_filename(title).lower()[:20]
    for fname in os.listdir(LETTERS_DIR):
        if fname.endswith(".txt") and sc in fname.lower() and st_part in fname.lower():
            try:
                with open(os.path.join(LETTERS_DIR, fname), "r", encoding="utf-8") as f:
                    return f.read(), fname
            except Exception:
                pass
    return None, None


def source_badge(source):
    s = source.lower()
    if "wework" in s or "wwr" in s:
        return '<span class="src-badge src-wwr">WWR</span>'
    elif "remoteok" in s or "remote ok" in s:
        return '<span class="src-badge src-rok">RemoteOK</span>'
    elif "remotive" in s:
        return '<span class="src-badge src-rem">Remotive</span>'
    else:
        return f'<span class="src-badge src-other">{source[:12]}</span>'


def build_zip(letters_dir):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as zf:
        for fname in sorted(os.listdir(letters_dir)):
            if fname.endswith(".txt"):
                fpath = os.path.join(letters_dir, fname)
                zf.write(fpath, fname)
    buf.seek(0)
    return buf


# ============================================
# LOAD PROFILE
# ============================================

_disk_profile = load_json(PROFILE_FILE)
if isinstance(_disk_profile, dict) and (_disk_profile.get("name") or _disk_profile.get("skills")):
    profile = _disk_profile
else:
    profile = {"name": "", "headline": "", "skills": []}

has_profile = bool(profile.get("skills"))
has_matches = isinstance(load_json(MATCHES_FILE), list) and len(load_json(MATCHES_FILE)) > 0

# ============================================
# PRE-SEED EDIT FIELDS FROM PROFILE
# ============================================

if has_profile:
    if "name_input" not in st.session_state:
        st.session_state["name_input"] = profile.get("name", "")
    if "headline_input" not in st.session_state:
        st.session_state["headline_input"] = profile.get("headline", "")
    if "skills_input" not in st.session_state:
        st.session_state["skills_input"] = "\n".join(profile.get("skills", []))

# ============================================
# HERO
# ============================================

st.markdown("""
<div class="hero">
    <div class="hero-content">
        <h1>⚡ Job<span class="accent">Bot</span></h1>
        <p>Smart matching · Instant cover letters · Zero busywork</p>
        <div class="tag-row">
            <span class="tag">Gemini 2.5 Flash</span>
            <span class="tag">3 Job Boards</span>
            <span class="tag">Keyword + AI Scoring</span>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# ============================================
# WELCOME
# ============================================

if has_profile and profile.get("name") and profile["name"] != "Candidate":
    skill_count = len(profile.get("skills", []))
    headline = profile.get("headline", "")
    sub = f"{headline} · " if headline else ""
    first_name = profile["name"].split()[0] if profile["name"] else "there"
    st.markdown(f"""
    <div class="welcome">
        <div class="welcome-emoji">👋</div>
        <div>
            <h3>Hey, {first_name}</h3>
            <p>{sub}{skill_count} skills loaded · Ready to match</p>
        </div>
    </div>
    """, unsafe_allow_html=True)

# ============================================
# STEP PILLS
# ============================================

p1 = "done" if has_profile else "on"
p2 = "done" if has_profile else "wait"
p3 = "done" if has_matches else ("on" if has_profile else "wait")
p4 = "done" if has_matches else "wait"

st.markdown(f"""
<div class="stepper">
    <div class="step {p1}"><div class="step-dot"></div>Upload</div>
    <div class="step-line"></div>
    <div class="step {p2}"><div class="step-dot"></div>Profile</div>
    <div class="step-line"></div>
    <div class="step {p3}"><div class="step-dot"></div>Match</div>
    <div class="step-line"></div>
    <div class="step {p4}"><div class="step-dot"></div>Letters</div>
</div>
""", unsafe_allow_html=True)

# ============================================
# SIDEBAR
# ============================================

with st.sidebar:
    st.markdown("### ⚙️ Session")
    st.caption(f"ID: `{SID}`")
    if st.button("🔄 Start Fresh"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()
    st.divider()
    st.markdown("### How it works")
    st.markdown(
        "1. **Upload** your resume PDF\n"
        "2. **Review** your extracted profile\n"
        "3. **Run matching** against live remote jobs\n"
        "4. **Read & download** tailored cover letters"
    )
    st.divider()
    st.markdown("### Engine")
    st.markdown(
        "**Phase 1** — Keyword matching (instant)  \n"
        "**Phase 2** — Gemini 2.5 Flash scoring  \n"
        "**Phase 3** — Seniority + diversity filters"
    )

# ============================================
# TWO-COLUMN LAYOUT: Upload + Profile
# ============================================

col_left, col_right = st.columns([1, 1], gap="large")

# ============================================
# LEFT: UPLOAD + PARSE
# ============================================

with col_left:
    st.markdown('<div class="card"><h3><span class="card-icon upload">📄</span> Resume</h3>', unsafe_allow_html=True)

    uploaded = st.file_uploader(
        "Drop your resume here",
        type=["pdf"],
        label_visibility="collapsed",
    )

    if uploaded:
        save_path = os.path.join(SESSION_DIR, uploaded.name)

        if st.session_state.get("_uploaded_name") != uploaded.name:
            with open(save_path, "wb") as f:
                f.write(uploaded.getvalue())
            st.session_state["_uploaded_name"] = uploaded.name
            st.session_state["_uploaded_path"] = save_path
            st.session_state.pop("_profile_built", None)

        save_path = st.session_state.get("_uploaded_path", save_path)
        st.success(f"📎 {uploaded.name}")

        if not st.session_state.get("_profile_built"):
            if st.button("🧠 Parse Resume", use_container_width=True):
                with st.spinner("Extracting with Gemini 2.5 Flash…"):
                    try:
                        build_profile(save_path, output_path=PROFILE_FILE)
                        if os.path.exists(PROFILE_FILE):
                            with open(PROFILE_FILE, "r") as f:
                                saved = json.load(f)
                            st.session_state["_profile_built"] = True
                            st.session_state["name_input"] = saved.get("name", "")
                            st.session_state["headline_input"] = saved.get("headline", "")
                            st.session_state["skills_input"] = "\n".join(saved.get("skills", []))
                            n = saved.get("name", "Candidate")
                            sc = len(saved.get("skills", []))
                            st.success(f"✅ {n} — {sc} skills")
                            time.sleep(0.5)
                            st.rerun()
                        else:
                            st.error("Profile not created. Check your PDF.")
                    except Exception as e:
                        st.error(f"❌ {e}")
                        st.info("Try entering your profile manually.")
        else:
            st.info("✅ Parsed. Upload a new file to re-parse.")
    else:
        st.caption("PDF format · Drag & drop or browse")

    st.markdown('</div>', unsafe_allow_html=True)

# ============================================
# RIGHT: PROFILE DISPLAY + EDIT
# ============================================

with col_right:
    st.markdown('<div class="card"><h3><span class="card-icon profile">👤</span> Profile</h3>', unsafe_allow_html=True)

    if has_profile:
        display_name = profile.get("name", "Candidate")
        display_headline = profile.get("headline", "")

        if display_name and display_name != "Candidate":
            st.markdown(f"**{display_name}**")
        if display_headline:
            st.caption(display_headline)

        skills = profile.get("skills", [])
        if skills:
            chips = "".join(f'<span class="chip">{s}</span>' for s in skills)
            st.markdown(f'<div class="chips">{chips}</div>', unsafe_allow_html=True)
            st.caption(f"{len(skills)} skills · from resume")
    else:
        st.caption("No profile yet — upload a resume or create one below.")

    st.markdown('</div>', unsafe_allow_html=True)

    # ---- Edit form ----
    with st.expander(
        "✏️ Edit profile" if has_profile else "✏️ Create profile manually",
        expanded=not has_profile,
    ):
        name_val = st.text_input("Full Name", key="name_input")
        headline_val = st.text_input("Professional Headline", key="headline_input")
        skills_val = st.text_area("Skills (one per line)", height=150, key="skills_input")

        if st.button("💾 Save Profile", use_container_width=True):
            skills_list = [s.strip() for s in skills_val.split("\n") if s.strip()]
            if not skills_list and not name_val:
                st.error("Enter at least a name or some skills.")
            else:
                updated = {
                    "name": name_val or "Candidate",
                    "headline": headline_val,
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
# JOB MATCHING
# ============================================

st.markdown('<div class="soft-divider"></div>', unsafe_allow_html=True)
st.markdown('<div class="card"><h3><span class="card-icon match">🚀</span> Job Matching</h3>', unsafe_allow_html=True)

profile_ready = bool(profile.get("skills"))

if not profile_ready:
    st.info("Add skills to your profile above to unlock matching.")
else:
    with st.expander("📁 Upload custom jobs.json (optional)"):
        jobs_upload = st.file_uploader("Upload jobs.json", type=["json"], key="jobs_upload", label_visibility="collapsed")
        if jobs_upload and st.session_state.get("_jobs_uploaded_name") != jobs_upload.name:
            try:
                jobs_data = json.loads(jobs_upload.getvalue())
                save_json(JOBS_FILE, jobs_data)
                st.session_state["_jobs_uploaded_name"] = jobs_upload.name
                st.success(f"✅ {len(jobs_data)} jobs loaded")
            except Exception as e:
                st.error(f"Invalid JSON: {e}")

    if st.session_state.get("_matching_done"):
        st.success("✅ Matching complete — scroll down for results.")
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
        st.warning("⏳ Pipeline running — please wait…")

    else:
        st.markdown(
            "Scans **WeWorkRemotely**, **RemoteOK** & **Remotive**, "
            "filters by keyword match, then scores top candidates with Gemini."
        )
        if st.button("▶ Start Matching", type="primary", use_container_width=True):
            st.session_state["_matching_running"] = True
            status = st.empty()
            log_box = st.empty()
            lines = []

            def _progress(msg):
                lines.append(msg)
                log_box.code("\n".join(lines[-15:]), language=None)

            status.info("🔍 Fetching jobs & matching…")
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
                    status.success(f"✅ {result['matches']} matches from {result['total_scored']} jobs")
                elif result and result.get("status") == "no_matches":
                    status.warning("No strong matches found. Try broadening your skills.")
                else:
                    status.error(f"Pipeline: {result}")
                time.sleep(1)
                st.rerun()
            except Exception as e:
                st.session_state.pop("_matching_running", None)
                status.error(f"❌ {e}")
                st.exception(e)

st.markdown('</div>', unsafe_allow_html=True)

# ============================================
# MATCH RESULTS
# ============================================

matches_data = load_json(MATCHES_FILE)

if isinstance(matches_data, list) and matches_data:
    st.markdown('<div class="soft-divider"></div>', unsafe_allow_html=True)

    # ---- Stats ----
    scores = [j.get("match_score", 0) for j in matches_data]
    avg_score = sum(scores) / len(scores) if scores else 0
    sources = {}
    for j in matches_data:
        src = j.get("source", "Other")
        sources[src] = sources.get(src, 0) + 1

    letter_files = []
    if os.path.exists(LETTERS_DIR):
        letter_files = [f for f in os.listdir(LETTERS_DIR) if f.endswith(".txt")]

    st.markdown(f"""
    <div class="stats-row">
        <div class="stat-card">
            <div class="num">{len(matches_data)}</div>
            <div class="lbl">Matches</div>
        </div>
        <div class="stat-card">
            <div class="num">{avg_score:.0f}%</div>
            <div class="lbl">Avg Score</div>
        </div>
        <div class="stat-card">
            <div class="num">{len(letter_files)}</div>
            <div class="lbl">Letters</div>
        </div>
        <div class="stat-card">
            <div class="num">{len(sources)}</div>
            <div class="lbl">Sources</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ---- Download ZIP ----
    if letter_files:
        col_title, col_zip = st.columns([3, 1])
        with col_title:
            st.markdown(f"### Your Top {len(matches_data)} Matches")
        with col_zip:
            zip_buf = build_zip(LETTERS_DIR)
            st.download_button(
                "📦 Download All Letters",
                data=zip_buf,
                file_name="cover_letters.zip",
                mime="application/zip",
                use_container_width=True,
            )
    else:
        st.markdown(f"### Your Top {len(matches_data)} Matches")

    # ---- Match cards ----
    for i, job in enumerate(matches_data, 1):
        score = job.get("match_score", 0)
        company = job.get("company", "Unknown")
        title = job.get("title", "Unknown")
        source = job.get("source", "")
        raw_summary = job.get("summary", "")
        clean_summary = strip_html(raw_summary)
        if len(clean_summary) > 400:
            clean_summary = clean_summary[:400] + "…"

        if score >= 80:
            badge = f'<span class="score-hi">{score}%</span>'
        elif score >= 65:
            badge = f'<span class="score-md">{score}%</span>'
        else:
            badge = f'<span class="score-lo">{score}%</span>'

        src_html = source_badge(source)

        with st.expander(f"#{i}  ·  {company} — {title}  ({score}%)"):
            c1, c2 = st.columns([4, 1])
            with c1:
                st.markdown(f"**{title}**")
                st.markdown(
                    f"🏢 {company}  ·  {src_html}",
                    unsafe_allow_html=True,
                )
                if clean_summary:
                    st.write(clean_summary)
            with c2:
                st.markdown(
                    f'<div style="text-align:center;margin-top:0.3rem;">{badge}</div>',
                    unsafe_allow_html=True,
                )
                if job.get("apply_url"):
                    st.link_button("🔗 Apply", job["apply_url"], use_container_width=True)

            # ---- Cover letter ----
            cl_content, cl_fname = find_cover_letter(company, title)
            if cl_content:
                st.markdown("---")
                st.markdown('<p class="cl-label">📝 Tailored Cover Letter</p>', unsafe_allow_html=True)
                st.markdown(f'<div class="cl-wrap">{cl_content}</div>', unsafe_allow_html=True)
                st.download_button(
                    "📥 Download Letter",
                    data=cl_content,
                    file_name=cl_fname or f"cover_letter_{i}.txt",
                    mime="text/plain",
                    key=f"dl_{i}",
                    use_container_width=True,
                )

# ============================================
# FOOTER
# ============================================

st.markdown("""
<div class="footer">
    Built with Streamlit & Gemini 2.5 Flash · Each session is fully isolated ·
    Click <b>Start Fresh</b> in the sidebar to begin again
</div>
""", unsafe_allow_html=True)
