"""
Job Fetcher v2
==============
Sources:
  1. WeWorkRemotely (RSS)
  2. RemoteOK (RSS)
  3. Remotive (REST API)
  4. Greenhouse boards (REST API — no auth)
  5. Lever postings (REST API — no auth)
  6. Ashby boards (REST API — no auth)
  7. Workday endpoints (REST — no auth)
  8. Naukri (light scrape — 5-10 jobs, IP block detection)
"""

import feedparser
import requests
import json
import os
import re
import time
import random
import logging

# ============================================
# LOGGING
# ============================================

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ============================================
# CONFIG
# ============================================

OUTPUT_DEFAULT = "data/jobs.json"
NETWORK_TIMEOUT = 30
MAX_RETRIES = 2
RETRY_DELAY = 2

# ============================================
# HTML STRIPPING
# ============================================

def strip_html(text):
    if not text:
        return ""
    clean = re.sub(r'<[^>]+>', ' ', text)
    clean = clean.replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>')
    clean = clean.replace('&quot;', '"').replace('&#39;', "'").replace('&nbsp;', ' ')
    return re.sub(r'\s+', ' ', clean).strip()


def extract_company_from_title(title):
    if ": " in title:
        parts = title.split(": ", 1)
        if len(parts) == 2 and len(parts[0]) < 60:
            return parts[0].strip(), parts[1].strip()
    return "", title


# ============================================
# USER AGENT ROTATION
# ============================================

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
]


def get_session(rotate_ua=False):
    """Create a requests session with realistic headers."""
    s = requests.Session()
    ua = random.choice(USER_AGENTS) if rotate_ua else "JobBot/2.0 (Job Aggregator)"
    s.headers.update({
        "User-Agent": ua,
        "Accept": "application/json, text/html, application/xhtml+xml",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
    })
    return s


# ============================================
# 1. WeWorkRemotely (RSS)
# ============================================

WWR_FEEDS = [
    "https://weworkremotely.com/categories/remote-programming-jobs.rss",
    "https://weworkremotely.com/categories/remote-design-jobs.rss",
    "https://weworkremotely.com/categories/remote-marketing-jobs.rss",
    "https://weworkremotely.com/categories/remote-customer-support-jobs.rss",
]


def parse_rss(url, source, timeout=NETWORK_TIMEOUT):
    jobs = []
    for attempt in range(MAX_RETRIES):
        try:
            resp = requests.get(url, timeout=timeout, headers={
                "User-Agent": "JobBot/2.0",
                "Accept": "application/rss+xml, application/xml, text/xml",
            })
            resp.raise_for_status()
            feed = feedparser.parse(resp.content)

            if not hasattr(feed, 'entries') or not feed.entries:
                return []

            for entry in feed.entries:
                raw_title = entry.get("title", "").strip()
                author = entry.get("author", "").strip()
                raw_summary = entry.get("summary", "").strip()

                if author and author.lower() != "unknown":
                    company = author
                    title = raw_title
                else:
                    parsed_co, parsed_title = extract_company_from_title(raw_title)
                    company = parsed_co or "Unknown"
                    title = parsed_title

                if title and entry.get("link"):
                    jobs.append({
                        "title": title,
                        "company": company,
                        "summary": strip_html(raw_summary)[:500],
                        "apply_url": entry.get("link", "").strip(),
                        "source": source,
                    })

            logger.info(f"{source}: {len(jobs)} jobs")
            return jobs

        except Exception as e:
            logger.warning(f"{source} attempt {attempt+1} failed: {e}")
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAY * (attempt + 1))

    return jobs


# ============================================
# 2. RemoteOK (RSS)
# ============================================

REMOTEOK_URL = "https://remoteok.com/remote-jobs.rss"


# ============================================
# 3. Remotive (REST API)
# ============================================

def fetch_remotive():
    jobs = []
    try:
        resp = requests.get("https://remotive.com/api/remote-jobs", timeout=NETWORK_TIMEOUT, headers={
            "User-Agent": "JobBot/2.0", "Accept": "application/json",
        })
        resp.raise_for_status()
        data = resp.json()

        for j in data.get("jobs", []):
            if not isinstance(j, dict):
                continue
            title = j.get("title", "").strip()
            url = j.get("url", "").strip()
            if title and url:
                jobs.append({
                    "title": title,
                    "company": j.get("company_name", "Unknown").strip(),
                    "summary": strip_html(j.get("description", ""))[:500],
                    "apply_url": url,
                    "source": "Remotive",
                })

        logger.info(f"Remotive: {len(jobs)} jobs")
    except Exception as e:
        logger.error(f"Remotive failed: {e}")
    return jobs


