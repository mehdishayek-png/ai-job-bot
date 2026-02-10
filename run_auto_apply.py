"""
JobBot Matching Engine v8 — HYBRID: Best of Both Worlds
=======================================================
FIXED VERSION - Compatible with existing location_utils.py
"""

import json
import os
import re
import hashlib
import time
import logging
from openai import OpenAI
from dotenv import load_dotenv
from cover_letter_generator import generate_cover_letter
from location_utils import filter_jobs_by_location

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

load_dotenv()
api_key = os.getenv("OPENROUTER_API_KEY")
if not api_key:
    try:
        import streamlit as st
        api_key = st.secrets.get("OPENROUTER_API_KEY")
    except (ImportError, KeyError, AttributeError):
        pass
if not api_key:
    raise ValueError("OPENROUTER_API_KEY not found.")

client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=api_key)

MODEL = os.getenv("SCORING_MODEL", "google/gemini-2.5-flash")
FALLBACK_MODEL = "mistralai/mistral-7b-instruct"
MAX_MATCHES = int(os.getenv("MAX_MATCHES", "25"))
API_RATE_LIMIT = float(os.getenv("API_RATE_LIMIT", "0.5"))
MAX_LLM_CANDIDATES = 50
LLM_BATCH_SIZE = 15
MATCH_THRESHOLD = 35
MAX_PER_COMPANY = 3

SENIOR_MARKERS = [
    "lead", "head of", "head,", "director", "vp ", "vice president",
    "principal", "chief", "cto", "coo", "ceo", "cfo",
    "founding", "co-founder", "partner", "svp", "evp",
    "staff engineer", "staff developer", "distinguished",
]

MID_MARKERS = ["senior", "sr ", "sr.", "manager", "team lead"]


def title_seniority(title):
    t = title.lower()
    if any(m in t for m in SENIOR_MARKERS):
        return "senior"
    if any(m in t for m in MID_MARKERS):
        return "mid"
    return "open"


def estimate_years(profile):
    """HYBRID: Advanced 4-layer experience detection"""
    exp_str = (profile.get("experience", "") or "").strip()
    EXP_MAP = {
        "0–1 years": 0, "0-1 years": 0,
        "1–3 years": 2, "1-3 years": 2,
        "3–6 years": 4, "3-6 years": 4,
        "6–10 years": 7, "6-10 years": 7,
        "10+ years": 12,
    }
    if exp_str in EXP_MAP:
        return EXP_MAP[exp_str]
    
    headline = (profile.get("headline", "") or "").lower()
    m = re.search(r'(\d+)\+?\s*(?:years?|yrs?)', headline)
    if m:
        years = int(m.group(1))
        return min(years, 15)
    
    skill_count = len(profile.get("skills", []))
    
    if any(w in headline for w in ["cto", "ceo", "cfo", "vp ", "vice president", "svp", "evp", "chief", "director", "head of"]):
        return 10
    
    if any(w in headline for w in ["principal", "staff ", "distinguished", "founding", "co-founder"]):
        return 8
    
    if "senior" in headline or "sr " in headline or "sr." in headline:
        if skill_count >= 30:
            return 7
        return 6
    
    if "lead" in headline or "team lead" in headline:
        return 6
    
    if "manager" in headline:
        if "senior manager" in headline or "sr manager" in headline:
            return 8
        if any(w in headline for w in ["project manager", "product manager", "program manager"]):
            return 5
        return 4
    
    if any(w in headline for w in ["architect", "consultant"]):
        if skill_count >= 30:
            return 5
        return 4
    
    if any(w in headline for w in ["specialist", "expert"]):
        if skill_count >= 30:
            return 5
        if skill_count >= 15:
            return 3
        return 2
    
    if any(w in headline for w in ["intern", "trainee", "fresher", "graduate"]):
        return 0
    
    if any(w in headline for w in ["junior", "associate", "jr ", "jr."]):
        return 1
    
    if any(w in headline for w in ["analyst", "coordinator", "assistant"]):
        if skill_count >= 20:
            return 3
        if skill_count >= 10:
            return 2
        return 1
    
    if skill_count >= 40:
        return 7
    if skill_count >= 30:
        return 5
    if skill_count >= 20:
        return 4
    if skill_count >= 10:
        return 2
    
    return 2


