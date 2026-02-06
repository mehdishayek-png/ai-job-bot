"""
JobBot Matching Engine v5
=========================
Fixes from user testing:
- Seniority detection: "GTM Strategy Lead" should NOT match a 2yr candidate
- Location filter: India + Remote first, everything else deprioritized
- Company diversity: max 3 matches per company
- 25 results shown (was 15)
- LLM prompt includes experience level for proper scoring
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
MATCH_THRESHOLD = int(os.getenv("MATCH_THRESHOLD", "78"))
MAX_MATCHES = int(os.getenv("MAX_MATCHES", "25"))
API_RATE_LIMIT = float(os.getenv("API_RATE_LIMIT", "0.5"))
MAX_LLM_CANDIDATES = int(os.getenv("MAX_LLM_CANDIDATES", "40"))
BATCH_SIZE = int(os.getenv("BATCH_SIZE", "5"))
MAX_PER_COMPANY = 3


# ============================================
# SENIORITY DETECTION
# ============================================

def estimate_experience_years(profile):
    # First check explicit field from parser
    explicit = profile.get("experience_years")
    if isinstance(explicit, (int, float)) and explicit > 0:
        return int(explicit)

    headline = (profile.get("headline", "") or "").lower()

    years_match = re.search(r'(\d+)\+?\s*(?:years?|yrs?)\s*(?:of)?\s*(?:experience|hands-on)?', headline)
    if years_match:
        return int(years_match.group(1))

    if any(w in headline for w in ["intern", "trainee", "fresher", "entry"]):
        return 0
    if any(w in headline for w in ["junior", "associate", "jr "]):
        return 1
    if any(w in headline for w in ["specialist", "analyst", "coordinator", "executive"]):
        return 2
    if any(w in headline for w in ["senior", "sr ", "lead", "manager"]):
        return 5
    if any(w in headline for w in ["director", "head of", "vp ", "vice president"]):
        return 10
    if any(w in headline for w in ["principal", "chief", "cto", "coo", "ceo"]):
        return 15

    skills = profile.get("skills", [])
    return min(3, len(skills) // 3)


SENIOR_TITLE_MARKERS = [
    "lead", "head of", "head,", "director", "vp ", "vice president",
    "principal", "chief", "c-level", "cto", "coo", "ceo", "cfo",
    "founding", "co-founder", "partner", "svp", "evp",
    "staff ", "distinguished",
]

MID_TITLE_MARKERS = [
    "senior", "sr ", "sr.", "manager", "team lead",
]


def title_seniority_level(title):
    t = title.lower()
    if any(m in t for m in SENIOR_TITLE_MARKERS):
        return "senior"
    if any(m in t for m in MID_TITLE_MARKERS):
        return "mid"
    return "any"


def seniority_mismatch_penalty(job_title, candidate_years):
    job_level = title_seniority_level(job_title)
    if job_level == "senior" and candidate_years < 5:
        return -0.6
    if job_level == "senior" and candidate_years < 8:
        return -0.3
    if job_level == "mid" and candidate_years < 2:
        return -0.2
    return 0.0


# ============================================
# LOCATION FILTER
# ============================================

INDIA_SIGNALS = [
    "india", "bangalore", "bengaluru", "mumbai", "delhi",
    "hyderabad", "pune", "chennai", "kolkata", "gurgaon",
    "gurugram", "noida", "jaipur", "ahmedabad", "kochi",
    "chandigarh", "indore", "lucknow", "nagpur", "coimbatore",
]

REMOTE_SIGNALS = [
    "remote", "work from home", "wfh", "anywhere",
    "distributed", "fully remote", "remote-first",
]


def classify_location(job):
    loc = (job.get("location", "") or "").lower()
    title = job.get("title", "").lower()
    summary = (job.get("summary", "") or "")[:300].lower()
    combined = f"{loc} {title} {summary}"

    if any(s in combined for s in INDIA_SIGNALS):
        return "india"
    if any(s in combined for s in REMOTE_SIGNALS):
        return "remote"
    return "other"


# ============================================
# SYNONYM / FUNCTION EXPANSION
# ============================================

SYNONYM_GROUPS = [
    {"customer support", "customer service", "customer experience", "customer success",
     "client support", "client success", "client services",
     "customer care", "user support", "customer operations"},
    {"incident management", "incident triage", "incident response",
     "escalation management", "ticket escalation", "issue resolution",
     "issue management", "ticket triage", "case management",
     "escalation handling", "problem management"},
    {"ticketing", "help desk", "helpdesk", "service desk",
     "ticket management", "support tickets", "case handling"},
    {"account management", "account manager", "key accounts",
     "client relationship", "relationship management",
     "customer retention", "churn management", "renewal management"},
    {"customer onboarding", "client onboarding", "user onboarding",
     "implementation", "customer implementation", "product adoption"},
    {"technical support", "tech support", "technical troubleshooting",
     "technical assistance", "product support", "application support",
     "l1 support", "l2 support", "tier 1", "tier 2"},
    {"sla management", "sla compliance", "service level agreement",
     "tat management", "response time", "resolution time"},
    {"process optimization", "process improvement", "workflow design",
     "sop development", "standard operating procedures",
     "operational excellence", "ops management"},
    {"root cause analysis", "rca", "post-mortem", "post mortem",
     "postmortem", "retrospective", "incident review"},
    {"cross-functional coordination", "cross-functional collaboration",
     "stakeholder management", "stakeholder communication"},
    {"zendesk", "freshdesk", "intercom", "helpscout", "freshservice",
     "jira service management", "servicenow", "salesforce service cloud"},
    {"jira", "linear", "asana", "monday.com", "clickup", "trello"},
    {"okta", "sso", "single sign-on", "identity management",
     "identity access management", "iam", "authentication"},
    {"workato", "zapier", "automation", "workflow automation",
     "process automation", "integration platform"},
    {"saas", "software as a service", "b2b saas", "enterprise saas",
     "cloud software"},
    {"product operations", "product ops", "product support",
     "product feedback", "beta testing", "uat"},
    {"data analysis", "reporting", "analytics", "metrics",
     "kpi tracking", "dashboard", "business intelligence"},
    {"software engineer", "software developer", "programmer",
     "full stack developer", "backend developer", "frontend developer"},
    {"ci/cd", "continuous integration", "continuous deployment",
     "devops", "infrastructure"},
    {"seo", "search engine optimization", "sem", "search marketing"},
    {"content marketing", "content strategy", "copywriting", "content creation"},
    {"lead generation", "pipeline development", "prospecting", "outbound sales"},
    {"crm", "salesforce", "hubspot crm", "pipedrive"},
    {"recruiting", "talent acquisition", "hiring", "sourcing candidates"},
    {"employee engagement", "people operations", "hr operations"},
    {"sql", "database", "data warehousing", "etl", "data pipeline"},
]

_SYNONYM_MAP = {}
for group in SYNONYM_GROUPS:
    for term in group:
        _SYNONYM_MAP[term] = group


def expand_terms(terms):
    expanded = set()
    for t in terms:
        t_lower = t.lower().strip()
        expanded.add(t_lower)
        if t_lower in _SYNONYM_MAP:
            expanded.update(_SYNONYM_MAP[t_lower])
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
    return any(ht in title.lower() for ht in HARD_TECH_TITLES)

def infer_candidate_domain(profile):
    headline = (profile.get("headline", "") or "").lower()
    skills = [s.lower() for s in profile.get("skills", [])]
    role_kw = [s.lower() for s in profile.get("role_keywords", [])]
    all_text = headline + " " + " ".join(skills) + " " + " ".join(role_kw)

    domain_signals = {
        "Customer Success / CX": ["customer success", "customer experience", "cx", "nps", "csat", "churn", "retention", "onboarding", "customer support"],
        "Operations": ["operations", "project manage", "process", "workflow", "sla", "escalation", "triage", "incident"],
        "Technical Support": ["technical support", "tech support", "troubleshoot", "ticketing", "zendesk", "helpdesk"],
        "Product": ["product manage", "product ops", "product owner", "roadmap", "beta testing"],
        "Sales": ["sales", "business development", "bdr", "sdr", "revenue"],
        "Marketing": ["marketing", "content", "seo", "social media", "brand"],
        "Engineering": ["software engineer", "developer", "full stack", "backend", "frontend", "devops"],
    }

    domains = []
    for domain, signals in domain_signals.items():
        if sum(1 for s in signals if s in all_text) >= 2:
            domains.append(domain)
    return " / ".join(domains[:2]) if domains else "General professional"


# ============================================
# LOCAL SCORING
# ============================================

def local_relevance_score(job, profile, candidate_years):
    skills = [s.lower().strip() for s in profile.get("skills", []) if s]
    role_kw = [s.lower().strip() for s in profile.get("role_keywords", []) if s]
    all_terms = skills + role_kw

    if not all_terms:
        return {"skill_hits": 0, "role_hits": 0, "composite": 0.0, "location": "other"}

    job_text = (job.get("title", "") + " " + job.get("summary", "")).lower()
    job_title = job.get("title", "").lower()
    expanded = expand_terms(all_terms)

    skill_hits = sum(1 for s in skills if s in job_text) if skills else 0

    role_hits = 0
    for term in expanded:
        if len(term) > 3 and term in job_text:
            role_hits += 1
    role_hits = min(role_hits, 10)

    headline = (profile.get("headline", "") or "").lower()
    headline_words = set(w for w in headline.split() if len(w) > 3)
    title_words = set(w for w in job_title.split() if len(w) > 3)
    title_overlap = len(headline_words & title_words) / len(headline_words) if headline_words else 0.0

    fn_keywords = ["manager", "specialist", "analyst", "coordinator", "associate",
                   "customer", "success", "experience", "operations", "support",
                   "technical", "account", "product", "incident", "service"]
    fn_bonus = sum(0.08 for kw in fn_keywords if kw in headline and kw in job_title)
    fn_bonus = min(fn_bonus, 0.3)

    seniority_pen = seniority_mismatch_penalty(job.get("title", ""), candidate_years)

    loc_class = classify_location(job)
    loc_boost = 0.15 if loc_class == "india" else (0.10 if loc_class == "remote" else 0.0)

    role_norm = min(role_hits / 5.0, 1.0)
    skill_norm = skill_hits / len(skills) if skills else 0.0

    composite = (skill_norm * 0.30) + (role_norm * 0.25) + (title_overlap * 0.15) + (fn_bonus * 0.10) + loc_boost + seniority_pen

    return {
        "skill_hits": skill_hits, "role_hits": role_hits,
        "title_overlap": round(title_overlap, 3),
        "seniority_pen": round(seniority_pen, 3),
        "location": loc_class,
        "composite": round(max(composite, 0), 3),
    }


# ============================================
# PRE-FILTER
# ============================================

def prefilter_jobs(jobs, profile, candidate_years, progress_callback=None):
    non_tech = is_profile_non_technical(profile)
    passed = []
    stats = {"non_english": 0, "wrong_domain": 0, "low_relevance": 0,
             "wrong_location": 0, "too_senior": 0, "passed": 0}

    for job in jobs:
        title = job.get("title", "")
        summary = job.get("summary", "")

        if is_non_english(title, summary):
            stats["non_english"] += 1
            continue

        if non_tech and is_hard_tech_role(title):
            stats["wrong_domain"] += 1
            continue

        loc_class = classify_location(job)
        if loc_class == "other":
            stats["wrong_location"] += 1
            continue

        if candidate_years < 3 and title_seniority_level(title) == "senior":
            stats["too_senior"] += 1
            continue

        rel = local_relevance_score(job, profile, candidate_years)

        passes = (rel["skill_hits"] >= 1 or rel["role_hits"] >= 2 or rel.get("title_overlap", 0) >= 0.3)
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
        f"({stats['non_english']} lang, {stats['wrong_domain']} domain, "
        f"{stats['wrong_location']} location, {stats['too_senior']} seniority, "
        f"{stats['low_relevance']} relevance)"
    )
    if progress_callback:
        progress_callback(
            f"Pre-filter: {len(jobs)} → {stats['passed']} relevant → top {len(passed)} to LLM "
            f"(filtered: {stats['wrong_location']} wrong location, "
            f"{stats['too_senior']} too senior, {stats['low_relevance']} low relevance)"
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


def build_batch_prompt(batch, profile, candidate_domain, candidate_years):
    name = str(profile.get("name", "Candidate"))[:100]
    headline = str(profile.get("headline", ""))[:200]
    skills_str = ", ".join(str(s)[:50] for s in profile.get("skills", [])[:15])
    role_str = ", ".join(str(s)[:50] for s in profile.get("role_keywords", [])[:8])

    job_entries = []
    for idx, job in enumerate(batch, 1):
        title = job.get("title", "Unknown")
        company = job.get("company", "Unknown")
        summary = strip_html_basic(job.get("summary", ""))[:600]
        location = job.get("location", "") or job.get("_local", {}).get("location", "")
        job_entries.append(f"JOB_{idx}:\n  Title: {title}\n  Company: {company}\n  Location: {location}\n  Description: {summary}")

    jobs_block = "\n\n".join(job_entries)

    return f"""You are a strict job matching expert. Score how well this candidate fits EACH job.