# ============================================
# 4. Greenhouse Boards (REST — no auth)
# ============================================

# Curated remote-friendly companies with Greenhouse boards
GREENHOUSE_BOARDS = [
    "gitlab", "hashicorp", "figma", "datadog", "mongodb",
    "cloudflare", "twilio", "elastic", "notion", "airtable",
    "canva", "webflow", "zapier", "gusto", "buffer",
    "doist", "automattic", "hotjar", "loom", "miro",
]


def fetch_greenhouse():
    """
    Greenhouse public board API.
    Endpoint: https://boards-api.greenhouse.io/v1/boards/{company}/jobs
    No auth required. Returns JSON.
    """
    all_jobs = []
    session = get_session()

    for board in GREENHOUSE_BOARDS:
        try:
            url = f"https://boards-api.greenhouse.io/v1/boards/{board}/jobs"
            resp = session.get(url, timeout=NETWORK_TIMEOUT, params={"content": "true"})

            if resp.status_code == 404:
                logger.debug(f"Greenhouse board not found: {board}")
                continue

            resp.raise_for_status()
            data = resp.json()

            board_jobs = data.get("jobs", [])
            count = 0

            for j in board_jobs:
                title = j.get("title", "").strip()
                abs_url = j.get("absolute_url", "").strip()

                if not title or not abs_url:
                    continue

                # Extract location — check if remote
                location_name = ""
                locations = j.get("location", {})
                if isinstance(locations, dict):
                    location_name = locations.get("name", "")

                # Get description
                content = strip_html(j.get("content", ""))[:500]

                # Get company name from metadata if available
                company_name = j.get("company", {}).get("name", board.replace("-", " ").title()) if isinstance(j.get("company"), dict) else board.replace("-", " ").title()

                all_jobs.append({
                    "title": title,
                    "company": company_name,
                    "summary": content,
                    "apply_url": abs_url,
                    "source": "Greenhouse",
                    "location": location_name,
                })
                count += 1

            if count:
                logger.info(f"Greenhouse/{board}: {count} jobs")

            # Polite delay between boards
            time.sleep(0.3)

        except Exception as e:
            logger.warning(f"Greenhouse/{board} failed: {e}")
            continue

    logger.info(f"Greenhouse total: {len(all_jobs)} jobs from {len(GREENHOUSE_BOARDS)} boards")
    return all_jobs


# ============================================
# 5. Lever Postings (REST — no auth)
# ============================================

LEVER_COMPANIES = [
    "netflix", "stripe", "coinbase", "figma", "notion",
    "vercel", "supabase", "linear", "planetscale", "fly",
    "render", "railway", "retool", "airbyte", "dbt-labs",
    "grafana-labs", "postman", "snyk", "sentry",
]


def fetch_lever():
    """
    Lever public postings API.
    Endpoint: https://api.lever.co/v0/postings/{company}?mode=json
    No auth required.
    """
    all_jobs = []
    session = get_session()

    for company in LEVER_COMPANIES:
        try:
            url = f"https://api.lever.co/v0/postings/{company}"
            resp = session.get(url, timeout=NETWORK_TIMEOUT, params={"mode": "json"})

            if resp.status_code == 404:
                continue

            resp.raise_for_status()
            postings = resp.json()

            if not isinstance(postings, list):
                continue

            count = 0
            for p in postings:
                title = p.get("text", "").strip()
                apply_url = p.get("hostedUrl", "").strip()

                if not title or not apply_url:
                    continue

                # Categories
                cats = p.get("categories", {})
                location = cats.get("location", "") if isinstance(cats, dict) else ""
                team = cats.get("team", "") if isinstance(cats, dict) else ""

                # Description
                desc_parts = []
                for list_block in p.get("lists", []):
                    desc_parts.append(strip_html(list_block.get("content", "")))
                description = " ".join(desc_parts)[:500]

                # Additional description
                if not description:
                    description = strip_html(p.get("descriptionPlain", ""))[:500]

                all_jobs.append({
                    "title": title,
                    "company": company.replace("-", " ").title(),
                    "summary": description,
                    "apply_url": apply_url,
                    "source": "Lever",
                    "location": location,
                })
                count += 1

            if count:
                logger.info(f"Lever/{company}: {count} jobs")

            time.sleep(0.3)

        except Exception as e:
            logger.warning(f"Lever/{company} failed: {e}")
            continue

    logger.info(f"Lever total: {len(all_jobs)} jobs")
    return all_jobs