TITLE_SYNONYMS = {
    "game designer": ["game designer", "system designer", "level designer", "gameplay designer", "game design", "systems design", "ux designer gaming"],
    "system designer": ["system designer", "game designer", "systems designer", "game systems", "mechanics designer"],
    "construction manager": ["construction manager", "construction supervisor", "project manager", "site manager", "construction lead", "project coordinator", "pm", "construction project manager", "site supervisor", "project engineer"],
    "software engineer": ["software engineer", "software developer", "developer", "engineer", "programmer", "coding engineer", "sde", "application developer"],
    "full stack developer": ["full stack developer", "full stack engineer", "fullstack developer", "web developer", "software engineer", "application developer"],
    "frontend developer": ["frontend developer", "front end developer", "frontend engineer", "ui developer", "web developer", "react developer", "vue developer"],
    "backend developer": ["backend developer", "back end developer", "backend engineer", "server developer", "api developer", "node developer"],
    "devops engineer": ["devops engineer", "devops specialist", "site reliability engineer", "sre", "infrastructure engineer", "cloud engineer", "platform engineer"],
    "data analyst": ["data analyst", "business analyst", "analytics specialist", "data specialist", "analyst", "business intelligence analyst"],
    "data scientist": ["data scientist", "machine learning engineer", "ml engineer", "ai engineer", "data researcher", "research scientist"],
    "data engineer": ["data engineer", "big data engineer", "etl developer", "data pipeline engineer", "analytics engineer"],
    "product manager": ["product manager", "pm", "product owner", "product lead", "product specialist", "technical product manager"],
    "ux designer": ["ux designer", "user experience designer", "ui/ux designer", "product designer", "interaction designer", "ui designer"],
    "graphic designer": ["graphic designer", "visual designer", "designer", "creative designer", "brand designer", "digital designer"],
    "sales manager": ["sales manager", "sales lead", "business development manager", "account manager", "sales director", "revenue manager"],
    "marketing manager": ["marketing manager", "digital marketing manager", "marketing lead", "growth manager", "brand manager", "marketing specialist"],
    "account executive": ["account executive", "sales executive", "business development executive", "ae", "sales representative", "account manager"],
    "customer support": ["customer support", "customer service", "technical support", "support specialist", "help desk", "customer care", "support engineer", "customer success specialist", "client support"],
    "customer success manager": ["customer success manager", "csm", "client success manager", "account success manager", "customer experience manager"],
    "financial analyst": ["financial analyst", "finance analyst", "business analyst", "fp&a analyst", "investment analyst", "credit analyst"],
    "accountant": ["accountant", "accounting specialist", "staff accountant", "senior accountant", "accounts executive", "accounting manager"],
    "operations manager": ["operations manager", "ops manager", "operations lead", "business operations manager", "operational manager"],
    "project coordinator": ["project coordinator", "project assistant", "coordinator", "project specialist", "program coordinator"],
    "office manager": ["office manager", "administrative manager", "office administrator", "operations coordinator", "admin manager"],
    "hr manager": ["hr manager", "human resources manager", "hr lead", "people manager", "talent manager", "hr business partner"],
    "recruiter": ["recruiter", "talent acquisition", "recruitment specialist", "hiring manager", "ta specialist", "technical recruiter"],
    "qa engineer": ["qa engineer", "quality assurance engineer", "test engineer", "sdet", "automation engineer", "qa analyst", "tester"],
    "content writer": ["content writer", "writer", "copywriter", "content creator", "technical writer", "blog writer", "content specialist"],
    "architect": ["architect", "architectural designer", "design architect", "project architect", "senior architect", "chief architect", "solution architect", "technical architect"],
    "civil engineer": ["civil engineer", "structural engineer", "site engineer", "construction engineer", "infrastructure engineer"],
}


