# AI Job Application Bot - Streamlit Cloud Deployment

## 🔧 Files Modified for Streamlit Cloud

The following files have been updated to work with Streamlit Cloud secrets:

1. **cover_letter_generator.py** - Added Streamlit secrets support
2. **run_auto_apply.py** - Added Streamlit secrets support + error handling
3. **run_batch.py** - Added Streamlit secrets support
4. **semantic_matcher.py** - Added Streamlit secrets support + removed hardcoded API key
5. **ui_dashboard.py** - Major refactor with proper error handling and Streamlit integration

## 🚀 Deployment Steps

### 1. Add Your API Key to Streamlit Cloud

Go to your Streamlit Cloud dashboard → Your app → Settings → Secrets

Add this:

```toml
OPENROUTER_API_KEY = "your-actual-api-key-here"
```

**Important:** 
- Use `=` not `:` 
- No quotes around the key name
- Replace `your-actual-api-key-here` with your real OpenRouter API key

### 2. Push These Fixed Files to Your GitHub Repo

Replace your existing files with these fixed versions:

```bash
# Navigate to your repo
cd ai-job-bot

# Copy the fixed files (overwrite existing)
# Then commit and push
git add .
git commit -m "Fix: Add Streamlit secrets support for deployment"
git push
```

### 3. Files That Work Both Locally and on Streamlit Cloud

All fixed files now:
- ✅ Try Streamlit secrets first (for cloud deployment)
- ✅ Fall back to .env file (for local development)
- ✅ Show clear error messages if API key is missing
- ✅ Include proper error handling for API calls

## 🔍 How It Works

### API Key Loading Pattern

```python
# Try Streamlit secrets first
try:
    import streamlit as st
    api_key = st.secrets["OPENROUTER_API_KEY"]
except (ImportError, KeyError, AttributeError):
    # Fall back to .env for local development
    load_dotenv()
    api_key = os.getenv("OPENROUTER_API_KEY")

# Validate
if not api_key:
    st.error("API key not found!")
    st.stop()
```

## 🐛 Debugging

### Check Streamlit Cloud Logs

1. Go to your app in Streamlit Cloud
2. Click the "⋮" menu (three dots)
3. Select "Logs"
4. Look for error messages

### Common Issues

**Issue:** "OPENROUTER_API_KEY not found"
- **Fix:** Add the secret in Streamlit Cloud settings

**Issue:** API calls failing instantly
- **Fix:** Check that your OpenRouter API key is valid and has credits

**Issue:** Extraction results empty
- **Fix:** Check logs for API errors, verify model name is correct

### Test Locally First

Before deploying, test locally:

```bash
# Make sure you have a .env file with:
# OPENROUTER_API_KEY=your-key-here

streamlit run ui_dashboard.py
```

## 📝 What Changed

### Key Improvements

1. **Removed hardcoded API keys** - Security issue fixed in semantic_matcher.py
2. **Added error handling** - All API calls now have try/catch blocks
3. **Better user feedback** - Shows errors in Streamlit UI instead of silent failures
4. **Dual environment support** - Works locally with .env and in cloud with secrets
5. **Debug messages** - UI now shows where API key is loaded from

### File-by-File Changes

**cover_letter_generator.py:**
- Added Streamlit secrets support (lines 11-25)
- Added error display in Streamlit UI (lines 106-111)

**run_auto_apply.py:**
- Added Streamlit secrets support (lines 20-35)
- Better error handling in scoring function
- Added run_auto_apply_pipeline() alias for UI compatibility

**run_batch.py:**
- Added Streamlit secrets support (lines 8-20)
- Added error handling for API calls

**semantic_matcher.py:**
- **CRITICAL:** Removed hardcoded API key (was a security risk!)
- Added Streamlit secrets support
- Added error handling

**ui_dashboard.py:**
- Complete refactor with API key validation at startup
- Better error messages and user guidance
- Progress indicators
- Download buttons for cover letters
- Proper exception handling throughout

## 📦 Requirements

Make sure your requirements.txt includes:

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

## 🎯 Usage

1. Upload your resume (PDF)
2. Click "Build Profile From Resume"
3. Edit skills/headline if needed
4. Click "Save Profile"
5. Click "Run Job Matching"
6. View matches and generated cover letters

## 💡 Tips

- Start with a small test to verify API connectivity
- Check logs frequently during initial deployment
- Make sure you have credits in your OpenRouter account
- The app creates `data/` and `output/` directories automatically

## 🆘 Still Having Issues?

If you're still having problems:

1. Check that OPENROUTER_API_KEY is spelled exactly right in secrets
2. Verify your API key works by testing it directly with OpenRouter
3. Look at the Streamlit Cloud logs for the actual error message
4. Make sure all files were updated (not just some)

---

**Need more help?** Share your Streamlit Cloud logs and I can help diagnose the issue!