# ============================================
# 6. Ashby Boards (REST — no auth)
# ============================================

ASHBY_BOARDS = [
    "ramp", "notion", "linear", "vercel", "mercury",
    "deel", "brex", "plaid", "retool", "clerk",
]


def fetch_ashby():
    """
    Ashby public job board API.
    Endpoint: https://api.ashbyhq.com/posting-api/job-board/{company}
    No auth required.
    """
    all_jobs = []
    session = get_session()

    for board in ASHBY_BOARDS:
        try:
            url = f"https://api.ashbyhq.com/posting-api/job-board/{board}"
            resp = session.get(url, timeout=NETWORK_TIMEOUT)

            if resp.status_code == 404:
                continue

            resp.raise_for_status()
            data = resp.json()

            postings = data.get("jobs", [])
            count = 0

            for p in postings:
                title = p.get("title", "").strip()
                job_url = p.get("jobUrl", "").strip()

                if not title or not job_url:
                    continue

                location = p.get("location", "")
                department = p.get("department", "")
                desc = strip_html(p.get("descriptionHtml", p.get("descriptionPlain", "")))[:500]

                # Try to get company name
                company_name = data.get("organizationName", board.replace("-", " ").title())

                all_jobs.append({
                    "title": title,
                    "company": company_name,
                    "summary": desc,
                    "apply_url": job_url,
                    "source": "Ashby",
                    "location": location if isinstance(location, str) else "",
                })
                count += 1

            if count:
                logger.info(f"Ashby/{board}: {count} jobs")

            time.sleep(0.3)

        except Exception as e:
            logger.warning(f"Ashby/{board} failed: {e}")
            continue

    logger.info(f"Ashby total: {len(all_jobs)} jobs")
    return all_jobs


# ============================================
# 7. Workday Endpoints (REST — no auth)
# ============================================

# Format: (company_slug, workday_instance, site_name)
WORKDAY_BOARDS = [
    ("salesforce", "wd12", "salesforce", "External_Career_Site"),
    ("servicenow", "wd1", "servicenow", "Careers"),
    ("visa", "wd5", "visa", "Visa_Careers"),
    ("adobe", "wd5", "adobe", "external_experienced"),
]


def fetch_workday():
    """
    Workday public job search.
    POST to: https://{company}.{instance}.myworkday.com/wday/cxs/{company}/{site}/jobs
    No auth. Returns JSON with jobPostings array.
    """
    all_jobs = []
    session = get_session()
    session.headers.update({"Content-Type": "application/json"})

    for company_slug, instance, path_company, site in WORKDAY_BOARDS:
        try:
            url = f"https://{company_slug}.{instance}.myworkday.com/wday/cxs/{path_company}/{site}/jobs"

            payload = {
                "appliedFacets": {},
                "limit": 20,
                "offset": 0,
                "searchText": "",
            }

            resp = session.post(url, json=payload, timeout=NETWORK_TIMEOUT)

            if resp.status_code in (404, 403, 500):
                logger.debug(f"Workday/{company_slug}: HTTP {resp.status_code}")
                continue

            resp.raise_for_status()
            data = resp.json()

            postings = data.get("jobPostings", [])
            count = 0

            for p in postings:
                title = p.get("title", "").strip()
                external_path = p.get("externalPath", "")

                if not title or not external_path:
                    continue

                # Build full URL
                apply_url = f"https://{company_slug}.{instance}.myworkday.com/en-US{external_path}"

                # Location
                locales = p.get("locationsText", "")

                # Posted date
                posted = p.get("postedOn", "")

                all_jobs.append({
                    "title": title,
                    "company": company_slug.replace("-", " ").title(),
                    "summary": f"Location: {locales}. Posted: {posted}".strip(),
                    "apply_url": apply_url,
                    "source": "Workday",
                    "location": locales,
                })
                count += 1

            if count:
                logger.info(f"Workday/{company_slug}: {count} jobs")

            time.sleep(0.5)

        except Exception as e:
            logger.warning(f"Workday/{company_slug} failed: {e}")
            continue

    logger.info(f"Workday total: {len(all_jobs)} jobs")
    return all_jobs


