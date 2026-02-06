"""
Job Fetcher v3
==============
Sources: WWR, RemoteOK, Remotive, Greenhouse, Lever, Ashby, Workday, Naukri

Company boards now balanced across CX/ops AND engineering companies
so non-technical candidates actually find relevant roles.
"""

import feedparser
import requests
import json
import os
import re
import time
import random
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

OUTPUT_DEFAULT = "data/jobs.json"
NETWORK_TIMEOUT = 30
MAX_RETRIES = 2
RETRY_DELAY = 2


# ============================================
# HELPERS
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


USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 Version/17.2 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
]


def get_session(rotate_ua=False):
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
    "https://weworkremotely.com/categories/remote-customer-support-jobs.rss",
    "https://weworkremotely.com/categories/remote-marketing-jobs.rss",
    "https://weworkremotely.com/categories/remote-programming-jobs.rss",
    "https://weworkremotely.com/categories/remote-design-jobs.rss",
    "https://weworkremotely.com/categories/remote-devops-and-sysadmin-jobs.rss",
    "https://weworkremotely.com/categories/remote-product-jobs.rss",
    "https://weworkremotely.com/categories/remote-data-jobs.rss",
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
                    company, title = author, raw_title
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

            logger.info(f"{source}: {len(jobs)} jobs from {url.split('/')[-1]}")
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
# 3. Remotive (API)
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
# 4. Greenhouse (API — balanced boards)
# ============================================

# Mix of CX/ops companies AND tech companies
GREENHOUSE_BOARDS = [
    # CX / Support / Ops heavy
    "zendesk", "intercom", "hubspot", "freshworks", "aircall",
    "front", "dixa", "kustomer", "helpscout", "gorgias",
    "ada", "forethought", "assembled", "statuspage",
    # Product / SaaS (also hire CX/ops)
    "gitlab", "hashicorp", "datadog", "mongodb", "cloudflare",
    "twilio", "elastic", "notion", "airtable", "canva",
    "zapier", "gusto", "buffer", "automattic", "hotjar",
    "loom", "miro", "calendly", "typeform", "lattice",
]


GREENHOUSE_PER_BOARD_CAP = 50  # Don't pull 600+ jobs from one company


def fetch_greenhouse():
    all_jobs = []
    session = get_session()
    for board in GREENHOUSE_BOARDS:
        try:
            url = f"https://boards-api.greenhouse.io/v1/boards/{board}/jobs"
            resp = session.get(url, timeout=NETWORK_TIMEOUT, params={"content": "true"})
            if resp.status_code == 404:
                continue
            resp.raise_for_status()
            data = resp.json()
            count = 0
            for j in data.get("jobs", []):
                if count >= GREENHOUSE_PER_BOARD_CAP:
                    break
                title = j.get("title", "").strip()
                abs_url = j.get("absolute_url", "").strip()
                if not title or not abs_url:
                    continue
                loc = j.get("location", {})
                location_name = loc.get("name", "") if isinstance(loc, dict) else ""
                content = strip_html(j.get("content", ""))[:500]
                co = j.get("company", {})
                company_name = co.get("name", board.replace("-", " ").title()) if isinstance(co, dict) else board.replace("-", " ").title()
                all_jobs.append({
                    "title": title, "company": company_name,
                    "summary": content, "apply_url": abs_url,
                    "source": "Greenhouse", "location": location_name,
                })
                count += 1
            if count:
                capped = " (capped)" if count >= GREENHOUSE_PER_BOARD_CAP else ""
                logger.info(f"Greenhouse/{board}: {count}{capped}")
            time.sleep(0.3)
        except Exception as e:
            logger.warning(f"Greenhouse/{board}: {e}")
    logger.info(f"Greenhouse total: {len(all_jobs)} jobs")
    return all_jobs


# ============================================
# 5. Lever (API — balanced)
# ============================================

LEVER_COMPANIES = [
    # CX / Support / Ops heavy
    "intercom", "notion", "chainalysis", "plaid", "brex",
    "figma", "webflow", "rippling", "ramp", "mercury",
    "deel", "remote", "oysterhr", "papaya-global",
    # Tech (also hire CX/ops)
    "netflix", "stripe", "coinbase", "vercel", "supabase",
    "linear", "retool", "grafana-labs", "postman", "snyk",
]