def get_title_synonyms(headline):
    headline_lower = headline.lower()
    synonyms = set()
    
    for base_title, synonym_list in TITLE_SYNONYMS.items():
        if base_title in headline_lower:
            synonyms.update(synonym_list)
            for syn in synonym_list:
                words = syn.split()
                synonyms.update(w for w in words if len(w) > 2)
    
    role_keywords = {
        "manager": ["manager", "lead", "supervisor", "head", "director"],
        "engineer": ["engineer", "developer", "programmer", "architect"],
        "analyst": ["analyst", "specialist", "consultant"],
        "designer": ["designer", "creative", "artist"],
        "developer": ["developer", "engineer", "programmer", "coder"],
        "support": ["support", "service", "care", "success"],
        "sales": ["sales", "business development", "account executive"],
    }
    
    for keyword, variants in role_keywords.items():
        if keyword in headline_lower:
            synonyms.update(variants)
    
    return synonyms


def extract_profile_keywords(profile):
    skills = [s.lower().strip() for s in profile.get("skills", []) if s]
    headline = (profile.get("headline", "") or "").lower()

    primary = set()
    for s in skills:
        primary.add(s)

    headline_terms = re.findall(r'[a-z][a-z0-9/\-\.]+(?:\s+[a-z][a-z0-9/\-\.]+)?', headline)
    for term in headline_terms:
        if len(term) > 2:
            primary.add(term.strip())

    expanded = set()
    stop_words = {
        "and", "the", "for", "with", "from", "into", "our", "you", "your",
        "tool", "tools", "using", "used", "based", "related", "across",
        "including", "such", "various", "multiple", "key", "core", "new",
        "high", "low", "top", "best", "good", "main", "major", "full",
    }
    for skill in skills:
        words = skill.split()
        for word in words:
            word = word.strip(".,;:()/-")
            if len(word) > 3 and word not in stop_words:
                expanded.add(word)

    stem_map = {
        "financial": ["finance", "financial"],
        "finance": ["financial", "finance"],
        "analysis": ["analyst", "analytics", "analytical"],
        "analyst": ["analysis", "analytics", "analytical"],
        "analytics": ["analyst", "analysis", "analytical"],
        "operations": ["operational", "ops"],
        "operational": ["operations", "ops"],
        "management": ["manager", "managing"],
        "manager": ["management", "managing"],
        "consulting": ["consultant", "consultancy"],
        "consultant": ["consulting", "consultancy"],
        "marketing": ["market", "marketer"],
        "engineering": ["engineer", "engineers"],
        "engineer": ["engineering", "engineers"],
        "development": ["developer", "developing"],
        "developer": ["development", "developing"],
        "accounting": ["accountant", "accounts"],
        "accountant": ["accounting", "accounts"],
        "strategy": ["strategic", "strategist"],
        "strategic": ["strategy", "strategist"],
        "automation": ["automated", "automate"],
        "data": ["data"],
        "product": ["product"],
        "sales": ["sales"],
        "support": ["support"],
        "technical": ["tech", "technology"],
        "technology": ["tech", "technical"],
    }
    for word in list(expanded):
        if word in stem_map:
            for variant in stem_map[word]:
                expanded.add(variant)

    secondary = expanded - primary
    title_words = set(re.findall(r'\b[a-z]{3,}\b', headline))
    title_words -= stop_words
    title_synonyms = get_title_synonyms(headline)

    return primary, secondary, title_words, title_synonyms


