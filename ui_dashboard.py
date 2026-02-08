import streamlit as st
import json, os, re, uuid, time, io, zipfile
from dotenv import load_dotenv
from datetime import datetime, timedelta

st.set_page_config(page_title="JobBot - AI Job Matching", page_icon="🚀", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');
:root {
    --pri:#7c3aed;--pri2:#6d28d9;--coral:#f43f5e;--green:#10b981;--amber:#f59e0b;
    --bg:#fafaf9;--card:#ffffff;--elev:#f5f5f4;
    --t1:#1c1917;--t2:#57534e;--t3:#a8a29e;--bdr:#e7e5e4;--r:12px;
}
.stApp{font-family:'Plus Jakarta Sans',sans-serif!important;background:var(--bg)!important}
h1,h2,h3,h4,h5,h6{font-family:'Plus Jakarta Sans',sans-serif!important;font-weight:800!important;color:var(--t1)!important}

/* === HERO === */
.hero{background:linear-gradient(135deg,#7c3aed 0%,#a78bfa 35%,#f43f5e 100%);border-radius:20px;padding:2.5rem 2rem;margin-bottom:1.5rem;box-shadow:0 8px 32px rgba(124,58,237,.25)}
.hero h1{color:#fff!important;font-size:2.4rem!important;margin:0 0 .4rem!important}
.hero-sub{color:rgba(255,255,255,.9);font-size:1rem;font-weight:500;line-height:1.6;max-width:600px}
.htags{display:flex;gap:.5rem;flex-wrap:wrap;margin-top:1rem}
.htag{background:rgba(255,255,255,.18);border:1px solid rgba(255,255,255,.25);color:#fff;padding:.4rem .8rem;border-radius:8px;font-size:.75rem;font-weight:600}

/* === STEPPER === */
.stepper{display:flex;justify-content:center;align-items:center;gap:.6rem;margin:1.2rem 0 1.5rem;padding:.8rem 1.2rem;background:var(--card);border:1px solid var(--bdr);border-radius:16px}
.stp{display:flex;align-items:center;gap:.5rem;padding:.5rem .8rem;border-radius:var(--r);font-size:.82rem;font-weight:600;color:var(--t3)}
.sn{width:30px;height:30px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:.8rem;font-weight:700}
.stp.done{color:var(--green)}.stp.done .sn{background:var(--green);color:#fff}
.stp.active{color:var(--pri);background:rgba(124,58,237,.06)}.stp.active .sn{background:var(--pri);color:#fff}
.stp.pending .sn{background:var(--elev);border:2px dashed var(--bdr);color:var(--t3)}
.sc{width:36px;height:2px;background:var(--bdr)}

/* === STATS === */
.sg{display:grid;grid-template-columns:repeat(auto-fit,minmax(130px,1fr));gap:.6rem;margin:1.2rem 0}
.sc2{background:var(--card);border:1px solid var(--bdr);border-radius:14px;padding:1rem .8rem;text-align:center}
.sv{font-size:1.8rem;font-weight:800;line-height:1;margin-bottom:.25rem}
.sv.p{color:var(--pri)}.sv.c{color:var(--coral)}.sv.g{color:var(--green)}.sv.a{color:var(--amber)}
.sl{color:var(--t3);font-size:.7rem;font-weight:700;text-transform:uppercase;letter-spacing:.05em}

/* === BADGES === */
.sb{display:inline-block;padding:.35rem .9rem;border-radius:100px;font-size:.9rem;font-weight:700}
.sb.ex{background:#d1fae5;color:#059669;border:1px solid #a7f3d0}
.sb.gd{background:#fef3c7;color:#d97706;border:1px solid #fde68a}
.sb.fr{background:#ede9fe;color:#7c3aed;border:1px solid #ddd6fe}
.srcb{display:inline-block;padding:.12rem .45rem;border-radius:100px;font-size:.6rem;font-weight:700;text-transform:uppercase;background:var(--elev);color:var(--t2);border:1px solid var(--bdr)}
.tsb{display:inline-flex;align-items:center;gap:.2rem;padding:.12rem .45rem;border-radius:100px;font-size:.6rem;font-weight:700}
.tsb.f{background:#d1fae5;color:#059669;border:1px solid #a7f3d0}
.tsb.r{background:#fed7aa;color:#ea580c;border:1px solid #fdba74}
.tsb.o{background:var(--elev);color:var(--t3);border:1px solid var(--bdr)}
.pinb{display:inline-flex;padding:.12rem .45rem;border-radius:100px;font-size:.6rem;font-weight:700;background:#fecaca;color:#ef4444;border:1px solid #fca5a5}

/* === SKILL CHIPS === */
.skw{display:flex;flex-wrap:wrap;gap:.35rem;margin-top:.6rem}
.skc{padding:.25rem .6rem;border-radius:100px;font-size:.75rem;font-weight:600}
.skc:nth-child(5n+1){background:#f5f3ff;color:#7c3aed;border:1px solid #ddd6fe}
.skc:nth-child(5n+2){background:#fef2f2;color:#ef4444;border:1px solid #fecaca}
.skc:nth-child(5n+3){background:#ecfdf5;color:#059669;border:1px solid #a7f3d0}
.skc:nth-child(5n+4){background:#fff7ed;color:#ea580c;border:1px solid #fed7aa}
.skc:nth-child(5n+5){background:#f0f9ff;color:#0284c7;border:1px solid #bae6fd}

/* ========================================================
   CRITICAL: Buttons — white text on purple
   ======================================================== */
.stButton>button{background:var(--pri)!important;color:#fff!important;border:none!important;border-radius:var(--r)!important;font-weight:700!important;font-size:.88rem!important;box-shadow:0 2px 8px rgba(124,58,237,.2)!important}
.stButton>button:hover{background:var(--pri2)!important}
.stButton>button *{color:#fff!important}

/* ========================================================
   CRITICAL: Expanders — light bg, dark text, HIDE broken icon
   Streamlit 1.54 renders Material Symbols as literal text
   ("arrow_right") when the icon font fails to load.
   ======================================================== */
div[data-testid="stExpander"]{border:1px solid var(--bdr)!important;border-radius:var(--r)!important;background:var(--card)!important;margin-bottom:.4rem!important;overflow:hidden!important}
div[data-testid="stExpander"]>details>summary{background:var(--card)!important;color:var(--t1)!important;padding:.7rem 1rem!important;font-weight:600!important}
div[data-testid="stExpander"]>details>summary *{color:var(--t1)!important;-webkit-text-fill-color:var(--t1)!important}
div[data-testid="stExpander"]>details>div{background:var(--card)!important}
div[data-testid="stExpander"]>details>div *{color:var(--t2)!important}
div[data-testid="stExpander"]>details>div strong,div[data-testid="stExpander"]>details>div b{color:var(--t1)!important}
/* HIDE the broken icon that renders as "arrow_right" text */
div[data-testid="stExpander"] [data-testid="stExpanderToggleIcon"],
div[data-testid="stExpander"] summary svg,
div[data-testid="stExpander"] summary .material-symbols-rounded{font-size:0!important;width:0!important;height:0!important;overflow:hidden!important;display:none!important}

/* ========================================================
   CRITICAL: Inputs — visible text + cursor
   ======================================================== */
.stTextInput>div>div>input,.stTextArea>div>div>textarea{background:#fff!important;border:1.5px solid var(--bdr)!important;border-radius:var(--r)!important;color:var(--t1)!important;font-size:.88rem!important;caret-color:var(--pri)!important;-webkit-text-fill-color:var(--t1)!important}
.stTextInput>div>div>input:focus,.stTextArea>div>div>textarea:focus{border-color:var(--pri)!important;box-shadow:0 0 0 3px rgba(124,58,237,.1)!important}
.stTextInput input::placeholder,.stTextArea textarea::placeholder{color:var(--t3)!important;-webkit-text-fill-color:var(--t3)!important;opacity:1!important}

/* ========================================================
   CRITICAL: Dropdowns — light bg, dark text
   ======================================================== */
.stSelectbox>div>div,div[data-baseweb="select"]{background:#fff!important;border:1.5px solid var(--bdr)!important;border-radius:var(--r)!important}
div[data-baseweb="select"] *{color:var(--t1)!important;-webkit-text-fill-color:var(--t1)!important}
div[data-baseweb="popover"],div[data-baseweb="popover"] ul,div[data-baseweb="popover"] li,ul[role="listbox"],ul[role="listbox"] li,div[data-baseweb="menu"],div[data-baseweb="menu"] li{background:#fff!important;color:var(--t1)!important}
ul[role="listbox"] li:hover,div[data-baseweb="menu"] li:hover{background:var(--elev)!important}
ul[role="listbox"] li[aria-selected="true"]{background:var(--pri)!important;color:#fff!important}

/* ========================================================
   CRITICAL: File uploader — visible "Browse files" button
   ======================================================== */
.stFileUploader>div{border:2px dashed var(--bdr)!important;border-radius:var(--r)!important;background:var(--elev)!important}
.stFileUploader button{background:var(--pri)!important;color:#fff!important;border:none!important;border-radius:8px!important;font-weight:600!important}
.stFileUploader [data-testid="stFileUploaderDropzone"] *{color:var(--t2)!important}

/* ========================================================
   CRITICAL: Link buttons — visible text
   ======================================================== */
.stLinkButton>a{background:var(--card)!important;color:var(--pri)!important;border:1.5px solid var(--pri)!important;border-radius:var(--r)!important;font-weight:700!important}
.stLinkButton>a:hover{background:var(--pri)!important;color:#fff!important}
.stDownloadButton>button{background:var(--green)!important;color:#fff!important}
.stDownloadButton>button *{color:#fff!important}

/* === MISC === */
label{color:var(--t1)!important;font-weight:600!important;font-size:.83rem!important}
.divider{height:1px;background:linear-gradient(90deg,transparent,var(--bdr),transparent);margin:1.8rem 0}
.clbox{background:var(--elev);border:1px solid var(--bdr);border-radius:var(--r);padding:1.2rem;margin-top:.6rem;color:var(--t2);line-height:1.7;font-size:.86rem}
.cllbl{color:var(--pri);font-weight:700;font-size:.78rem;text-transform:uppercase}
.footer{text-align:center;padding:1.5rem 1rem;margin-top:2.5rem;color:var(--t3);font-size:.75rem;border-top:1px solid var(--bdr)}
.footer a{color:var(--pri);text-decoration:none;font-weight:700}
section[data-testid="stSidebar"]{background:var(--card);border-right:1px solid var(--bdr)}
.stMarkdown,.stMarkdown p{color:var(--t2)!important}.stMarkdown strong{color:var(--t1)!important}
.stAlert p{color:inherit!important}
.stProgress>div>div>div{background:var(--pri)!important}
a{color:var(--pri)}
</style>
""", unsafe_allow_html=True)

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
DD = f"data/session_{SID}"; os.makedirs(DD, exist_ok=True)
PF=os.path.join(DD,"profile.json"); JF=os.path.join(DD,"jobs.json")
MF=os.path.join(DD,"matches.json"); CF=os.path.join(DD,"semantic_cache.json")
LF=os.path.join(DD,"pipeline.log"); LD=os.path.join(DD,"cover_letters")

COUNTRIES=["India","United States","United Kingdom","Canada","Germany","Australia","UAE","Saudi Arabia","Singapore","Netherlands","France","Ireland","Israel","Brazil","Japan","South Korea","Philippines","Indonesia","Malaysia","Mexico","Remote Only"]
STATES={
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
    with open(fp,"w",encoding="utf-8") as f: json.dump(d,f,indent=2,ensure_ascii=False)
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
    p=job.get("posted_date") or ""
    if p:
        try: return datetime.fromisoformat(p.replace("Z","+00:00"))
        except: pass
        # Try parsing "X days ago" from posted_date string
        m=re.search(r'(\d+)\s*(hour|day|week|month)s?\s*ago',p.lower())
        if m:
            n,u=int(m.group(1)),m.group(2)
            d={"hour":timedelta(hours=n),"day":timedelta(days=n),"week":timedelta(weeks=n),"month":timedelta(days=n*30)}
            return datetime.now()-d.get(u,timedelta())
        if "today" in p.lower() or "just" in p.lower(): return datetime.now()
    c=f"{job.get('summary','')}".lower()
    if "just posted" in c or "just now" in c: return datetime.now()
    m=re.search(r'(\d+)\s*(hour|day|week|month)s?\s*ago',c)
    if m:
        n,u=int(m.group(1)),m.group(2)
        d={"hour":timedelta(hours=n),"day":timedelta(days=n),"week":timedelta(weeks=n),"month":timedelta(days=n*30)}
        return datetime.now()-d.get(u,timedelta())
    return None
def fmt_ts(dt):
    if not dt: return None,None,"o"
    diff=datetime.now()-dt; s=diff.total_seconds()
    if s<3600: return "Just now",dt.strftime("%b %d, %Y"),"f"
    if s<86400: return f"{int(s//3600)}h ago",dt.strftime("%b %d, %Y"),"f"
    if diff.days<3: return f"{diff.days}d ago",dt.strftime("%b %d, %Y"),"f"
    if diff.days<7: return f"{diff.days}d ago",dt.strftime("%b %d, %Y"),"r"
    if diff.days<30: return f"{diff.days//7}w ago",dt.strftime("%b %d, %Y"),"r"
    return f"{diff.days//30}mo ago",dt.strftime("%b %d, %Y"),"o"
def get_pinned(): return st.session_state.get("_pins",set())
def toggle_pin(k):
    p=st.session_state.get("_pins",set()); p.symmetric_difference_update({k}); st.session_state["_pins"]=p
def jkey(j): return f"{j.get('company','')}__{j.get('title','')}__{j.get('apply_url','')[:50]}"

# === SIDEBAR ===
with st.sidebar:
    st.markdown("### Session")
    st.caption(f"ID: `{SID}`")
    if st.button("Start Fresh", use_container_width=True):
        for k in list(st.session_state.keys()): del st.session_state[k]
        st.rerun()
    st.markdown("---")
    st.markdown("### How It Works")
    st.markdown("1. Upload resume\n2. Scans 6+ job sources\n3. AI ranks matches\n4. Generate cover letters")
    st.markdown("---")
    st.markdown("### Sources")
    for s in ["Google Jobs (Serper.dev)","Indeed, Naukri, Glassdoor","LinkedIn, Instahyre","Lever (50+ companies)","Remotive, WeWorkRemotely","RemoteOK, Jobicy"]:
        st.caption(f"- {s}")

# === HERO ===
st.markdown("""
<div class="hero">
    <h1>JobBot</h1>
    <p class="hero-sub">Upload your resume, get matched with the right opportunities, and generate tailored cover letters.</p>
    <div class="htags">
        <span class="htag">AI Matching</span><span class="htag">6+ Sources</span>
        <span class="htag">Local + Remote</span><span class="htag">Cover Letters</span>
    </div>
</div>
""", unsafe_allow_html=True)

# === STEPPER ===
profile=load_j(PF); matches=load_j(MF)
s1="done" if profile and profile.get("skills") else "active"
s2="done" if matches else ("active" if s1=="done" else "pending")
s3="done" if os.path.exists(LD) and os.listdir(LD) else ("active" if s2=="done" else "pending")
st.markdown(f"""
<div class="stepper">
    <div class="stp {s1}"><div class="sn">1</div><span>Profile</span></div><div class="sc"></div>
    <div class="stp {s2}"><div class="sn">2</div><span>Jobs</span></div><div class="sc"></div>
    <div class="stp {s3}"><div class="sn">3</div><span>Apply</span></div>
</div>
""", unsafe_allow_html=True)

# === STEP 1 ===
st.subheader("Step 1: Your Profile")
col1,col2=st.columns([2,1])
with col1:
    uploaded=st.file_uploader("Upload your resume (PDF)",type=["pdf"],key="resume_upload")
with col2:
    if uploaded:
        if st.button("Parse Resume",type="primary",use_container_width=True):
            with st.spinner("Analyzing..."):
                try:
                    rp=os.path.join(DD,"resume.pdf")
                    with open(rp,"wb") as f: f.write(uploaded.getbuffer())
                    ex=load_j(PF); profile=build_profile(rp,PF)
                    if ex:
                        for fld in ["country","state","experience","job_preference"]:
                            if fld not in profile and fld in ex: profile[fld]=ex[fld]
                    profile.setdefault("country",""); profile.setdefault("state","Any")
                    profile.setdefault("experience","3-6 years"); profile.setdefault("job_preference","Both (local + remote)")
                    save_j(PF,profile); st.success("Resume parsed!"); time.sleep(0.5); st.rerun()
                except Exception as e: st.error(f"Error: {e}")

profile=load_j(PF)
if profile and profile.get("skills"):
    st.markdown("---")
    st.markdown(f"**{profile.get('name','Candidate')}**")
    if profile.get('headline'): st.caption(profile['headline'])
    skills=profile.get("skills",[])
    if skills:
        st.markdown('<div class="skw">'+"".join(f'<span class="skc">{s}</span>' for s in skills)+'</div>',unsafe_allow_html=True)
        st.caption(f"{len(skills)} skills detected")
    cn=profile.get("country",""); sn=profile.get("state","")
    if cn and cn!="Remote Only": st.caption(f"Location: {cn}"+(" / "+sn if sn and sn!="Any" else ""))
    elif cn=="Remote Only": st.caption("Remote Only")
else:
    st.info("Upload your resume above, or create a profile manually below.")

with st.expander("Edit Profile Manually" if profile else "Create Profile Manually"):
    nm=st.text_input("Full Name",value=profile.get("name","") if profile else "",placeholder="e.g. Jane Doe")
    hl=st.text_input("Headline",value=profile.get("headline","") if profile else "",placeholder="e.g. Financial Analyst")
    sk=st.text_area("Skills (one per line)",value="\n".join(profile.get("skills",[])) if profile else "",height=150,placeholder="financial analysis\nM&A\nPower BI")
    lc1,lc2=st.columns(2)
    with lc1:
        cc=profile.get("country","") if profile else ""
        co=list(COUNTRIES)
        if cc and cc not in co: co.append(cc)
        ci=st.selectbox("Country",options=["-- Select --"]+co,index=(co.index(cc)+1) if cc in co else 0)
        if ci=="-- Select --": ci=""
    with lc2:
        sl=STATES.get(ci,["Any"]); cs=profile.get("state","Any") if profile else "Any"
        if cs not in sl: cs="Any"
        si=st.selectbox("State / City",options=sl,index=sl.index(cs) if cs in sl else 0)
    ec1,ec2=st.columns(2)
    with ec1:
        EXP=["0-1 years","1-3 years","3-6 years","6-10 years","10+ years"]
        ce=profile.get("experience","3-6 years") if profile else "3-6 years"
        if ce not in EXP: ce="3-6 years"
        ei=st.selectbox("Experience",options=EXP,index=EXP.index(ce))
    with ec2:
        PREFS=["Local jobs in my city","Remote jobs","Both (local + remote)"]
        cp=profile.get("job_preference","Both (local + remote)") if profile else "Both (local + remote)"
        if cp not in PREFS: cp="Both (local + remote)"
        pi=st.selectbox("Job Preference",options=PREFS,index=PREFS.index(cp))
    if st.button("Save Profile",use_container_width=True):
        sklist=[s.strip() for s in sk.split("\n") if s.strip()]
        if not sklist and not nm: st.error("Enter at least a name or skills")
        else:
            ex=load_j(PF) or {}
            save_j(PF,{"name":nm or "Candidate","headline":hl,"skills":sklist,"country":ci,"state":si,
                "experience":ei,"job_preference":pi,"industry":ex.get("industry",""),"search_terms":ex.get("search_terms",[])})
            st.success("Profile saved!"); time.sleep(0.5); st.rerun()

# === STEP 2 ===
st.markdown('<div class="divider"></div>',unsafe_allow_html=True)
st.subheader("Step 2: Find Your Matches")
profile=load_j(PF); ok=bool(profile and profile.get("skills"))
if not ok:
    st.warning("Complete your profile above to unlock job matching.")
else:
    with st.expander("How does matching work"):
        st.markdown("**3-phase pipeline:** Keyword Extraction, Local Scoring, then AI Ranking (Gemini 2.5 Flash)\n\n**Sources:** Google Jobs (Indeed, Naukri, Glassdoor, LinkedIn), Lever, Remotive, WeWorkRemotely, RemoteOK, Jobicy")
    with st.expander("Upload Custom Jobs (Optional)"):
        ju=st.file_uploader("Upload jobs.json",type=["json"],help="Your own jobs file")
        if ju:
            try: jd=json.loads(ju.getvalue()); save_j(JF,jd); st.success(f"Loaded {len(jd)} jobs")
            except Exception as e: st.error(f"Invalid JSON: {e}")

    if st.session_state.get("_done"):
        st.success("Matching complete! Scroll down for results.")
        mdc=load_j(MF); mc=len(mdc) if isinstance(mdc,list) else 0
        us=profile.get("state","Any"); uc=profile.get("country","")
        c1,c2=st.columns(2)
        with c1:
            if st.button("Re-run (Fresh Jobs)",use_container_width=True):
                st.session_state.pop("_done",None); st.session_state.pop("_pins",None)
                for fp in [JF,MF,CF]:
                    if os.path.exists(fp): os.remove(fp)
                if os.path.exists(LD):
                    for lf in os.listdir(LD): os.remove(os.path.join(LD,lf))
                st.rerun()
        with c2:
            if mc<5 and us!="Any" and uc:
                if st.button(f"Expand to all of {uc}",type="primary",use_container_width=True):
                    pd=load_j(PF)
                    if pd: pd["state"]="Any"; save_j(PF,pd)
                    st.session_state.pop("_done",None)
                    for fp in [JF,MF,CF]:
                        if os.path.exists(fp): os.remove(fp)
                    st.rerun()
    elif st.session_state.get("_running"):
        st.warning("Matching in progress... usually 30-60 seconds.")
    else:
        country=profile.get("country",""); state=profile.get("state","")
        if country and country!="Remote Only":
            loc=f"**{state+', ' if state and state!='Any' else ''}{country}**"
        elif country=="Remote Only": loc="**remote opportunities worldwide**"
        else: loc="**relevant regions**"
        st.markdown(f"Scanning **6+ sources** focused on {loc}. All qualifying matches will be shown.")
        if st.button("Start Job Matching",type="primary",use_container_width=True):
            st.session_state["_running"]=True
            status=st.empty(); bar=st.progress(0,text="Starting..."); detail=st.empty(); logs=[]
            stages={"Starting":0,"Fetching":5,"Serper":20,"Remotive":25,"Lever":35,"Google":40,"SerpAPI":40,"Loaded":50,"Location":55,"Matching":60,"Phase 1":65,"Batch 1":70,"Batch 2":78,"Batch 3":85,"Threshold":95,"Done":100}
            def cb(msg):
                logs.append(msg); detail.code("\n".join(logs[-8:]),language=None)
                pct=max((p for k,p in stages.items() if k.lower() in msg.lower()),default=0)
                pct=max(pct,getattr(cb,'_mx',0)); cb._mx=pct
                bar.progress(min(pct,100)/100,text=msg[:80])
            cb._mx=0
            try:
                status.info("Scanning sources and running AI matching...")
                result=run_auto_apply_pipeline(profile_file=PF,jobs_file=JF,matches_file=MF,cache_file=CF,log_file=LF,letters_dir=None,progress_callback=cb)
                bar.progress(1.0,text="Complete!")
                st.session_state["_done"]=True; st.session_state.pop("_running",None)
                if result and result.get("status")=="success": status.success(f"Found {result['matches']} matches from {result['total_scored']} jobs!")
                elif result and result.get("status")=="no_matches": status.warning("No strong matches found. Try broadening your skills.")
                else: status.error(f"Pipeline issue: {result}")
                time.sleep(1); st.rerun()
            except Exception as e:
                st.session_state.pop("_running",None); bar.progress(1.0,text="Error")
                status.error(f"Error: {e}"); st.exception(e)

# === STEP 3: RESULTS ===
md=load_j(MF)
if isinstance(md,list) and md:
    st.markdown('<div class="divider"></div>',unsafe_allow_html=True)
    for j in md: j["_ts"]=parse_ts(j)
    pinned=get_pinned()
    def sk2(j):
        ts=j.get("_ts")
        return (0,-ts.timestamp()) if ts else (1,-j.get("match_score",0))
    pj=sorted([j for j in md if jkey(j) in pinned],key=sk2)
    uj=sorted([j for j in md if jkey(j) not in pinned],key=sk2)
    all_s=pj+uj
    scores=[j.get("match_score",0) for j in md]
    avg=sum(scores)/len(scores) if scores else 0
    letters=[f for f in os.listdir(LD) if f.endswith(".txt")] if os.path.exists(LD) else []

    st.markdown(f"""
    <div class="sg">
        <div class="sc2"><div class="sv p">{len(md)}</div><div class="sl">Matches</div></div>
        <div class="sc2"><div class="sv c">{avg:.0f}%</div><div class="sl">Avg Score</div></div>
        <div class="sc2"><div class="sv g">{max(scores)}%</div><div class="sl">Top Score</div></div>
        <div class="sc2"><div class="sv a">{len(letters)}</div><div class="sl">Letters</div></div>
    </div>
    """,unsafe_allow_html=True)

    if letters:
        zc1,zc2=st.columns([3,1])
        with zc1: st.subheader(f"All {len(md)} Matches")
        with zc2:
            st.download_button(f"Download {len(letters)} Letters",data=mk_zip(LD),file_name="jobbot_letters.zip",mime="application/zip",use_container_width=True)
    else:
        st.subheader(f"All {len(md)} Matches")
        st.caption("Click 'Generate Letter' on any job below.")

    if pinned: st.caption(f"{len(pj)} pinned at top | Sorted newest to oldest")
    else: st.caption("Sorted newest to oldest | Pin jobs to keep them at top")

    for i,j in enumerate(all_s,1):
        sc=j.get("match_score",0); co=j.get("company","Unknown"); ti=j.get("title","Unknown")
        src=j.get("source",""); sm=strip_html(j.get("summary",""))[:400]
        jk=jkey(j); ip=jk in pinned
        ts_rel,ts_full,ts_cls=fmt_ts(j.get("_ts"))

        # PLAIN TEXT label — NO emojis, NO unicode, NO special chars
        parts=[f"#{i}"]
        if ip: parts.append("[PINNED]")
        parts.append(f"{co} - {ti} ({sc}%)")
        if ts_rel: parts.append(f"[{ts_rel}]")
        label=" ".join(parts)

        with st.expander(label):
            c1,c2=st.columns([3,1])
            with c1:
                st.markdown(f"**{ti}**")
                info=f"**{co}**"
                if src: info+=f' &nbsp;<span class="srcb">{src}</span>'
                if ts_rel: info+=f' &nbsp;<span class="tsb {ts_cls}">{ts_rel}</span>'
                if ip: info+=' &nbsp;<span class="pinb">PINNED</span>'
                st.markdown(info,unsafe_allow_html=True)
                if ts_full: st.caption(f"Posted: {ts_full}")
                jl=j.get("location","")
                if not jl:
                    for t in j.get("location_tags",[]):
                        if t: jl=t; break
                meta=[]
                if jl: meta.append(f"Location: {jl}")
                em=re.search(r'(\d+)\+?\s*(?:to\s*\d+\s*)?(?:years?|yrs?)',j.get("summary","").lower())
                if em: meta.append(f"Exp: {em.group(0).strip()}")
                if meta: st.caption(" | ".join(meta))
                if sm: st.write(sm)
            with c2:
                bc="ex" if sc>=75 else ("gd" if sc>=60 else "fr")
                st.markdown(f'<div style="text-align:center;margin-bottom:.4rem"><span class="sb {bc}">{sc}%</span></div>',unsafe_allow_html=True)
                if j.get("apply_url"): st.link_button("Apply Now",j["apply_url"],use_container_width=True)
                if st.button("Unpin" if ip else "Pin to Top",key=f"p_{i}",use_container_width=True):
                    toggle_pin(jk); st.rerun()
                cl,cn=find_cl(co,ti)
                if not cl:
                    if st.button("Generate Letter",key=f"g_{i}",use_container_width=True):
                        with st.spinner("Writing..."):
                            try:
                                os.makedirs(LD,exist_ok=True)
                                generate_cover_letter(j,load_j(PF),LD); st.rerun()
                            except Exception as e: st.error(f"Failed: {e}")
            cl,cn=find_cl(co,ti)
            if cl:
                st.markdown("---")
                st.markdown('<p class="cllbl">Tailored Cover Letter</p>',unsafe_allow_html=True)
                st.markdown(f'<div class="clbox">{cl}</div>',unsafe_allow_html=True)
                st.download_button("Download Letter",data=cl,file_name=cn or f"letter_{i}.txt",mime="text/plain",key=f"d_{i}",use_container_width=True)

st.markdown('<div class="footer">Built with Streamlit and Gemini 2.5 Flash | <a href="https://github.com" target="_blank">GitHub</a></div>',unsafe_allow_html=True)