def fetch_lever():
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
                cats = p.get("categories", {})
                location = cats.get("location", "") if isinstance(cats, dict) else ""
                desc_parts = []
                for lb in p.get("lists", []):
                    desc_parts.append(strip_html(lb.get("content", "")))
                desc = " ".join(desc_parts)[:500]
                if not desc:
                    desc = strip_html(p.get("descriptionPlain", ""))[:500]
                all_jobs.append({
                    "title": title, "company": company.replace("-", " ").title(),
                    "summary": desc, "apply_url": apply_url,
                    "source": "Lever", "location": location,
                })
                count += 1
            if count:
                logger.info(f"Lever/{company}: {count}")
            time.sleep(0.3)
        except Exception as e:
            logger.warning(f"Lever/{company}: {e}")
    logger.info(f"Lever total: {len(all_jobs)} jobs")
    return all_jobs


# ============================================
# 6. Ashby (API)
# ============================================

# Slugs must match exactly what's in jobs.ashbyhq.com/{slug}
# Case-sensitive! Found by checking each company's Ashby job board URL.
ASHBY_BOARDS = [
    "Ramp", "Notion", "Linear", "Vercel", "Mercury",
    "Deel", "Brex", "Plaid", "Retool", "Clerk",
    "OpenAI", "Anthropic", "Coda", "Anduril", "Abridge",
]


def fetch_ashby():
    all_jobs = []
    session = get_session()
    session.headers.update({"Accept": "application/json"})

    for board in ASHBY_BOARDS:
        try:
            url = f"https://api.ashbyhq.com/posting-api/job-board/{board}"
            resp = session.get(url, timeout=NETWORK_TIMEOUT)

            if resp.status_code == 404:
                logger.debug(f"Ashby/{board}: not found")
                continue
            if resp.status_code != 200:
                logger.warning(f"Ashby/{board}: HTTP {resp.status_code}")
                continue

            # Check content type — Ashby may return HTML instead of JSON
            ct = resp.headers.get("Content-Type", "")
            if "application/json" not in ct and "text/json" not in ct:
                logger.warning(f"Ashby/{board}: got {ct} instead of JSON, skipping")
                continue

            data = resp.json()
            count = 0
            for p in data.get("jobs", []):
                title = p.get("title", "").strip()
                job_url = p.get("jobUrl", "").strip()
                if not title or not job_url:
                    continue
                loc = p.get("location", "")
                desc = strip_html(p.get("descriptionHtml", p.get("descriptionPlain", "")))[:500]
                company_name = data.get("organizationName", board)
                all_jobs.append({
                    "title": title, "company": company_name,
                    "summary": desc, "apply_url": job_url,
                    "source": "Ashby",
                    "location": loc if isinstance(loc, str) else "",
                })
                count += 1
            if count:
                logger.info(f"Ashby/{board}: {count}")
            time.sleep(0.3)
        except ValueError as e:
            logger.warning(f"Ashby/{board}: JSON parse error — {e}")
        except Exception as e:
            logger.warning(f"Ashby/{board}: {e}")
    logger.info(f"Ashby total: {len(all_jobs)} jobs")
    return all_jobs


# ============================================
# 7. Workday (POST API)
# ============================================

# Format: (company_slug, wd_instance, site_path)
# URL: https://{slug}.{instance}.myworkdayjobs.com/wday/cxs/{slug}/{site}/jobs
# Verified from actual career pages
WORKDAY_BOARDS = [
    ("workday", "wd5", "Workday"),
    ("mastercard", "wd1", "CorporateCareers"),
    ("salesforce", "wd12", "External_Career_Site"),
    ("walmart", "wd5", "WalmartExternal"),
    ("adobe", "wd5", "external_experienced"),
    ("servicenow", "wd1", "Careers"),
]