def score_job_locally(job, primary_kw, secondary_kw, title_words, title_synonyms, candidate_years):
    title = job.get("title", "").lower()
    summary = job.get("summary", "").lower()
    company = job.get("company", "").lower()
    tags = " ".join(job.get("tags", [])).lower()
    
    text = f"{title} {summary} {company} {tags}"
    
    score = 0
    matched_primary = set()
    matched_secondary = set()
    matched_title = set()
    matched_synonyms = set()
    
    for kw in primary_kw:
        if kw in text:
            score += 8
            matched_primary.add(kw)
    
    for kw in secondary_kw:
        if kw in text:
            score += 2
            matched_secondary.add(kw)
    
    for tw in title_words:
        if tw in title:
            score += 10
            matched_title.add(tw)
    
    for syn in title_synonyms:
        if syn in title or syn in text:
            score += 12
            matched_synonyms.add(syn)
    
    for kw in primary_kw:
        if kw in company:
            score += 5
    
    job_seniority = title_seniority(title)
    if job_seniority == "senior" and candidate_years < 3:
        score = int(score * 0.3)
    elif job_seniority == "open" and candidate_years >= 8:
        score = int(score * 0.7)
    
    return {
        "score": min(score, 100),
        "primary": list(matched_primary)[:10],
        "secondary": list(matched_secondary)[:10],
        "title": list(matched_title),
        "synonyms": list(matched_synonyms),
    }


def llm_batch_score(jobs, profile, candidate_years):
    if not jobs:
        return []
    
    profile_summary = {
        "headline": profile.get("headline", ""),
        "skills": profile.get("skills", [])[:30],
        "experience_years": candidate_years,
    }
    
    jobs_for_llm = []
    for j in jobs:
        jobs_for_llm.append({
            "id": j.get("id", ""),
            "title": j.get("title", ""),
            "company": j.get("company", ""),
            "summary": j.get("summary", "")[:400],
            "tags": j.get("tags", [])[:10],
        })
    
    prompt = f"""You are a job matching AI. Score how well each job matches this profile.

PROFILE:
{json.dumps(profile_summary, indent=2)}

JOBS TO SCORE:
{json.dumps(jobs_for_llm, indent=2)}

Return ONLY a JSON array of scores (0-100) in the same order as the jobs.
Consider:
- Skill overlap (most important)
- Role alignment with headline
- Experience level match
- Company domain relevance

Example output: [75, 82, 45, 91, ...]
"""
    
    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=500,
        )
        result = response.choices[0].message.content.strip()
        result = re.sub(r'^```json\s*', '', result)
        result = re.sub(r'\s*```$', '', result)
        scores = json.loads(result)
        
        if len(scores) != len(jobs):
            logger.warning(f"LLM returned {len(scores)} scores for {len(jobs)} jobs")
            scores = scores[:len(jobs)] + [50] * (len(jobs) - len(scores))
        
        return [max(0, min(100, int(s))) for s in scores]
    
    except Exception as e:
        logger.error(f"LLM scoring failed with {MODEL}: {e}")
        try:
            response = client.chat.completions.create(
                model=FALLBACK_MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=500,
            )
            result = response.choices[0].message.content.strip()
            result = re.sub(r'^```json\s*', '', result)
            result = re.sub(r'\s*```$', '', result)
            scores = json.loads(result)
            return [max(0, min(100, int(s))) for s in scores][:len(jobs)]
        except Exception as e2:
            logger.error(f"Fallback model also failed: {e2}")
            return [50] * len(jobs)


def is_non_english(title, summary):
    text = f"{title} {summary}".lower()
    if re.search(r'[\u4e00-\u9fff\u3040-\u309f\u30a0-\u30ff\uac00-\ud7af]', text):
        return True
    if re.search(r'[\u0900-\u097f\u0a00-\u0a7f\u0980-\u09ff]', text):
        return True
    return False


def create_job_id(job):
    key = f"{job.get('company','?')}_{job.get('title','?')}_{job.get('source','?')}"
    return hashlib.md5(key.encode()).hexdigest()[:12]