# ============================================
# 8. Naukri Light Scrape (5-10 jobs, IP-safe)
# ============================================

NAUKRI_MAX_JOBS = 10
NAUKRI_KEYWORDS = ["customer success", "operations manager", "customer experience"]


def detect_ip_block(response):
    """
    Detect if Naukri has blocked our IP.
    Returns (is_blocked: bool, reason: str)
    """
    # HTTP-level blocks
    if response.status_code == 403:
        return True, "HTTP 403 Forbidden"
    if response.status_code == 429:
        return True, "HTTP 429 Too Many Requests"
    if response.status_code == 503:
        return True, "HTTP 503 Service Unavailable"

    # Content-level blocks
    content = response.text[:2000].lower()
    block_signals = [
        "captcha", "recaptcha", "cf-challenge", "cloudflare",
        "access denied", "blocked", "suspicious activity",
        "rate limit", "too many requests", "please verify",
        "bot detection", "human verification",
    ]
    for signal in block_signals:
        if signal in content:
            return True, f"Content block signal: '{signal}'"

    # Check if response is HTML when we expected JSON
    content_type = response.headers.get("Content-Type", "")
    if "text/html" in content_type and response.status_code == 200:
        # Naukri API should return JSON, HTML = probably a block page
        if "jobPostings" not in content and "noOfJobs" not in content:
            return True, "Unexpected HTML response (likely block page)"

    return False, ""


def fetch_naukri():
    """
    Light Naukri scrape — max 5-10 jobs from India.
    Uses Naukri's internal job search API with careful IP protection.
    """
    all_jobs = []
    session = get_session(rotate_ua=True)

    # Add Naukri-specific headers
    session.headers.update({
        "Accept": "application/json",
        "Referer": "https://www.naukri.com/",
        "Origin": "https://www.naukri.com",
        "sec-ch-ua": '"Not_A Brand";v="8", "Chromium";v="120"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-origin",
    })

    ip_blocked = False

    for keyword in NAUKRI_KEYWORDS:
        if ip_blocked:
            break

        if len(all_jobs) >= NAUKRI_MAX_JOBS:
            break

        try:
            # Polite delay with jitter
            time.sleep(random.uniform(2.0, 4.0))

            # Naukri search API
            search_url = "https://www.naukri.com/jobapi/v3/search"
            params = {
                "noOfResults": 5,  # Conservative — only 5 per keyword
                "urlType": "search_by_keyword",
                "searchType": "adv",
                "keyword": keyword,
                "location": "india",
                "jobAge": 7,  # Last 7 days only
                "experience": 3,  # 3+ years
            }

            resp = session.get(search_url, params=params, timeout=NETWORK_TIMEOUT)

            # IP block detection
            blocked, reason = detect_ip_block(resp)
            if blocked:
                logger.warning(f"Naukri IP BLOCK detected: {reason}")
                logger.warning("Stopping Naukri scraping to protect IP")
                ip_blocked = True
                break

            resp.raise_for_status()

            try:
                data = resp.json()
            except Exception:
                logger.warning("Naukri returned non-JSON response, stopping")
                ip_blocked = True
                break

            postings = data.get("jobDetails", [])

            for p in postings:
                if len(all_jobs) >= NAUKRI_MAX_JOBS:
                    break

                title = p.get("title", "").strip()
                company = p.get("companyName", "Unknown").strip()
                job_id = p.get("jobId", "")

                if not title:
                    continue

                # Build URL
                apply_url = f"https://www.naukri.com/job-listings-{job_id}" if job_id else ""

                # Description
                snippet = strip_html(p.get("jobDescription", ""))[:400]

                # Location
                location = ""
                places = p.get("placeholders", [])
                for ph in places:
                    if isinstance(ph, dict) and ph.get("type") == "location":
                        location = ph.get("label", "")

                all_jobs.append({
                    "title": title,
                    "company": company,
                    "summary": snippet,
                    "apply_url": apply_url,
                    "source": "Naukri",
                    "location": location,
                })

            logger.info(f"Naukri/'{keyword}': {len(postings)} results")

        except requests.Timeout:
            logger.warning(f"Naukri timeout for '{keyword}'")
            continue

        except requests.RequestException as e:
            error_str = str(e).lower()
            if "403" in error_str or "429" in error_str:
                logger.warning(f"Naukri request blocked: {e}")
                ip_blocked = True
                break
            logger.warning(f"Naukri request failed: {e}")
            continue

        except Exception as e:
            logger.warning(f"Naukri unexpected error: {e}")
            continue

    if ip_blocked:
        logger.warning(f"Naukri: stopped early due to IP block — got {len(all_jobs)} jobs before block")
    else:
        logger.info(f"Naukri total: {len(all_jobs)} jobs")

    return all_jobs


