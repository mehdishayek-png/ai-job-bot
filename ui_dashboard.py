import streamlit as st
import json, os, re, uuid, time, io, zipfile
from dotenv import load_dotenv
from datetime import datetime, timedelta, timezone

st.set_page_config(page_title="JobBot - AI Job Matching", page_icon="🚀", layout="wide", initial_sidebar_state="collapsed")
st.markdown("""
<style>
    .stApp {max-width: 1200px; margin: 0 auto;}
    .job-card {padding: 1.5rem; border-radius: 10px; border: 1px solid #e0e0e0; background-color: #ffffff; margin-bottom: 1rem; transition: all 0.2s;}
    .job-card:hover {border-color: #2196f3; box-shadow: 0 4px 12px rgba(0,0,0,0.1);}
    .match-score {font-weight: 800; font-size: 1.2rem; color: #2196f3;}
    .company-name {font-weight: 600; color: #555;}
    .source-tag {font-size: 0.8rem; padding: 2px 8px; border-radius: 12px; background-color: #f0f2f6; color: #666;}
    .skill-tag {display: inline-block; padding: 2px 8px; border-radius: 4px; background-color: #e3f2fd; color: #1565c0; font-size: 0.85rem; margin-right: 4px; margin-bottom: 4px;}
    .pinned {border-left: 5px solid #ff9800;}
</style>
""", unsafe_allow_html=True)

load_dotenv()

# Reload modules for dev
import importlib, sys
for _m in ["location_utils", "job_fetcher", "resume_parser", "run_auto_apply", "cover_letter_generator"]:
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
    st.error(f"Missing module: {e}")
    st.stop()

# Session State
if "session_id" not in st.session_state:
    st.session_state["session_id"] = str(uuid.uuid4())[:8]

SID = st.session_state["session_id"]
DD = f"data/session_{SID}"
os.makedirs(DD, exist_ok=True)

PF = os.path.join(DD, "profile.json")
JF = os.path.join(DD, "jobs.json")
MF = os.path.join(DD, "matches.json")
CF = os.path.join(DD, "semantic_cache.json")
LF = os.path.join(DD, "pipeline.log")
LD = os.path.join(DD, "cover_letters")

COUNTRIES = ["India", "United States", "United Kingdom", "Canada", "Germany", "Australia", "UAE", "Saudi Arabia", "Singapore", "Netherlands", "France", "Ireland", "Israel", "Brazil", "Japan", "South Korea", "Philippines", "Indonesia", "Malaysia", "Mexico", "Remote Only"]
STATES = {
    "India": ["Any", "Karnataka (Bangalore)", "Maharashtra (Mumbai/Pune)", "Delhi NCR", "Telangana (Hyderabad)", "Tamil Nadu (Chennai)", "West Bengal (Kolkata)", "Gujarat (Ahmedabad)", "Rajasthan (Jaipur)", "Uttar Pradesh (Noida/Lucknow)", "Kerala (Kochi)", "Haryana (Gurgaon)"],
    "United States": ["Any", "California", "New York", "Texas", "Washington", "Massachusetts", "Illinois", "Florida", "Georgia", "Colorado"],
    "United Kingdom": ["Any", "London", "Manchester", "Edinburgh", "Birmingham"],
    "Canada": ["Any", "Ontario (Toronto)", "British Columbia (Vancouver)", "Quebec (Montreal)", "Alberta (Calgary)"],
    "Germany": ["Any", "Berlin", "Munich", "Hamburg", "Frankfurt"],
    "Australia": ["Any", "New South Wales (Sydney)", "Victoria (Melbourne)", "Queensland (Brisbane)"],
    "UAE": ["Any", "Dubai", "Abu Dhabi"],
    "Saudi Arabia": ["Any", "Riyadh", "Jeddah"],
    "Singapore": ["Any"], "Netherlands": ["Any", "Amsterdam"], "France": ["Any", "Paris"],
    "Ireland": ["Any", "Dublin"], "Israel": ["Any", "Tel Aviv"], "Brazil": ["Any", "Sao Paulo"],
    "Japan": ["Any", "Tokyo"], "South Korea": ["Any", "Seoul"], "Philippines": ["Any", "Metro Manila"],
    "Indonesia": ["Any", "Jakarta"], "Malaysia": ["Any", "Kuala Lumpur"], "Mexico": ["Any", "Mexico City"],
    "Remote Only": ["Any"],
}

