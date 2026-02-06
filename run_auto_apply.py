"""
JobBot Matching Engine v3
=========================
Two-pass pipeline with batch LLM scoring.

Cost model (206 fetched jobs):
  Old v1: 206 jobs × 1 API call  = 206 calls
  Old v2: 206 → prefilter ~80 × 1 call = ~80 calls
  This v3: 206 → prefilter → cap 40 → batch 5 = 8 calls  (96% reduction)
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
# LOGGING
# ============================================

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
# CONFIGURATION
# ============================================

MODEL = os.getenv("SCORING_MODEL", "mistralai/mistral-7b-instruct")
MATCH_THRESHOLD = int(os.getenv("MATCH_THRESHOLD", "82"))
MAX_MATCHES = int(os.getenv("MAX_MATCHES", "10"))
API_RATE_LIMIT = float(os.getenv("API_RATE_LIMIT", "0.5"))

# Cost controls
MAX_LLM_CANDIDATES = int(os.getenv("MAX_LLM_CANDIDATES", "40"))   # Hard cap on API-scored jobs
BATCH_SIZE = int(os.getenv("BATCH_SIZE", "5"))                     # Jobs per API call
MIN_SKILL_HITS = int(os.getenv("MIN_SKILL_HITS", "2"))             # Minimum local skill matches

# ============================================
# LANGUAGE DETECTION
# ============================================

NON_ENGLISH_MARKERS = [
    "(m/w/d)", "vollzeit", "teilzeit", "praktikum",
    "estagiário", "estágio", "desenvolvedor", "analista de",
    "desarrollador", "ingeniero de", "practicante",
    "développeur", "ingénieur", "stagiaire",
    "medewerker", "vacature",
    "weltweit", "sofort", "à distance",
    "работа", "вакансия",
]


def is_non_english(title: str, summary: str) -> bool:
    text = (title + " " + summary).lower()
    return any(m in text for m in NON_ENGLISH_MARKERS)


# ============================================
# DOMAIN / ROLE CLASSIFICATION
# ============================================

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

NON_TECH_HEADLINES = [
    "customer success", "customer experience", "account manager",
    "operations", "project manager", "program manager",
    "marketing", "sales", "business development", "recruiter",
    "hr ", "human resources", "people operations",
    "content", "copywriter", "social media",
    "support", "community", "partnerships",
    "finance", "accounting", "legal",
]


def is_profile_non_technical(profile: dict) -> bool:
    headline = (profile.get("headline", "") or "").lower()
    if any(nt in headline for nt in NON_TECH_HEADLINES):
        return True
    tech_kw = {
        "python", "javascript", "typescript", "react", "node", "java",
        "golang", "rust", "c++", "c#", "ruby", "php", "sql", "aws",
        "docker", "kubernetes", "terraform", "git", "linux", "api",
    }
    skills = [s.lower() for s in profile.get("skills", [])]
    tech_count = sum(1 for s in skills if any(t in s for t in tech_kw))
    return len(skills) > 0 and tech_count / len(skills) < 0.2


def is_hard_tech_role(title: str) -> bool:
    t = title.lower()
    return any(ht in t for ht in HARD_TECH_TITLES)


def infer_candidate_domain(profile: dict) -> str:
    headline = (profile.get("headline", "") or "").lower()
    skills = [s.lower() for s in profile.get("skills", [])]
    all_text = headline + " " + " ".join(skills)

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
            "quota", "revenue", "prospecting",
        ],
        "Marketing": [
            "marketing", "content", "seo", "sem", "social media",
            "brand", "campaign", "copywriting", "growth",
        ],
        "Technical Support / IT": [
            "technical support", "helpdesk", "it support", "troubleshoot",
            "ticketing", "zendesk", "freshdesk",
        ],
        "Product Management": [
            "product manage", "product owner", "roadmap", "user research",
            "a/b test", "feature", "backlog",
        ],
        "Human Resources / People": [
            "hr ", "human resources", "people operations", "recruiting",
            "talent", "employer brand",
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

    domains = []
    for domain, signals in domain_signals.items():
        hits = sum(1 for s in signals if s in all_text)
        if hits >= 2:
            domains.append(domain)

    return " / ".join(domains[:2]) if domains else "General professional"


# ============================================
# LOCAL SCORING (FREE — no API calls)
# ============================================

def local_relevance_score(job: dict, profile: dict) -> dict:
    """
    Multi-signal local relevance scorer.
    Returns {"skill_hits": int, "skill_pct": float, "title_relevance": float, "composite": float}
    """
    skills = [s.lower().strip() for s in profile.get("skills", []) if s]
    if not skills:
        return {"skill_hits": 0, "skill_pct": 0.0, "title_relevance": 0.0, "composite": 0.0}

    job_text = (job.get("title", "") + " " + job.get("summary", "")).lower()
    job_title = job.get("title", "").lower()

    # ---- Signal 1: Skill keyword hits ----
    skill_hits = 0
    for skill in skills:
        # Exact match or substring (e.g. "customer success" in "customer success manager")
        if skill in job_text:
            skill_hits += 1
        # Also check individual words for multi-word skills
        elif len(skill.split()) > 1:
            words = skill.split()
            if sum(1 for w in words if w in job_text) >= len(words) * 0.7:
                skill_hits += 0.5

    skill_pct = skill_hits / len(skills)

    # ---- Signal 2: Title relevance ----
    # Does the job title contain words from the candidate's headline?
    headline = (profile.get("headline", "") or "").lower()
    headline_words = set(w for w in headline.split() if len(w) > 3)  # Skip "and", "the", etc.
    title_words = set(w for w in job_title.split() if len(w) > 3)

    if headline_words:
        title_overlap = len(headline_words & title_words) / len(headline_words)
    else:
        title_overlap = 0.0

    # ---- Signal 3: Title keyword bonus ----
    # Specific role-category words appearing in both headline and title
    role_keywords = [
        "manager", "lead", "director", "specialist", "analyst",
        "coordinator", "associate", "senior", "head", "vp",
        "customer", "success", "experience", "operations", "support",
        "marketing", "sales", "product", "data", "design",
    ]
    title_kw_bonus = sum(
        0.1 for kw in role_keywords
        if kw in headline and kw in job_title
    )
    title_kw_bonus = min(title_kw_bonus, 0.3)  # Cap

    # ---- Composite ----
    composite = (skill_pct * 0.6) + (title_overlap * 0.25) + (title_kw_bonus * 0.15)

    return {
        "skill_hits": skill_hits,
        "skill_pct": round(skill_pct, 3),
        "title_relevance": round(title_overlap, 3),
        "composite": round(composite, 3),
    }


# ============================================
# PASS 1: LOCAL PRE-FILTER
# ============================================

def prefilter_jobs(jobs: list, profile: dict, progress_callback=None) -> list:
    """
    Fast local filter — removes obviously bad jobs before any API call.

    Filters:
    1. Non-English postings
    2. Hard tech roles for non-tech candidates
    3. Minimum skill hits (configurable, default 2)

    Returns top MAX_LLM_CANDIDATES sorted by local composite score.
    """
    non_tech = is_profile_non_technical(profile)
    passed = []
    stats = {"non_english": 0, "wrong_domain": 0, "low_overlap": 0, "passed": 0}

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

        # Filter 3: Local relevance check
        rel = local_relevance_score(job, profile)

        if rel["skill_hits"] < MIN_SKILL_HITS:
            stats["low_overlap"] += 1
            continue

        # Attach scores for sorting
        job["_local"] = rel
        passed.append(job)
        stats["passed"] += 1

    # Sort by composite score descending — best local fits first
    passed.sort(key=lambda j: j.get("_local", {}).get("composite", 0), reverse=True)

    # Hard cap — only send top N to LLM
    if len(passed) > MAX_LLM_CANDIDATES:
        logger.info(f"Capping {len(passed)} pre-filtered jobs → {MAX_LLM_CANDIDATES}")
        passed = passed[:MAX_LLM_CANDIDATES]

    logger.info(
        f"Pre-filter: {len(jobs)} → {stats['passed']} passed → {len(passed)} capped "
        f"(skipped {stats['non_english']} non-English, "
        f"{stats['wrong_domain']} wrong domain, "
        f"{stats['low_overlap']} low overlap)"
    )

    if progress_callback:
        progress_callback(
            f"Pre-filter: {len(jobs)} jobs → {stats['passed']} relevant → "
            f"scoring top {len(passed)} "
            f"(skipped {stats['non_english']} non-English, "
            f"{stats['wrong_domain']} wrong domain, "
            f"{stats['low_overlap']} low overlap)"
        )

    return passed


# ============================================
# PASS 2: BATCH LLM SCORING
# ============================================

def build_batch_prompt(batch: list, profile: dict, candidate_domain: str) -> str:
    """
    Build a single prompt that scores multiple jobs at once.
    Returns scores in format: "JOB_1: 45\nJOB_2: 82\n..."
    """
    name = str(profile.get("name", "Candidate"))[:100]
    headline = str(profile.get("headline", ""))[:200]
    skills = profile.get("skills", [])
    skills_str = ", ".join(str(s)[:50] for s in skills[:30])

    # Build job list
    job_entries = []
    for idx, job in enumerate(batch, 1):
        title = job.get("title", "Unknown")
        company = job.get("company", "Unknown")
        summary = strip_html_basic(job.get("summary", ""))[:600]  # Shorter per job in batch
        job_entries.append(f"JOB_{idx}:\n  Title: {title}\n  Company: {company}\n  Description: {summary}")

    jobs_block = "\n\n".join(job_entries)

    return f"""You are a strict job matching expert. Score how well this candidate fits EACH job below.