CANDIDATE:
Name: {name}
Role: {headline}
Domain: {candidate_domain}
Experience: {candidate_years} years (THIS IS CRITICAL — do NOT ignore)
Skills: {skills_str}
Functions: {role_str}

JOBS:

{jobs_block}

SCORING RUBRIC — be VERY harsh on seniority mismatches:

90-100: Perfect. Same function + domain. 4+ skills. SAME seniority level.
80-89:  Strong. Same function. 3+ skills. Seniority within 1-2 years.
70-79:  Good. Related function. 2-3 skills. Reasonable seniority.
60-69:  Weak. Adjacent function. 1-2 overlaps.
40-59:  Poor. Different function or major seniority gap.
0-39:   No fit.

CRITICAL SENIORITY RULES (candidate has {candidate_years} years experience):
- "Lead", "Head of", "Director", "VP", "Principal", "Staff" need 7+ years.
  If candidate has <5 years, score 30-50 MAX regardless of skill overlap.
- "Senior" or "Manager" need 4+ years.
  If candidate has <3 years, score 50-65 MAX.
- "Specialist", "Associate", "Coordinator" fit 1-4 years perfectly.
- Seniority mismatch OVERRIDES skill overlap.

PENALTIES:
- Developer/engineer for non-technical candidate: -40
- Different professional function entirely: -30

