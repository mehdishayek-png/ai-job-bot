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
# LOGGING
# ============================================

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ============================================
# LOAD API KEY
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
# CONFIGURATION
# ============================================

MODEL = os.getenv("SCORING_MODEL", "mistralai/mistral-7b-instruct")
MATCH_THRESHOLD = int(os.getenv("MATCH_THRESHOLD", "82"))  # Raised from 70
MAX_MATCHES = int(os.getenv("MAX_MATCHES", "10"))           # Tighter from 15
API_RATE_LIMIT = float(os.getenv("API_RATE_LIMIT", "0.5"))

# ============================================
# LANGUAGE / GARBAGE DETECTION
# ============================================

# Non-English markers — if title or summary contains these, skip
NON_ENGLISH_MARKERS = [
    # German
    "freelancer (m/w/d)", "(m/w/d)", "vollzeit", "teilzeit", "praktikum",
    "estagiário", "estágio",
    # Portuguese
    "desenvolvedor", "analista de",
    # Spanish
    "desarrollador", "ingeniero de", "practicante",
    # French
    "développeur", "ingénieur", "stagiaire",
    # Dutch
    "medewerker", "vacature",
    # Generic non-English
    "weltweit", "sofort", "à distance",
]

# Titles that are clearly engineering/dev roles — skip for non-technical profiles
HARD_TECH_TITLES = [
    "software engineer", "backend engineer", "frontend engineer",
    "full stack engineer", "fullstack engineer", "devops engineer",
    "site reliability engineer", "sre ", "machine learning engineer",
    "data engineer", "platform engineer", "infrastructure engineer",
    "ios developer", "android developer", "mobile developer",
    "ruby developer", "python developer", "java developer",
    "golang developer", "rust developer", "php developer",
    ".net developer", "c++ developer", "c# developer",
    "firmware engineer", "embedded engineer", "systems engineer",
    "security engineer", "cloud engineer", "solutions architect",
    "software architect", "principal engineer", "staff engineer",
]

# Non-tech profile indicators — if headline contains these, filter out hard tech
NON_TECH_HEADLINES = [
    "customer success", "customer experience", "account manager",
    "operations", "project manager", "program manager",
    "marketing", "sales", "business development", "recruiter",
    "hr ", "human resources", "people operations",
    "content", "copywriter", "social media",
    "support", "community", "partnerships",
    "finance", "accounting", "legal",
]


def is_non_english(title: str, summary: str) -> bool:
    """Check if job posting is in a non-English language."""
    text = (title + " " + summary).lower()
    return any(marker in text for marker in NON_ENGLISH_MARKERS)


def is_profile_non_technical(profile: dict) -> bool:
    """Determine if the candidate's profile is non-technical."""
    headline = (profile.get("headline", "") or "").lower()
    if any(nt in headline for nt in NON_TECH_HEADLINES):
        return True
    # Also check skills — if <20% are technical, they're non-technical
    tech_skills = {
        "python", "javascript", "typescript", "react", "node", "java",
        "golang", "rust", "c++", "c#", "ruby", "php", "sql", "aws",
        "docker", "kubernetes", "terraform", "git", "linux", "api",
        "graphql", "mongodb", "postgresql", "redis", "elasticsearch",
    }
    skills = [s.lower() for s in profile.get("skills", [])]
    tech_count = sum(1 for s in skills if any(t in s for t in tech_skills))
    if len(skills) > 0 and tech_count / len(skills) < 0.2:
        return True
    return False


def is_hard_tech_role(title: str) -> bool:
    """Check if job title is a hardcore engineering/dev role."""
    t = title.lower()
    return any(ht in t for ht in HARD_TECH_TITLES)


# ============================================
# DOMAIN INFERENCE
# ============================================