CANDIDATE:
Name: {name}
Role: {headline}
Domain: {candidate_domain}
Skills: {skills_str}

JOBS TO SCORE:

{jobs_block}

SCORING RUBRIC — be harsh. Most jobs should score below 60:

90-100: Perfect fit. Same domain, 5+ skills match, same seniority.
80-89:  Strong fit. Same domain, 3-4 skills, close seniority.
70-79:  Decent fit. Related domain, 2-3 skills.
60-69:  Weak fit. Adjacent domain, 1-2 generic overlaps.
40-59:  Poor fit. Different function. Superficial overlap.
20-39:  Bad fit. Completely different career track.
0-19:   No fit. Wrong language/industry.

PENALTIES:
- Different professional function (e.g. engineering vs operations): -30
- "developer"/"engineer" title but candidate is non-technical: -40
- Wrong seniority level: -20
- Missing must-have requirements: -15

Return ONLY scores in this exact format, one per line:
JOB_1: <score>
JOB_2: <score>
{chr(10).join(f"JOB_{i}: <score>" for i in range(3, len(batch) + 1))}

No explanations. Only numbers 0-100."""


def parse_batch_scores(response_text: str, batch_size: int) -> list:
    """
    Parse "JOB_1: 85\nJOB_2: 42\n..." format.
    Returns list of ints, with 0 for any unparseable entries.
    """
    scores = [0] * batch_size
    lines = response_text.strip().split("\n")

    for line in lines:
        line = line.strip()
        if not line:
            continue
        # Match patterns like "JOB_1: 85" or "JOB_1:85" or "1: 85" or "1. 85"
        match = re.match(r'(?:JOB[_\s]*)?(\d+)\s*[:.\-)\]]\s*(\d+)', line, re.IGNORECASE)
        if match:
            idx = int(match.group(1)) - 1  # 0-based
            score = max(0, min(100, int(match.group(2))))
            if 0 <= idx < batch_size:
                scores[idx] = score

    return scores


def batch_score(batch: list, profile: dict, candidate_domain: str, max_retries: int = 3) -> list:
    """
    Score a batch of jobs in a single API call.
    Returns list of int scores, same length as batch.
    """
    prompt = build_batch_prompt(batch, profile, candidate_domain)

    for attempt in range(max_retries):
        try:
            res = client.chat.completions.create(
                model=MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=0,
                max_tokens=50,  # Enough for "JOB_1: XX\n" × batch_size
            )

            text = res.choices[0].message.content.strip()
            scores = parse_batch_scores(text, len(batch))

            # Sanity check — if we got all zeros, something went wrong
            if sum(scores) == 0 and len(batch) > 1:
                logger.warning(f"All-zero batch scores. Raw response: {text[:200]}")
                # Fallback: try to extract ANY numbers
                numbers = re.findall(r'\b(\d{1,3})\b', text)
                if len(numbers) >= len(batch):
                    scores = [max(0, min(100, int(n))) for n in numbers[:len(batch)]]
                    logger.info(f"Recovered scores from fallback parsing: {scores}")

            return scores

        except Exception as e:
            error_msg = str(e).lower()
            if "rate" in error_msg or "limit" in error_msg:
                wait = (2 ** attempt) * 2
                logger.warning(f"Rate limited, waiting {wait}s")
                time.sleep(wait)
            elif attempt < max_retries - 1:
                logger.warning(f"Batch scoring attempt {attempt + 1} failed: {e}")
                time.sleep(1)
            else:
                logger.error(f"Batch scoring failed after {max_retries} attempts: {e}")
                return [0] * len(batch)

    return [0] * len(batch)


# Single job fallback (for batches of 1 or retries)
def single_score(job: dict, profile: dict, candidate_domain: str, max_retries: int = 3) -> int:
    """Fallback: score a single job."""
    scores = batch_score([job], profile, candidate_domain, max_retries)
    return scores[0] if scores else 0


def strip_html_basic(text):
    if not text: return ""
    clean = re.sub(r'<[^>]+>', ' ', text)
    clean = re.sub(r'&\w+;', ' ', clean)
    return re.sub(r'\s+', ' ', clean).strip()


# ============================================
# UTILITIES
# ============================================

def create_job_id(job: dict) -> str:
    raw = "|".join([
        job.get("company", "unknown"),
        job.get("title", "unknown"),
        job.get("apply_url", "")[:100],
    ])
    return hashlib.md5(raw.encode()).hexdigest()[:16]


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
    Three-stage pipeline:
      1. Local pre-filter (free, instant) — language, domain, keyword overlap
      2. Cap at top N by local score (free)
      3. Batch LLM scoring — 5 jobs per API call
    """

    # ---- Load profile ----
    if not os.path.exists(profile_file):
        raise FileNotFoundError(f"Profile not found: {profile_file}")

    with open(profile_file, "r", encoding="utf-8") as f:
        profile = json.load(f)

    logger.info(f"Profile: {profile.get('name', '?')} — {len(profile.get('skills', []))} skills")

    # ---- Infer domain ----
    candidate_domain = infer_candidate_domain(profile)
    logger.info(f"Domain: {candidate_domain}")
    if progress_callback:
        progress_callback(f"Candidate domain: {candidate_domain}")

    # ---- Fetch jobs if needed ----
    if not os.path.exists(jobs_file):
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
    # STAGE 1+2: LOCAL PRE-FILTER + CAP
    # ============================================

    candidates = prefilter_jobs(jobs, profile, progress_callback)

    if not candidates:
        if progress_callback:
            progress_callback("No jobs passed pre-filter. Try broadening your skills.")
        return [], total_unique

    # ============================================
    # STAGE 3: BATCH LLM SCORING
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

    # Separate cached vs uncached jobs
    uncached_jobs = []
    cached_results = []  # (job, score) pairs

    for job in candidates:
        job_id = create_job_id(job)
        cache_key = f"v3_{p_hash}_{job_id}"  # v3 = batch scoring era
        job["_cache_key"] = cache_key

        if cache_key in cache:
            cached_results.append((job, cache[cache_key]))
        else:
            uncached_jobs.append(job)

    logger.info(f"Cache: {len(cached_results)} hits, {len(uncached_jobs)} to score")
    if progress_callback:
        progress_callback(
            f"Cache: {len(cached_results)} already scored, "
            f"{len(uncached_jobs)} need scoring in {(len(uncached_jobs) + BATCH_SIZE - 1) // BATCH_SIZE} batches"
        )

    # ---- Score uncached jobs in batches ----
    api_calls = 0
    scored_pairs = []  # (job, score)

    for batch_start in range(0, len(uncached_jobs), BATCH_SIZE):
        batch = uncached_jobs[batch_start:batch_start + BATCH_SIZE]
        batch_num = batch_start // BATCH_SIZE + 1
        total_batches = (len(uncached_jobs) + BATCH_SIZE - 1) // BATCH_SIZE

        if progress_callback:
            titles = [f"{j.get('company','?')[:15]}: {j.get('title','?')[:30]}" for j in batch]
            progress_callback(f"Batch {batch_num}/{total_batches} — scoring {len(batch)} jobs...")
            for t in titles:
                progress_callback(f"  · {t}")

        scores = batch_score(batch, profile, candidate_domain)
        api_calls += 1

        for job, score in zip(batch, scores):
            # Cache the score
            ck = job.get("_cache_key", "")
            if ck:
                cache[ck] = score

            scored_pairs.append((job, score))

            # Log each score
            c = job.get("company", "?")[:20]
            t = job.get("title", "?")[:40]
            local_comp = job.get("_local", {}).get("composite", 0)
            logger.info(f"  {c}: {t} → local:{local_comp:.2f} llm:{score}")

        if progress_callback:
            batch_scores_str = ", ".join(str(s) for s in scores)
            progress_callback(f"  → Scores: [{batch_scores_str}]")

        # Rate limit between batch calls
        if batch_start + BATCH_SIZE < len(uncached_jobs):
            time.sleep(API_RATE_LIMIT)

    # ---- Merge cached + freshly scored ----
    all_results = cached_results + scored_pairs

    # ---- Filter by threshold ----
    matches = []
    for job, score in all_results:
        if score >= MATCH_THRESHOLD:
            matched = job.copy()
            # Remove internal fields
            matched.pop("_local", None)
            matched.pop("_cache_key", None)
            matched["match_score"] = score
            matches.append(matched)

    logger.info(
        f"Scoring done: {len(matches)} matches from {len(candidates)} candidates "
        f"({len(cached_results)} cached, {api_calls} API calls for {len(uncached_jobs)} jobs)"
    )

    if progress_callback:
        progress_callback(
            f"✅ Done: {len(matches)} matches — "
            f"{api_calls} API calls (saved {len(cached_results)} from cache)"
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

    if matches and progress_callback:
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
            progress_callback(f"Pipeline complete — {len(matches)} matches from {total_scored} jobs.")

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