# --- Utils ---
def load_j(fp):
    if not os.path.exists(fp): return None
    try:
        with open(fp, "r", encoding="utf-8") as f: return json.load(f)
    except: return None

def save_j(fp, d):
    os.makedirs(os.path.dirname(fp) or ".", exist_ok=True)
    with open(fp, "w", encoding="utf-8") as f: json.dump(d, f, indent=2, ensure_ascii=False)

def strip_html(t):
    return re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ', t)).strip() if t else ""

def mk_zip(d):
    b = io.BytesIO()
    with zipfile.ZipFile(b, "w", zipfile.ZIP_DEFLATED) as z:
        for f in os.listdir(d):
            if f.endswith(".txt"): z.write(os.path.join(d, f), f)
    b.seek(0)
    return b.getvalue()

def find_cl(company, title):
    if not os.path.exists(LD): return None, None
    cc = re.sub(r'[^a-zA-Z0-9_\-]', '', company.replace(' ', '_')).lower()
    tc = re.sub(r'[^a-zA-Z0-9_\-]', '', title.replace(' ', '_')).lower()
    for fn in os.listdir(LD):
        if fn.endswith(".txt") and (cc in fn.lower() or tc in fn.lower()):
            try:
                with open(os.path.join(LD, fn), "r", encoding="utf-8") as f: return f.read(), fn
            except: pass
    return None, None

def parse_ts(job):
    p = job.get("posted_date") or ""
    now = datetime.now(timezone.utc)  # Use aware UTC time

    if p:
        try:
            # Try parsing ISO format
            dt = datetime.fromisoformat(p.replace("Z", "+00:00"))
            # Ensure aware
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except:
            pass

        # Try parsing "X days ago"
        m = re.search(r'(\d+)\s*(hour|day|week|month)s?\s*ago', p.lower())
        if m:
            n, u = int(m.group(1)), m.group(2)
            d = {"hour": timedelta(hours=n), "day": timedelta(days=n), 
                 "week": timedelta(weeks=n), "month": timedelta(days=n*30)}
            return now - d.get(u, timedelta())

        if "today" in p.lower() or "just" in p.lower():
            return now

    # Try parsing summary text for relative dates
    c = f"{job.get('summary','')}".lower()
    if "just posted" in c or "just now" in c:
        return now

    m = re.search(r'(\d+)\s*(hour|day|week|month)s?\s*ago', c)
    if m:
        n, u = int(m.group(1)), m.group(2)
        d = {"hour": timedelta(hours=n), "day": timedelta(days=n), 
             "week": timedelta(weeks=n), "month": timedelta(days=n*30)}
        return now - d.get(u, timedelta())

    return None

def fmt_ts(dt):
    if not dt:
        return None, None, "o"

    # Ensure both are timezone aware or both naive
    now = datetime.now(timezone.utc)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)

    diff = now - dt
    s = diff.total_seconds()

    # Format date string
    date_str = dt.strftime("%b %d, %Y")

    if s < 3600:
        return "Just now", date_str, "f"
    if s < 86400:
        return f"{int(s//3600)}h ago", date_str, "f"
    if diff.days < 3:
        return f"{diff.days}d ago", date_str, "f"
    if diff.days < 7:
        return f"{diff.days}d ago", date_str, "r"
    if diff.days < 30:
        return f"{diff.days//7}w ago", date_str, "r"

    return f"{diff.days//30}mo ago", date_str, "o"

def get_pinned():
    return st.session_state.get("_pins", set())

def toggle_pin(k):
    p = st.session_state.get("_pins", set())
    p.symmetric_difference_update({k})
    st.session_state["_pins"] = p

def jkey(j):
    return f"{j.get('company','')}__{j.get('title','')}__{j.get('apply_url','')[:50]}"

