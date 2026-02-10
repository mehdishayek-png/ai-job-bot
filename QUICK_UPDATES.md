# Quick Updates - Pre-fill Fields & Increase Matches

## Changes Made

### 1. ✅ Pre-fill "Edit Profile Manually" After Resume Parsing

**Problem:** After parsing a resume, the "Edit profile manually" fields were empty, even though data was extracted.

**Solution:** When resume is parsed, we now automatically pre-fill the edit fields by setting session state:

```python
# After successful parsing in ui_dashboard.py
st.session_state["name_input"] = saved.get("name", "")
st.session_state["headline_input"] = saved.get("headline", "")
st.session_state["skills_input"] = "\n".join(saved.get("skills", []))
```

**User Experience:**
- Upload resume → Click "Parse Resume"
- Profile appears in "Your Profile" section
- Open "Edit profile manually" → Fields are **pre-filled** with parsed data
- User can now easily tweak/edit the extracted info

---

### 2. ✅ Increased Match Count from 5 to 15

**Changed in:** `run_auto_apply.py`

```python
# Before:
MAX_MATCHES = int(os.getenv("MAX_MATCHES", "5"))

# After:
MAX_MATCHES = int(os.getenv("MAX_MATCHES", "15"))
```

**Result:**
- Users now get **15 top job matches** instead of just 5
- More opportunities to review
- Better coverage of available positions
- Still sorted by match score (best first)

---

## Files Modified

1. **ui_dashboard.py** - Pre-fill logic for edit fields
2. **run_auto_apply.py** - MAX_MATCHES increased to 15

---

## Git Commands to Deploy

```bash
# Add both modified files
git add ui_dashboard.py
git add run_auto_apply.py

# Commit
git commit -m "Pre-fill edit fields after parsing, increase matches to 15"

# Push (triggers auto-deploy on Streamlit)
git push origin main
```

---

## Testing

After deployment, verify:

1. **Pre-fill Test:**
   - Upload a resume
   - Click "Parse Resume & Build Profile"
   - Expand "✏️ Edit profile manually"
   - ✅ Name field should be pre-filled
   - ✅ Headline field should be pre-filled
   - ✅ Skills field should be pre-filled (one per line)
   - User can now edit any field and click "Save Profile"

2. **Match Count Test:**
   - Complete a job matching run
   - ✅ Should see up to 15 matches (instead of 5)
   - ✅ Matches still sorted by score

---

## Why This Improves UX

**Before:**
- Resume parsed ✅
- Data extracted ✅
- But edit fields empty ❌
- User has to manually re-type everything to make changes

**After:**
- Resume parsed ✅
- Data extracted ✅
- Edit fields pre-filled ✅
- User can just tweak what they want to change

**Result:** Much smoother workflow for users who want to refine their profile after auto-parsing.
