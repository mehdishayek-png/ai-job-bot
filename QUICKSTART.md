# Quick Start - V3 Fixed

## 🚀 Get Running in 3 Minutes

### Step 1: Install Dependencies (30 seconds)
```bash
pip install -r requirements.txt
```

### Step 2: Get API Keys (90 seconds)

**Required keys:**

1. **Serper.dev** (primary job search):
   - Go to https://serper.dev/
   - Sign up (free)
   - Get API key
   - 2,500 free searches/month

2. **OpenRouter** (LLM for matching):
   - Go to https://openrouter.ai/
   - Sign up (free)
   - Get API key
   - ~$0.02 per session

**Optional:**

3. **SerpAPI** (fallback):
   - Go to https://serpapi.com/
   - 100 free searches/month
   - Only needed if Serper.dev fails

### Step 3: Configure (30 seconds)

Create `.env` file:
```bash
cp .env.example .env
# Edit .env and add your keys
```

Your `.env` should look like:
```env
OPENROUTER_API_KEY=sk-or-v1-xxxxx
SERPER_API_KEY=xxxxx
SERPAPI_KEY=xxxxx  # Optional
```

### Step 4: Run! (30 seconds)
```bash
streamlit run ui_dashboard.py
```

Navigate to `http://localhost:8501`

---

## ✅ Verify the Fix Works

### Test 1: Run job fetcher directly
```bash
python job_fetcher.py
```

**Expected output:**
```
Serper.dev: Searching 'remote analyst India'
Serper.dev: 'remote analyst India' -> 10 new jobs
...
Source breakdown:
  LinkedIn: 15
  Naukri: 10
  Indeed: 8
  Google Jobs: 12
```

**✅ Good signs:**
- Multiple sources (not all "Unknown")
- Real company names
- 40-60 jobs total

**❌ Bad signs:**
- All companies "Unknown"
- Titles like "92 jobs available"
- Only 5-10 jobs total

### Test 2: Run full matching
1. Upload your resume
2. Click "Start Matching"
3. Wait 30-60 seconds

**Expected results:**
- 20-30 matches
- Real company names (not "Unknown")
- Clean job titles
- Direct apply links

**If you get only 3-5 matches:**
- Check your skills are specific (not soft skills)
- Verify API keys are correct
- Check terminal for errors

---

## 🔍 What Changed vs V3 Original?

**One line fix in job_fetcher.py:**

```python
# Line 390
# OLD: "https://google.serper.dev/search"
# NEW: "https://google.serper.dev/jobs"
```

**Plus updated parsing (lines 408-465):**
- Was: Parsing `data["organic"]` (web search results)
- Now: Parsing `data["jobs"]` (actual job postings)

**Result:**
- V3 Original: 5 matches (garbage data, all "Unknown")
- V3 Fixed: 25+ matches (real companies, clean titles)

---

## 🎯 Quick Comparison

| Version | Jobs Fetched | Companies | Matches | API Cost |
|---------|-------------|-----------|---------|----------|
| **V2** | 107 | ✅ Real | 25 | 100 free/mo |
| **V3 Original** | 104 | ❌ All "Unknown" | 5 | 2500 free/mo |
| **V3 Fixed** | ~105 | ✅ Real | 25+ | 2500 free/mo |

**Winner:** V3 Fixed (25x more free searches, same quality)

---

## 💡 Pro Tips

### Get Better Results:
1. **Be specific with skills:**
   - ✅ "Python", "React", "Salesforce", "SQL"
   - ❌ "communication", "leadership", "team player"

2. **Update location preferences:**
   - Select your city in profile
   - Enables local job search
   - Gets better targeted results

3. **Run daily:**
   - Job boards update daily
   - Fresh listings every 24h
   - 2,500 free searches/month = ~80/day

### Save API Credits:
```python
# In job_fetcher.py, adjust:
SERPAPI_MAX_QUERIES = 6  # Lower for fewer API calls
LEVER_PER_COMPANY = 10   # Reduce from 20 if needed
```

### Monitor Usage:
- Serper.dev: Check dashboard for remaining searches
- OpenRouter: Check billing for API costs
- SerpAPI: Check dashboard (fallback only)

---

## 🐛 Troubleshooting

### "No API key" error:
```bash
# Check .env file exists
ls -la .env

# Check keys are set
cat .env | grep API_KEY
```

### "401 Unauthorized":
Your API key is wrong. Re-copy from provider.

### "429 Rate Limit":
You've used all free searches. Wait until next month or upgrade.

### Still getting "Unknown" companies:
You're using the old V3 file! Use the **fixed** version.

### Only 5 matches:
Your skills may be too niche. Add more general skills to profile.

---

## 📞 Need Help?

**Common Questions:**

**Q: Is this better than V2?**
A: Yes - same quality, 25x more free searches

**Q: Do I need SerpAPI key?**
A: No - only needed if Serper.dev fails (rare)

**Q: Why Serper.dev over SerpAPI?**
A: 2,500 vs 100 free searches/month (25x more)

**Q: Will this work for remote-only jobs?**
A: Yes - set job preference to "Remote Only"

**Q: Can I use both V2 and V3?**
A: Yes - they're separate codebases

---

## 🎉 You're Ready!

1. ✅ Dependencies installed
2. ✅ API keys configured
3. ✅ Fix verified
4. ✅ App running

**Start job hunting! 🚀**