# === SIDEBAR ===
with st.sidebar:
    st.markdown("### Session")
    st.caption(f"ID: `{SID}`")
    if st.button("Start Fresh", use_container_width=True):
        for k in list(st.session_state.keys()):
            del st.session_state[k]
        st.rerun()

    st.markdown("---")
    st.markdown("### How It Works")
    st.markdown("1. Upload resume\n2. Scans 6+ job sources\n3. AI ranks matches\n4. Generate cover letters")

    st.markdown("---")
    st.markdown("### Sources")
    for s in ["Google Jobs (via JSearch)", "Indeed, Naukri, Glassdoor", "LinkedIn, Instahyre", "Lever (50+ companies)", "Remotive, WeWorkRemotely", "RemoteOK, Jobicy"]:
        st.caption(f"- {s}")

# === HERO ===
st.markdown("""
# 🚀 JobBot AI
### Upload your resume, get matched with the right opportunities, and generate tailored cover letters.
""", unsafe_allow_html=True)

# === MAIN PIPELINE ===
col1, col2 = st.columns([1, 2])

with col1:
    st.subheader("1. Your Profile")
    uploaded_file = st.file_uploader("Upload Resume (PDF)", type="pdf")

    profile = load_j(PF)

    if uploaded_file and (not profile or st.button("Re-parse Resume")):
        with st.spinner("Analyzing resume..."):
            raw_text = ""
            try:
                import pypdf
                pdf = pypdf.PdfReader(uploaded_file)
                for page in pdf.pages:
                    raw_text += page.extract_text() + "\n"
            except Exception as e:
                st.error(f"Error reading PDF: {e}")

            if raw_text:
                profile = build_profile(raw_text)
                save_j(PF, profile)
                st.success("Resume parsed!")
                st.rerun()

    if profile:
        with st.expander("Edit Preferences", expanded=True):
            name_input = st.text_input("Name", value=profile.get("name", ""))
            headline_input = st.text_input("Professional Headline", value=profile.get("headline", ""))
            skills_input = st.text_area("Skills (one per line)", value="\n".join(profile.get("skills", [])), height=150)

            lc1, lc2 = st.columns(2)
            with lc1:
                cc = profile.get("country", "India")
                # Ensure valid country
                if cc not in COUNTRIES: cc = "India"
                country_input = st.selectbox("Country", COUNTRIES, index=COUNTRIES.index(cc))
            with lc2:
                ss = profile.get("state", "Any")
                opts = STATES.get(country_input, ["Any"])
                if ss not in opts: ss = "Any"
                state_input = st.selectbox("Region/City", opts, index=opts.index(ss))

            # Additional search terms
            search_terms = st.text_input("Additional Search Terms (comma separated)", value=", ".join(profile.get("search_terms", [])))

            if st.button("Update Profile"):
                profile["name"] = name_input
                profile["headline"] = headline_input
                profile["skills"] = [s.strip() for s in skills_input.split("\n") if s.strip()]
                profile["country"] = country_input
                profile["state"] = state_input
                profile["search_terms"] = [t.strip() for t in search_terms.split(",") if t.strip()]
                save_j(PF, profile)
                st.success("Profile updated!")
                st.rerun()

