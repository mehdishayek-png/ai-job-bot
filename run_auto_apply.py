"""
JobBot Matching Engine v4
=========================
Key fix: Synonym expansion + role_keywords matching.

The problem with v3: a job saying "manage customer escalations via Zendesk"
would fail pre-filter for a candidate with "incident triage" because exact
string matching found zero overlap. Now we expand both sides through a
synonym graph so related terms match.

Cost model: 206 jobs → prefilter ~60 → cap 40 → batch 5 = 8 API calls
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

MODEL = os.getenv("SCORING_MODEL", "mistralai/mistral-7b-instruct")
MATCH_THRESHOLD = int(os.getenv("MATCH_THRESHOLD", "78"))     # Slightly lower to catch more
MAX_MATCHES = int(os.getenv("MAX_MATCHES", "15"))
API_RATE_LIMIT = float(os.getenv("API_RATE_LIMIT", "0.5"))
MAX_LLM_CANDIDATES = int(os.getenv("MAX_LLM_CANDIDATES", "40"))
BATCH_SIZE = int(os.getenv("BATCH_SIZE", "5"))


# ============================================
# SYNONYM / FUNCTION EXPANSION
# ============================================

# Each group = terms that describe the SAME function.
# If a candidate has ANY term in a group, ALL terms in that group
# become matchable against job descriptions.

SYNONYM_GROUPS = [
    # Customer-facing roles
    {"customer support", "customer service", "customer experience", "customer success",
     "client support", "client success", "client services", "cx ", "cs ",
     "customer care", "user support", "customer operations"},

    # Incident / escalation
    {"incident management", "incident triage", "incident response",
     "escalation management", "ticket escalation", "issue resolution",
     "issue management", "ticket triage", "case management",
     "escalation handling", "problem management"},

    # Ticketing / helpdesk
    {"ticketing", "help desk", "helpdesk", "service desk",
     "ticket management", "support tickets", "case handling"},

    # Account management
    {"account management", "account manager", "key accounts",
     "client relationship", "relationship management",
     "customer retention", "churn management", "renewal management"},

    # Onboarding
    {"customer onboarding", "client onboarding", "user onboarding",
     "implementation", "customer implementation", "product adoption"},

    # Technical support
    {"technical support", "tech support", "technical troubleshooting",
     "technical assistance", "product support", "application support",
     "l1 support", "l2 support", "tier 1", "tier 2"},

    # SLA / quality
    {"sla management", "sla compliance", "service level agreement",
     "tat management", "response time", "resolution time"},

    # Process / ops
    {"process optimization", "process improvement", "workflow design",
     "sop development", "standard operating procedures",
     "operational excellence", "ops management"},

    # Root cause / post mortem
    {"root cause analysis", "rca", "post-mortem", "post mortem",
     "postmortem", "retrospective", "incident review"},

    # Cross-functional
    {"cross-functional coordination", "cross-functional collaboration",
     "stakeholder management", "stakeholder communication",
     "executive communication"},

    # Tools — CRM / support platforms
    {"zendesk", "freshdesk", "intercom", "helpscout", "freshservice",
     "jira service management", "servicenow", "salesforce service cloud"},

    # Tools — project management
    {"jira", "linear", "asana", "monday.com", "clickup", "trello"},

    # Identity / SSO
    {"okta", "sso", "single sign-on", "identity management",
     "identity access management", "iam", "authentication"},

    # Automation
    {"workato", "zapier", "automation", "workflow automation",
     "process automation", "integration platform"},

    # SaaS domain
    {"saas", "software as a service", "b2b saas", "enterprise saas",
     "cloud software", "subscription software"},

    # Product ops
    {"product operations", "product ops", "product support",
     "product feedback", "beta testing", "uat"},

    # Data / analytics
    {"data analysis", "reporting", "analytics", "metrics",
     "kpi tracking", "dashboard", "business intelligence"},
]

# Build lookup: term → set of all synonyms
_SYNONYM_MAP = {}
for group in SYNONYM_GROUPS:
    for term in group:
        _SYNONYM_MAP[term] = group


def expand_terms(terms):
    """Given a list of terms, return expanded set including all synonyms."""
    expanded = set()
    for t in terms:
        t_lower = t.lower().strip()
        expanded.add(t_lower)
        if t_lower in _SYNONYM_MAP:
            expanded.update(_SYNONYM_MAP[t_lower])
        # Also check if any synonym group contains this as substring
        for group in SYNONYM_GROUPS:
            for syn in group:
                if t_lower in syn or syn in t_lower:
                    expanded.update(group)
                    break
    return expanded


# ============================================
# LANGUAGE / DOMAIN FILTERS
# ============================================

NON_ENGLISH_MARKERS = [
    "(m/w/d)", "vollzeit", "teilzeit", "praktikum",
    "estagiário", "estágio", "desenvolvedor", "analista de",
    "desarrollador", "ingeniero de", "practicante",
    "développeur", "ingénieur", "stagiaire",
    "medewerker", "vacature", "weltweit", "sofort",
]

HARD_TECH_TITLES = [
    "software engineer", "backend engineer", "frontend engineer",
    "full stack engineer", "fullstack engineer", "devops engineer",
    "site reliability engineer", "sre ", "machine learning engineer",
    "data engineer", "platform engineer", "infrastructure engineer",
    "ios developer", "android developer", "mobile developer",
    "ruby developer", "python developer", "java developer",
    "golang developer", "rust developer", "php developer",
    ".net developer", "c++ developer", "c# developer",
    "firmware engineer", "embedded engineer",
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
    "product operations", "cx ", "incident",
]


def is_non_english(title, summary):
    text = (title + " " + summary).lower()
    return any(m in text for m in NON_ENGLISH_MARKERS)


def is_profile_non_technical(profile):
    headline = (profile.get("headline", "") or "").lower()
    if any(nt in headline for nt in NON_TECH_HEADLINES):
        return True
    tech_kw = {"python", "javascript", "typescript", "react", "node", "java",
               "golang", "rust", "c++", "c#", "ruby", "php", "sql", "aws",
               "docker", "kubernetes", "terraform", "git", "linux"}
    skills = [s.lower() for s in profile.get("skills", [])]
    tc = sum(1 for s in skills if any(t in s for t in tech_kw))
    return len(skills) > 0 and tc / len(skills) < 0.2


def is_hard_tech_role(title):
    t = title.lower()
    return any(ht in t for ht in HARD_TECH_TITLES)


def infer_candidate_domain(profile):
    headline = (profile.get("headline", "") or "").lower()
    skills = [s.lower() for s in profile.get("skills", [])]
    role_kw = [s.lower() for s in profile.get("role_keywords", [])]
    all_text = headline + " " + " ".join(skills) + " " + " ".join(role_kw)

    domain_signals = {
        "Customer Success / Customer Experience": [
            "customer success", "customer experience", "cx", "cs",
            "nps", "csat", "churn", "retention", "onboarding",
            "account management", "client success", "customer support",
        ],
        "Operations / Project Management": [
            "operations", "project manage", "program manage", "process",
            "workflow", "coordination", "cross-functional", "sla",
            "escalation", "triage", "incident",
        ],
        "Technical Support": [
            "technical support", "tech support", "troubleshoot",
            "ticketing", "zendesk", "helpdesk", "service desk",
        ],
        "Product Management / Ops": [
            "product manage", "product ops", "product owner", "roadmap",
            "beta testing", "product feedback",
        ],
        "Sales / Business Development": [
            "sales", "business development", "bdr", "sdr", "revenue",
        ],
        "Marketing": [
            "marketing", "content", "seo", "social media", "brand",
        ],
        "Software Engineering": [
            "software engineer", "developer", "full stack", "backend",
            "frontend", "devops",
        ],
    }

    domains = []
    for domain, signals in domain_signals.items():
        hits = sum(1 for s in signals if s in all_text)
        if hits >= 2:
            domains.append(domain)

    return " / ".join(domains[:2]) if domains else "General professional"


# ============================================
# LOCAL SCORING WITH SYNONYM EXPANSION
# ============================================

def local_relevance_score(job, profile):
    """
    Scores local relevance using:
    1. Skill hits (with synonym expansion)
    2. Role keyword hits (with synonym expansion)
    3. Title-to-headline overlap
    4. Title function keyword bonus
    """
    skills = [s.lower().strip() for s in profile.get("skills", []) if s]
    role_kw = [s.lower().strip() for s in profile.get("role_keywords", []) if s]
    all_profile_terms = skills + role_kw

    if not all_profile_terms:
        return {"skill_hits": 0, "role_hits": 0, "composite": 0.0}

    job_text = (job.get("title", "") + " " + job.get("summary", "")).lower()
    job_title = job.get("title", "").lower()

    # Expand profile terms with synonyms
    expanded = expand_terms(all_profile_terms)

    # ---- Signal 1: Direct skill hits ----
    skill_hits = sum(1 for s in skills if s in job_text) if skills else 0

    # ---- Signal 2: Role keyword hits (including synonyms) ----
    role_hits = 0
    for term in expanded:
        if len(term) > 3 and term in job_text:  # Skip short terms like "cx "
            role_hits += 1
    role_hits = min(role_hits, 10)  # Cap to avoid over-counting synonym groups

    # ---- Signal 3: Title-headline overlap ----
    headline = (profile.get("headline", "") or "").lower()
    headline_words = set(w for w in headline.split() if len(w) > 3)
    title_words = set(w for w in job_title.split() if len(w) > 3)
    title_overlap = len(headline_words & title_words) / len(headline_words) if headline_words else 0.0

    # ---- Signal 4: Function keyword bonus ----
    fn_keywords = [
        "manager", "lead", "director", "specialist", "analyst",
        "coordinator", "associate", "senior", "head",
        "customer", "success", "experience", "operations", "support",
        "technical", "account", "product", "incident", "service",
    ]
    fn_bonus = sum(0.08 for kw in fn_keywords if kw in headline and kw in job_title)
    fn_bonus = min(fn_bonus, 0.3)

    # ---- Composite ----
    # Normalize role_hits to 0-1 range (10 = perfect)
    role_norm = min(role_hits / 5.0, 1.0)
    skill_norm = skill_hits / len(skills) if skills else 0.0

    composite = (skill_norm * 0.35) + (role_norm * 0.30) + (title_overlap * 0.20) + (fn_bonus * 0.15)

    return {
        "skill_hits": skill_hits,
        "role_hits": role_hits,
        "title_overlap": round(title_overlap, 3),
        "composite": round(composite, 3),
    }


# ============================================
# PRE-FILTER
# ============================================

def prefilter_jobs(jobs, profile, progress_callback=None):
    """
    A job passes if ANY of:
    - 1+ direct skill hits
    - 2+ synonym/role_keyword hits
    - Title overlap > 0.3 with headline
    """
    non_tech = is_profile_non_technical(profile)
    passed = []
    stats = {"non_english": 0, "wrong_domain": 0, "low_relevance": 0, "passed": 0}

    for job in jobs:
        title = job.get("title", "")
        summary = job.get("summary", "")

        if is_non_english(title, summary):
            stats["non_english"] += 1
            continue

        if non_tech and is_hard_tech_role(title):
            stats["wrong_domain"] += 1
            continue

        rel = local_relevance_score(job, profile)

        # Pass if: any skill hit OR 2+ role/synonym hits OR strong title match
        passes = (
            rel["skill_hits"] >= 1 or
            rel["role_hits"] >= 2 or
            rel.get("title_overlap", 0) >= 0.3
        )

        if not passes:
            stats["low_relevance"] += 1
            continue

        job["_local"] = rel
        passed.append(job)
        stats["passed"] += 1

    passed.sort(key=lambda j: j.get("_local", {}).get("composite", 0), reverse=True)

    if len(passed) > MAX_LLM_CANDIDATES:
        passed = passed[:MAX_LLM_CANDIDATES]

    logger.info(
        f"Pre-filter: {len(jobs)} → {stats['passed']} passed → {len(passed)} capped "
        f"({stats['non_english']} non-English, {stats['wrong_domain']} wrong domain, "
        f"{stats['low_relevance']} low relevance)"
    )
    if progress_callback:
        progress_callback(
            f"Pre-filter: {len(jobs)} → {stats['passed']} relevant → top {len(passed)} sent to LLM "
            f"({stats['non_english']} non-English, {stats['wrong_domain']} wrong domain, "
            f"{stats['low_relevance']} low relevance)"
        )
    return passed


# ============================================
# BATCH LLM SCORING
# ============================================

def strip_html_basic(text):
    if not text: return ""
    clean = re.sub(r'<[^>]+>', ' ', text)
    clean = re.sub(r'&\w+;', ' ', clean)
    return re.sub(r'\s+', ' ', clean).strip()


def build_batch_prompt(batch, profile, candidate_domain):
    name = str(profile.get("name", "Candidate"))[:100]
    headline = str(profile.get("headline", ""))[:200]
    skills = profile.get("skills", [])
    role_kw = profile.get("role_keywords", [])
    skills_str = ", ".join(str(s)[:50] for s in skills[:15])
    role_str = ", ".join(str(s)[:50] for s in role_kw[:8])

    job_entries = []
    for idx, job in enumerate(batch, 1):
        title = job.get("title", "Unknown")
        company = job.get("company", "Unknown")
        summary = strip_html_basic(job.get("summary", ""))[:600]
        job_entries.append(f"JOB_{idx}:\n  Title: {title}\n  Company: {company}\n  Description: {summary}")

    jobs_block = "\n\n".join(job_entries)

    return f"""You are a strict job matching expert. Score how well this candidate fits EACH job.