def profile_hash(profile):
    key = f"{profile.get('headline','')}_{','.join(profile.get('skills',[])[:30])}"
    return hashlib.md5(key.encode()).hexdigest()[:12]


def enforce_company_diversity(matches):
    seen = {}
    result = []
    for m in matches:
        company = m.get("company", "Unknown")
        count = seen.get(company, 0)
        if count < MAX_PER_COMPANY:
            result.append(m)
            seen[company] = count + 1
    return result


def run_pipeline(profile_file, jobs_file, session_dir, letters_dir=None,
                 progress_callback=None, prioritize_local_run=False):
    
    if progress_callback:
        progress_callback("🚀 Starting HYBRID pipeline...")
    
    with open(profile_file, "r", encoding="utf-8") as f:
        profile = json.load(f)
    
    candidate_years = estimate_years(profile)
    
    if progress_callback:
        progress_callback(f"👤 Profile loaded: ~{candidate_years} years experience")
    
    logger.info(f"Profile: {profile.get('headline', '?')} — {candidate_years} years")
    
    if progress_callback:
        progress_callback("📡 Loading jobs from all sources...")
    
    with open(jobs_file, "r", encoding="utf-8") as f:
        all_jobs = json.load(f)
    
    total_unique = len(all_jobs)
    logger.info(f"Loaded {total_unique} unique jobs")
    
    if progress_callback:
        progress_callback(f"📊 Loaded {total_unique} unique jobs from all sources")
    
    # FIXED: Use simple location filter that matches your location_utils.py
    if progress_callback:
        progress_callback("🌍 Applying location filters...")
    
    # Get user's location preferences (list like ["americas", "asia", "global"])
    user_preferences = profile.get("location_preferences", ["global"])
    
    # Call filter with correct signature
    jobs = filter_jobs_by_location(all_jobs, user_preferences)
    
    logger.info(f"Location filter: {len(jobs)} jobs match preferences {user_preferences}")
    
    if progress_callback:
        progress_callback(f"🌍 Location filter: {len(jobs)} jobs match your preferences")
    
    if not jobs:
        logger.warning("No jobs passed location filter")
        if progress_callback:
            progress_callback("⚠️ No jobs match your location preferences")
        return [], total_unique
    
    # Get country for local boost (separate from location filter)
    user_country = profile.get("country", "").strip()
    user_country_lc = user_country.lower() if user_country else ""
    country_aliases = []
    if user_country_lc == "india":
        country_aliases = ["india", "indian", "bangalore", "bengaluru", "mumbai", 
                          "delhi", "hyderabad", "pune", "chennai"]
    
    if progress_callback:
        progress_callback("🎯 Building keyword profile with semantic title matching...")
    
    primary_kw, secondary_kw, title_words, title_synonyms = extract_profile_keywords(profile)
    
    logger.info(f"Keywords: {len(primary_kw)} primary, {len(secondary_kw)} secondary, "
                f"{len(title_words)} title words, {len(title_synonyms)} title synonyms")
    
    skill_count = len(profile.get("skills", []))
    
    if progress_callback:
        progress_callback(f"🎯 Phase 1: Keyword matching ({skill_count} skills + {len(title_synonyms)} title synonyms)...")
    
    scored_jobs = []
    
    for idx, job in enumerate(jobs):
        if idx > 0 and idx % 50 == 0 and progress_callback:
            progress_callback(f"⚡ Analyzing job {idx}/{len(jobs)}... ({len(scored_jobs)} matches so far)")
        
        title = job.get("title", "")
        summary = job.get("summary", "")
        
        if is_non_english(title, summary):
            continue
        
        if candidate_years < 3 and title_seniority(title) == "senior":
            continue
        
        local = score_job_locally(job, primary_kw, secondary_kw, title_words, 
                                  title_synonyms, candidate_years)
        
        if local["score"] >= MATCH_THRESHOLD:
            job["_local_score"] = local["score"]
            job["_local_detail"] = local
            scored_jobs.append(job)
    
    scored_jobs.sort(key=lambda j: j.get("_local_score", 0), reverse=True)
    
    logger.info(f"Phase 2: {len(scored_jobs)} jobs passed keyword threshold ({MATCH_THRESHOLD})")
    
    if progress_callback:
        progress_callback(f"✅ Phase 1 complete: {len(scored_jobs)} relevant jobs")
    
    if not scored_jobs:
        logger.info("Zero keyword matches — retrying with threshold=20")
        if progress_callback:
            progress_callback("Keywords too specific — broadening search...")
        
        for job in jobs:
            title = job.get("title", "")
            summary = job.get("summary", "")
            if is_non_english(title, summary):
                continue
            if candidate_years < 3 and title_seniority(title) == "senior":
                continue
            
            local = score_job_locally(job, primary_kw, secondary_kw, title_words,
                                     title_synonyms, candidate_years)
            if local["score"] >= 20:
                job["_local_score"] = local["score"]
                job["_local_detail"] = local
                scored_jobs.append(job)
        
        scored_jobs.sort(key=lambda j: j.get("_local_score", 0), reverse=True)
        logger.info(f"Fallback: {len(scored_jobs)} jobs passed at threshold=20")
        
        if progress_callback:
            progress_callback(f"Broadened search: {len(scored_jobs)} candidates for AI")
    
    if not scored_jobs:
        if progress_callback:
            progress_callback("No relevant jobs found. Your profile may be too niche for these job boards.")
        return [], total_unique
    
    top_candidates = scored_jobs[:MAX_LLM_CANDIDATES]
    
    if progress_callback:
        progress_callback(f"🤖 Phase 2: AI ranking top {len(top_candidates)} candidates...")
    
    p_hash = profile_hash(profile)
    cache_file = os.path.join(session_dir, "semantic_cache.json")
    cache = {}
    if os.path.exists(cache_file):
        try:
            if os.path.getsize(cache_file) < 10 * 1024 * 1024:
                with open(cache_file, "r", encoding="utf-8") as f:
                    cache = json.load(f)
        except Exception:
            pass
    
    uncached = []
    cached_results = []
    for job in top_candidates:
        jid = create_job_id(job)
        ck = f"v8_{p_hash}_{jid}"
        job["_cache_key"] = ck
        if ck in cache:
            cached_results.append((job, cache[ck]))
        else:
            uncached.append(job)
    
    logger.info(f"Cache: {len(cached_results)} hits, {len(uncached)} to score")
    
    api_calls = 0
    scored_results = []
    
    for i in range(0, len(uncached), LLM_BATCH_SIZE):
        batch = uncached[i:i + LLM_BATCH_SIZE]
        bn = i // LLM_BATCH_SIZE + 1
        tb = (len(uncached) + LLM_BATCH_SIZE - 1) // LLM_BATCH_SIZE
        
        if progress_callback:
            progress_callback(f"🧠 AI Batch {bn}/{tb}: Scoring {len(batch)} jobs...")
        
        scores = llm_batch_score(batch, profile, candidate_years)
        api_calls += 1
        
        avg_score = sum(scores) // len(scores) if scores else 0
        
        for job, llm_score in zip(batch, scores):
            local_score = job.get("_local_score", 0)
            combined = int(local_score * 0.4 + llm_score * 0.6)
            
            # LOCAL JOB BOOST
            source = job.get("source", "").lower()
            PRIORITY_SOURCES = {"google jobs", "indeed", "naukri", "linkedin", 
                              "instahyre", "foundit", "glassdoor"}
            priority_boost = 10 if prioritize_local_run else 5
            if source in PRIORITY_SOURCES:
                combined = min(combined + priority_boost, 100)
            
            if user_country_lc and user_country_lc != "remote only":
                job_text = f"{job.get('title','')} {job.get('summary','')} {job.get('source','')}".lower()
                if user_country_lc in job_text or any(alias in job_text for alias in country_aliases):
                    combined = min(combined + 8, 100)
            
            ck = job.get("_cache_key", "")
            if ck:
                cache[ck] = combined
            scored_results.append((job, combined))
            
            logger.info(f"  {job.get('company','?')[:20]}: {job.get('title','?')[:35]} "
                       f"→ local={local_score}, llm={llm_score}, combined={combined}")
        
        if progress_callback:
            progress_callback(f"✓ Batch {bn} complete - avg score: {avg_score}%")
        
        if i + LLM_BATCH_SIZE < len(uncached):
            time.sleep(API_RATE_LIMIT)
    
    all_results = []
    for job, cached_score in cached_results:
        all_results.append((job, cached_score))
    all_results.extend(scored_results)
    
    if progress_callback:
        progress_callback("🎯 Phase 3: Filtering and ranking final matches...")
    
    for threshold in [55, 50, 45]:
        matches = []
        for job, score in all_results:
            if score >= threshold:
                m = job.copy()
                m.pop("_local_score", None)
                m.pop("_local_detail", None)
                m.pop("_cache_key", None)
                m["match_score"] = score
                matches.append(m)
        
        if matches:
            logger.info(f"Threshold {threshold} yielded {len(matches)} matches")
            break
        else:
            logger.info(f"Threshold {threshold} yielded 0 — trying lower")
    
    matches.sort(key=lambda x: x["match_score"], reverse=True)
    matches = enforce_company_diversity(matches)
    matches = matches[:MAX_MATCHES]
    
    logger.info(f"Final: {len(matches)} matches from {len(top_candidates)} candidates ({api_calls} API calls)")
    
    if progress_callback:
        progress_callback(f"✅ Complete! {len(matches)} top matches ready ({api_calls} API calls used)")
    
    os.makedirs(session_dir, exist_ok=True)
    try:
        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump(cache, f, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Cache save: {e}")
    
    return matches, total_unique


def run_auto_apply_pipeline(profile_file=None, jobs_file=None, matches_file=None,
                            cache_file=None, log_file=None, letters_dir=None,
                            progress_callback=None):
    try:
        if progress_callback:
            progress_callback("Starting HYBRID pipeline...")
        
        session_dir = os.path.dirname(profile_file)
        matches, total = run_pipeline(
            profile_file=profile_file, jobs_file=jobs_file,
            session_dir=session_dir, letters_dir=letters_dir,
            progress_callback=progress_callback,
        )
        
        if matches_file:
            os.makedirs(os.path.dirname(matches_file) or ".", exist_ok=True)
            with open(matches_file, "w", encoding="utf-8") as f:
                json.dump(matches, f, indent=2, ensure_ascii=False)
        
        if progress_callback:
            progress_callback(f"Done — {len(matches)} matches from {total} jobs.")
        
        if not matches:
            return {"status": "no_matches", "matches": 0, "total_scored": total}
        return {"status": "success", "matches": len(matches), "total_scored": total}
    
    except Exception as e:
        logger.exception("Pipeline error")
        if progress_callback:
            progress_callback(f"Error: {e}")
        return {"status": "error", "message": str(e)}


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 3:
        print("Usage: python run_auto_apply.py <profile.json> <jobs.json>")
        sys.exit(1)
    try:
        matches, total = run_pipeline(sys.argv[1], sys.argv[2], "data/test_session")
        print(f"\n✅ {len(matches)} matches from {total} jobs")
        for i, j in enumerate(matches, 1):
            print(f"  {i}. [{j['match_score']}%] {j['company']} — {j['title']}")
    except Exception as e:
        print(f"\n❌ {e}")
        sys.exit(1)
