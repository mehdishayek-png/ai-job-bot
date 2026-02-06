"""
JobBot Matching Engine v6 — Keyword-First Approach
====================================================
Previous versions relied on Mistral 7B to score every job individually.
Result: 162 API calls, 2 garbage matches (Java Developer for an Oracle OMS consultant).

New approach:
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
        "sales", "marketing", "growth", "strategy", "business development",
        "pipeline", "lead generation", "market research",
        # Data
        "data", "analytics", "insights", "dashboard", "metrics",
        "kpi", "visualization", "database",
        # Product / project
        "product", "project", "agile", "scrum", "roadmap",
        "stakeholder", "cross-functional",
    ]
    all_skill_text = " ".join(skills) + " " + headline
    for term in domain_terms:
        if term in all_skill_text:
            secondary.add(term)

    # Title words for headline-to-title matching
    title_words = set(w for w in headline.split() if len(w) > 2)
    noise = {"and", "the", "for", "with", "from", "into", "our", "you", "your"}
    title_words -= noise

    return primary_expanded, secondary, title_words


# ============================================
# LOCAL KEYWORD SCORING (NO LLM)
# ============================================

def score_job_locally(job, primary_kw, secondary_kw, title_words, candidate_years):
    """
    Score a job purely by keyword overlap. Returns 0-100.

    Scoring breakdown:
    - Primary keyword hits: up to 50 points
    - Secondary keyword hits: up to 20 points
    - Title-headline overlap: up to 20 points
    - Seniority match: up to 10 points (or penalty)
    """
    title = (job.get("title", "") or "").lower()
    summary = (job.get("summary", "") or "").lower()
    job_text = f"{title} {summary}"

    # ---- Primary keyword hits (0-50) ----
    primary_hits = 0
    matched_primary = []
    for kw in primary_kw:
        if kw in job_text:
            primary_hits += 1
            matched_primary.append(kw)

    if not primary_kw:
        primary_score = 0
    else:
        # 1 hit=15, 2=28, 3=38, 4=45, 5+=50
        primary_score = min(50, primary_hits * 15 - max(0, (primary_hits - 1) * 5))
        primary_score = max(0, primary_score)

    # ---- Secondary keyword hits (0-25) ----
    secondary_hits = sum(1 for kw in secondary_kw if kw in job_text)
    secondary_score = min(25, secondary_hits * 6)

    # ---- Title-headline overlap (0-20) ----
    title_tokens = set(w for w in title.split() if len(w) > 2)
    title_tokens -= {"and", "the", "for", "with", "remote", "hybrid", "onsite"}
    overlap = len(title_words & title_tokens)
    title_score = min(20, overlap * 8)

    # ---- Seniority (0 to 10, or negative) ----
    job_seniority = title_seniority(title)
    if job_seniority == "senior" and candidate_years < 5:
        seniority_score = -30  # Hard penalty
    elif job_seniority == "mid" and candidate_years < 2:
        seniority_score = -15
    elif job_seniority == "open":
        seniority_score = 5   # Slight boost for matching seniority
    else:
        seniority_score = 10  # Good match

    total = primary_score + secondary_score + title_score + seniority_score
    total = max(0, min(100, total))

    return {
        "score": total,
        "primary_hits": primary_hits,
        "matched_primary": matched_primary[:5],  # For debugging
        "secondary_hits": secondary_hits,
        "title_overlap": overlap,
        "seniority": job_seniority,
    }


# ============================================
# NON-ENGLISH FILTER
# ============================================

NON_ENGLISH_MARKERS = [
    "(m/w/d)", "vollzeit", "teilzeit", "praktikum",
    "estagiário", "desenvolvedor", "analista de",
    "desarrollador", "ingeniero de", "practicante",
    "développeur", "ingénieur", "stagiaire",
    "medewerker", "vacature",
]

def is_non_english(title, summary):
    text = (title + " " + summary).lower()
    return any(m in text for m in NON_ENGLISH_MARKERS)


# ============================================
# LLM BATCH SCORING (only for top candidates)
# ============================================

def build_batch_prompt(batch, profile, candidate_years):
    name = str(profile.get("name", "Candidate"))[:100]
    headline = str(profile.get("headline", ""))[:200]
    skills = profile.get("skills", [])
    skills_str = ", ".join(str(s)[:50] for s in skills[:20])

    job_entries = []
    for idx, job in enumerate(batch, 1):
        title = job.get("title", "Unknown")
        company = job.get("company", "Unknown")
        summary = re.sub(r'<[^>]+>', ' ', job.get("summary", ""))[:400]
        summary = re.sub(r'\s+', ' ', summary).strip()
        job_entries.append(
            f"JOB_{idx}: {title} at {company}\n  {summary[:300]}"
        )

    jobs_block = "\n\n".join(job_entries)

    return f"""You are a strict, realistic recruiter scoring job fit. Score each job 0-100.

