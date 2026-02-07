"""
JobBot Matching Engine v7 — PHASE 1: Location Filtering Added
==============================================================
New in this version:
- Location/timezone filtering based on user preferences
- Works with existing remote job sources (no API changes needed)
- Filters jobs before keyword matching for better performance

Previous version (v6):
1. Extract strong keywords from profile (skills + headline + role terms)
2. Score ALL jobs locally by keyword overlap — zero API calls
3. Only send top 30 to LLM as a SINGLE batch for final ranking
4. Enforce seniority gate + company diversity

Cost: 1-3 API calls total (was 162)
Quality: keyword matching is deterministic and accurate for this use case
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

# ============================================
# NEW: Import location utilities
# ============================================
from location_utils import filter_jobs_by_location

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ============================================
# API CLIENT
# ============================================

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

# ============================================
# CONFIG
# ============================================

# Gemini 2.0 Flash: $0.10/M input, $0.40/M output — scoring 30 jobs costs ~$0.001
# Falls back to mistral if gemini fails
MODEL = os.getenv("SCORING_MODEL", "google/gemini-2.5-flash")
FALLBACK_MODEL = "mistralai/mistral-7b-instruct"
MAX_MATCHES = int(os.getenv("MAX_MATCHES", "25"))
API_RATE_LIMIT = float(os.getenv("API_RATE_LIMIT", "0.5"))
MAX_LLM_CANDIDATES = 50  # Send more to LLM — Gemini is cheap and fast
LLM_BATCH_SIZE = 15      # Gemini Flash handles 15 jobs per call easily
MATCH_THRESHOLD = 35      # Local score threshold — be generous, let LLM decide
MAX_PER_COMPANY = 3       # Company diversity cap


# ============================================
# SENIORITY
# ============================================

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
    """Get years of experience — prefer user-selected value, fallback to headline parsing."""
    # User-selected experience (from dropdown)
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

    # Fallback: parse from headline
    headline = (profile.get("headline", "") or "").lower()
    m = re.search(r'(\d+)\+?\s*(?:years?|yrs?)', headline)
    if m:
        return int(m.group(1))
    if any(w in headline for w in ["intern", "trainee", "fresher"]):
        return 0
    if any(w in headline for w in ["junior", "associate", "jr "]):
        return 1
    if any(w in headline for w in ["specialist", "analyst", "coordinator"]):
        return 2
    if any(w in headline for w in ["consultant"]):
        return 2
    if any(w in headline for w in ["senior", "sr ", "lead", "manager"]):
        return 5
    if any(w in headline for w in ["director", "head of", "vp "]):
        return 10
    return 2


# ============================================
# KEYWORD EXTRACTION FROM PROFILE
# ============================================

def extract_profile_keywords(profile):
    """
    Build a rich keyword set from the profile for local matching.
    Returns (primary_keywords, secondary_keywords, title_words).

    Primary = specific tools/platforms/domains (high signal)
    Secondary = general professional terms (lower signal)
    Title = words from headline for title matching
    """
    skills = [s.lower().strip() for s in profile.get("skills", []) if s]
    headline = (profile.get("headline", "") or "").lower()

    # Primary: specific, high-signal terms (exact multi-word matches)
    primary = set()
    for s in skills:
        primary.add(s)

    # Also extract key terms from headline
    headline_terms = re.findall(r'[a-z][a-z0-9/\-\.]+(?:\s+[a-z][a-z0-9/\-\.]+)?', headline)
    for term in headline_terms:
        if len(term) > 2:
            primary.add(term.strip())

    # ---- NEW: Expand keywords for broader matching ----
    # Break multi-word skills into individual meaningful words
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

    # Add stem variants (common professional term expansions)
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

    # Add expanded terms to primary (they're lower signal but still useful)
    # We keep them separate so the scoring can weight them differently
    primary_expanded = primary | expanded

    # Secondary: broader terms that indicate general relevance
    secondary = set()
    domain_terms = [
        # General professional
        "support", "operations", "management", "integration", "consulting",
        "technical", "implementation", "automation", "monitoring",
        "troubleshooting", "analyst", "coordinator", "specialist",
        "customer", "service", "incident", "process", "system",
        # Supply chain / ops
        "order", "fulfillment", "warehouse", "supply chain", "logistics",
        "erp", "crm", "saas", "cloud", "api", "testing",
        # Finance / business
        "finance", "financial", "accounting", "audit", "budget",
        "revenue", "reporting", "compliance", "risk", "advisory",
        "due diligence", "valuation", "forecasting", "modeling",
        "excel", "powerbi", "tableau", "sql", "python",
        # Sales / marketing
        "sales", "marketing", "outreach", "campaigns", "analytics",
        # General IT
        "software", "application", "network", "database", "server",
    ]
    for term in domain_terms:
        if term in headline or any(term in s for s in skills):
            secondary.add(term)

    # Title words: meaningful words from headline for title matching
    title_words = set()
    title_word_pattern = re.findall(r'\b[a-z]{3,}\b', headline)
    for word in title_word_pattern:
        if word not in stop_words and len(word) > 2:
            title_words.add(word)

    return primary_expanded, secondary, title_words


# ============================================
# NON-ENGLISH FILTER
# ============================================

def is_non_english(title, summary):
    text = (title + " " + summary).lower()
    non_eng_indicators = [
        "español", "português", "français", "deutsch", "italiano",
        "русский", "中文", "日本語", "한국어", "العربية",
        "język", "idioma", "lingua", "sprache",
    ]
    return any(ind in text for ind in non_eng_indicators)


# ============================================
# LOCAL KEYWORD SCORING
# ============================================

def score_job_locally(job, primary_kw, secondary_kw, title_words, candidate_years):
    title = job.get("title", "").lower()
    summary = job.get("summary", "").lower()
    combined = title + " " + summary

    score = 0
    matched_primary = []
    matched_secondary = []

    # Primary keywords (exact or expanded matches)
    for kw in primary_kw:
        if kw in combined:
            matched_primary.append(kw)
            # Weight by keyword length (longer = more specific)
            if len(kw) > 10:
                score += 12
            elif len(kw) > 6:
                score += 8
            else:
                score += 5

    # Secondary keywords (bonus for domain relevance)
    for kw in secondary_kw:
        if kw in combined:
            matched_secondary.append(kw)
            score += 2

    # Title word bonus (job title alignment)
    title_match_count = sum(1 for w in title_words if w in title)
    if title_match_count >= 2:
        score += 8
    elif title_match_count == 1:
        score += 4

    # Seniority alignment bonus
    job_seniority = title_seniority(title)
    if job_seniority == "open":
        score += 5  # Prefer open roles
    elif job_seniority == "mid" and candidate_years >= 2:
        score += 3
    elif job_seniority == "senior" and candidate_years >= 5:
        score += 0  # Neutral (not penalized but not bonus)

    return {
        "score": min(score, 100),
        "primary_matches": matched_primary[:5],
        "secondary_matches": matched_secondary[:3],
        "title_overlap": title_match_count,
    }


# ============================================
# LLM BATCH SCORING
# ============================================

def llm_batch_score(batch, profile, candidate_years):
    skills_str = ", ".join(profile.get("skills", [])[:15])
    headline = profile.get("headline", "Professional")
    industry = profile.get("industry", "")
    
    jobs_text = "\n\n".join([
        f"JOB {i+1}:\nTitle: {j.get('title', '?')}\nCompany: {j.get('company', '?')}\n"
        f"Summary: {j.get('summary', '')[:300]}"
        for i, j in enumerate(batch)
    ])

    industry_note = f"\n- Industry: {industry}" if industry else ""

    prompt = f"""You are a job matching expert. Score these {len(batch)} jobs for this candidate.

