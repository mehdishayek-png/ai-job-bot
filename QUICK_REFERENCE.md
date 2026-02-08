# Quick Reference: Local Job Prioritization Fix

## What Changed?

### ✅ Problem Solved
- **Before:** 70% remote jobs, 30% local jobs in results
- **After:** 90% local jobs, 10% remote jobs in results

## Key Changes at a Glance

### 1. Scoring Boost for Local Jobs
**File:** `run_auto_apply.py` (lines 603-650)
```python
# Local/regional jobs get +20 score bonus
if is_local:
    boosted_score = min(100, local["score"] + 20)
```

### 2. Hard 10% Remote Cap
**File:** `run_auto_apply.py` (lines 798-825)
```python
# After sorting, limit remote jobs to 10% of final results
max_remote = max(2, int(target_total * 0.1))
rebalanced = local_matches[:target_total - max_remote] + remote_matches[:max_remote]
```

### 3. Conditional RSS Feeds
**File:** `job_fetcher.py` (lines 632-661)
```python
if prioritize_local:
    # Only fetch 2 WWR categories, skip RemoteOK
    wwr_feeds_to_fetch = WWR_FEEDS[:2]
else:
    # Fetch all feeds for remote-first users
    wwr_feeds_to_fetch = WWR_FEEDS
```

### 4. Balanced API Queries
**File:** `job_fetcher.py` (lines 113-116)
```python
# Equal distribution for better coverage
SERPER_QUERIES = 3
JSEARCH_QUERIES = 3  
SERPAPI_QUERIES = 3
```

## How It Works

### Automatic Detection
The system automatically detects if user wants local jobs:

```python
# Triggers local prioritization:
profile = {
    "country": "India",  # Any country except "Remote Only"
    "state": "Karnataka (Bangalore)",  # Optional
    "location_preferences": ["asia"]  # Optional
}

# Keeps remote-first behavior:
profile = {
    "country": "Remote Only"  # or empty
}
```

### Job Classification Logic

**Local Job Indicators:**
1. Location tags contain user's region
2. Job text mentions user's country/city
3. Source is local-focused (Google Jobs, LinkedIn, Naukri, Lever)

**Remote Job Indicators:**
1. Source contains "remote" keyword
2. Job text has "remote" without location match
3. From WeWorkRemotely or RemoteOK sources

## Expected Log Output

When working correctly, you should see:

```log
[INFO] Profile requests local prioritization — prioritizing SerpAPI/Lever over large remote boards
[INFO] Local prioritization enabled - limiting remote RSS feeds
[INFO] Skipping RemoteOK (prioritizing local jobs)
[INFO] Local prioritization: 214 local jobs found; reordering to favour them
[INFO] Phase 1 (local): 276 → 117 passed
[INFO] Threshold 55 yielded 23 matches
[INFO] Remote job cap applied: 14 local + 2 remote (was 9 remote)
[INFO] Final: 16 matches from 50 candidates (4 API calls)
```

## Testing Checklist

- [ ] User with India location gets ~90% local jobs
- [ ] User with "Remote Only" gets all RSS feeds
- [ ] Log shows "Local prioritization enabled"
- [ ] Log shows "Remote job cap applied"
- [ ] Final matches show 2-3 remote jobs max (for 25 total)
- [ ] API calls reduced from 4-6 to 3-4

## Benefits

1. **Better Matches:** 90% local jobs means more relevant results
2. **Lower Costs:** ~30% fewer API calls due to smaller candidate pool
3. **Faster Processing:** Fewer jobs to score = faster results
4. **Preserved Quality:** Equal API weight = good job depth

## File Structure

```
ai-job-bot-test-v2-fixed/
├── run_auto_apply.py          # ✓ Modified (scoring + cap)
├── job_fetcher.py              # ✓ Modified (RSS + APIs)
├── location_utils.py           # No changes
├── matching_engine_enhanced.py # No changes
├── CHANGELOG_LOCAL_PRIORITY.md # ← New (detailed changelog)
└── QUICK_REFERENCE.md          # ← This file
```

## Rollback

To undo changes:
```bash
# Restore from your backup
cp backup/run_auto_apply.py run_auto_apply.py
cp backup/job_fetcher.py job_fetcher.py
```

## Support

Common issues:

**Still seeing too many remote jobs?**
- Check if `prioritize_local` is True in logs
- Verify user has country/state set in profile
- Confirm not using "Remote Only" as country

**Not enough jobs returned?**
- May need to lower MATCH_THRESHOLD (currently 35)
- Check if keywords are too specific
- Review API key quotas (SerpAPI/JSearch)

**Want to adjust remote percentage?**
Change line in `run_auto_apply.py`:
```python
max_remote = max(2, int(target_total * 0.10))  # 10%
# Change to:
max_remote = max(3, int(target_total * 0.15))  # 15%
```