CANDIDATE:
Name: {name}
Role: {headline}
Domain: {candidate_domain}
Skills: {skills_str}
Functions: {role_str}

JOBS:

{jobs_block}

SCORING RUBRIC — be harsh, most should score below 60:

90-100: Perfect. Same function + domain. 5+ skills match. Same seniority.
80-89:  Strong. Same function. 3-4 skills. Close seniority.
70-79:  Good. Related function OR same function in adjacent domain. 2-3 skills.
60-69:  Weak. Adjacent function. 1-2 generic overlaps.
40-59:  Poor. Different function entirely.
0-39:   No fit.

IMPORTANT: "Customer Experience" roles include customer support, incident triage,
ticket management, escalation handling, account management, and CX operations.
These are the SAME professional family — score accordingly.

PENALTIES:
- Different professional function (engineering vs operations): -30
- Developer/engineer title for non-technical candidate: -40
- Wrong seniority: -20

Return ONLY scores in this format:
JOB_1: <score>
JOB_2: <score>
{chr(10).join(f"JOB_{i}: <score>" for i in range(3, len(batch) + 1))}

Numbers only. No explanation."""


def parse_batch_scores(response_text, batch_size):
    scores = [0] * batch_size
    for line in response_text.strip().split("\n"):
        line = line.strip()
        if not line:
            continue
        match = re.match(r'(?:JOB[_\s]*)?(\d+)\s*[:.\-)\]]\s*(\d+)', line, re.IGNORECASE)
        if match:
            idx = int(match.group(1)) - 1
            score = max(0, min(100, int(match.group(2))))
            if 0 <= idx < batch_size:
                scores[idx] = score
    return scores


def batch_score(batch, profile, candidate_domain, max_retries=3):
    prompt = build_batch_prompt(batch, profile, candidate_domain)
    for attempt in range(max_retries):
        try:
            res = client.chat.completions.create(
                model=MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=0,
                max_tokens=50,
            )
            text = res.choices[0].message.content.strip()
            scores = parse_batch_scores(text, len(batch))
            if sum(scores) == 0 and len(batch) > 1:
                numbers = re.findall(r'\b(\d{1,3})\b', text)
                if len(numbers) >= len(batch):
                    scores = [max(0, min(100, int(n))) for n in numbers[:len(batch)]]
            return scores
        except Exception as e:
            if "rate" in str(e).lower() or "limit" in str(e).lower():
                time.sleep((2 ** attempt) * 2)
            elif attempt < max_retries - 1:
                time.sleep(1)
            else:
                return [0] * len(batch)
    return [0] * len(batch)


# ============================================
# UTILITIES
# ============================================

def create_job_id(job):
    raw = "|".join([job.get("company", ""), job.get("title", ""), job.get("apply_url", "")[:100]])
    return hashlib.md5(raw.encode()).hexdigest()[:16]

def profile_hash(profile):
    relevant = {
        "name": profile.get("name", ""),
        "headline": profile.get("headline", ""),
        "skills": sorted(profile.get("skills", [])),
        "role_keywords": sorted(profile.get("role_keywords", [])),
    }
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


# ============================================
# PIPELINE
# ============================================

def run_pipeline(profile_file, jobs_file, session_dir, letters_dir=None, progress_callback=None):
    if not os.path.exists(profile_file):
        raise FileNotFoundError(f"Profile not found: {profile_file}")

    with open(profile_file, "r", encoding="utf-8") as f:
        profile = json.load(f)

    logger.info(f"Profile: {profile.get('name', '?')} — {len(profile.get('skills', []))} skills, {len(profile.get('role_keywords', []))} role_kw")

    candidate_domain = infer_candidate_domain(profile)
    logger.info(f"Domain: {candidate_domain}")
    if progress_callback:
        progress_callback(f"Domain: {candidate_domain}")

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

    # Pre-filter
    candidates = prefilter_jobs(jobs, profile, progress_callback)
    if not candidates:
        if progress_callback:
            progress_callback("No relevant jobs found. Try broadening your skills.")
        return [], total_unique

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

    uncached, cached_results = [], []
    for job in candidates:
        jid = create_job_id(job)
        ck = f"v4_{p_hash}_{jid}"
        job["_cache_key"] = ck
        if ck in cache:
            cached_results.append((job, cache[ck]))
        else:
            uncached.append(job)

    logger.info(f"Cache: {len(cached_results)} hits, {len(uncached)} to score")
    if progress_callback:
        total_batches = (len(uncached) + BATCH_SIZE - 1) // BATCH_SIZE
        progress_callback(f"Scoring {len(uncached)} jobs in {total_batches} batches ({len(cached_results)} cached)")

    # Batch score
    api_calls = 0
    scored = []
    for i in range(0, len(uncached), BATCH_SIZE):
        batch = uncached[i:i + BATCH_SIZE]
        bn = i // BATCH_SIZE + 1
        tb = (len(uncached) + BATCH_SIZE - 1) // BATCH_SIZE

        if progress_callback:
            titles = [f"{j.get('company','?')[:15]}: {j.get('title','?')[:35]}" for j in batch]
            progress_callback(f"Batch {bn}/{tb}:")
            for t in titles:
                progress_callback(f"  · {t}")

        scores = batch_score(batch, profile, candidate_domain)
        api_calls += 1

        for job, score in zip(batch, scores):
            ck = job.get("_cache_key", "")
            if ck:
                cache[ck] = score
            scored.append((job, score))
            c = job.get("company", "?")[:20]
            t = job.get("title", "?")[:40]
            logger.info(f"  {c}: {t} → {score}")

        if progress_callback:
            progress_callback(f"  → [{', '.join(str(s) for s in scores)}]")

        if i + BATCH_SIZE < len(uncached):
            time.sleep(API_RATE_LIMIT)

    # Merge
    all_results = cached_results + scored
    matches = []
    for job, score in all_results:
        if score >= MATCH_THRESHOLD:
            m = job.copy()
            m.pop("_local", None)
            m.pop("_cache_key", None)
            m["match_score"] = score
            matches.append(m)

    logger.info(f"Done: {len(matches)} matches from {len(candidates)} candidates ({api_calls} API calls)")
    if progress_callback:
        progress_callback(f"✅ {len(matches)} matches — {api_calls} API calls ({len(cached_results)} cached)")

    matches.sort(key=lambda x: x["match_score"], reverse=True)
    matches = matches[:MAX_MATCHES]

    # Save cache
    os.makedirs(session_dir, exist_ok=True)
    try:
        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump(cache, f, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Cache save: {e}")

    # Cover letters
    if not letters_dir:
        letters_dir = os.path.join(session_dir, "cover_letters")
    os.makedirs(letters_dir, exist_ok=True)

    if matches and progress_callback:
        progress_callback(f"Generating {len(matches)} cover letters...")

    for j in matches:
        try:
            generate_cover_letter(j, profile, letters_dir)
        except Exception as e:
            logger.error(f"Cover letter: {j.get('title')}: {e}")

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