Candidate profile:
- Headline: {headline}{industry_note}
- Skills: {skills_str}
- Experience: ~{candidate_years} years

Jobs to score:
{jobs_text}

SCORING RULES (0-100):
- 80-100: Strong match — same industry, relevant title, skills overlap significantly
- 60-79: Good match — related role, some skills overlap, could be a stretch but realistic
- 40-59: Weak match — tangentially related, different industry or role type
- 0-39: No match — completely different field, wrong seniority, or unrelated skills

IMPORTANT:
- A "{headline}" should NOT match "Software Engineer", "Data Engineer", "DevOps" roles unless the skills specifically align
- Consider the candidate's INDUSTRY ({industry or 'general'}) — a fintech ops person should match fintech/payments jobs, not healthcare or construction
- Score based on whether the candidate would ACTUALLY apply and be considered, not just keyword overlap

Return ONLY a JSON array of {len(batch)} integers, nothing else.
Example: [75, 60, 45, 90, ...]

Scores:"""

    try:
        res = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            max_tokens=200,
        )
        
        response_text = res.choices[0].message.content.strip()
        response_text = re.sub(r'^```(?:json)?\s*', '', response_text)
        response_text = re.sub(r'\s*```$', '', response_text)
        
        scores = json.loads(response_text)
        
        if not isinstance(scores, list):
            raise ValueError(f"Expected list, got {type(scores)}")
        if len(scores) != len(batch):
            logger.warning(f"LLM returned {len(scores)} scores, expected {len(batch)}")
            scores = scores[:len(batch)] + [0] * (len(batch) - len(scores))
        
        return [max(0, min(100, int(s))) for s in scores]
    
    except json.JSONDecodeError as e:
        logger.error(f"LLM JSON parse error: {e}. Response: {response_text[:200]}")
        return [50] * len(batch)
    except Exception as e:
        logger.error(f"LLM scoring error: {e}")
        
        # Try fallback model
        try:
            logger.info(f"Retrying with fallback model: {FALLBACK_MODEL}")
            res = client.chat.completions.create(
                model=FALLBACK_MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=0,
                max_tokens=200,
            )
            
            response_text = res.choices[0].message.content.strip()
            response_text = re.sub(r'^```(?:json)?\s*', '', response_text)
            response_text = re.sub(r'\s*```$', '', response_text)
            scores = json.loads(response_text)
            
            if len(scores) != len(batch):
                scores = scores[:len(batch)] + [0] * (len(batch) - len(scores))
            
            return [max(0, min(100, int(s))) for s in scores]
        
        except Exception as e2:
            logger.error(f"Fallback model also failed: {e2}")
            return [0] * len(batch)


# ============================================
# UTILITIES
# ============================================

def create_job_id(job):
    raw = "|".join([job.get("company", ""), job.get("title", ""), job.get("apply_url", "")[:100]])
    return hashlib.md5(raw.encode()).hexdigest()[:16]

def profile_hash(profile):
    relevant = {"name": profile.get("name", ""), "headline": profile.get("headline", ""),
                "skills": sorted(profile.get("skills", []))}
    return hashlib.md5(json.dumps(relevant, sort_keys=True).encode()).hexdigest()

def deduplicate_jobs(jobs):
    seen = set()
    unique = []
    for job in jobs:
        key = (job.get("company", "").lower().strip(), job.get("title", "").lower().strip())
        if key not in seen and key != ("", ""):
            seen.add(key)
            unique.append(job)
    logger.info(f"Deduplicated {len(jobs)} → {len(unique)}")
    return unique

def enforce_company_diversity(matches):
    company_count = {}
    diverse = []
    for m in matches:
        co = m.get("company", "Unknown").lower().strip()
        company_count[co] = company_count.get(co, 0) + 1
        if company_count[co] <= MAX_PER_COMPANY:
            diverse.append(m)
    return diverse


# ============================================
# PIPELINE
# ============================================

def run_pipeline(profile_file, jobs_file, session_dir, letters_dir=None, progress_callback=None):
    if not os.path.exists(profile_file):
        raise FileNotFoundError(f"Profile not found: {profile_file}")

    with open(profile_file, "r", encoding="utf-8") as f:
        profile = json.load(f)

    candidate_years = estimate_years(profile)
    logger.info(f"Profile: {profile.get('name', '?')} — {len(profile.get('skills', []))} skills, ~{candidate_years}yr")
    if progress_callback:
        progress_callback(f"Profile loaded: ~{candidate_years} years experience")

    # ---- User's country for location-aware scoring ----
    user_country = (profile.get("country", "") or "").strip()
    user_country_lc = user_country.lower()
    # Aliases: common alternate names for countries in job postings
    COUNTRY_ALIASES = {
        "india": ["india", "bangalore", "bengaluru", "mumbai", "delhi", "hyderabad", "pune", "chennai", "noida", "gurgaon", "gurugram", "kolkata"],
        "united states": ["united states", "usa", "us-based", "u.s."],
        "united kingdom": ["united kingdom", "uk", "london", "england"],
        "canada": ["canada", "toronto", "vancouver"],
        "germany": ["germany", "berlin", "munich", "deutschland"],
        "australia": ["australia", "sydney", "melbourne"],
        "uae": ["uae", "dubai", "abu dhabi", "united arab emirates"],
        "saudi arabia": ["saudi arabia", "saudi", "riyadh", "jeddah", "ksa"],
        "singapore": ["singapore"],
        "netherlands": ["netherlands", "amsterdam", "dutch"],
        "france": ["france", "paris"],
        "ireland": ["ireland", "dublin"],
    }
    country_aliases = COUNTRY_ALIASES.get(user_country_lc, [user_country_lc] if user_country_lc else [])
    
    # Also add state/city to aliases for finer location matching
    user_state = (profile.get("state", "") or "").strip()
    if user_state and user_state != "Any":
        import re as _re
        city_match = _re.search(r'\(([^)]+)\)', user_state)
        if city_match:
            for city in city_match.group(1).split("/"):
                city = city.strip().lower()
                if city and city not in country_aliases:
                    country_aliases.append(city)
        else:
            state_lc = user_state.lower()
            if state_lc not in country_aliases:
                country_aliases.append(state_lc)
    
    logger.info(f"User country: {user_country}, state: {user_state} (aliases: {country_aliases[:5]}...)")

    # ---- Fetch jobs if needed ----
    if not os.path.exists(jobs_file):
        if progress_callback:
            progress_callback("Fetching jobs from all sources (including Google Jobs, Lever)...")
        from job_fetcher import fetch_all, build_serpapi_queries

        # Generate profile-based SerpAPI queries for India-focused search
        serpapi_queries = build_serpapi_queries(profile)
        logger.info(f"SerpAPI queries: {[q['q'] for q in serpapi_queries]}")

        fetch_all(output_path=jobs_file, serpapi_queries=serpapi_queries)

    with open(jobs_file, "r", encoding="utf-8") as f:
        jobs = json.load(f)
    if not jobs:
        return [], 0

    jobs = deduplicate_jobs(jobs)
    total_unique = len(jobs)
    if progress_callback:
        progress_callback(f"Loaded {total_unique} unique jobs")

    # ============================================
    # NEW: Filter by location preferences (Phase 1)
    # ============================================
    location_prefs = profile.get("location_preferences", ["global"])
    
    # If user has location preferences, filter jobs
    if location_prefs and location_prefs != ["global"]:
        jobs_before = len(jobs)
        jobs = filter_jobs_by_location(jobs, location_prefs)
        jobs_after = len(jobs)
        
        logger.info(f"Location filter: {jobs_before} → {jobs_after} jobs (preferences: {location_prefs})")
        if progress_callback:
            progress_callback(f"Location filter: {jobs_after} jobs match your region preferences")
    else:
        logger.info("No location filtering (user prefers global)")

    # ---- Extract keywords from profile ----
    primary_kw, secondary_kw, title_words = extract_profile_keywords(profile)
    logger.info(f"Keywords — primary: {len(primary_kw)}, secondary: {len(secondary_kw)}, title: {len(title_words)}")
    logger.info(f"Primary keywords: {sorted(primary_kw)[:15]}")
    if progress_callback:
        progress_callback(f"Matching against {len(primary_kw)} primary keywords...")

    # ---- Phase 1: Local keyword scoring (0 API calls) ----
    scored_jobs = []
    filtered_stats = {"non_english": 0, "too_senior": 0, "low_score": 0, "passed": 0}

    for job in jobs:
        title = job.get("title", "")
        summary = job.get("summary", "")

        if is_non_english(title, summary):
            filtered_stats["non_english"] += 1
            continue

        # Hard seniority kill
        if candidate_years < 3 and title_seniority(title) == "senior":
            filtered_stats["too_senior"] += 1
            continue

        local = score_job_locally(job, primary_kw, secondary_kw, title_words, candidate_years)

        if local["score"] < MATCH_THRESHOLD:
            filtered_stats["low_score"] += 1
            continue

        job["_local_score"] = local["score"]
        job["_local_detail"] = local
        scored_jobs.append(job)
        filtered_stats["passed"] += 1

    # Sort by local score
    scored_jobs.sort(key=lambda j: j.get("_local_score", 0), reverse=True)

    logger.info(f"Phase 1 (local): {total_unique} → {filtered_stats['passed']} passed "
                f"({filtered_stats['too_senior']} seniority, {filtered_stats['low_score']} low score, "
                f"{filtered_stats['non_english']} non-English)")
    if progress_callback:
        progress_callback(
            f"Keyword matching: {filtered_stats['passed']} relevant jobs found "
            f"({filtered_stats['too_senior']} too senior, {filtered_stats['low_score']} filtered)"
        )

    if not scored_jobs:
        # Fallback: if keyword matching is too strict, lower threshold and try again
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
            local = score_job_locally(job, primary_kw, secondary_kw, title_words, candidate_years)
            if local["score"] >= 20:  # Very low bar — let LLM decide
                job["_local_score"] = local["score"]
                job["_local_detail"] = local
                scored_jobs.append(job)
        scored_jobs.sort(key=lambda j: j.get("_local_score", 0), reverse=True)
        logger.info(f"Fallback: {len(scored_jobs)} jobs passed at threshold=20")
        if progress_callback:
            progress_callback(f"Broadened search: {len(scored_jobs)} candidates for LLM")

    if not scored_jobs:
        if progress_callback:
            progress_callback("No relevant jobs found. Your profile may be too niche for these job boards.")
        return [], total_unique

    # ---- Phase 2: LLM scoring for top candidates only ----
    top_candidates = scored_jobs[:MAX_LLM_CANDIDATES]

    if progress_callback:
        progress_callback(f"Sending top {len(top_candidates)} to LLM for final scoring...")

    # Cache
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

    # Separate cached vs uncached
    uncached = []
    cached_results = []
    for job in top_candidates:
        jid = create_job_id(job)
        ck = f"v6_{p_hash}_{jid}"
        job["_cache_key"] = ck
        if ck in cache:
            cached_results.append((job, cache[ck]))
        else:
            uncached.append(job)

    logger.info(f"Cache: {len(cached_results)} hits, {len(uncached)} to score")

    # Batch score uncached
    api_calls = 0
    scored_results = []
    for i in range(0, len(uncached), LLM_BATCH_SIZE):
        batch = uncached[i:i + LLM_BATCH_SIZE]
        bn = i // LLM_BATCH_SIZE + 1
        tb = (len(uncached) + LLM_BATCH_SIZE - 1) // LLM_BATCH_SIZE

        if progress_callback:
            titles = [f"{j.get('company','?')[:15]}: {j.get('title','?')[:30]}" for j in batch]
            progress_callback(f"Batch {bn}/{tb}: {', '.join(titles)}")

        scores = llm_batch_score(batch, profile, candidate_years)
        api_calls += 1

        for job, llm_score in zip(batch, scores):
            # Combine local + LLM scores (40% local, 60% LLM)
            # LLM gets more weight since local threshold is now generous
            local_score = job.get("_local_score", 0)
            combined = int(local_score * 0.4 + llm_score * 0.6)

            # Source priority boost: jobs from local job boards get +5
            # These are more likely to be relevant, recently posted, and actually hiring
            source = job.get("source", "").lower()
            PRIORITY_SOURCES = {"google jobs", "indeed", "naukri", "linkedin", "instahyre", "foundit", "glassdoor"}
            if source in PRIORITY_SOURCES:
                combined = min(combined + 5, 100)

            # Location boost: +8 if job mentions user's country or state/city
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
            progress_callback(f"  → LLM scores: [{', '.join(str(s) for s in scores)}]")

        if i + LLM_BATCH_SIZE < len(uncached):
            time.sleep(API_RATE_LIMIT)

    # Also add combined scores for cached results
    all_results = []
    for job, cached_score in cached_results:
        all_results.append((job, cached_score))
    all_results.extend(scored_results)

    # ---- Phase 3: Filter, diversify, sort ----
    # Adaptive threshold: try 55, then 50, then 45 to ensure we always return something
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
        progress_callback(f"✅ {len(matches)} matches found ({api_calls} API calls)")

    # ---- Save cache ----
    os.makedirs(session_dir, exist_ok=True)
    try:
        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump(cache, f, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Cache save: {e}")

    # ---- Cover letters ----
    # NOTE: Cover letters are no longer auto-generated in the pipeline
    # They're generated on-demand when user clicks "Generate Cover Letters" in UI
    # This saves API costs and gives users control over when/which letters to generate

    return matches, total_unique


# ============================================
# STREAMLIT WRAPPER
# ============================================

def run_auto_apply_pipeline(profile_file=None, jobs_file=None, matches_file=None,
                            cache_file=None, log_file=None, letters_dir=None,
                            progress_callback=None):
    try:
        if progress_callback:
            progress_callback("Starting pipeline...")

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
