# Production Deployment Guide
## Critical Fixes Implementation

---

## 📋 Pre-Deployment Checklist

### ✅ Files to Replace

Replace these files with their fixed versions:

1. **run_auto_apply.py** → `run_auto_apply_fixed.py`
   - ✅ Job fetching integrated
   - ✅ Rate limiting added
   - ✅ Retry logic implemented
   - ✅ Cache collision fixes
   - ✅ Input validation
   - ✅ Logging infrastructure
   - ✅ Progress reporting

2. **job_fetcher.py** → `job_fetcher_fixed.py`
   - ✅ Network error handling
   - ✅ Timeout protection
   - ✅ Retry with exponential backoff
   - ✅ Response validation
   - ✅ Proper exception handling

3. **cover_letter_generator.py** → `cover_letter_generator_fixed.py`
   - ✅ Filename sanitization
   - ✅ Path traversal protection
   - ✅ Input validation
   - ✅ API key validation

4. **resume_parser.py** → Already fixed (from previous work)
5. **ui_dashboard.py** → Already fixed (from previous work)

---

## 🚀 Deployment Steps

### Step 1: Backup Current Files
```bash
# Create backup directory
mkdir -p backup/$(date +%Y%m%d)

# Backup current files
cp run_auto_apply.py backup/$(date +%Y%m%d)/
cp job_fetcher.py backup/$(date +%Y%m%d)/
cp cover_letter_generator.py backup/$(date +%Y%m%d)/
```

### Step 2: Deploy Fixed Files
```bash
# Replace with fixed versions
cp run_auto_apply_fixed.py run_auto_apply.py
cp job_fetcher_fixed.py job_fetcher.py
cp cover_letter_generator_fixed.py cover_letter_generator.py
```

### Step 3: Install Dependencies (if needed)
```bash
pip install --upgrade feedparser requests openai python-dotenv pdfplumber streamlit
```

### Step 4: Validate API Key
```bash
# Check .env file
cat .env | grep OPENROUTER_API_KEY

# Or for Streamlit Cloud, verify in settings
```

### Step 5: Test Locally
```bash
# Test job fetching
python job_fetcher.py

# Test with sample data
python run_auto_apply.py data/profile.json data/jobs.json

# Start Streamlit
streamlit run ui_dashboard.py
```

---

## 🧪 Critical Tests to Run

### Test 1: Job Fetching
```bash
# This should fetch ~100+ jobs from all sources
python job_fetcher.py test_jobs.json
```

**Expected Output:**
```
Successfully fetched 150+ jobs!
Breakdown by source:
  WeWorkRemotely: 80 jobs
  RemoteOK: 45 jobs
  Remotive: 30 jobs
```

**If It Fails:**
- Check internet connection
- Verify no firewall blocking
- Check if RSS feeds are accessible

---

### Test 2: End-to-End Pipeline
```bash
python run_auto_apply.py data/profile.json data/jobs.json
```

**Expected Output:**
```
✅ Success!
Matches found: 5 from 150 jobs

1. Acme Corp - Senior Customer Success Manager (95%)
2. TechCo - Customer Support Specialist (88%)
...
```

**If It Fails:**
- Check OPENROUTER_API_KEY is set
- Verify profile.json has skills
- Check logs for specific errors

---

### Test 3: Streamlit UI Flow

1. **Start Streamlit:**
   ```bash
   streamlit run ui_dashboard.py
   ```

2. **Upload Resume:**
   - Upload a PDF resume
   - Click "Parse Resume & Build Profile"
   - ✅ Verify name appears
   - ✅ Verify headline appears
   - ✅ Verify skills appear as chips

3. **Job Matching:**
   - Click "Start Matching"
   - ✅ Verify progress updates appear
   - ✅ Verify no crashes
   - ✅ Verify matches appear
   - ✅ Verify cover letters are generated

---

### Test 4: Edge Cases

#### Test 4a: Special Characters in Job Data
Create `test_edge_cases.py`:
```python
from cover_letter_generator import generate_cover_letter

# Test special characters
job = {
    "company": "Acme/Corp <Test>",
    "title": "Software Engineer: AI/ML | Remote",
    "summary": "Great job"
}

profile = {
    "name": "Test User",
    "headline": "Professional",
    "skills": ["python", "ai"]
}

path = generate_cover_letter(job, profile, "test_output")
print(f"✅ Generated: {path}")
# Should create safe filename without crashes
```

#### Test 4b: Network Failures
```bash
# Disconnect internet temporarily
# Run job fetcher
python job_fetcher.py

# Should fail gracefully with clear error message
```

