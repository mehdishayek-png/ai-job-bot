import streamlit as st
import json, os, re, uuid, time, io, zipfile
from dotenv import load_dotenv
from datetime import datetime, timedelta

st.set_page_config(page_title="JobBot - AI Job Matching", page_icon="🚀", layout="wide", initial_sidebar_state="collapsed")

# ==============================================
# CSS — Addresses ALL visibility / contrast bugs
# ==============================================
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');

:root {
    --primary: #7c3aed; --primary-hover: #6d28d9;
    --accent-coral: #f43f5e; --accent-emerald: #10b981; --accent-amber: #f59e0b;
    --bg: #fafaf9; --card: #ffffff; --elevated: #f5f5f4;
    --text: #1c1917; --text2: #57534e; --muted: #a8a29e;
    --border: #e7e5e4; --r: 12px;
}
.stApp { font-family:'Plus Jakarta Sans',sans-serif!important; background:var(--bg)!important; }
h1,h2,h3,h4,h5,h6 { font-family:'Plus Jakarta Sans',sans-serif!important; font-weight:800!important; color:var(--text)!important; }
p,li,span,div { font-family:'Plus Jakarta Sans',sans-serif!important; }

/* ===== HERO ===== */
.hero{background:linear-gradient(135deg,#7c3aed 0%,#a78bfa 35%,#f43f5e 100%);border-radius:20px;padding:2.8rem 2.2rem;margin-bottom:1.5rem;position:relative;overflow:hidden;box-shadow:0 8px 32px rgba(124,58,237,0.25)}
.hero h1{color:#fff!important;font-size:2.6rem!important;margin:0 0 .5rem 0!important}
.hero-sub{color:rgba(255,255,255,.9);font-size:1.05rem;margin:0 0 1.4rem;font-weight:500;line-height:1.6;max-width:600px}
.hero-tags{display:flex;gap:.6rem;flex-wrap:wrap;margin-top:1rem}
.hero-tag{background:rgba(255,255,255,.18);border:1px solid rgba(255,255,255,.25);color:#fff;padding:.45rem .9rem;border-radius:8px;font-size:.78rem;font-weight:600}

/* ===== STEPPER ===== */
.stepper{display:flex;justify-content:center;align-items:center;gap:.75rem;margin:1.5rem 0 2rem;padding:1rem;background:var(--card);border:1px solid var(--border);border-radius:16px}
.step{display:flex;align-items:center;gap:.5rem;padding:.5rem .8rem;border-radius:var(--r);font-size:.85rem;font-weight:600;color:var(--muted)}
.step-num{width:32px;height:32px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:.85rem;font-weight:700}
.step.done{color:var(--accent-emerald)} .step.done .step-num{background:var(--accent-emerald);color:#fff}
.step.active{color:var(--primary);background:var(--primary);background:rgba(124,58,237,.08)} .step.active .step-num{background:var(--primary);color:#fff}
.step.pending .step-num{background:var(--elevated);border:2px dashed var(--border);color:var(--muted)}
.step-conn{width:40px;height:2px;background:var(--border)}

/* ===== STATS ===== */
.stats-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:.75rem;margin:1.5rem 0}
.stat-card{background:var(--card);border:1px solid var(--border);border-radius:16px;padding:1.2rem 1rem;text-align:center}
.stat-val{font-size:2rem;font-weight:800;line-height:1;margin-bottom:.3rem}
.stat-val.purple{color:var(--primary)} .stat-val.coral{color:var(--accent-coral)}
.stat-val.emerald{color:var(--accent-emerald)} .stat-val.amber{color:var(--accent-amber)}
.stat-lbl{color:var(--muted);font-size:.72rem;font-weight:700;text-transform:uppercase;letter-spacing:.06em}

/* ===== BADGES ===== */
.score-badge{display:inline-block;padding:.4rem 1rem;border-radius:100px;font-size:.95rem;font-weight:700}
.score-excellent{background:#d1fae5;color:#059669;border:1px solid #a7f3d0}
.score-good{background:#fef3c7;color:#d97706;border:1px solid #fde68a}
.score-fair{background:#ede9fe;color:#7c3aed;border:1px solid #ddd6fe}
.src-badge{display:inline-block;padding:.15rem .5rem;border-radius:100px;font-size:.65rem;font-weight:700;text-transform:uppercase;background:var(--elevated);color:var(--text2);border:1px solid var(--border)}
.ts-badge{display:inline-flex;align-items:center;gap:.25rem;padding:.15rem .5rem;border-radius:100px;font-size:.65rem;font-weight:700}
.ts-fresh{background:#d1fae5;color:#059669;border:1px solid #a7f3d0}
.ts-recent{background:#fed7aa;color:#ea580c;border:1px solid #fdba74}
.ts-old{background:var(--elevated);color:var(--muted);border:1px solid var(--border)}
.pin-badge{display:inline-flex;padding:.15rem .5rem;border-radius:100px;font-size:.65rem;font-weight:700;background:#fecaca;color:#ef4444;border:1px solid #fca5a5}

/* ===== SKILL CHIPS ===== */
.skills-wrap{display:flex;flex-wrap:wrap;gap:.4rem;margin-top:.75rem}
.sc{padding:.3rem .7rem;border-radius:100px;font-size:.78rem;font-weight:600}
.sc:nth-child(5n+1){background:#f5f3ff;color:#7c3aed;border:1px solid #ddd6fe}
.sc:nth-child(5n+2){background:#fef2f2;color:#ef4444;border:1px solid #fecaca}
.sc:nth-child(5n+3){background:#ecfdf5;color:#059669;border:1px solid #a7f3d0}
.sc:nth-child(5n+4){background:#fff7ed;color:#ea580c;border:1px solid #fed7aa}
.sc:nth-child(5n+5){background:#f0f9ff;color:#0284c7;border:1px solid #bae6fd}

/* ========================================================
   FIX 1: BUTTONS — white text on purple, high contrast
   ======================================================== */
.stButton > button {
    background: var(--primary) !important; color: #ffffff !important;
    border: none !important; border-radius: var(--r) !important;
    padding: .65rem 1.25rem !important; font-weight: 700 !important;
    font-size: .9rem !important; box-shadow: 0 2px 8px rgba(124,58,237,.2) !important;
}
.stButton > button:hover { background: var(--primary-hover) !important; }
.stButton > button span, .stButton > button p { color: #ffffff !important; }

/* ========================================================
   FIX 2: EXPANDER — force light bg, dark text on header
   The dark header + grey text issue; also fix arrow_right
   ======================================================== */
div[data-testid="stExpander"] {
    border: 1px solid var(--border) !important;
    border-radius: var(--r) !important;
    background: var(--card) !important;
    margin-bottom: .5rem !important;
    overflow: hidden !important;
}
/* Force the expander HEADER (summary) to be LIGHT bg with DARK text */
div[data-testid="stExpander"] > details > summary {
    background: var(--card) !important;
    color: var(--text) !important;
    padding: .75rem 1rem !important;
    font-weight: 600 !important;
    border-bottom: 1px solid var(--border) !important;
}
div[data-testid="stExpander"] > details > summary span,
div[data-testid="stExpander"] > details > summary p {
    color: var(--text) !important;
    -webkit-text-fill-color: var(--text) !important;
}
/* Fix the expanded content area too */
div[data-testid="stExpander"] > details > div {
    background: var(--card) !important;
}
div[data-testid="stExpander"] > details > div p,
div[data-testid="stExpander"] > details > div span {
    color: var(--text2) !important;
}

/* ========================================================
   FIX 3: Hide broken Material Icon text (arrow_right etc)
   Streamlit 1.54 renders Material Symbols as text when
   the font fails to load. Hide via font-family override.
   ======================================================== */
div[data-testid="stExpander"] summary svg { display: inline-block !important; }
/* If icon text leaks, at least make it invisible */
div[data-testid="stExpander"] summary [data-testid="stExpanderToggleIcon"] {
    font-size: 0 !important;
    width: 24px !important;
    height: 24px !important;
    overflow: hidden !important;
}

/* ========================================================
   FIX 4: INPUTS — visible text, visible cursor
   ======================================================== */
.stTextInput > div > div > input, .stTextArea > div > div > textarea {
    background: #ffffff !important; border: 1.5px solid var(--border) !important;
    border-radius: var(--r) !important; color: var(--text) !important;
    font-size: .9rem !important; font-weight: 500 !important;
    caret-color: var(--primary) !important;
    -webkit-text-fill-color: var(--text) !important;
}
.stTextInput > div > div > input:focus, .stTextArea > div > div > textarea:focus {
    border-color: var(--primary) !important;
    box-shadow: 0 0 0 3px rgba(124,58,237,.12) !important;
}
.stTextInput input::placeholder, .stTextArea textarea::placeholder {
    color: var(--muted) !important; -webkit-text-fill-color: var(--muted) !important; opacity:1!important;
}

/* ========================================================
   FIX 5: SELECTBOX / DROPDOWN — light bg, dark text
   This fixes the black dropdown with invisible text
   ======================================================== */
.stSelectbox > div > div,
.stMultiSelect > div > div,
div[data-baseweb="select"] {
    background: #ffffff !important;
    border: 1.5px solid var(--border) !important;
    border-radius: var(--r) !important;
}
div[data-baseweb="select"] span,
div[data-baseweb="select"] div,
.stSelectbox [data-baseweb="select"] * {
    color: var(--text) !important;
    -webkit-text-fill-color: var(--text) !important;
}
/* Dropdown MENU (the popup list) — force light */
div[data-baseweb="popover"],
div[data-baseweb="popover"] ul,
div[data-baseweb="popover"] li,
ul[role="listbox"],
ul[role="listbox"] li,
div[data-baseweb="menu"] {
    background: #ffffff !important;
    color: var(--text) !important;
}
ul[role="listbox"] li:hover,
div[data-baseweb="menu"] li:hover {
    background: var(--elevated) !important;
    color: var(--text) !important;
}
/* Selected option highlight */
ul[role="listbox"] li[aria-selected="true"],
div[data-baseweb="menu"] li[aria-selected="true"] {
    background: var(--primary) !important;
    color: #ffffff !important;
}

/* ========================================================
   FIX 6: FILE UPLOADER — visible browse button
   ======================================================== */
.stFileUploader > div {
    border: 2px dashed var(--border) !important;
    border-radius: var(--r) !important;
    background: var(--elevated) !important;
}
.stFileUploader button {
    background: var(--primary) !important;
    color: #ffffff !important;
    border: none !important;
    border-radius: 8px !important;
    font-weight: 600 !important;
}
.stFileUploader [data-testid="stFileUploaderDropzone"] p,
.stFileUploader [data-testid="stFileUploaderDropzone"] span,
.stFileUploader [data-testid="stFileUploaderDropzone"] small {
    color: var(--text2) !important;
}

/* ===== MISC ===== */
label { color: var(--text) !important; font-weight: 600 !important; font-size: .85rem !important; }
.divider{height:1px;background:linear-gradient(90deg,transparent,var(--border),transparent);margin:2rem 0}
.cover-letter-box{background:var(--elevated);border:1px solid var(--border);border-radius:var(--r);padding:1.25rem;margin-top:.75rem;color:var(--text2);line-height:1.75;font-size:.88rem}
.cover-letter-label{color:var(--primary);font-weight:700;font-size:.82rem;text-transform:uppercase}
.footer{text-align:center;padding:2rem 1rem;margin-top:3rem;color:var(--muted);font-size:.78rem;border-top:1px solid var(--border)}
.footer a{color:var(--primary);text-decoration:none;font-weight:700}
section[data-testid="stSidebar"]{background:var(--card);border-right:1px solid var(--border)}
.stMarkdown,.stMarkdown p{color:var(--text2)!important} .stMarkdown strong,.stMarkdown b{color:var(--text)!important}
.stAlert p{color:inherit!important}
.stProgress > div > div > div{background:var(--primary)!important}
a{color:var(--primary)} a:hover{color:var(--primary-hover)}

/* Link buttons should have visible text */
.stLinkButton > a {
    background: var(--card) !important;
    color: var(--primary) !important;
    border: 1.5px solid var(--primary) !important;
    border-radius: var(--r) !important;
    font-weight: 700 !important;
}
.stLinkButton > a:hover {
    background: var(--primary) !important;
    color: #ffffff !important;
}

/* Download buttons */
.stDownloadButton > button {
    background: var(--accent-emerald) !important;
    color: #ffffff !important;
}
</style>
""", unsafe_allow_html=True)

# ============================================
# IMPORTS
# ============================================
load_dotenv()
import importlib, sys
for _m in ["location_utils","job_fetcher","resume_parser","run_auto_apply","cover_letter_generator"]:
    if _m in sys.modules:
        try: importlib.reload(sys.modules[_m])
        except: sys.modules.pop(_m, None)
try:
    from job_fetcher import fetch_all
    from resume_parser import build_profile
    from run_auto_apply import run_auto_apply_pipeline
    from cover_letter_generator import generate_cover_letter
    from location_utils import get_all_regions, get_region_display_name
except (ImportError, KeyError) as e:
    st.error(f"Missing module: {e}"); st.stop()

if "session_id" not in st.session_state:
    st.session_state["session_id"] = str(uuid.uuid4())[:8]
SID = st.session_state["session_id"]
DD = f"data/session_{SID}"
os.makedirs(DD, exist_ok=True)
PF = os.path.join(DD,"profile.json"); JF = os.path.join(DD,"jobs.json")
MF = os.path.join(DD,"matches.json"); CF = os.path.join(DD,"semantic_cache.json")
LF = os.path.join(DD,"pipeline.log"); LD = os.path.join(DD,"cover_letters")

COUNTRIES = ["India","United States","United Kingdom","Canada","Germany","Australia","UAE",
    "Saudi Arabia","Singapore","Netherlands","France","Ireland","Israel","Brazil",
    "Japan","South Korea","Philippines","Indonesia","Malaysia","Mexico","Remote Only"]
STATES = {
    "India":["Any","Karnataka (Bangalore)","Maharashtra (Mumbai/Pune)","Delhi NCR","Telangana (Hyderabad)","Tamil Nadu (Chennai)","West Bengal (Kolkata)","Gujarat (Ahmedabad)","Rajasthan (Jaipur)","Uttar Pradesh (Noida/Lucknow)","Kerala (Kochi)","Haryana (Gurgaon)"],
    "United States":["Any","California","New York","Texas","Washington","Massachusetts","Illinois","Florida","Georgia","Colorado"],
    "United Kingdom":["Any","London","Manchester","Edinburgh","Birmingham"],
    "Canada":["Any","Ontario (Toronto)","British Columbia (Vancouver)","Quebec (Montreal)","Alberta (Calgary)"],
    "Germany":["Any","Berlin","Munich","Hamburg","Frankfurt"],
    "Australia":["Any","New South Wales (Sydney)","Victoria (Melbourne)","Queensland (Brisbane)"],
    "UAE":["Any","Dubai","Abu Dhabi"],"Saudi Arabia":["Any","Riyadh","Jeddah"],
    "Singapore":["Any"],"Netherlands":["Any","Amsterdam"],"France":["Any","Paris"],
    "Ireland":["Any","Dublin"],"Israel":["Any","Tel Aviv"],"Brazil":["Any","Sao Paulo"],
    "Japan":["Any","Tokyo"],"South Korea":["Any","Seoul"],"Philippines":["Any","Metro Manila"],
    "Indonesia":["Any","Jakarta"],"Malaysia":["Any","Kuala Lumpur"],"Mexico":["Any","Mexico City"],
    "Remote Only":["Any"],
}

def load_j(fp):
    if not os.path.exists(fp): return None
    try:
        with open(fp,"r",encoding="utf-8") as f: return json.load(f)
    except: return None
def save_j(fp, d):
    os.makedirs(os.path.dirname(fp) or ".", exist_ok=True)
    with open(fp,"w",encoding="utf-8") as f: json.dump(d, f, indent=2, ensure_ascii=False)
def strip_html(t):
    return re.sub(r'\s+',' ',re.sub(r'<[^>]+',' ',t)).strip() if t else ""
def mk_zip(d):
    b=io.BytesIO()
    with zipfile.ZipFile(b,"w",zipfile.ZIP_DEFLATED) as z:
        for f in os.listdir(d):
            if f.endswith(".txt"): z.write(os.path.join(d,f),f)
    b.seek(0); return b.getvalue()
def find_cl(company, title):
    if not os.path.exists(LD): return None,None
    cc=re.sub(r'[^a-zA-Z0-9_\-]','',company.replace(' ','_')).lower()
    tc=re.sub(r'[^a-zA-Z0-9_\-]','',title.replace(' ','_')).lower()
    for fn in os.listdir(LD):
        if fn.endswith(".txt") and (cc in fn.lower() or tc in fn.lower()):
            try:
                with open(os.path.join(LD,fn),"r",encoding="utf-8") as f: return f.read(),fn
            except: pass
    return None,None

def parse_ts(job):
    """Extract a datetime from job's posted_date or summary text."""
    p = job.get("posted_date") or ""
    if p:
        try: return datetime.fromisoformat(p.replace("Z","+00:00"))
        except: pass
    c = f"{job.get('summary','')} {job.get('title','')}".lower()
    if "just posted" in c or "just now" in c: return datetime.now()
    m = re.search(r'(\d+)\s*(hour|day|week|month)s?\s*ago', c)
    if m:
        n,u = int(m.group(1)), m.group(2)
        deltas = {"hour":timedelta(hours=n),"day":timedelta(days=n),"week":timedelta(weeks=n),"month":timedelta(days=n*30)}
        return datetime.now() - deltas.get(u, timedelta())
    return None

def fmt_ts(dt):
    """Format datetime into relative string + CSS class."""
    if not dt: return None, None, "ts-old"
    diff = datetime.now() - dt
    s = diff.total_seconds()
    if s < 3600: return "Just now", dt.strftime("%b %d, %Y"), "ts-fresh"
    if s < 86400: return f"{int(s//3600)}h ago", dt.strftime("%b %d, %Y"), "ts-fresh"
    if diff.days < 3: return f"{diff.days}d ago", dt.strftime("%b %d, %Y"), "ts-fresh"
    if diff.days < 7: return f"{diff.days}d ago", dt.strftime("%b %d, %Y"), "ts-recent"
    if diff.days < 30: return f"{diff.days//7}w ago", dt.strftime("%b %d, %Y"), "ts-recent"
    return f"{diff.days//30}mo ago", dt.strftime("%b %d, %Y"), "ts-old"

def get_pinned(): return st.session_state.get("_pins", set())
def toggle_pin(k):
    p = st.session_state.get("_pins", set())
    p.symmetric_difference_update({k})
    st.session_state["_pins"] = p
def jkey(j): return f"{j.get('company','')}__{j.get('title','')}__{j.get('apply_url','')[:50]}"

# ============================================
# SIDEBAR
# ============================================
with st.sidebar:
    st.markdown("### Session")
    st.caption(f"ID: `{SID}`")
    if st.button("Start Fresh", use_container_width=True):
        for k in list(st.session_state.keys()): del st.session_state[k]
        st.rerun()
    st.markdown("---")
    st.markdown("### How It Works")
    st.markdown("**1.** Upload resume\n\n**2.** Scans 6+ job sources\n\n**3.** AI ranks matches\n\n**4.** Generate cover letters")
    st.markdown("---")
    st.markdown("### Sources")
    for s in ["Google Jobs (Serper.dev)","Indeed, Naukri, Glassdoor","LinkedIn, Instahyre","Lever (50+ companies)","Remotive","WeWorkRemotely / RemoteOK"]:
        st.caption(f"- {s}")

# ============================================
# HERO
# ============================================
st.markdown("""
<div class="hero"><div class="hero-content">
    <h1>JobBot</h1>
    <p class="hero-sub">Upload your resume, get matched with the right opportunities, and generate tailored cover letters.</p>
    <div class="hero-tags">
        <span class="hero-tag">AI Matching</span>
        <span class="hero-tag">6+ Sources</span>
        <span class="hero-tag">Local + Remote</span>
        <span class="hero-tag">Cover Letters</span>
    </div>
</div></div>
""", unsafe_allow_html=True)

# ============================================
# STEPPER (numbers only, no icons/emojis)
# ============================================
profile = load_j(PF); matches = load_j(MF)
s1 = "done" if profile and profile.get("skills") else "active"
s2 = "done" if matches else ("active" if s1=="done" else "pending")
s3 = "done" if os.path.exists(LD) and os.listdir(LD) else ("active" if s2=="done" else "pending")
st.markdown(f"""
<div class="stepper">
    <div class="step {s1}"><div class="step-num">1</div><span>Profile</span></div>
    <div class="step-conn"></div>
    <div class="step {s2}"><div class="step-num">2</div><span>Find Jobs</span></div>
    <div class="step-conn"></div>
    <div class="step {s3}"><div class="step-num">3</div><span>Apply</span></div>
</div>
""", unsafe_allow_html=True)

# ============================================
# STEP 1: PROFILE
# ============================================
st.subheader("Step 1: Your Profile")

col1, col2 = st.columns([2, 1])
with col1:
    uploaded = st.file_uploader("Upload your resume (PDF)", type=["pdf"], key="resume_upload")
with col2:
    if uploaded:
        if st.button("Parse Resume", type="primary", use_container_width=True):
            with st.spinner("Analyzing..."):
                try:
                    rp = os.path.join(DD,"resume.pdf")
                    with open(rp,"wb") as f: f.write(uploaded.getbuffer())
                    ex = load_j(PF)
                    profile = build_profile(rp, PF)
                    if ex:
                        for fld in ["country","state","experience","job_preference"]:
                            if fld not in profile and fld in ex: profile[fld]=ex[fld]
                    profile.setdefault("country",""); profile.setdefault("state","Any")
                    profile.setdefault("experience","3-6 years"); profile.setdefault("job_preference","Both (local + remote)")
                    save_j(PF, profile); st.success("Resume parsed!"); time.sleep(0.5); st.rerun()
                except Exception as e: st.error(f"Error: {e}")

profile = load_j(PF)
if profile and profile.get("skills"):
    st.markdown("---")
    st.markdown(f"**{profile.get('name','Candidate')}**")
    if profile.get('headline'): st.caption(profile['headline'])
    skills = profile.get("skills",[])
    if skills:
        chips = "".join(f'<span class="sc">{s}</span>' for s in skills)
        st.markdown(f'<div class="skills-wrap">{chips}</div>', unsafe_allow_html=True)
        st.caption(f"{len(skills)} skills detected")
    cn = profile.get("country",""); sn = profile.get("state","")
    if cn and cn != "Remote Only":
        st.caption(f"Location: {cn}" + (f" / {sn}" if sn and sn != "Any" else ""))
    elif cn == "Remote Only": st.caption("Remote Only")
else:
    st.info("Upload your resume above, or create a profile manually below.")

# Manual edit — plain text label, NO emojis
with st.expander("Edit Profile Manually" if profile else "Create Profile Manually"):
    nm = st.text_input("Full Name", value=profile.get("name","") if profile else "", placeholder="e.g. Jane Doe")
    hl = st.text_input("Headline", value=profile.get("headline","") if profile else "", placeholder="e.g. Financial Analyst")
    sk = st.text_area("Skills (one per line)", value="\n".join(profile.get("skills",[])) if profile else "", height=150, placeholder="financial analysis\nM&A\nPower BI")

    lc1, lc2 = st.columns(2)
    with lc1:
        cc = profile.get("country","") if profile else ""
        co = list(COUNTRIES)
        if cc and cc not in co: co.append(cc)
        ci = st.selectbox("Country", options=["-- Select --"]+co,
            index=(co.index(cc)+1) if cc in co else 0)
        if ci == "-- Select --": ci = ""
    with lc2:
        sl = STATES.get(ci, ["Any"]); cs = profile.get("state","Any") if profile else "Any"
        if cs not in sl: cs = "Any"
        si = st.selectbox("State / City", options=sl, index=sl.index(cs) if cs in sl else 0)

    ec1, ec2 = st.columns(2)
    with ec1:
        EXP = ["0-1 years","1-3 years","3-6 years","6-10 years","10+ years"]
        ce = profile.get("experience","3-6 years") if profile else "3-6 years"
        if ce not in EXP: ce = "3-6 years"
        ei = st.selectbox("Experience", options=EXP, index=EXP.index(ce))
    with ec2:
        PREFS = ["Local jobs in my city","Remote jobs","Both (local + remote)"]
        cp = profile.get("job_preference","Both (local + remote)") if profile else "Both (local + remote)"
        if cp not in PREFS: cp = "Both (local + remote)"
        pi = st.selectbox("Job Preference", options=PREFS, index=PREFS.index(cp))

    if st.button("Save Profile", use_container_width=True):
        sklist = [s.strip() for s in sk.split("\n") if s.strip()]
        if not sklist and not nm: st.error("Enter at least a name or skills")
        else:
            ex = load_j(PF) or {}
            save_j(PF, {"name":nm or "Candidate","headline":hl,"skills":sklist,
                "country":ci,"state":si,"experience":ei,"job_preference":pi,
                "industry":ex.get("industry",""),"search_terms":ex.get("search_terms",[])})
            st.success("Profile saved!"); time.sleep(0.5); st.rerun()

# ============================================
# STEP 2: JOB MATCHING
# ============================================
st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
st.subheader("Step 2: Find Your Matches")

profile = load_j(PF)
ok = bool(profile and profile.get("skills"))

if not ok:
    st.warning("Complete your profile above to unlock job matching.")
else:
    # Use st.expander with plain text — NO emojis, NO special chars
    with st.expander("How does matching work?"):
        st.markdown("**3-phase pipeline:** Keyword Extraction, Local Scoring, then AI Ranking (Gemini 2.5 Flash)\n\n**Sources:** Google Jobs (Indeed, Naukri, Glassdoor, LinkedIn), Lever, Remotive, WeWorkRemotely, RemoteOK, Jobicy")

    with st.expander("Upload Custom Jobs (Optional)"):
        ju = st.file_uploader("Upload jobs.json", type=["json"], help="Use your own jobs file")
        if ju:
            try: jd=json.loads(ju.getvalue()); save_j(JF,jd); st.success(f"Loaded {len(jd)} jobs")
            except Exception as e: st.error(f"Invalid JSON: {e}")

    if st.session_state.get("_done"):
        st.success("Matching complete! Scroll down for results.")
        mdc = load_j(MF); mc = len(mdc) if isinstance(mdc,list) else 0
        us = profile.get("state","Any"); uc = profile.get("country","")
        c1,c2 = st.columns(2)
        with c1:
            if st.button("Re-run (Fresh)", use_container_width=True):
                st.session_state.pop("_done",None); st.session_state.pop("_pins",None)
                for fp in [JF,MF,CF]:
                    if os.path.exists(fp): os.remove(fp)
                if os.path.exists(LD):
                    for lf in os.listdir(LD): os.remove(os.path.join(LD,lf))
                st.rerun()
        with c2:
            if mc < 5 and us != "Any" and uc:
                if st.button(f"Expand to all of {uc}", type="primary", use_container_width=True):
                    pd = load_j(PF)
                    if pd: pd["state"]="Any"; save_j(PF,pd)
                    st.session_state.pop("_done",None)
                    for fp in [JF,MF,CF]:
                        if os.path.exists(fp): os.remove(fp)
                    st.rerun()
    elif st.session_state.get("_running"):
        st.warning("Matching in progress... usually 30-60 seconds.")
    else:
        country = profile.get("country",""); state = profile.get("state","")
        if country and country != "Remote Only":
            loc = f"**{state+', ' if state and state!='Any' else ''}{country}**"
        elif country == "Remote Only": loc = "**remote opportunities worldwide**"
        else: loc = "**relevant regions**"
        st.markdown(f"Scanning **6+ sources** (Google Jobs, Indeed, Naukri, Glassdoor, Lever, Remotive) focused on {loc}. All qualifying matches will be shown.")

        if st.button("Start Job Matching", type="primary", use_container_width=True):
            st.session_state["_running"] = True
            status = st.empty(); bar = st.progress(0, text="Starting..."); detail = st.empty(); logs = []
            stages = {"Starting":0,"Fetching":5,"Serper":20,"Remotive":25,"Lever":35,"Google":40,"SerpAPI":40,"Loaded":50,"Location":55,"Matching":60,"Phase 1":65,"Batch 1":70,"Batch 2":78,"Batch 3":85,"Threshold":95,"Done":100}
            def cb(msg):
                logs.append(msg); detail.code("\n".join(logs[-8:]),language=None)
                pct = max((p for k,p in stages.items() if k.lower() in msg.lower()), default=0)
                pct = max(pct, getattr(cb,'_mx',0)); cb._mx = pct
                bar.progress(min(pct,100)/100, text=msg[:80])
            cb._mx = 0
            try:
                status.info("Scanning sources and running AI matching...")
                result = run_auto_apply_pipeline(profile_file=PF,jobs_file=JF,matches_file=MF,cache_file=CF,log_file=LF,letters_dir=None,progress_callback=cb)
                bar.progress(1.0, text="Complete!")
                st.session_state["_done"] = True; st.session_state.pop("_running",None)
                if result and result.get("status")=="success": status.success(f"Found {result['matches']} matches from {result['total_scored']} jobs!")
                elif result and result.get("status")=="no_matches": status.warning("No strong matches. Try broadening skills.")
                else: status.error(f"Pipeline error: {result}")
                time.sleep(1); st.rerun()
            except Exception as e:
                st.session_state.pop("_running",None); bar.progress(1.0,text="Error")
                status.error(f"Error: {e}"); st.exception(e)

# ============================================
# STEP 3: RESULTS — all matches, sorted by recency, with pin + posted date
# ============================================
md = load_j(MF)

if isinstance(md, list) and md:
    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)

    # Parse timestamps
    for j in md:
        j["_ts"] = parse_ts(j)

    pinned = get_pinned()
    def sk(j):
        ts = j.get("_ts")
        return (0, -ts.timestamp()) if ts else (1, -j.get("match_score",0))
    pj = sorted([j for j in md if jkey(j) in pinned], key=sk)
    uj = sorted([j for j in md if jkey(j) not in pinned], key=sk)
    all_sorted = pj + uj

    scores = [j.get("match_score",0) for j in md]
    avg = sum(scores)/len(scores) if scores else 0
    letters = [f for f in os.listdir(LD) if f.endswith(".txt")] if os.path.exists(LD) else []

    st.markdown(f"""
    <div class="stats-grid">
        <div class="stat-card"><div class="stat-val purple">{len(md)}</div><div class="stat-lbl">Matches</div></div>
        <div class="stat-card"><div class="stat-val coral">{avg:.0f}%</div><div class="stat-lbl">Avg Score</div></div>
        <div class="stat-card"><div class="stat-val emerald">{max(scores)}%</div><div class="stat-lbl">Top Score</div></div>
        <div class="stat-card"><div class="stat-val amber">{len(letters)}</div><div class="stat-lbl">Letters</div></div>
    </div>
    """, unsafe_allow_html=True)

    if letters:
        zc1,zc2 = st.columns([3,1])
        with zc1: st.subheader(f"All {len(md)} Matches")
        with zc2:
            st.download_button(f"Download {len(letters)} Letters", data=mk_zip(LD),
                file_name="jobbot_letters.zip", mime="application/zip", use_container_width=True)
    else:
        st.subheader(f"All {len(md)} Matches")
        st.caption("Click 'Generate Letter' on any job to create a cover letter.")

    if pinned:
        st.caption(f"{len(pj)} pinned at top | Sorted newest to oldest")
    else:
        st.caption("Sorted newest to oldest | Pin jobs to keep them at top")

    # ---- Job Cards ----
    for i, j in enumerate(all_sorted, 1):
        sc = j.get("match_score", 0)
        co = j.get("company", "Unknown")
        ti = j.get("title", "Unknown")
        src = j.get("source", "")
        sm = strip_html(j.get("summary",""))[:400]
        jk = jkey(j)
        ip = jk in pinned
        ts_rel, ts_full, ts_cls = fmt_ts(j.get("_ts"))

        # Build label — PLAIN TEXT ONLY (no emojis, no unicode arrows)
        parts = [f"#{i}"]
        if ip: parts.append("[PINNED]")
        parts.append(f"{co} -- {ti} ({sc}%)")
        if ts_rel: parts.append(f"| {ts_rel}")
        label = "  ".join(parts)

        with st.expander(label):
            c1, c2 = st.columns([3, 1])
            with c1:
                st.markdown(f"**{ti}**")

                # Company + source badge + timestamp badge (HTML)
                info = f"**{co}**"
                if src: info += f' &nbsp; <span class="src-badge">{src}</span>'
                if ts_rel: info += f' &nbsp; <span class="ts-badge {ts_cls}">{ts_rel}</span>'
                if ip: info += ' &nbsp; <span class="pin-badge">PINNED</span>'
                st.markdown(info, unsafe_allow_html=True)

                # Posted date — ALWAYS show if available
                if ts_full:
                    st.caption(f"Posted: {ts_full}")

                # Location + experience
                jl = j.get("location","")
                if not jl:
                    for t in j.get("location_tags",[]):
                        if t: jl = t; break
                meta = []
                if jl: meta.append(f"Location: {jl}")
                em = re.search(r'(\d+)\+?\s*(?:to\s*\d+\s*)?(?:years?|yrs?)\s*(?:of\s*)?(?:experience|exp)?', j.get("summary","").lower())
                if em: meta.append(f"Exp: {em.group(0).strip()}")
                if meta: st.caption(" | ".join(meta))

                if sm: st.write(sm)

            with c2:
                bc = "score-excellent" if sc >= 75 else ("score-good" if sc >= 60 else "score-fair")
                st.markdown(f'<div style="text-align:center;margin-bottom:.5rem"><span class="score-badge {bc}">{sc}%</span></div>', unsafe_allow_html=True)
                if j.get("apply_url"):
                    st.link_button("Apply Now", j["apply_url"], use_container_width=True)
                if st.button("Unpin" if ip else "Pin to Top", key=f"p_{i}", use_container_width=True):
                    toggle_pin(jk); st.rerun()
                cl, cn = find_cl(co, ti)
                if not cl:
                    if st.button("Generate Letter", key=f"g_{i}", use_container_width=True):
                        with st.spinner("Writing..."):
                            try:
                                os.makedirs(LD, exist_ok=True)
                                generate_cover_letter(j, load_j(PF), LD)
                                st.rerun()
                            except Exception as e: st.error(f"Failed: {e}")

            cl, cn = find_cl(co, ti)
            if cl:
                st.markdown("---")
                st.markdown('<p class="cover-letter-label">Tailored Cover Letter</p>', unsafe_allow_html=True)
                st.markdown(f'<div class="cover-letter-box">{cl}</div>', unsafe_allow_html=True)
                st.download_button("Download Letter", data=cl, file_name=cn or f"letter_{i}.txt",
                    mime="text/plain", key=f"d_{i}", use_container_width=True)

# ============================================
# FOOTER
# ============================================
st.markdown('<div class="footer">Built with Streamlit and Gemini 2.5 Flash | <a href="https://github.com" target="_blank">GitHub</a></div>', unsafe_allow_html=True)
