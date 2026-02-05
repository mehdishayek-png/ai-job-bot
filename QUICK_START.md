# 🚀 Quick Start Guide

## Step 1: Add Your API Key to Streamlit Cloud

1. Go to: https://share.streamlit.io/
2. Find your app
3. Click "Settings" (⚙️ icon)
4. Click "Secrets" in the left sidebar
5. Paste this (replace with your real key):

```toml
OPENROUTER_API_KEY = "sk-or-v1-your-actual-key-here"
```

6. Click "Save"

## Step 2: Upload Fixed Files to GitHub

Replace these 5 critical files in your repo:

### ⚠️ MUST UPDATE (Have API Key Changes):
1. ✅ `cover_letter_generator.py` 
2. ✅ `run_auto_apply.py`
3. ✅ `run_batch.py`
4. ✅ `semantic_matcher.py` (Had hardcoded API key - security issue!)
5. ✅ `ui_dashboard.py` (Major improvements)

### ℹ️ DON'T NEED TO UPDATE:
- `job_fetcher.py` (no changes)
- `resume_parser.py` (no changes)
- `resume_keyword_builder.py` (no changes)
- `startup_*.py` (no changes)
- `test_*.py` (no changes)

## Step 3: Test Your App

1. Open your Streamlit app URL
2. You should see: "✅ API key loaded from Streamlit secrets"
3. Upload a resume
4. Click "Build Profile From Resume"
5. Verify skills are extracted

## Troubleshooting

### Problem: "❌ OPENROUTER_API_KEY not found"
**Solution:** Go back to Step 1, make sure you:
- Used `=` not `:`
- Spelled OPENROUTER_API_KEY correctly
- Actually clicked "Save"

### Problem: Extraction results empty
**Solution:** 
1. Check Streamlit Cloud logs (⋮ menu → Logs)
2. Look for API errors
3. Verify your OpenRouter key has credits
4. Check if the model name is correct

### Problem: "Module not found" errors
**Solution:** Make sure `requirements.txt` includes:
```
streamlit
openai
requests
python-dotenv
pandas
numpy
scikit-learn
pdfplumber
pdfminer.six
beautifulsoup4
lxml
feedparser
```

## Quick Test

To verify everything works:

1. **API Key Loaded?**
   - Look for green message at top: "✅ API key loaded from Streamlit secrets"

2. **Upload Resume**
   - Should see: "Resume uploaded successfully"

3. **Parse Resume**
   - Click "Build Profile From Resume"
   - Should see: "✅ Profile built successfully!"
   - Skills should appear in left column

4. **If any step fails:**
   - Click ⋮ menu → Logs
   - Look for the error message
   - It will tell you exactly what went wrong

## Files in This Package

### 📋 Documentation
- `README_DEPLOYMENT.md` - Full deployment guide
- `CHANGES_SUMMARY.md` - Detailed list of all changes
- `QUICK_START.md` - This file

### 🔧 Fixed Python Files
- `cover_letter_generator.py` - ✅ Fixed
- `run_auto_apply.py` - ✅ Fixed
- `run_batch.py` - ✅ Fixed
- `semantic_matcher.py` - ✅ Fixed (removed hardcoded key!)
- `ui_dashboard.py` - ✅ Fixed (major refactor)

### 📦 Unchanged Files (Still Need These!)
- `job_fetcher.py`
- `resume_parser.py`
- `resume_keyword_builder.py`
- `startup_email_scraper.py`
- `startup_fetcher.py`
- `startup_domains.txt`
- `startup_contacts.csv`
- `test_*.py` files
- `requirements.txt`

## What Changed?

### The Problem
Your app worked locally but failed on Streamlit Cloud because:
1. It couldn't find `.env` file
2. API key wasn't configured for cloud
3. Errors weren't shown to users
4. One file had a hardcoded API key (security issue!)

### The Solution
Now the app:
1. ✅ Checks Streamlit secrets first
2. ✅ Falls back to .env for local dev
3. ✅ Shows clear error messages
4. ✅ Has proper error handling
5. ✅ Works on both local and cloud

## Need Help?

If you're stuck:
1. Check the error message in your app
2. Look at Streamlit Cloud logs
3. Read `README_DEPLOYMENT.md` for details
4. Make sure API key is spelled correctly in secrets

---

**Everything should work now!** 🎉

The key change: Your app now looks for `OPENROUTER_API_KEY` in Streamlit secrets instead of only looking for a local `.env` file.