#### Test 4c: Missing API Key
```bash
# Temporarily rename .env
mv .env .env.backup

python run_auto_apply.py data/profile.json data/jobs.json

# Should show clear error: "OPENROUTER_API_KEY not found"

# Restore
mv .env.backup .env
```

---

## 📊 Performance Benchmarks

### Expected Performance:
- **Job Fetching:** 30-60 seconds
- **Scoring 100 jobs:** 2-4 minutes (with rate limiting)
- **Cover letter generation:** 5-10 seconds per letter
- **Total pipeline:** 3-5 minutes for typical run

### Memory Usage:
- **Baseline:** ~100MB
- **During scoring:** ~300MB
- **Maximum:** Should stay under 500MB

### API Calls:
- **With empty cache:** 1 call per job (~100 calls)
- **With 50% cache hits:** ~50 calls
- **Rate:** Max 2 calls/second (protected)

---

## 🐛 Troubleshooting

### Issue: "Profile file missing"
**Solution:** Ensure profile.json exists and has valid format:
```json
{
  "name": "Your Name",
  "headline": "Your Title",
  "skills": ["skill1", "skill2"]
}
```

### Issue: "Could not fetch jobs from any source"
**Causes:**
- No internet connection
- Firewall blocking requests
- All RSS feeds are down (unlikely)

**Solution:**
- Check internet connectivity
- Try manually accessing RSS feeds in browser
- Check firewall settings

### Issue: Rate limit errors
**Solution:**
- Increase `API_RATE_LIMIT` in run_auto_apply.py
- Default is 0.5s, try 1.0s or 2.0s
```python
API_RATE_LIMIT = 1.0  # Wait 1 second between API calls
```

### Issue: "Filename too long" errors
**Solution:** Already fixed in cover_letter_generator_fixed.py
- Filenames are sanitized and truncated
- Should not occur with fixed version

### Issue: Cache file corrupted
**Solution:**
```bash
# Delete cache file
rm data/session_*/semantic_cache.json

# Will rebuild on next run
```

---

## 🔐 Security Checklist

- ✅ API key stored in environment variable (not hardcoded)
- ✅ Filename sanitization prevents path traversal
- ✅ File size limits prevent DoS
- ✅ Input validation on all user data
- ✅ No unsafe deserialization
- ✅ Proper error messages (no stack traces to users)

---

## 📈 Monitoring

### What to Monitor:

1. **API Usage:**
   - Track daily API calls
   - Monitor rate limit hits
   - Check for errors

2. **Job Fetching:**
   - Jobs fetched per source
   - Fetch success rate
   - Time to fetch

3. **Matching Quality:**
   - Average match scores
   - Number of matches per run
   - Cache hit rate

4. **Errors:**
   - Review logs daily
   - Track error types
   - Monitor crash rate

### Log Files:
```bash
# View logs
tail -f jobbot.log

# Search for errors
grep ERROR jobbot.log

# Count API calls
grep "Scored job" jobbot.log | wc -l
```

---

## 🆘 Rollback Plan

If deployment causes issues:

```bash
# Stop Streamlit
# (Ctrl+C in terminal)

# Restore backups
cp backup/$(date +%Y%m%d)/* .

# Restart
streamlit run ui_dashboard.py
```

---

## ✅ Post-Deployment Validation

### Day 1:
- [ ] Run end-to-end test successfully
- [ ] Upload real resume and verify parsing
- [ ] Complete one full matching cycle
- [ ] Verify cover letters generated correctly
- [ ] Check logs for any errors

### Day 3:
- [ ] Review API usage patterns
- [ ] Check cache hit rates
- [ ] Verify no memory leaks
- [ ] Confirm error handling working

### Week 1:
- [ ] Collect user feedback
- [ ] Review error logs
- [ ] Optimize rate limiting if needed
- [ ] Tune match threshold if needed

---

## 🎯 Success Criteria

The deployment is successful if:

✅ Job fetching works from at least 2/3 sources
✅ Resume parsing extracts name, headline, skills
✅ Job matching completes without crashes
✅ Cover letters generated for all matches
✅ No critical errors in logs
✅ API rate limits not exceeded
✅ User can complete full workflow

---

## 📞 Support

If you encounter issues:

1. Check logs: `jobbot.log`
2. Review `STRESS_TEST_REPORT.md` for known issues
3. Verify all fixes were applied correctly
4. Test individual components in isolation

---

## Next Steps

After successful deployment:

1. Monitor for 1 week
2. Collect metrics on performance
3. Gather user feedback
4. Plan next iteration of improvements

See `STRESS_TEST_REPORT.md` for medium/low priority improvements to implement in future releases.