def infer_candidate_domain(profile: dict) -> str:
    """
    Infer the candidate's professional domain from headline + skills.
    Returns a concise domain description for the scoring prompt.
    """
    headline = (profile.get("headline", "") or "").lower()
    skills = [s.lower() for s in profile.get("skills", [])]
    all_text = headline + " " + " ".join(skills)

    domains = []

    # Map keywords to domains
    domain_signals = {
        "Customer Success / Customer Experience": [
            "customer success", "customer experience", "cx ", "cs ",
            "nps", "csat", "churn", "retention", "onboarding",
            "account management", "client success", "customer journey",
        ],
        "Operations / Project Management": [
            "operations", "project manage", "program manage", "process",
            "workflow", "coordination", "cross-functional", "sla",
            "escalation", "triage", "incident",
        ],
        "Sales / Business Development": [
            "sales", "business development", "bdr", "sdr", "pipeline",
            "quota", "revenue", "prospecting", "closing",
        ],
        "Marketing": [
            "marketing", "content", "seo", "sem", "social media",
            "brand", "campaign", "copywriting", "growth",
        ],
        "Technical Support / IT": [
            "technical support", "helpdesk", "it support", "troubleshoot",
            "ticketing", "zendesk", "freshdesk", "jira service",
        ],
        "Product Management": [
            "product manage", "product owner", "roadmap", "user research",
            "a/b test", "feature", "backlog",
        ],
        "Human Resources / People": [
            "hr ", "human resources", "people operations", "recruiting",
            "talent", "onboarding", "employer brand",
        ],
        "Data / Analytics": [
            "data analyst", "analytics", "bi ", "business intelligence",
            "tableau", "looker", "sql", "reporting",
        ],
        "Software Engineering": [
            "software engineer", "developer", "full stack", "backend",
            "frontend", "devops", "sre", "architect",
        ],
    }

    for domain, signals in domain_signals.items():
        matches = sum(1 for s in signals if s in all_text)
        if matches >= 2:
            domains.append(domain)

    if not domains:
        return "General professional"

    return " / ".join(domains[:2])


# ============================================
# KEYWORD RELEVANCE (LOCAL, FREE)
# ============================================

def keyword_overlap_score(job: dict, profile: dict) -> float:
    """
    Quick local relevance check — percentage of profile skills
    that appear in the job title + description.
    Returns 0.0 to 1.0.
    """
    skills = [s.lower().strip() for s in profile.get("skills", []) if s]
    if not skills:
        return 0.0

    job_text = (
        job.get("title", "") + " " + job.get("summary", "")
    ).lower()

    hits = sum(1 for skill in skills if skill in job_text)
    return hits / len(skills)


# ============================================
# PASS 1: LOCAL PRE-FILTER
# ============================================

def prefilter_jobs(jobs: list, profile: dict, progress_callback=None) -> list:
    """
    Fast local filter to remove obviously irrelevant jobs
    before burning API calls on scoring.
    
    Filters:
    1. Non-English postings
    2. Hard tech roles for non-tech candidates
    3. Zero keyword overlap
    """
    non_tech = is_profile_non_technical(profile)
    passed = []
    stats = {"non_english": 0, "wrong_domain": 0, "no_overlap": 0, "passed": 0}

    for job in jobs:
        title = job.get("title", "")
        summary = job.get("summary", "")

        # Filter 1: Non-English
        if is_non_english(title, summary):
            stats["non_english"] += 1
            continue

        # Filter 2: Hard tech roles for non-tech profiles
        if non_tech and is_hard_tech_role(title):
            stats["wrong_domain"] += 1
            continue

        # Filter 3: Minimum keyword overlap (at least 1 skill mention)
        overlap = keyword_overlap_score(job, profile)
        if overlap == 0.0:
            stats["no_overlap"] += 1
            continue

        # Store overlap for sorting priority
        job["_keyword_overlap"] = overlap
        passed.append(job)
        stats["passed"] += 1

    # Sort by keyword overlap descending — score the most promising first
    passed.sort(key=lambda j: j.get("_keyword_overlap", 0), reverse=True)

    logger.info(
        f"Pre-filter: {len(jobs)} → {stats['passed']} passed "
        f"(skipped {stats['non_english']} non-English, "
        f"{stats['wrong_domain']} wrong domain, "
        f"{stats['no_overlap']} zero overlap)"
    )

    if progress_callback:
        progress_callback(
            f"Pre-filter: {stats['passed']}/{len(jobs)} jobs passed "
            f"({stats['non_english']} non-English, "
            f"{stats['wrong_domain']} wrong domain, "
            f"{stats['no_overlap']} no skill overlap)"
        )

    return passed


