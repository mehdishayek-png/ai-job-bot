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
    page_title="AI Job Search",
    page_icon="🔎",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ============================================
# CUSTOM CSS — SVG-MATCHED
# ============================================

st.markdown(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap');

:root{
  --bg: #0e1525;
  --panel: #121a2b;
  --panel-2: #0f1727;
  --stroke: rgba(255,255,255,0.14);
  --stroke-2: rgba(255,255,255,0.10);
  --muted: rgba(255,255,255,0.55);
  --muted-2: rgba(255,255,255,0.42);
  --btn-a: #1a86e8;
  --btn-b: #6f57ea;
  --slot: rgba(255,255,255,0.03);
  --slot-2: rgba(255,255,255,0.05);
}

* { box-sizing: border-box; }

.stApp {
  font-family: 'Poppins', -apple-system, BlinkMacSystemFont, sans-serif;
  background: var(--bg);
}

/* Hide Streamlit chrome */
#MainMenu, footer { visibility: hidden; }
header[data-testid="stHeader"] { background: transparent; }
section[data-testid="stSidebar"]{ display:none; }

/* Page padding / proportions */
div.block-container { padding-top: 0.6rem; padding-left: 1.1rem; padding-right: 1.1rem; max-width: 1400px; }

h1, h2, h3, h4, h5, h6,
.stMarkdown h1, .stMarkdown h2, .stMarkdown h3 {
  font-family: 'Poppins', sans-serif !important;
  font-weight: 800 !important;
  letter-spacing: -0.02em;
  color: #fff !important;
}

.stCaption, .stMarkdown p { color: var(--muted) !important; }

/* Header */
.app-header{ display:flex; align-items:center; justify-content:space-between; margin: 0.35rem 0 1.0rem; }
.header-left{ display:flex; align-items:center; gap:0.75rem; }
.app-title{ font-size: 1.35rem; font-weight: 800; color:#fff; }
.profile-circle{ width:44px; height:44px; border-radius:999px; background: rgba(255,255,255,0.06); border:1px solid var(--stroke); display:flex; align-items:center; justify-content:center; }

/* Panels */
.panel{ background: rgba(255,255,255,0.03); border:1px solid var(--stroke); border-radius: 16px; overflow:hidden; }
.panel-inner{ padding: 1.15rem; }

/* Tab bars */
.tabs{ display:flex; width:100%; border-bottom:1px solid var(--stroke); }
.tab{ flex:1; text-align:center; padding: 0.95rem 0; font-weight: 800; color:#fff; background: rgba(255,255,255,0.06); }
.tab.active{ background: linear-gradient(90deg, var(--btn-a), var(--btn-b)); }

/* Section divider */
.section-tabs{ display:flex; width:100%; border-top:1px solid var(--stroke); border-bottom:1px solid var(--stroke); margin-top: 1.1rem; }

/* Inputs */
label { color:#fff !important; font-weight: 800 !important; }
.stTextInput > div > div > input,
.stTextArea > div > div > textarea,
.stSelectbox > div > div,
.stNumberInput > div > div > input {
  background: rgba(255,255,255,0.04) !important;
  border: 1px solid var(--stroke) !important;
  border-radius: 12px !important;
  color: #fff !important;
}

/* Make selectboxes look like SVG dropdown */
.stSelectbox svg { color: rgba(255,255,255,0.65) !important; }

/* Remove extra spacing of empty labels */
div[data-testid="stMarkdownContainer"] + div:has(> div[data-testid="stTextInput"]) { margin-top: -0.35rem; }

/* Upload tile */
.upload-tile{ background: rgba(255,255,255,0.06); border:1px solid var(--stroke); border-radius: 16px; padding: 1.35rem 1rem; text-align:center; margin-top: 1.1rem; }
.upload-icon{ width: 66px; height: 66px; border-radius: 14px; border: 2px solid rgba(255,255,255,0.25); margin: 0 auto 0.8rem; display:flex; align-items:center; justify-content:center; }
.upload-tile-title{ font-weight: 800; font-size: 1.0rem; }

/* Buttons */
.stButton > button{
  background: linear-gradient(90deg, var(--btn-a), var(--btn-b)) !important;
  color:#fff !important;
  border: none !important;
  border-radius: 12px !important;
  padding: 0.85rem 1.15rem !important;
  font-weight: 800 !important;
  box-shadow: 0 10px 26px rgba(0,0,0,0.28) !important;
}
.stButton > button:hover{ filter: brightness(1.05); transform: translateY(-1px); }

/* File uploader (hidden label) */
div[data-testid="stFileUploader"] section{
  background: rgba(255,255,255,0.04) !important;
  border: 1px solid var(--stroke) !important;
  border-radius: 12px !important;
}

/* Right side progress bar */
.progress-wrap{ margin-top: 0.25rem; margin-bottom: 1.2rem; }
.progress-label{ color: var(--muted-2); font-weight: 800; margin-bottom: 0.35rem; }
.progress-track{ height: 12px; border-radius: 999px; overflow:hidden; background: rgba(255,255,255,0.12); border:1px solid var(--stroke-2); }
.progress-fill{ height:100%; background: linear-gradient(90deg, var(--btn-a), var(--btn-b)); }

/* Job slots/cards */
.slot{ border: 1px solid var(--stroke); border-radius: 16px; background: var(--slot); height: 88px; margin-bottom: 1.2rem; }
.job-card{ border: 1px solid var(--stroke); border-radius: 16px; background: var(--slot); padding: 1.0rem 1.1rem; margin-bottom: 1.2rem; }
.job-card:hover{ background: var(--slot-2); }
.job-title{ font-weight: 800; font-size: 1.0rem; margin-bottom: 0.25rem; }
.job-meta{ color: var(--muted); font-weight: 600; font-size: 0.9rem; }
.score-pill{ display:inline-block; padding: 0.25rem 0.6rem; border-radius: 10px; border: 1px solid var(--stroke); background: rgba(255,255,255,0.06); font-weight: 800; }

/* Scrollbar */
::-webkit-scrollbar { width: 10px; }
::-webkit-scrollbar-track { background: var(--bg); }
::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.16); border-radius: 999px; border: 1px solid rgba(255,255,255,0.12); }
::-webkit-scrollbar-thumb:hover { background: rgba(255,255,255,0.22); }

</style>
""",
    unsafe_allow_html=True,
)

# ============================================
# IMPORTS & SETUP
# ============================================

load_dotenv()

# Hot reload friendliness
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
    from resume_parser import build_profile
    from run_auto_apply import run_auto_apply_pipeline
except (ImportError, KeyError) as e:
    st.error(f"Missing required module: {e}. Please ensure all files are in the same directory.")
    st.stop()

# ============================================
# SESSION / STORAGE
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

# ============================================
# HELPERS
# ============================================

def load_json(filepath):
    if not os.path.exists(filepath):
        return None
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def save_json(filepath, data):
    os.makedirs(os.path.dirname(filepath) or ".", exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def normalize_lines(text: str):
    lines = [ln.strip() for ln in (text or "").splitlines()]
    return [ln for ln in lines if ln]


COUNTRY_REGIONS = {
    "India": [
        "Any",
        "Karnataka (Bangalore)",
        "Maharashtra (Mumbai)",
        "Delhi (New Delhi)",
        "Telangana (Hyderabad)",
        "Tamil Nadu (Chennai)",
        "West Bengal (Kolkata)",
        "Gujarat (Ahmedabad)",
        "Kerala (Kochi)",
        "Rajasthan (Jaipur)",
        "Punjab (Chandigarh)",
    ],
    "United Kingdom": [
        "Any",
        "England (London)",
        "England (Birmingham)",
        "England (Manchester)",
        "England (Leeds)",
        "Scotland (Edinburgh)",
        "Scotland (Glasgow)",
        "Wales (Cardiff)",
        "Northern Ireland (Belfast)",
    ],
    "United Arab Emirates": [
        "Any",
        "Dubai (Dubai)",
        "Abu Dhabi (Abu Dhabi)",
        "Sharjah (Sharjah)",
    ],
    "Saudi Arabia": [
        "Any",
        "Riyadh (Riyadh)",
        "Makkah (Jeddah)",
        "Eastern Province (Dammam)",
        "NEOM (Tabuk)",
    ],
    "Qatar": ["Any", "Doha (Doha)"],
    "Singapore": ["Any", "Singapore (Singapore)"],
    "Switzerland": [
        "Any",
        "Zurich (Zurich)",
        "Geneva (Geneva)",
        "Basel (Basel)",
        "Bern (Bern)",
        "Lausanne (Lausanne)",
    ],
    "United States": [
        "Any",
        "California (San Francisco)",
        "California (Los Angeles)",
        "New York (New York City)",
        "Texas (Austin)",
        "Washington (Seattle)",
    ],
    "Remote Only": ["Any"],
}


def get_country_options():
    return [
        "India",
        "United Kingdom",
        "United Arab Emirates",
        "Saudi Arabia",
        "Qatar",
        "Singapore",
        "Switzerland",
        "United States",
        "Remote Only",
    ]


# ============================================
# HEADER
# ============================================

st.markdown(
    """
<div class="app-header">
  <div class="header-left">
    <svg width="34" height="34" viewBox="0 0 48 48" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path d="M9 30c3-6 10-10 19-10" stroke="url(#g)" stroke-width="4" stroke-linecap="round"/>
      <path d="M12 38c1-10 9-18 20-20" stroke="url(#g)" stroke-width="4" stroke-linecap="round" opacity="0.85"/>
      <path d="M29 8h11v11" stroke="url(#g)" stroke-width="4" stroke-linecap="round" stroke-linejoin="round"/>
      <path d="M40 8L24 24" stroke="url(#g)" stroke-width="4" stroke-linecap="round"/>
      <defs>
        <linearGradient id="g" x1="6" y1="42" x2="44" y2="6" gradientUnits="userSpaceOnUse">
          <stop stop-color="#1a86e8"/>
          <stop offset="1" stop-color="#6f57ea"/>
        </linearGradient>
      </defs>
    </svg>
    <div class="app-title">AI Job Search</div>
  </div>
  <div class="profile-circle" title="Profile">
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none">
      <path d="M12 12a4.5 4.5 0 1 0-4.5-4.5A4.5 4.5 0 0 0 12 12Z" stroke="white" stroke-width="2"/>
      <path d="M4 20c1.8-3.6 5-5.5 8-5.5S18.2 16.4 20 20" stroke="white" stroke-width="2" stroke-linecap="round"/>
    </svg>
  </div>
</div>
""",
    unsafe_allow_html=True,
)

# ============================================
# LOAD STATE
# ============================================

profile = load_json(PROFILE_FILE) or {}
matches_data = load_json(MATCHES_FILE)

# ============================================
# MAINFRAME — LEFT/RIGHT PANELS
# ============================================

left_col, right_col = st.columns([0.34, 0.66], gap="large")

# ----------------------------
# LEFT PANEL
# ----------------------------
with left_col:
    st.markdown('<div class="panel">', unsafe_allow_html=True)

    # Tabs (Tailor CV is placeholder as requested)
    st.markdown(
        """
<div class="tabs">
  <div class="tab active">My Profile</div>
  <div class="tab">Tailor CV</div>
</div>
""",
        unsafe_allow_html=True,
    )

    st.markdown('<div class="panel-inner">', unsafe_allow_html=True)

    st.markdown("### My Profile")

    headline_in = st.text_input(
        "My Profile",
        value=profile.get("headline") or profile.get("name") or "",
        placeholder="My Profile",
    )

    exp_in = st.text_input(
        "Years Of Experience",
        value=str(profile.get("experience") or ""),
        placeholder="Years Of Experience",
    )

    skills_in = st.text_area(
        "Skills",
        value="\n".join(profile.get("skills") or profile.get("search_terms") or [])
        if isinstance(profile.get("skills") or profile.get("search_terms") or [], list)
        else str(profile.get("skills") or profile.get("search_terms") or ""),
        placeholder="Skills/Roles",
        height=120,
    )

    # Section tabs
    st.markdown(
        """
<div class="section-tabs">
  <div class="tab active">Job Preferences</div>
  <div class="tab">Job Preferences</div>
</div>
""",
        unsafe_allow_html=True,
    )

    st.markdown("#### Select Location")

    country_options = get_country_options()
    current_country = profile.get("country") or "India"
    if current_country not in country_options:
        country_options = [current_country] + country_options

    country_in = st.selectbox(
        "Country",
        country_options,
        index=country_options.index(current_country),
        label_visibility="collapsed",
        key="country_select",
    )

    region_options = COUNTRY_REGIONS.get(country_in, ["Any"])
    current_region = profile.get("state") or "Any"
    if current_region not in region_options:
        region_options = [current_region] + region_options

    region_in = st.selectbox(
        "City/Region",
        region_options,
        index=region_options.index(current_region),
        label_visibility="collapsed",
        key="region_select",
    )

    # Upload tile
    st.markdown(
        """
<div class="upload-tile">
  <div class="upload-icon">
    <svg width="34" height="34" viewBox="0 0 24 24" fill="none">
      <path d="M14 2H7a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8l-5-6Z" stroke="rgba(255,255,255,0.55)" stroke-width="2"/>
      <path d="M14 2v6h6" stroke="rgba(255,255,255,0.55)" stroke-width="2"/>
      <path d="M8 13h8M8 17h8" stroke="rgba(255,255,255,0.45)" stroke-width="2" stroke-linecap="round"/>
    </svg>
  </div>
  <div class="upload-tile-title">Upload Resume</div>
</div>
""",
        unsafe_allow_html=True,
    )

    uploaded_resume = st.file_uploader(
        " ",
        type=["pdf"],
        label_visibility="collapsed",
        key="resume_upload_svg",
    )

    parse_clicked = st.button("Parse File", type="primary", use_container_width=True)

    # Auto-save profile edits (no explicit Save button in SVG)
    def persist_profile():
        existing = load_json(PROFILE_FILE) or {}
        updated = dict(existing)
        updated["headline"] = (headline_in or "").strip()
        updated["experience"] = (exp_in or "").strip()
        updated["country"] = country_in
        updated["state"] = region_in

        # Skills list
        lines = normalize_lines(skills_in)
        if lines:
            updated["skills"] = lines
            # keep search_terms in sync for older pipeline parts
            if not updated.get("search_terms"):
                updated["search_terms"] = lines

        save_json(PROFILE_FILE, updated)

    persist_profile()

    if parse_clicked:
        if not uploaded_resume:
            st.warning("Please upload a PDF first.")
        else:
            with st.spinner("Analyzing your resume..."):
                try:
                    resume_path = os.path.join(DATA_DIR, "resume.pdf")
                    with open(resume_path, "wb") as f:
                        f.write(uploaded_resume.getbuffer())

                    existing = load_json(PROFILE_FILE) or {}
                    parsed = build_profile(resume_path, PROFILE_FILE) or {}

                    # Preserve UI selections
                    parsed["country"] = country_in
                    parsed["state"] = region_in
                    parsed["experience"] = (exp_in or parsed.get("experience") or "").strip()

                    # If skills were typed manually, keep them
                    typed_skills = normalize_lines(skills_in)
                    if typed_skills:
                        parsed["skills"] = typed_skills
                        parsed.setdefault("search_terms", typed_skills)

                    save_json(PROFILE_FILE, parsed)
                    st.success("✅ Resume parsed successfully!")
                    time.sleep(0.35)
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Error parsing resume: {e}")

    st.markdown("</div>", unsafe_allow_html=True)  # panel-inner
    st.markdown("</div>", unsafe_allow_html=True)  # panel

# ----------------------------
# RIGHT PANEL
# ----------------------------
with right_col:
    st.markdown('<div class="panel">', unsafe_allow_html=True)
    st.markdown('<div class="panel-inner">', unsafe_allow_html=True)

    # Title + Search button
    title_col, btn_col = st.columns([0.72, 0.28])
    with title_col:
        st.markdown("## Compiled Jobs According To Profile")
    with btn_col:
        start_search = st.button("Search", type="primary", use_container_width=True)

    # Refresh profile/matches
    profile = load_json(PROFILE_FILE) or {}
    matches_data = load_json(MATCHES_FILE)

    profile_ready = bool(profile and (profile.get("skills") or profile.get("search_terms")))

    compiled_count = len(matches_data) if isinstance(matches_data, list) else 0
    total_scored = st.session_state.get("last_total_scored") or st.session_state.get("last_total_jobs") or max(compiled_count, 1)

    pct = 0.0
    if total_scored:
        pct = min(1.0, compiled_count / float(total_scored))

    st.markdown(
        f"""
<div class="progress-wrap">
  <div class="progress-label">Compiled {compiled_count}/{total_scored}</div>
  <div class="progress-track"><div class="progress-fill" style="width:{pct*100:.1f}%"></div></div>
</div>
""",
        unsafe_allow_html=True,
    )

    # Start pipeline
    if start_search:
        if not profile_ready:
            st.warning("Please add Skills/Roles (and optionally parse a resume) before searching.")
        else:
            st.session_state["_matching_running"] = True

    if st.session_state.get("_matching_running"):
        status_text = st.empty()
        detail_box = st.empty()

        status_text.info("🔍 Searching across sources and ranking matches…")
        progress_bar = st.progress(0, text="Starting…")

        stage_pct = {
            "Starting pipeline": 0,
            "Fetching jobs": 8,
            "WeWorkRemotely": 15,
            "RemoteOK": 20,
            "Remotive": 25,
            "Lever": 35,
            "Google Jobs": 45,
            "SerpAPI": 45,
            "Loaded": 55,
            "Location filter": 62,
            "Matching against": 70,
            "Phase 1": 78,
            "Batch 1": 82,
            "Batch 2": 86,
            "Batch 3": 90,
            "Batch 4": 94,
            "Threshold": 97,
            "Done": 100,
        }

        log_lines = []

        def progress_callback(msg: str):
            log_lines.append(msg)
            detail_box.code("\n".join(log_lines[-6:]), language=None)

            pct_local = 0
            for keyword, p in stage_pct.items():
                if keyword.lower() in msg.lower():
                    pct_local = p
            current = getattr(progress_callback, "_max_pct", 0)
            pct_local = max(pct_local, current)
            progress_callback._max_pct = pct_local
            progress_bar.progress(min(pct_local, 100) / 100.0, text=msg[:80])

        progress_callback._max_pct = 0

        try:
            result = run_auto_apply_pipeline(
                profile_file=PROFILE_FILE,
                jobs_file=JOBS_FILE,
                matches_file=MATCHES_FILE,
                cache_file=CACHE_FILE,
                log_file=LOG_FILE,
                letters_dir=None,
                progress_callback=progress_callback,
            )

            st.session_state.pop("_matching_running", None)
            st.session_state["_matching_done"] = True

            if isinstance(result, dict):
                if "total_scored" in result:
                    st.session_state["last_total_scored"] = result["total_scored"]
                elif "total" in result:
                    st.session_state["last_total_scored"] = result["total"]

            if result and isinstance(result, dict) and result.get("status") == "success":
                status_text.success(f"✅ Found {result.get('matches', 0)} matches!")
            elif result and isinstance(result, dict) and result.get("status") == "no_matches":
                status_text.warning("⚠️ No strong matches found. Try expanding Skills/Roles or location.")
            else:
                status_text.warning("Finished, but no structured result returned.")

            time.sleep(0.35)
            st.rerun()

        except Exception as e:
            st.session_state.pop("_matching_running", None)
            status_text.error(f"❌ Error: {e}")
            st.exception(e)

    # Render results in SVG-style boxes
    matches_data = load_json(MATCHES_FILE)

    if isinstance(matches_data, list) and matches_data:
        for j in matches_data[:30]:
            title = j.get("title") or j.get("job_title") or "Job"
            company = j.get("company") or j.get("employer") or ""
            loc = j.get("location") or ""
            score = j.get("match_score", j.get("score", ""))
            url = j.get("url") or j.get("apply_url") or ""

            left_meta, right_meta = st.columns([0.78, 0.22])
            with left_meta:
                st.markdown(f"<div class='job-card'><div class='job-title'>{title}</div>", unsafe_allow_html=True)
                meta_line = " · ".join([x for x in [company, loc] if x])
                if meta_line:
                    st.markdown(f"<div class='job-meta'>{meta_line}</div></div>", unsafe_allow_html=True)
                else:
                    st.markdown("</div>", unsafe_allow_html=True)
            with right_meta:
                if score != "":
                    st.markdown(f"<div class='score-pill'>{score}%</div>", unsafe_allow_html=True)
                if url:
                    st.link_button("Apply", url, use_container_width=True)

        with st.expander("Actions"):
            if st.button("Clear Results", use_container_width=True):
                for fp in [JOBS_FILE, MATCHES_FILE, CACHE_FILE]:
                    if os.path.exists(fp):
                        os.remove(fp)
                st.session_state.pop("_matching_done", None)
                st.session_state.pop("last_total_scored", None)
                st.rerun()
    else:
        # Empty slots like the SVG mock
        for _ in range(6):
            st.markdown('<div class="slot"></div>', unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)  # panel-inner
    st.markdown("</div>", unsafe_allow_html=True)  # panel