with col2:
    st.subheader("2. Job Hunt")

    if not profile:
        st.info("👈 Please upload your resume first to start.")
    else:
        # Run Pipeline Button
        if st.button("Find & Match Jobs", type="primary", use_container_width=True):
            with st.status("Running Job Hunt Pipeline...", expanded=True) as status:
                st.write("🔍 fetching jobs from all sources...")
                try:
                    run_auto_apply_pipeline(SID)
                    status.update(label="Pipeline Complete!", state="complete", expanded=False)
                    st.rerun()
                except Exception as e:
                    st.error(f"Pipeline failed: {e}")
                    status.update(label="Pipeline Failed", state="error")

        # Display Results
        matches = load_j(MF)
        if matches:
            matches.sort(key=lambda x: x.get("match_score", 0), reverse=True)

            # Filters
            fc1, fc2, fc3 = st.columns(3)
            with fc1: 
                min_score = st.slider("Min Match Score", 0, 100, 50)
            with fc2:
                sort_by = st.selectbox("Sort By", ["Match Score", "Date Posted"])
            with fc3:
                show_pinned = st.checkbox("Show Pinned Only")

            filtered = [m for m in matches if m.get("match_score", 0) >= min_score]

            if show_pinned:
                pinned_keys = get_pinned()
                filtered = [m for m in filtered if jkey(m) in pinned_keys]

            if sort_by == "Date Posted":
                # Sort by parsed date, putting recent first
                filtered.sort(key=lambda x: parse_ts(x) or datetime.min.replace(tzinfo=timezone.utc), reverse=True)

            st.write(f"Showing {len(filtered)} matches")

            for job in filtered:
                score = job.get("match_score", 0)
                score_color = "#4caf50" if score >= 80 else "#ff9800" if score >= 50 else "#f44336"
                jk = jkey(job)
                is_pinned = jk in get_pinned()

                # Timestamp handling
                ts_dt = parse_ts(job)
                rel_time, abs_date, urgency = fmt_ts(ts_dt)
                time_badge = ""
                if rel_time:
                    tc = "#e8f5e9" if urgency == "f" else "#fff3e0" if urgency == "r" else "#f5f5f5"
                    time_badge = f'<span style="background:{tc}; padding:2px 6px; border-radius:4px; font-size:0.8rem; margin-left:8px">🕒 {rel_time}</span>'

                with st.container():
                    cols = st.columns([0.1, 0.7, 0.2])

                    # Pin button
                    with cols[0]:
                        if st.button("📌" if is_pinned else "📍", key=f"pin_{jk}"):
                            toggle_pin(jk)
                            st.rerun()

                    # Main content
                    with cols[1]:
                        st.markdown(f"""
                        <div style="font-size:1.1rem; font-weight:700;">
                            <a href="{job.get('apply_url')}" target="_blank" style="text-decoration:none; color:#1565c0;">{job.get('title')}</a>
                        </div>
                        <div style="color:#555; margin-bottom:4px;">
                            🏢 <b>{job.get('company')}</b> &nbsp;•&nbsp; 📍 {job.get('location', 'Remote')} {time_badge}
                        </div>
                        """, unsafe_allow_html=True)

                        # Tags
                        tags_html = f'<span class="source-tag">{job.get("source")}</span> '
                        for kw in job.get("keywords_found", [])[:5]:
                            tags_html += f'<span class="skill-tag">{kw}</span>'
                        st.markdown(tags_html, unsafe_allow_html=True)

                        with st.expander("Why this matches?"):
                            reason = job.get("reasoning", "No reasoning provided.")
                            st.write(reason)

                            if st.button("Generate Cover Letter", key=f"cl_{jk}"):
                                with st.spinner("Generating..."):
                                    cl_text = generate_cover_letter(profile, job)
                                    # Save
                                    os.makedirs(LD, exist_ok=True)
                                    fn = f"{re.sub(r'[^a-zA-Z0-9]', '', job['company'])}_{int(time.time())}.txt"
                                    with open(os.path.join(LD, fn), "w") as f: f.write(cl_text)
                                    st.success("Generated!")
                                    st.rerun()

                            # Show existing CL
                            cl_content, cl_file = find_cl(job['company'], job['title'])
                            if cl_content:
                                st.download_button("Download Cover Letter", cl_content, file_name=cl_file)
                                st.text_area("Preview", cl_content, height=200)

                    # Score
                    with cols[2]:
                        st.markdown(f"""
                        <div style="text-align:center; background:{score_color}15; padding:10px; border-radius:8px; border:1px solid {score_color};">
                            <div style="font-size:1.5rem; font-weight:800; color:{score_color}">{score}%</div>
                            <div style="font-size:0.8rem; color:#666">Match</div>
                        </div>
                        """, unsafe_allow_html=True)

                st.markdown("<hr style='margin:10px 0;'>", unsafe_allow_html=True)