Return ONLY scores:
JOB_1: <score>
JOB_2: <score>
{chr(10).join(f"JOB_{i}: <score>" for i in range(3, len(batch) + 1))}

Numbers only. No explanation."""


def parse_batch_scores(response_text, batch_size):
    scores = [0] * batch_size
    for line in response_text.strip().split("\n"):
        line = line.strip()
        if not line: continue
        match = re.match(r'(?:JOB[_\s]*)?(\d+)\s*[:.\-)\]]\s*(\d+)', line, re.IGNORECASE)
        if match:
            idx = int(match.group(1)) - 1
            score = max(0, min(100, int(match.group(2))))
            if 0 <= idx < batch_size:
                scores[idx] = score
    return scores


def batch_score(batch, profile, candidate_domain, candidate_years, max_retries=3):
    prompt = build_batch_prompt(batch, profile, candidate_domain, candidate_years)
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
    relevant = {"name": profile.get("name", ""), "headline": profile.get("headline", ""),
                "skills": sorted(profile.get("skills", [])), "role_keywords": sorted(profile.get("role_keywords", []))}
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

def enforce_company_diversity(matches, max_per_company=MAX_PER_COMPANY):
    company_count = {}
    diverse = []
    overflow = []
    for m in matches:
        co = m.get("company", "Unknown").lower().strip()
        company_count[co] = company_count.get(co, 0) + 1
        if company_count[co] <= max_per_company:
            diverse.append(m)
        else:
            overflow.append(m)
    remaining = MAX_MATCHES - len(diverse)
    if remaining > 0 and overflow:
        diverse.extend(overflow[:remaining])
    return diverse


# ============================================
# PIPELINE
# ============================================

def run_pipeline(profile_file, jobs_file, session_dir, letters_dir=None, progress_callback=None):
    if not os.path.exists(profile_file):
        raise FileNotFoundError(f"Profile not found: {profile_file}")

    with open(profile_file, "r", encoding="utf-8") as f:
        profile = json.load(f)

    candidate_years = estimate_experience_years(profile)
    logger.info(f"Profile: {profile.get('name', '?')} — {len(profile.get('skills', []))} skills, ~{candidate_years}yr")

    candidate_domain = infer_candidate_domain(profile)
    logger.info(f"Domain: {candidate_domain}")
    if progress_callback:
        progress_callback(f"Profile: ~{candidate_years} years exp | Domain: {candidate_domain}")

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

    candidates = prefilter_jobs(jobs, profile, candidate_years, progress_callback)
    if not candidates:
        if progress_callback:
            progress_callback("No relevant jobs after filtering India/Remote + seniority.")
        return [], total_unique

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
        ck = f"v5_{p_hash}_{jid}"
        job["_cache_key"] = ck
        if ck in cache:
            cached_results.append((job, cache[ck]))
        else:
            uncached.append(job)

    logger.info(f"Cache: {len(cached_results)} hits, {len(uncached)} to score")
    if progress_callback:
        tb = (len(uncached) + BATCH_SIZE - 1) // BATCH_SIZE
        progress_callback(f"Scoring {len(uncached)} jobs in {tb} batches ({len(cached_results)} cached)")

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

        scores = batch_score(batch, profile, candidate_domain, candidate_years)
        api_calls += 1

        for job, score in zip(batch, scores):
            ck = job.get("_cache_key", "")
            if ck: cache[ck] = score
            scored.append((job, score))
            logger.info(f"  {job.get('company', '?')[:20]}: {job.get('title', '?')[:40]} → {score}")

        if progress_callback:
            progress_callback(f"  → [{', '.join(str(s) for s in scores)}]")

        if i + BATCH_SIZE < len(uncached):
            time.sleep(API_RATE_LIMIT)

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
    matches = enforce_company_diversity(matches)
    matches = matches[:MAX_MATCHES]

    os.makedirs(session_dir, exist_ok=True)
    try:
        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump(cache, f, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Cache save: {e}")

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