# ============================================
# PASS 2: STRICT LLM SCORING WITH RUBRIC
# ============================================

def build_scoring_prompt(job: dict, profile: dict, candidate_domain: str) -> str:
    """
    Build a strict scoring prompt with explicit rubric and penalty criteria.
    Forces the LLM to think about fit before returning a number.
    """
    name = str(profile.get("name", "Candidate"))[:100]
    headline = str(profile.get("headline", ""))[:200]
    skills = profile.get("skills", [])
    skills_str = ", ".join(str(s)[:50] for s in skills[:30])

    title = job.get("title", "Unknown")
    company = job.get("company", "Unknown")
    summary = strip_html_basic(job.get("summary", ""))[:1500]

    return f"""You are a strict job matching expert. Score how well this candidate fits this specific job.

CANDIDATE:
Name: {name}
Current role: {headline}
Domain: {candidate_domain}
Skills: {skills_str}

JOB:
Title: {title}
Company: {company}
Description: {summary}

SCORING RUBRIC — be harsh, most jobs should score below 60:

90-100: Perfect fit. Title matches candidate's domain exactly. 5+ skills directly mentioned. Same seniority level.
80-89:  Strong fit. Same professional domain. 3-4 skills match. Seniority is close.
70-79:  Decent fit. Related domain but not exact. 2-3 skills match.
60-69:  Weak fit. Adjacent domain. Only 1-2 generic skills overlap.
40-59:  Poor fit. Different function or domain. Superficial keyword overlap only.
20-39:  Bad fit. Completely different career track.
0-19:   No fit. Wrong language, wrong industry, or unrelated entirely.

MANDATORY PENALTIES (subtract from score):
- Job requires language candidate doesn't know: score 0
- Job is in a different professional function (e.g. engineering role for operations person): -30
- Job title contains "developer" or "engineer" but candidate is non-technical: -40
- Job is clearly a different seniority level (intern for a director, or VP for an associate): -20
- Job description mentions "must have" requirements the candidate clearly lacks: -15

Return ONLY a number between 0 and 100. No explanation."""


def strip_html_basic(text):
    """Quick HTML strip for prompts."""
    if not text:
        return ""
    clean = re.sub(r'<[^>]+>', ' ', text)
    clean = re.sub(r'&\w+;', ' ', clean)
    return re.sub(r'\s+', ' ', clean).strip()


def semantic_score(job: dict, profile: dict, candidate_domain: str, max_retries: int = 3) -> int:
    """
    Score match with strict rubric-based prompt.
    """
    prompt = build_scoring_prompt(job, profile, candidate_domain)

    for attempt in range(max_retries):
        try:
            res = client.chat.completions.create(
                model=MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=0,
                max_tokens=5,
            )

            score_text = res.choices[0].message.content.strip()
            digits = "".join(c for c in score_text if c.isdigit())

            if digits:
                score = max(0, min(100, int(digits)))
                return score

            logger.warning(f"No score in response: {score_text}")
            return 0

        except Exception as e:
            error_msg = str(e).lower()
            if "rate" in error_msg or "limit" in error_msg:
                wait_time = (2 ** attempt) * 2
                logger.warning(f"Rate limited, waiting {wait_time}s")
                time.sleep(wait_time)
            elif attempt < max_retries - 1:
                logger.warning(f"Scoring attempt {attempt + 1} failed: {e}")
                time.sleep(1)
            else:
                logger.error(f"Scoring failed after {max_retries} attempts: {e}")
                return 0

    return 0