# ============================================
# MAIN FETCH
# ============================================

def fetch_all(output_path=None):
    """Fetch jobs from all sources and save to JSON."""
    output_path = output_path or OUTPUT_DEFAULT
    all_jobs = []

    logger.info("=" * 60)
    logger.info("Starting job fetch from all sources")
    logger.info("=" * 60)

    # ---- WeWorkRemotely (RSS) ----
    for feed_url in WWR_FEEDS:
        try:
            jobs = parse_rss(feed_url, "WeWorkRemotely")
            all_jobs.extend(jobs)
        except Exception as e:
            logger.error(f"WWR feed failed: {e}")

    # ---- RemoteOK (RSS) ----
    try:
        jobs = parse_rss(REMOTEOK_URL, "RemoteOK")
        all_jobs.extend(jobs)
    except Exception as e:
        logger.error(f"RemoteOK failed: {e}")

    # ---- Remotive (API) ----
    try:
        all_jobs.extend(fetch_remotive())
    except Exception as e:
        logger.error(f"Remotive failed: {e}")

    # ---- Greenhouse (API) ----
    try:
        all_jobs.extend(fetch_greenhouse())
    except Exception as e:
        logger.error(f"Greenhouse failed: {e}")

    # ---- Lever (API) ----
    try:
        all_jobs.extend(fetch_lever())
    except Exception as e:
        logger.error(f"Lever failed: {e}")

    # ---- Ashby (API) ----
    try:
        all_jobs.extend(fetch_ashby())
    except Exception as e:
        logger.error(f"Ashby failed: {e}")

    # ---- Workday (API) ----
    try:
        all_jobs.extend(fetch_workday())
    except Exception as e:
        logger.error(f"Workday failed: {e}")

    # ---- Naukri (light scrape) ----
    try:
        all_jobs.extend(fetch_naukri())
    except Exception as e:
        logger.error(f"Naukri failed: {e}")

    # ---- Validate ----
    if not all_jobs:
        raise RuntimeError("Could not fetch jobs from any source. Check your internet.")

    # ---- Source breakdown ----
    sources = {}
    for j in all_jobs:
        s = j.get("source", "Unknown")
        sources[s] = sources.get(s, 0) + 1

    logger.info("=" * 60)
    logger.info(f"Total: {len(all_jobs)} jobs")
    for src, count in sorted(sources.items()):
        logger.info(f"  {src}: {count}")
    logger.info("=" * 60)

    # ---- Save ----
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(all_jobs, f, indent=2, ensure_ascii=False)

    logger.info(f"Saved to {output_path}")
    return all_jobs


# ============================================
# CLI
# ============================================

if __name__ == "__main__":
    import sys
    try:
        output = sys.argv[1] if len(sys.argv) > 1 else OUTPUT_DEFAULT
        jobs = fetch_all(output_path=output)
        print(f"\n✅ {len(jobs)} jobs fetched")

        sources = {}
        for j in jobs:
            s = j.get("source", "?")
            sources[s] = sources.get(s, 0) + 1
        for src, ct in sorted(sources.items()):
            print(f"  {src}: {ct}")

    except Exception as e:
        print(f"\n❌ {e}")
        sys.exit(1)
