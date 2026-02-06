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
    page_title="JobBot · AI Job Matcher",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ============================================
# CUSTOM CSS — modern glassmorphism design
# ============================================

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap');

/* ---- Reset & Global ---- */
.stApp {
    font-family: 'Outfit', sans-serif;
}
h1, h2, h3, h4,
.stMarkdown h1, .stMarkdown h2, .stMarkdown h3 {
    font-family: 'Outfit', sans-serif !important;
    font-weight: 700 !important;
}
code, .stCode, pre {
    font-family: 'JetBrains Mono', monospace !important;
}

/* ---- Animated hero ---- */
.hero {
    background: linear-gradient(-45deg, #0f172a, #1e3a5f, #0d9488, #0ea5e9);
    background-size: 400% 400%;
    animation: heroShift 12s ease infinite;
    padding: 2.8rem 2.2rem 2.2rem;
    border-radius: 20px;
    margin-bottom: 1.2rem;
    position: relative;
    overflow: hidden;
}
@keyframes heroShift {
    0%   { background-position: 0% 50%; }
    50%  { background-position: 100% 50%; }
    100% { background-position: 0% 50%; }
}
.hero::after {
    content: '';
    position: absolute;
    inset: 0;
    background: radial-gradient(ellipse at 70% 20%, rgba(255,255,255,0.07) 0%, transparent 60%);
    pointer-events: none;
}
.hero h1 {
    color: #ffffff !important;
    font-size: 2.2rem !important;
    font-weight: 800 !important;
    margin: 0 0 0.25rem 0 !important;
    letter-spacing: -0.03em;
}
.hero p {
    color: rgba(255,255,255,0.7);
    font-size: 0.95rem;
    margin: 0;
    font-weight: 400;
}

/* ---- Welcome card ---- */
.welcome {
    background: rgba(16, 185, 129, 0.08);
    backdrop-filter: blur(10px);
    border: 1px solid rgba(16, 185, 129, 0.2);
    border-radius: 14px;
    padding: 1.1rem 1.4rem;
    margin-bottom: 1.2rem;
}
.welcome h3 {
    color: #10b981 !important;
    margin: 0 0 0.15rem 0 !important;
    font-size: 1.15rem !important;
    font-weight: 600 !important;
}
.welcome p {
    color: #6ee7b7;
    margin: 0;
    font-size: 0.88rem;
    font-weight: 400;
}

/* ---- Glass cards ---- */
.glass {
    background: rgba(255,255,255,0.03);
    backdrop-filter: blur(12px);
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 16px;
    padding: 1.5rem;
    margin-bottom: 1rem;
}
.glass h3 {
    font-size: 1.05rem !important;
    font-weight: 600 !important;
    margin-bottom: 0.9rem !important;
    letter-spacing: -0.01em;
}

/* ---- Skill chips ---- */
.chips { display: flex; flex-wrap: wrap; gap: 0.35rem; margin-top: 0.6rem; }
.chip {
    background: rgba(14,165,233,0.12);
    color: #38bdf8;
    padding: 0.28rem 0.7rem;
    border-radius: 20px;
    font-size: 0.78rem;
    font-weight: 500;
    border: 1px solid rgba(14,165,233,0.2);
    white-space: nowrap;
    transition: all 0.15s;
}
.chip:hover {
    background: rgba(14,165,233,0.22);
    transform: translateY(-1px);
}

/* ---- Step pills ---- */
.steps { display: flex; justify-content: center; gap: 0.45rem; margin: 0.8rem 0 1.4rem; flex-wrap: wrap; }
.pill {
    padding: 0.35rem 0.85rem;
    border-radius: 20px;
    font-size: 0.78rem;
    font-weight: 600;
    letter-spacing: 0.02em;
}
.pill.done  { background: rgba(16,185,129,0.15); color: #34d399; border: 1px solid rgba(16,185,129,0.3); }
.pill.on    { background: rgba(14,165,233,0.15); color: #38bdf8; border: 1px solid rgba(14,165,233,0.3); }
.pill.wait  { background: rgba(255,255,255,0.03); color: rgba(255,255,255,0.3); border: 1px solid rgba(255,255,255,0.06); }

/* ---- Score badges ---- */
.score-hi {
    display: inline-block; background: linear-gradient(135deg,#059669,#10b981);
    color: #fff; padding: 0.3rem 0.8rem; border-radius: 10px;
    font-size: 0.9rem; font-weight: 700; letter-spacing: 0.02em;
}
.score-md {
    display: inline-block; background: linear-gradient(135deg,#d97706,#f59e0b);
    color: #fff; padding: 0.3rem 0.8rem; border-radius: 10px;
    font-size: 0.9rem; font-weight: 700;
}
.score-lo {
    display: inline-block; background: linear-gradient(135deg,#6b7280,#9ca3af);
    color: #fff; padding: 0.3rem 0.8rem; border-radius: 10px;
    font-size: 0.9rem; font-weight: 700;
}

/* ---- Source badges ---- */
.src-badge {
    display: inline-block;
    padding: 0.2rem 0.55rem;
    border-radius: 6px;
    font-size: 0.7rem;
    font-weight: 600;
    letter-spacing: 0.03em;
    text-transform: uppercase;
}
.src-wwr  { background: rgba(99,102,241,0.15); color: #818cf8; }
.src-rok  { background: rgba(244,63,94,0.15); color: #fb7185; }
.src-rem  { background: rgba(14,165,233,0.15); color: #38bdf8; }
.src-other{ background: rgba(255,255,255,0.06); color: rgba(255,255,255,0.5); }

/* ---- Cover letter box ---- */
.cl-wrap {
    background: rgba(255,255,255,0.03);
    border: 1px solid rgba(255,255,255,0.07);
    border-radius: 12px;
    padding: 1rem 1.3rem;
    margin-top: 0.8rem;
    line-height: 1.65;
    font-size: 0.88rem;
    color: rgba(255,255,255,0.78);
    white-space: pre-wrap;
}
.cl-label {
    font-size: 0.72rem;
    font-weight: 700;
    color: rgba(255,255,255,0.35);
    text-transform: uppercase;
    letter-spacing: 0.08em;
    margin-bottom: 0.5rem;
}

/* ---- Stats row ---- */
.stats-row { display: flex; gap: 0.8rem; margin-bottom: 1.2rem; flex-wrap: wrap; }
.stat-card {
    flex: 1;
    min-width: 120px;
    background: rgba(255,255,255,0.03);
    border: 1px solid rgba(255,255,255,0.06);
    border-radius: 12px;
    padding: 0.9rem 1rem;
    text-align: center;
}
.stat-card .num {
    font-size: 1.6rem;
    font-weight: 800;
    letter-spacing: -0.03em;
    color: #38bdf8;
}
.stat-card .lbl {
    font-size: 0.72rem;
    font-weight: 500;
    color: rgba(255,255,255,0.4);
    text-transform: uppercase;
    letter-spacing: 0.06em;
    margin-top: 0.15rem;
}

/* ---- Buttons ---- */
.stButton > button {
    border-radius: 12px !important;
    font-weight: 600 !important;
    font-family: 'Outfit', sans-serif !important;
    padding: 0.55rem 1.3rem !important;
}
div[data-testid="stExpander"] {
    border: 1px solid rgba(255,255,255,0.08) !important;
    border-radius: 14px !important;
    margin-bottom: 0.5rem !important;
}
div[data-testid="stExpander"] summary {
    font-weight: 600 !important;
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
    """Find cover letter matching a job, return (content, filename) or (None, None)."""
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
    # Fuzzy fallback
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
    """Create ZIP of all cover letters."""
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
# This is the critical fix — if the session_state keys don't
# exist yet, seed them from the profile on disk. This way
# the edit form is always pre-populated after a resume parse.

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
    <h1>🎯 JobBot</h1>
    <p>AI-powered job matching · Resume parsing · Auto cover letters</p>
</div>
""", unsafe_allow_html=True)

# ============================================
# WELCOME
# ============================================

if has_profile and profile.get("name") and profile["name"] != "Candidate":
    skill_count = len(profile.get("skills", []))
    headline = profile.get("headline", "")
    sub = f"{headline} · " if headline else ""
    st.markdown(f"""
    <div class="welcome">
        <h3>Welcome back, {profile["name"]} 👋</h3>
        <p>{sub}{skill_count} skills loaded</p>
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
<div class="steps">
    <span class="pill {p1}">{"✓" if has_profile else "1"} Upload</span>
    <span class="pill {p2}">{"✓" if has_profile else "2"} Profile</span>
    <span class="pill {p3}">{"✓" if has_matches else "3"} Match</span>
    <span class="pill {p4}">{"✓" if has_matches else "4"} Letters</span>
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

# ============================================
# TWO-COLUMN LAYOUT: Upload + Profile
# ============================================

col_left, col_right = st.columns([1, 1], gap="large")

# ============================================
# LEFT: UPLOAD + PARSE
# ============================================

with col_left:
    st.markdown('<div class="glass"><h3>📄 Resume Upload</h3>', unsafe_allow_html=True)

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
            if st.button("🧠 Parse Resume & Build Profile", use_container_width=True):
                with st.spinner("Extracting skills, name, and headline…"):
                    try:
                        build_profile(save_path, output_path=PROFILE_FILE)
                        if os.path.exists(PROFILE_FILE):
                            with open(PROFILE_FILE, "r") as f:
                                saved = json.load(f)
                            st.session_state["_profile_built"] = True
                            # Pre-populate edit fields
                            st.session_state["name_input"] = saved.get("name", "")
                            st.session_state["headline_input"] = saved.get("headline", "")
                            st.session_state["skills_input"] = "\n".join(saved.get("skills", []))
                            n = saved.get("name", "Candidate")
                            sc = len(saved.get("skills", []))
                            st.success(f"✅ {n} — {sc} skills extracted")
                            time.sleep(0.5)
                            st.rerun()
                        else:
                            st.error("❌ Profile not created. Check your PDF.")
                    except Exception as e:
                        st.error(f"❌ {e}")
                        st.info("Try entering your profile manually, or use a different resume.")
        else:
            st.info("✅ Parsed. Upload a new file to re-parse.")
    else:
        st.caption("PDF format · up to 200 MB")

    st.markdown('</div>', unsafe_allow_html=True)

# ============================================
# RIGHT: PROFILE DISPLAY + EDIT
# ============================================

with col_right:
    st.markdown('<div class="glass"><h3>👤 Your Profile</h3>', unsafe_allow_html=True)

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
        st.caption("No profile yet — upload a resume or create one manually below.")

    st.markdown('</div>', unsafe_allow_html=True)

    # ---- Edit form — ALWAYS pre-populated ----
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

st.markdown("---")
st.markdown('<div class="glass"><h3>🚀 Job Matching</h3>', unsafe_allow_html=True)

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
        st.success("✅ Matching complete — results below.")
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
            "Scans **WeWorkRemotely**, **RemoteOK** & **Remotive** "
            "and scores each role against your profile."
        )
        if st.button("▶ Start Matching", type="primary", use_container_width=True):
            st.session_state["_matching_running"] = True
            status = st.empty()
            log_box = st.empty()
            lines = []

            def _progress(msg):
                lines.append(msg)
                log_box.code("\n".join(lines[-20:]), language=None)

            status.info("🔍 Fetching & scoring… this takes 2–5 min.")
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
                    status.warning("No strong matches. Try adding more skills.")
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
# MATCH RESULTS — with stats + embedded cover letters
# ============================================

matches_data = load_json(MATCHES_FILE)

if isinstance(matches_data, list) and matches_data:
    st.markdown("---")

    # ---- Stats summary ----
    scores = [j.get("match_score", 0) for j in matches_data]
    avg_score = sum(scores) / len(scores) if scores else 0
    sources = {}
    for j in matches_data:
        src = j.get("source", "Other")
        sources[src] = sources.get(src, 0) + 1

    letter_files = []
    if os.path.exists(LETTERS_DIR):
        letter_files = [f for f in os.listdir(LETTERS_DIR) if f.endswith(".txt")]

    stats_html = f"""
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
            <div class="lbl">Cover Letters</div>
        </div>
        <div class="stat-card">
            <div class="num">{len(sources)}</div>
            <div class="lbl">Sources</div>
        </div>
    </div>
    """
    st.markdown(stats_html, unsafe_allow_html=True)

    # ---- Download all as ZIP ----
    if letter_files:
        col_title, col_zip = st.columns([3, 1])
        with col_title:
            st.markdown(f"### 📊 Top {len(matches_data)} Matches")
        with col_zip:
            zip_buf = build_zip(LETTERS_DIR)
            st.download_button(
                "📦 Download All Letters (ZIP)",
                data=zip_buf,
                file_name="cover_letters.zip",
                mime="application/zip",
                use_container_width=True,
            )
    else:
        st.markdown(f"### 📊 Top {len(matches_data)} Matches")

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

        # Score badge class
        if score >= 85:
            badge = f'<span class="score-hi">{score}%</span>'
        elif score >= 70:
            badge = f'<span class="score-md">{score}%</span>'
        else:
            badge = f'<span class="score-lo">{score}%</span>'

        src_html = source_badge(source)

        with st.expander(f"#{i}  ·  {company} — {title}  ({score}%)"):
            # ---- Header row ----
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

            # ---- Embedded cover letter ----
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

st.markdown("---")
st.caption(
    "Built with Streamlit & OpenRouter · Each session is fully isolated · "
    "Click **Start Fresh** in the sidebar to begin again."
)
