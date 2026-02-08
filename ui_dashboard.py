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
# CUSTOM CSS — Modern Professional Design with Logo-Inspired Colors
# ============================================

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap');

/* ============ GLOBAL ============ */
* { margin: 0; padding: 0; box-sizing: border-box; }

.stApp {
    font-family: 'DM Sans', -apple-system, BlinkMacSystemFont, sans-serif;
    background: linear-gradient(180deg, #f8f9fc 0%, #ffffff 100%);
}

h1, h2, h3, h4, h5, h6,
.stMarkdown h1, .stMarkdown h2, .stMarkdown h3 {
    font-family: 'DM Sans', sans-serif !important;
    font-weight: 700 !important;
    letter-spacing: -0.03em;
    color: #1a1f36 !important;
}

p, li, span, div { color: #3d3d56; }

code, .stCode, pre {
    font-family: 'JetBrains Mono', monospace !important;
}

/* ============ HERO SECTION ============ */
.hero {
    background: linear-gradient(135deg, #5B86E5 0%, #36D1DC 100%);
    border-radius: 24px;
    padding: 3rem 2.5rem;
    margin-bottom: 2rem;
    position: relative;
    overflow: hidden;
    box-shadow: 0 10px 40px rgba(91, 134, 229, 0.3);
}

.hero::before {
    content: '';
    position: absolute;
    top: -30%;
    right: -10%;
    width: 500px;
    height: 500px;
    background: radial-gradient(circle, rgba(255,255,255,0.2) 0%, transparent 70%);
    filter: blur(60px);
    animation: float 6s ease-in-out infinite;
}

@keyframes float {
    0%, 100% { transform: translateY(0px); }
    50% { transform: translateY(-20px); }
}

.hero-content { 
    position: relative; 
    z-index: 1; 
}

.hero h1 {
    color: #ffffff !important;
    font-size: 2.75rem !important;
    font-weight: 800 !important;
    margin: 0 0 0.5rem 0 !important;
    line-height: 1.1;
    text-shadow: 0 2px 10px rgba(0,0,0,0.1);
}

.hero-subtitle {
    color: rgba(255,255,255,0.95);
    font-size: 1.15rem;
    margin: 0 0 1.5rem 0;
    font-weight: 400;
    line-height: 1.6;
}

.hero-tags {
    display: flex;
    gap: 0.75rem;
    flex-wrap: wrap;
    margin-top: 1.25rem;
}

.hero-tag {
    background: rgba(255,255,255,0.25);
    backdrop-filter: blur(10px);
    border: 1px solid rgba(255,255,255,0.35);
    color: #fff;
    padding: 0.5rem 1rem;
    border-radius: 12px;
    font-size: 0.85rem;
    font-weight: 600;
    transition: all 0.3s ease;
}

.hero-tag:hover {
    background: rgba(255,255,255,0.35);
    transform: translateY(-2px);
}

/* ============ STEPPER ============ */
.stepper {
    display: flex;
    justify-content: center;
    align-items: center;
    gap: 1rem;
    margin: 2rem 0 2.5rem;
    padding: 1.5rem;
    background: #ffffff;
    border: 1px solid #e8ebf0;
    border-radius: 20px;
    box-shadow: 0 4px 20px rgba(0,0,0,0.06);
}

.step {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    padding: 0.75rem 1.25rem;
    border-radius: 12px;
    font-size: 0.9rem;
    font-weight: 600;
    color: #6c6c8a;
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

.step.done { color: #10b981; }
.step.done .step-icon {
    background: linear-gradient(135deg, #10b981 0%, #059669 100%);
    color: #fff;
    box-shadow: 0 4px 12px rgba(16, 185, 129, 0.3);
}

.step.active {
    color: #5B86E5;
    background: linear-gradient(135deg, #f0f4ff 0%, #e8f0fe 100%);
}

.step.active .step-icon {
    background: linear-gradient(135deg, #5B86E5 0%, #36D1DC 100%);
    color: #fff;
    box-shadow: 0 4px 15px rgba(91, 134, 229, 0.4);
    animation: pulse 2s ease-in-out infinite;
}

.step.pending { color: #c0c0d0; }
.step.pending .step-icon {
    background: #f5f6f8;
    border: 2px dashed #d5d7dd;
}

.step-connector {
    width: 50px; 
    height: 3px;
    background: linear-gradient(90deg, #e0e2ea 0%, #d0d2dd 100%);
    border-radius: 2px;
}

@keyframes pulse {
    0%, 100% { transform: scale(1); box-shadow: 0 4px 15px rgba(91, 134, 229, 0.4); }
    50% { transform: scale(1.1); box-shadow: 0 6px 20px rgba(91, 134, 229, 0.6); }
}

/* ============ CARDS ============ */
.glass-card {
    background: #ffffff;
    border: 1px solid #e8ebf0;
    border-radius: 20px;
    padding: 2rem;
    margin-bottom: 1.5rem;
    transition: all 0.3s ease;
    box-shadow: 0 2px 8px rgba(0,0,0,0.05);
}

.glass-card:hover {
    border-color: #5B86E5;
    box-shadow: 0 8px 30px rgba(91, 134, 229, 0.12);
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
    font-size: 1.4rem;
    background: linear-gradient(135deg, #f0f4ff 0%, #e8f0fe 100%);
    border: 1px solid #dde6f5;
}

.card-title {
    font-size: 1.3rem !important;
    font-weight: 700 !important;
    color: #1a1f36 !important;
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
    background: linear-gradient(135deg, #f0f4ff 0%, #e8f0fe 100%);
    border: 1px solid #dde6f5;
    color: #5B86E5;
    padding: 0.5rem 1rem;
    border-radius: 10px;
    font-size: 0.85rem;
    font-weight: 600;
    transition: all 0.3s ease;
}

.skill-chip:hover {
    background: linear-gradient(135deg, #5B86E5 0%, #36D1DC 100%);
    color: #ffffff;
    transform: translateY(-2px);
    box-shadow: 0 4px 12px rgba(91, 134, 229, 0.3);
}

/* ============ STATS ============ */
.stats-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
    gap: 1.25rem;
    margin: 2rem 0;
}

.stat-card {
    background: linear-gradient(135deg, #ffffff 0%, #f8f9fc 100%);
    border: 1px solid #e8ebf0;
    border-radius: 18px;
    padding: 1.75rem 1.25rem;
    text-align: center;
    box-shadow: 0 2px 10px rgba(0,0,0,0.05);
    transition: all 0.3s ease;
}

.stat-card:hover {
    border-color: #5B86E5;
    transform: translateY(-4px);
    box-shadow: 0 8px 25px rgba(91, 134, 229, 0.15);
}

.stat-value {
    font-size: 2.25rem;
    font-weight: 800;
    background: linear-gradient(135deg, #5B86E5 0%, #36D1DC 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    line-height: 1;
    margin-bottom: 0.5rem;
}

.stat-label {
    font-size: 0.9rem;
    font-weight: 500;
    color: #6c6c8a;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}

/* ============ SCORE BADGES ============ */
.score-badge {
    display: inline-block;
    padding: 0.75rem 1.5rem;
    border-radius: 12px;
    font-size: 1.5rem;
    font-weight: 800;
    box-shadow: 0 4px 15px rgba(0,0,0,0.1);
}

.score-excellent {
    background: linear-gradient(135deg, #10b981 0%, #059669 100%);
    color: #ffffff;
}

.score-good {
    background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%);
    color: #ffffff;
}

.score-fair {
    background: linear-gradient(135deg, #6366f1 0%, #4f46e5 100%);
    color: #ffffff;
}

/* ============ SOURCE BADGE ============ */
.source-badge {
    background: linear-gradient(135deg, #f0f4ff 0%, #e8f0fe 100%);
    color: #5B86E5;
    padding: 0.3rem 0.75rem;
    border-radius: 8px;
    font-size: 0.75rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}

/* ============ COVER LETTER ============ */
.cover-letter-label {
    font-size: 1.1rem;
    font-weight: 700;
    color: #1a1f36;
    margin: 1.5rem 0 1rem;
}

.cover-letter-box {
    background: linear-gradient(135deg, #f8f9fc 0%, #ffffff 100%);
    border: 2px solid #e8ebf0;
    border-radius: 16px;
    padding: 1.75rem;
    margin: 1rem 0;
    line-height: 1.8;
    color: #3d3d56;
    font-size: 0.95rem;
    box-shadow: 0 2px 10px rgba(0,0,0,0.04);
}

/* ============ BUTTONS ============ */
.stButton > button {
    border-radius: 12px !important;
    font-weight: 600 !important;
    transition: all 0.3s ease !important;
    border: none !important;
}

.stButton > button[kind="primary"] {
    background: linear-gradient(135deg, #5B86E5 0%, #36D1DC 100%) !important;
    box-shadow: 0 4px 15px rgba(91, 134, 229, 0.3) !important;
}

.stButton > button[kind="primary"]:hover {
    box-shadow: 0 6px 20px rgba(91, 134, 229, 0.4) !important;
    transform: translateY(-2px) !important;
}

/* ============ DIVIDER ============ */
.divider {
    height: 2px;
    background: linear-gradient(90deg, transparent 0%, #e8ebf0 20%, #e8ebf0 80%, transparent 100%);
    margin: 3rem 0;
}

/* ============ FOOTER ============ */
.footer {
    margin-top: 4rem;
    padding: 2rem;
    text-align: center;
    color: #6c6c8a;
    font-size: 0.9rem;
    border-top: 1px solid #e8ebf0;
    background: linear-gradient(180deg, #ffffff 0%, #f8f9fc 100%);
    border-radius: 20px 20px 0 0;
}

.footer a {
    color: #5B86E5;
    text-decoration: none;
    font-weight: 600;
    transition: all 0.3s ease;
}

.footer a:hover {
    color: #36D1DC;
    text-decoration: underline;
}

/* ============ STREAMLIT OVERRIDES ============ */
.stExpander {
    border: 1px solid #e8ebf0 !important;
    border-radius: 16px !important;
    overflow: hidden !important;
    margin-bottom: 1rem !important;
    transition: all 0.3s ease !important;
}

.stExpander:hover {
    border-color: #5B86E5 !important;
    box-shadow: 0 4px 20px rgba(91, 134, 229, 0.1) !important;
}

.stTextInput > div > div > input,
.stTextArea > div > div > textarea,
.stSelectbox > div > div > select {
    border-radius: 12px !important;
    border: 1px solid #e8ebf0 !important;
}

.stTextInput > div > div > input:focus,
.stTextArea > div > div > textarea:focus,
.stSelectbox > div > div > select:focus {
    border-color: #5B86E5 !important;
    box-shadow: 0 0 0 3px rgba(91, 134, 229, 0.1) !important;
}

/* ============ PROGRESS BAR ============ */
.stProgress > div > div {
    background: linear-gradient(90deg, #5B86E5 0%, #36D1DC 100%) !important;
    border-radius: 10px !important;
}
</style>
""", unsafe_allow_html=True)

# ============================================
# HELPER FUNCTIONS
# ============================================

def load_json(filepath):
    """Load JSON file or return empty dict/list"""
    if not os.path.exists(filepath):
        return {}
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}

def save_json(filepath, data):
    """Save data to JSON file"""
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def strip_html(text):
    """Remove HTML tags from text"""
    if not text:
        return ""
    return re.sub(r'<[^>]+>', '', text)

def build_zip(folder_path):
    """Create ZIP file from folder contents"""
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
        for filename in os.listdir(folder_path):
            filepath = os.path.join(folder_path, filename)
            if os.path.isfile(filepath):
                zf.write(filepath, filename)
    zip_buffer.seek(0)
    return zip_buffer.getvalue()

def find_cover_letter(company, title):
    """Find cover letter file for company/title"""
    if not os.path.exists(LETTERS_DIR):
        return None, None
    
    # Try exact match first
    safe_company = re.sub(r'[^\w\s-]', '', company).strip().replace(' ', '_')
    safe_title = re.sub(r'[^\w\s-]', '', title).strip().replace(' ', '_')
    filename = f"{safe_company}_{safe_title}.txt"
    filepath = os.path.join(LETTERS_DIR, filename)
    
    if os.path.exists(filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            return f.read(), filename
    
    # Try partial matches
    for fname in os.listdir(LETTERS_DIR):
        if fname.endswith('.txt'):
            if safe_company.lower() in fname.lower() and safe_title.lower() in fname.lower():
                filepath = os.path.join(LETTERS_DIR, fname)
                with open(filepath, 'r', encoding='utf-8') as f:
                    return f.read(), fname
    
    return None, None

# ============================================
# FILE PATHS
# ============================================

load_dotenv()

# Use current directory or specify your paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROFILE_FILE = os.path.join(BASE_DIR, "profile.json")
JOBS_FILE = os.path.join(BASE_DIR, "jobs.json")
MATCHES_FILE = os.path.join(BASE_DIR, "matches.json")
CACHE_FILE = os.path.join(BASE_DIR, "cache.json")
LOG_FILE = os.path.join(BASE_DIR, "logs.txt")
LETTERS_DIR = os.path.join(BASE_DIR, "cover_letters")

# Import pipeline function (adjust import based on your structure)
try:
    from run_auto_apply import run_auto_apply_pipeline
except ImportError:
    def run_auto_apply_pipeline(*args, **kwargs):
        return {"status": "error", "message": "Pipeline not found"}

try:
    from cover_letter_generator import generate_cover_letter
except ImportError:
    def generate_cover_letter(*args, **kwargs):
        pass

# ============================================
# HERO SECTION
# ============================================

st.markdown(f"""
<div class="hero">
    <div class="hero-content">
        <h1>🚀 Job AI Search</h1>
        <p class="hero-subtitle">
            Intelligent job matching powered by AI. Upload your resume, set your preferences, 
            and discover opportunities tailored specifically for you.
        </p>
        <div class="hero-tags">
            <span class="hero-tag">🔍 6 Job Sources</span>
            <span class="hero-tag">🤖 AI-Powered Matching</span>
            <span class="hero-tag">📄 Auto Cover Letters</span>
            <span class="hero-tag">🌍 Global + Remote</span>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# ============================================
# STEPPER / PROGRESS INDICATOR
# ============================================

profile = load_json(PROFILE_FILE)
matches = load_json(MATCHES_FILE)

step_states = []
if not profile or not profile.get("skills"):
    step_states = ["active", "pending", "pending"]
elif not matches or not isinstance(matches, list) or len(matches) == 0:
    step_states = ["done", "active", "pending"]
else:
    step_states = ["done", "done", "active"]

st.markdown(f"""
<div class="stepper">
    <div class="step {step_states[0]}">
        <div class="step-icon">{"✓" if step_states[0] == "done" else "1"}</div>
        <span>Your Profile</span>
    </div>
    <div class="step-connector"></div>
    <div class="step {step_states[1]}">
        <div class="step-icon">{"✓" if step_states[1] == "done" else "2"}</div>
        <span>Job Matching</span>
    </div>
    <div class="step-connector"></div>
    <div class="step {step_states[2]}">
        <div class="step-icon">{"✓" if step_states[2] == "done" else "3"}</div>
        <span>Results</span>
    </div>
</div>
""", unsafe_allow_html=True)

# ============================================
# STEP 1: PROFILE INPUT
# ============================================

st.markdown('<div class="glass-card">', unsafe_allow_html=True)
st.markdown(f"""
<div class="card-header">
    <div class="card-icon">👤</div>
    <h2 class="card-title">Step 1: Build Your Profile</h2>
</div>
""", unsafe_allow_html=True)

profile_data = profile if isinstance(profile, dict) else {}

with st.form("profile_form"):
    name = st.text_input("Full Name", value=profile_data.get("name", ""), placeholder="John Doe")
    email = st.text_input("Email", value=profile_data.get("email", ""), placeholder="john@example.com")
    phone = st.text_input("Phone", value=profile_data.get("phone", ""), placeholder="+1 234 567 8900")
    
    col1, col2 = st.columns(2)
    with col1:
        country = st.text_input("Country", value=profile_data.get("country", ""), placeholder="USA")
    with col2:
        city = st.text_input("City", value=profile_data.get("city", ""), placeholder="San Francisco")
    
    skills_input = st.text_area(
        "Skills (comma-separated)", 
        value=", ".join(profile_data.get("skills", [])),
        placeholder="Python, Machine Learning, Data Science, SQL",
        height=100
    )
    
    experience = st.text_area(
        "Experience Summary", 
        value=profile_data.get("experience", ""),
        placeholder="Describe your work experience...",
        height=150
    )
    
    preferences = st.text_area(
        "Job Preferences", 
        value=profile_data.get("preferences", ""),
        placeholder="Remote work, flexible hours, startup culture...",
        height=100
    )
    
    submit_profile = st.form_submit_button("💾 Save Profile", type="primary", use_container_width=True)
    
    if submit_profile:
        skills_list = [s.strip() for s in skills_input.split(",") if s.strip()]
        new_profile = {
            "name": name,
            "email": email,
            "phone": phone,
            "country": country,
            "city": city,
            "skills": skills_list,
            "experience": experience,
            "preferences": preferences,
        }
        save_json(PROFILE_FILE, new_profile)
        st.success("✅ Profile saved successfully!")
        time.sleep(0.5)
        st.rerun()

# Display current skills
if profile_data.get("skills"):
    st.markdown("**Current Skills:**")
    skills_html = '<div class="skills-container">' + ''.join([
        f'<span class="skill-chip">{skill}</span>' 
        for skill in profile_data.get("skills", [])
    ]) + '</div>'
    st.markdown(skills_html, unsafe_allow_html=True)

st.markdown('</div>', unsafe_allow_html=True)

# ============================================
# STEP 2: RUN JOB MATCHING
# ============================================

if profile and profile.get("skills"):
    st.markdown('<div class="glass-card">', unsafe_allow_html=True)
    st.markdown(f"""
    <div class="card-header">
        <div class="card-icon">🎯</div>
        <h2 class="card-title">Step 2: Find Your Perfect Match</h2>
    </div>
    """, unsafe_allow_html=True)
    
    # Only show button if not currently running
    if not st.session_state.get("_matching_running", False):
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