def fetch_workday():
    all_jobs = []
    session = get_session()
    session.headers.update({"Content-Type": "application/json"})

    for company_slug, instance, site in WORKDAY_BOARDS:
        try:
            # Correct Workday public career site URL format
            base = f"https://{company_slug}.{instance}.myworkdayjobs.com"
            url = f"{base}/wday/cxs/{company_slug}/{site}/jobs"

            payload = {"appliedFacets": {}, "limit": 20, "offset": 0, "searchText": ""}
            resp = session.post(url, json=payload, timeout=NETWORK_TIMEOUT)

            if resp.status_code in (404, 403, 500, 503):
                logger.debug(f"Workday/{company_slug}: HTTP {resp.status_code}")
                continue

            resp.raise_for_status()
            data = resp.json()
            count = 0

            for p in data.get("jobPostings", []):
                title = p.get("title", "").strip()
                ext_path = p.get("externalPath", "")
                if not title or not ext_path:
                    continue
                apply_url = f"{base}/en-US{ext_path}"
                loc = p.get("locationsText", "")
                posted = p.get("postedOn", "")
                all_jobs.append({
                    "title": title,
                    "company": company_slug.replace("-", " ").title(),
                    "summary": f"Location: {loc}. Posted: {posted}".strip(),
                    "apply_url": apply_url, "source": "Workday", "location": loc,
                })
                count += 1
            if count:
                logger.info(f"Workday/{company_slug}: {count}")
            time.sleep(0.5)
        except Exception as e:
            logger.warning(f"Workday/{company_slug}: {e}")
    logger.info(f"Workday total: {len(all_jobs)} jobs")
    return all_jobs


# ============================================
# 8. Naukri (light scrape — max 10, IP-safe)
# ============================================

NAUKRI_MAX_JOBS = 10
# Broad search URLs — one per keyword, public page scrape not internal API
NAUKRI_SEARCHES = [
    "https://www.naukri.com/customer-experience-jobs?k=customer+experience&experience=2&jobAge=7",
    "https://www.naukri.com/customer-success-jobs?k=customer+success&experience=2&jobAge=7",
    "https://www.naukri.com/operations-manager-jobs?k=operations+manager&experience=2&jobAge=7",
]


def detect_ip_block(response):
    if response.status_code in (403, 429, 503):
        return True, f"HTTP {response.status_code}"
    content = response.text[:3000].lower()
    signals = ["captcha", "recaptcha", "cf-challenge", "cloudflare",
               "access denied", "blocked", "suspicious activity",
               "rate limit", "too many requests", "bot detection",
               "please verify you are a human"]
    for sig in signals:
        if sig in content:
            return True, f"Block signal: '{sig}'"
    return False, ""


def parse_naukri_html(html_text):
    """
    Parse Naukri search results from HTML.
    Naukri embeds job data in script tags as JSON.
    Falls back to regex parsing of article/job cards.
    """
    jobs = []

    # Method 1: Try to find embedded JSON in script tags
    json_match = re.search(r'"jobDetails"\s*:\s*(\[.+?\])\s*[,}]', html_text)
    if json_match:
        try:
            job_list = json.loads(json_match.group(1))
            for item in job_list:
                title = item.get("title", "").strip()
                company = item.get("companyName", "Unknown").strip()
                job_id = item.get("jobId", "")
                snippet = strip_html(item.get("jobDescription", ""))[:400]

                loc = ""
                for ph in item.get("placeholders", []):
                    if isinstance(ph, dict) and ph.get("type") == "location":
                        loc = ph.get("label", "")

                apply_url = f"https://www.naukri.com/job-listings-{job_id}" if job_id else ""

                if title:
                    jobs.append({
                        "title": title, "company": company, "summary": snippet,
                        "apply_url": apply_url, "source": "Naukri", "location": loc,
                    })
            return jobs
        except Exception:
            pass

    # Method 2: Regex fallback — extract from article tags
    articles = re.findall(
        r'class="[^"]*jobTuple[^"]*"[^>]*>.*?</article>',
        html_text, re.DOTALL | re.IGNORECASE
    )
    for article in articles[:10]:
        title_m = re.search(r'class="[^"]*title[^"]*"[^>]*>([^<]+)', article)
        company_m = re.search(r'class="[^"]*comp[^"]*"[^>]*>([^<]+)', article)
        url_m = re.search(r'href="(https://www\.naukri\.com/job-listings[^"]*)"', article)

        if title_m:
            jobs.append({
                "title": title_m.group(1).strip(),
                "company": company_m.group(1).strip() if company_m else "Unknown",
                "summary": "",
                "apply_url": url_m.group(1) if url_m else "",
                "source": "Naukri", "location": "",
            })

    return jobs


