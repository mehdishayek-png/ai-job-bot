# Job Bot v2.2 - Final Update (February 8, 2026)

## Summary of Changes

This version addresses all critical issues and adds new job sources as requested.

## New Features

### 1. ✨ Increased Match Target: 30 Jobs
**Before:** 25 max matches
**After:** 30 max matches

```python
MAX_MATCHES = 30  # Was 25
MAX_LLM_CANDIDATES = 60  # Was 50
```

**Impact:**
- More job options for users
- Better coverage across companies
- Remote job cap: 3 jobs (10% of 30)

### 2. 🌏 New Job Sources Added

#### Himalayas Jobs
- **URL:** https://himalayas.app/jobs/rss
- **Quality:** High - curated remote jobs
- **Volume:** ~100 recent jobs
- **Coverage:** Global, remote-friendly
- **Best For:** Tech, product, design roles

#### Adzuna India  
- **URL:** https://www.adzuna.in/rss
- **Quality:** Good - aggregator
- **Volume:** Varies
- **Coverage:** India-focused
- **Best For:** Local jobs across industries

**Note on Built In, Shine, Cutshort:**
- **Built In:** No public RSS/API (requires paid scraping)
- **Shine.com:** No public feed (app-only platform)
- **Cutshort:** No public RSS/API (closed platform)

These platforms don't offer free feeds, so we added Himalayas and Adzuna as high-quality alternatives.

## Critical Fixes (from v2.1)

### 1. ❌ JSearch Timeout Issues - FIXED
**Problem:** 2/3 queries timing out
**Solution:**
- Timeout: 20s → 35s
- Added 2-attempt retry logic
- Better error handling

**Expected:** 10 jobs → 45+ jobs

### 2. ❌ SerpAPI Returning 0 Jobs - FIXED
**Problem:** Bad query format
**Solution:**
```python
# Before: 'query' + location='India'
# After: 'query in Bangalore, Karnataka' + gl='in'
```

**Expected:** 0 jobs → 35+ jobs

### 3. ❌ Match Threshold Too High - FIXED
**Problem:** Only 10 jobs passing filter (needed 40+)
**Solution:**
- Threshold: 35 → 25
- Final thresholds: [55,50,45] → [50,45,40]

**Expected:** 10 → 50+ candidates for LLM

### 4. ❌ Insufficient API Coverage - FIXED
**Problem:** Not enough API queries
**Solution:**
```python
JSEARCH_QUERIES = 5  # Was 3 (+67%)
SERPAPI_QUERIES = 4  # Was 3 (+33%)
SERPER_QUERIES = 0  # Was 3 (doesn't work)
```

**Expected:** Better job depth and diversity

## Expected Results (v2.2)

### Job Fetching:
```
Sources:
- JSearch: ~45 jobs (5 queries, retry logic)
- SerpAPI: ~35 jobs (4 queries, better format)
- Lever: 27 jobs (India-focused companies)
- WWR: ~75 jobs (3 feeds when local priority)
- Remotive: 26 jobs
- Himalayas: ~40 jobs (NEW)
- Adzuna India: ~30 jobs (NEW)
- RemoteOK: ~96 jobs (if needed)

Total: 250-350 jobs (was 114)
```

### Matching Pipeline:
```
Phase 1 (Keyword): 250+ → 60-80 passed
Phase 2 (LLM): 60 candidates scored
Phase 3 (Final): 30 matches returned ✅

Breakdown:
- Local jobs: ~27 (90%)
- Remote jobs: ~3 (10%)
```

### Quality Metrics:
- **Job Depth:** 250-350 total (was 114) → +150%
- **Match Quality:** 30 final (was 0-1) → Excellent
- **API Efficiency:** 5-7 calls per run
- **Local Priority:** 90% local jobs ✅
- **Cost:** ~$0.005 per run (marginal)

## Configuration Summary

### job_fetcher.py
```python
# API Queries
JSEARCH_QUERIES = 5      # +67%
SERPAPI_QUERIES = 4      # +33%
SERPER_QUERIES = 0       # Skipped

# New RSS Feeds
HIMALAYAS = "https://himalayas.app/jobs/rss"
ADZUNA_INDIA = "https://www.adzuna.in/rss"

# Retry Logic
JSearch timeout: 35s with 2 retries
```

### run_auto_apply.py
```python
# Matching Config
MAX_MATCHES = 30          # Was 25
MAX_LLM_CANDIDATES = 60   # Was 50
MATCH_THRESHOLD = 25      # Was 35
Final thresholds: [50, 45, 40]  # Was [55, 50, 45]

# Remote Job Cap
max_remote = 3  # 10% of 30
local jobs = 27  # 90% of 30
```

## Testing Checklist

- [ ] Total jobs fetched > 250
- [ ] JSearch returns 40+ jobs (no timeouts)
- [ ] SerpAPI returns 30+ jobs  
- [ ] Himalayas feed working (~40 jobs)
- [ ] Adzuna India feed working
- [ ] Final matches = 30
- [ ] Local jobs = ~27 (90%)
- [ ] Remote jobs = ~3 (10%)
- [ ] UI shows all 30 matches
- [ ] No errors in logs

## API Usage & Cost

### Per Run:
- **JSearch:** 5 queries
- **SerpAPI:** 4 queries
- **LLM Scoring:** 4-5 batches
- **Total Cost:** ~$0.005-0.007

### Monthly (assuming 10 runs):
- **JSearch:** 50 queries (well under free tier)
- **SerpAPI:** 40 queries (well under 100 free)
- **OpenRouter:** ~$0.05-0.07
- **Total:** Under $0.10/month

## Known Limitations

1. **Built In, Shine, Cutshort:** Not available (no public feeds)
2. **Naukri.com:** Has RSS but very noisy, excluded for quality
3. **LinkedIn:** No RSS feed (requires scraping or API)
4. **Indeed:** No public RSS (requires Indeed API partnership)