# ============================================
# UTILITIES
# ============================================

def create_job_id(job: dict) -> str:
    unique_str = "|".join([
        job.get("company", "unknown"),
        job.get("title", "unknown"),
        job.get("apply_url", "")[:100],
    ])
    return hashlib.md5(unique_str.encode()).hexdigest()[:16]


def profile_hash(profile: dict) -> str:
    relevant = {
        "name": profile.get("name", ""),
        "headline": profile.get("headline", ""),
        "skills": sorted(profile.get("skills", []))
    }
    return hashlib.md5(json.dumps(relevant, sort_keys=True).encode()).hexdigest()


def deduplicate_jobs(jobs: list) -> list:
    seen = set()
    unique = []
    for job in jobs:
        key = (
            job.get("company", "").lower().strip(),
            job.get("title", "").lower().strip()
        )
        if key not in seen and key != ("", ""):
            seen.add(key)
            unique.append(job)
    logger.info(f"Deduplicated {len(jobs)} → {len(unique)} jobs")
    return unique


# ============================================
# CORE PIPELINE
# ============================================

def run_pipeline(
    profile_file: str,
    jobs_file: str,
    session_dir: str,
    letters_dir: str = None,
    progress_callback=None,
) -> tuple:
    """
    Two-pass job matching pipeline:
      Pass 1: Local pre-filter (free, instant)
      Pass 2: Strict LLM scoring with rubric
    """

    # ---- Load profile ----
    if not os.path.exists(profile_file):
        raise FileNotFoundError(f"Profile not found: {profile_file}")

    with open(profile_file, "r", encoding="utf-8") as f:
        profile = json.load(f)

    logger.info(f"Profile: {profile.get('name', '?')} — {len(profile.get('skills', []))} skills")

    # ---- Infer candidate domain ----
    candidate_domain = infer_candidate_domain(profile)
    logger.info(f"Inferred domain: {candidate_domain}")
    if progress_callback:
        progress_callback(f"Candidate domain: {candidate_domain}")

    # ---- Fetch jobs if needed ----
    if not os.path.exists(jobs_file):
        logger.info("Fetching jobs from sources...")
        if progress_callback:
            progress_callback("Fetching jobs from remote sources...")
        from job_fetcher import fetch_all
        try:
            fetch_all(output_path=jobs_file)
        except Exception as e:
            raise RuntimeError(f"Could not fetch jobs: {e}")

    # ---- Load & deduplicate ----
    with open(jobs_file, "r", encoding="utf-8") as f:
        jobs = json.load(f)

    if not jobs:
        return [], 0

    total_fetched = len(jobs)
    jobs = deduplicate_jobs(jobs)
    total_unique = len(jobs)

    # ============================================
    # PASS 1: LOCAL PRE-FILTER
    # ============================================

    candidates = prefilter_jobs(jobs, profile, progress_callback)

    if not candidates:
        logger.warning("No jobs passed pre-filter")
        if progress_callback:
            progress_callback("No jobs passed pre-filter. Try broadening your skills.")
        return [], total_unique

    # ============================================
    # PASS 2: STRICT LLM SCORING
    # ============================================

    p_hash = profile_hash(profile)

    # Load cache
    cache_file = os.path.join(session_dir, "semantic_cache.json")
    cache = {}
    if os.path.exists(cache_file):
        try:
            if os.path.getsize(cache_file) < 10 * 1024 * 1024:
                with open(cache_file, "r", encoding="utf-8") as f:
                    cache = json.load(f)
        except Exception:
            cache = {}

    matches = []
    scored_count = 0
    cache_hits = 0

    if progress_callback:
        progress_callback(f"Scoring {len(candidates)} pre-filtered jobs (from {total_unique} total)...")

    for idx, job in enumerate(candidates, 1):
        if progress_callback and idx % 5 == 0:
            progress_callback(
                f"Scoring... {idx}/{len(candidates)} — "
                f"{len(matches)} matches so far"
            )

        job_id = create_job_id(job)
        cache_key = f"v2_{p_hash}_{job_id}"  # v2 prefix to invalidate old soft-scored cache

        if cache_key in cache:
            score = cache[cache_key]
            cache_hits += 1
        else:
            score = semantic_score(job, profile, candidate_domain)
            cache[cache_key] = score
            scored_count += 1
            time.sleep(API_RATE_LIMIT)

        if score >= MATCH_THRESHOLD:
            matched = job.copy()
            matched.pop("_keyword_overlap", None)  # Remove internal field
            matched["match_score"] = score
            matches.append(matched)

        # Log every score for visibility
        title_short = job.get("title", "?")[:50]
        company_short = job.get("company", "?")[:25]
        logger.info(f"  [{idx}/{len(candidates)}] {company_short}: {title_short} → {score}")
        if progress_callback and idx % 3 == 0:
            progress_callback(
                f"  [{idx}] {company_short}: {title_short} → {score}"
            )

    logger.info(
        f"Scoring done: {len(matches)} matches from {len(candidates)} candidates "
        f"({cache_hits} cached, {scored_count} API calls)"
    )

    # ---- Sort and limit ----
    matches.sort(key=lambda x: x["match_score"], reverse=True)
    matches = matches[:MAX_MATCHES]

    # ---- Save cache ----
    os.makedirs(session_dir, exist_ok=True)
    try:
        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump(cache, f, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Cache save failed: {e}")

    # ---- Generate cover letters ----
    if not letters_dir:
        letters_dir = os.path.join(session_dir, "cover_letters")
    os.makedirs(letters_dir, exist_ok=True)

    if progress_callback:
        progress_callback(f"Generating {len(matches)} cover letters...")

    for j in matches:
        try:
            generate_cover_letter(j, profile, letters_dir)
        except Exception as e:
            logger.error(f"Cover letter failed for {j.get('title')}: {e}")

    return matches, total_unique


# ============================================
# STREAMLIT WRAPPER
# ============================================

def run_auto_apply_pipeline(
    profile_file=None,
    jobs_file=None,
    matches_file=None,
    cache_file=None,
    log_file=None,
    letters_dir=None,
    progress_callback=None,
):
    try:
        if progress_callback:
            progress_callback("Starting pipeline...")

        session_dir = os.path.dirname(profile_file)

        matches, total_scored = run_pipeline(
            profile_file=profile_file,
            jobs_file=jobs_file,
            session_dir=session_dir,
            letters_dir=letters_dir,
            progress_callback=progress_callback,
        )

        if matches_file:
            os.makedirs(os.path.dirname(matches_file) or ".", exist_ok=True)
            with open(matches_file, "w", encoding="utf-8") as f:
                json.dump(matches, f, indent=2, ensure_ascii=False)

        if progress_callback:
            progress_callback(f"Done — {len(matches)} matches from {total_scored} jobs.")

        if len(matches) == 0:
            return {"status": "no_matches", "matches": 0, "total_scored": total_scored}

        return {"status": "success", "matches": len(matches), "total_scored": total_scored}

    except Exception as e:
        logger.exception("Pipeline error")
        if progress_callback:
            progress_callback(f"Error: {e}")
        return {"status": "error", "message": str(e)}


# ============================================
# CLI
# ============================================

if __name__ == "__main__":
    import sys

    if len(sys.argv) < 3:
        print("Usage: python run_auto_apply.py <profile.json> <jobs.json>")
        sys.exit(1)

    try:
        matches, total = run_pipeline(
            profile_file=sys.argv[1],
            jobs_file=sys.argv[2],
            session_dir="data/test_session",
        )
        print(f"\n✅ {len(matches)} matches from {total} jobs")
        for i, j in enumerate(matches, 1):
            print(f"  {i}. [{j['match_score']}%] {j['company']} — {j['title']}")
    except Exception as e:
        print(f"\n❌ {e}")
        sys.exit(1)