CANDIDATE PROFILE:
Name: {name}
Title: {headline}
Experience: ~{candidate_years} years
Skills: {skills_str}

JOBS TO SCORE:
{jobs_block}

SCORING CRITERIA (be strict — most jobs should score 40-65):

85-100: Near-perfect fit. Same domain, 4+ skill matches, correct seniority level.
70-84:  Strong fit. Same or adjacent domain, 3+ skills, reasonable seniority.
55-69:  Decent fit. Related domain, 2+ relevant skills.
40-54:  Weak. Some skill overlap but different domain or role type.
0-39:   No fit. Different field entirely.

SENIORITY RULES (non-negotiable):
- Candidate has ~{candidate_years} years experience.
- Jobs with "Lead", "Director", "VP", "Head of", "Principal", "Staff" require 7+ years → cap at 40 if candidate has <5yr.
- Jobs with "Senior", "Manager" require 4+ years → cap at 55 if candidate has <3yr.
- A job can have perfect skill overlap but WRONG seniority = score 35-50.

Return ONLY scores in this exact format, one per line:
{chr(10).join(f"JOB_{i}: <score>" for i in range(1, len(batch) + 1))}

Numbers only. No explanations. No extra text."""


def parse_batch_scores(text, batch_size):
    scores = [0] * batch_size
    for line in text.strip().split("\n"):
        m = re.match(r'(?:JOB[_\s]*)?(\d+)\s*[:.\-)\]]\s*(\d+)', line.strip(), re.IGNORECASE)
        if m:
            idx = int(m.group(1)) - 1
            score = max(0, min(100, int(m.group(2))))
            if 0 <= idx < batch_size:
                scores[idx] = score
    return scores


def llm_batch_score(batch, profile, candidate_years):
    """Score a batch of jobs using LLM. Falls back to FALLBACK_MODEL if primary fails."""
    prompt = build_batch_prompt(batch, profile, candidate_years)

    for model in [MODEL, FALLBACK_MODEL]:
        try:
            res = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0,
                max_tokens=300,
            )
            text = res.choices[0].message.content.strip()
            scores = parse_batch_scores(text, len(batch))
            # Fallback: extract any numbers if parsing failed
            if sum(scores) == 0 and len(batch) > 1:
                numbers = re.findall(r'\b(\d{1,3})\b', text)
                if len(numbers) >= len(batch):
                    scores = [max(0, min(100, int(n))) for n in numbers[:len(batch)]]
            if sum(scores) > 0:
                logger.info(f"LLM scored with {model}")
                return scores
        except Exception as e:
            logger.warning(f"LLM scoring failed with {model}: {e}")
            continue

    logger.error("All LLM models failed")
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

    # ---- Fetch jobs if needed ----
    if not os.path.exists(jobs_file):
        if progress_callback:
            progress_callback("Fetching jobs from all sources...")
        from job_fetcher import fetch_all
        fetch_all(output_path=jobs_file)

    with open(jobs_file, "r", encoding="utf-8") as f:
        jobs = json.load(f)
    if not jobs:
        return [], 0

    jobs = deduplicate_jobs(jobs)
    total_unique = len(jobs)
    if progress_callback:
        progress_callback(f"Loaded {total_unique} unique jobs")

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