def fetch_naukri():
    """
    Light Naukri scrape — max 10 jobs from India.
    Scrapes public search result pages, not internal API.
    """
    all_jobs = []
    session = get_session(rotate_ua=True)

    # Naukri-specific headers to look like a real browser
    session.headers.update({
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Referer": "https://www.naukri.com/",
        "sec-ch-ua": '"Not_A Brand";v="8", "Chromium";v="120"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
        "sec-fetch-dest": "document",
        "sec-fetch-mode": "navigate",
        "sec-fetch-site": "same-origin",
        "Upgrade-Insecure-Requests": "1",
    })

    ip_blocked = False

    for search_url in NAUKRI_SEARCHES:
        if ip_blocked or len(all_jobs) >= NAUKRI_MAX_JOBS:
            break

        try:
            # Polite delay with jitter
            time.sleep(random.uniform(2.5, 5.0))

            resp = session.get(search_url, timeout=NETWORK_TIMEOUT)

            blocked, reason = detect_ip_block(resp)
            if blocked:
                logger.warning(f"Naukri IP BLOCK: {reason}")
                ip_blocked = True
                break

            if resp.status_code != 200:
                logger.warning(f"Naukri: HTTP {resp.status_code} for {search_url[:60]}")
                continue

            page_jobs = parse_naukri_html(resp.text)
            for j in page_jobs:
                if len(all_jobs) >= NAUKRI_MAX_JOBS:
                    break
                all_jobs.append(j)

            keyword = re.search(r'k=([^&]+)', search_url)
            kw_name = keyword.group(1).replace('+', ' ') if keyword else "?"
            logger.info(f"Naukri/'{kw_name}': {len(page_jobs)} jobs parsed")

        except requests.Timeout:
            logger.warning("Naukri: timeout")
        except requests.RequestException as e:
            if "403" in str(e) or "429" in str(e):
                ip_blocked = True
                break
            logger.warning(f"Naukri: {e}")
        except Exception as e:
            logger.warning(f"Naukri: {e}")

    if ip_blocked:
        logger.warning(f"Naukri: IP blocked — got {len(all_jobs)} before block")
    else:
        logger.info(f"Naukri total: {len(all_jobs)} jobs")
    return all_jobs


# ============================================
# MAIN FETCH
# ============================================

def fetch_all(output_path=None):
    output_path = output_path or OUTPUT_DEFAULT
    all_jobs = []

    logger.info("=" * 60)
    logger.info("Fetching jobs from all sources")
    logger.info("=" * 60)

    # RSS feeds
    for feed_url in WWR_FEEDS:
        try:
            all_jobs.extend(parse_rss(feed_url, "WeWorkRemotely"))
        except Exception as e:
            logger.error(f"WWR: {e}")

    try:
        all_jobs.extend(parse_rss(REMOTEOK_URL, "RemoteOK"))
    except Exception as e:
        logger.error(f"RemoteOK: {e}")

    # APIs
    for name, fn in [("Remotive", fetch_remotive), ("Greenhouse", fetch_greenhouse),
                     ("Lever", fetch_lever), ("Ashby", fetch_ashby),
                     ("Workday", fetch_workday), ("Naukri", fetch_naukri)]:
        try:
            all_jobs.extend(fn())
        except Exception as e:
            logger.error(f"{name}: {e}")

    if not all_jobs:
        raise RuntimeError("No jobs from any source. Check internet.")

    # Breakdown
    sources = {}
    for j in all_jobs:
        s = j.get("source", "?")
        sources[s] = sources.get(s, 0) + 1
    logger.info("=" * 60)
    logger.info(f"Total: {len(all_jobs)} jobs")
    for src, ct in sorted(sources.items()):
        logger.info(f"  {src}: {ct}")
    logger.info("=" * 60)

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(all_jobs, f, indent=2, ensure_ascii=False)
    logger.info(f"Saved to {output_path}")
    return all_jobs


if __name__ == "__main__":
    import sys
    try:
        output = sys.argv[1] if len(sys.argv) > 1 else OUTPUT_DEFAULT
        jobs = fetch_all(output_path=output)
        print(f"\n✅ {len(jobs)} jobs")
        sources = {}
        for j in jobs:
            s = j.get("source", "?")
            sources[s] = sources.get(s, 0) + 1
        for src, ct in sorted(sources.items()):
            print(f"  {src}: {ct}")
    except Exception as e:
        print(f"\n❌ {e}")
        sys.exit(1)
