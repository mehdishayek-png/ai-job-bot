import os
import re
import logging
from openai import OpenAI
from dotenv import load_dotenv

# ============================================
# LOGGING SETUP
# ============================================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ============================================
# LOAD API KEY
# ============================================

load_dotenv()

api_key = os.getenv("OPENROUTER_API_KEY")
if not api_key:
    # Try Streamlit secrets
    try:
        import streamlit as st
        api_key = st.secrets.get("OPENROUTER_API_KEY")
    except (ImportError, KeyError, AttributeError):
        pass

if not api_key:
    raise ValueError(
        "OPENROUTER_API_KEY not found. "
        "Set it in .env file or Streamlit secrets."
    )

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=api_key,
)

MODEL = os.getenv("COVER_LETTER_MODEL", "google/gemini-2.0-flash-001")

# ============================================
# HTML STRIPPING
# ============================================

def strip_html(text: str) -> str:
    """Remove HTML tags and decode entities from text."""
    if not text:
        return ""
    clean = re.sub(r'<[^>]+>', ' ', text)
    clean = clean.replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>')
    clean = clean.replace('&quot;', '"').replace('&#39;', "'").replace('&nbsp;', ' ')
    clean = re.sub(r'\s+', ' ', clean).strip()
    return clean

# ============================================
# FILENAME SANITIZATION
# ============================================

def sanitize_filename(name: str, max_length: int = 100) -> str:
    """
    Sanitize filename to prevent filesystem errors and security issues.
    
    Args:
        name: Original filename
        max_length: Maximum length for filename
        
    Returns:
        str: Safe filename
    """
    if not name:
        return "unnamed"
    
    # Remove path separators and dangerous characters
    # Invalid chars for Windows: < > : " / \ | ? *
    # Also remove control characters
    name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '', name)
    
    # Replace spaces and multiple underscores
    name = re.sub(r'\s+', '_', name)
    name = re.sub(r'_+', '_', name)
    
    # Remove leading/trailing dots and spaces (Windows issues)
    name = name.strip('. ')
    
    # Limit length
    if len(name) > max_length:
        name = name[:max_length]
    
    # Ensure we have something left
    if not name:
        return "unnamed"
    
    return name


# ============================================
# COVER LETTER GENERATION
# ============================================

def generate_cover_letter(job: dict, profile: dict, output_dir: str) -> str:
    """
    Generate a tailored cover letter for a job.
    
    Args:
        job: Job dictionary with title, company, summary
        profile: Profile dictionary with name, headline, skills
        output_dir: Directory to save cover letter
        
    Returns:
        str: Path to generated cover letter file
    """
    
    try:
        os.makedirs(output_dir, exist_ok=True)
        
        # Validate inputs
        company = job.get("company", "Unknown Company")
        title = job.get("title", "Unknown Position")
        summary = strip_html(job.get("summary", ""))[:2000]  # Strip HTML + truncate
        
        name = profile.get("name", "Candidate")
        headline = profile.get("headline", "Professional")
        skills = profile.get("skills", [])
        
        # Ensure skills is a list
        if not isinstance(skills, list):
            logger.warning("Skills is not a list in profile")
            skills = []
        
        skills_str = ", ".join(str(s) for s in skills[:20])  # Limit to 20 skills
        
        # Build prompt
        prompt = f"""
Write a concise, tailored cover letter.

Rules:
- 2 paragraphs
- 70-90 words
- Professional but human tone
- No placeholders or template language
- Focus on relevant skills and experience

Candidate:
Name: {name}
Headline: {headline}
Skills: {skills_str}

Job:
Title: {title}
Company: {company}
Description: {summary}

Write the cover letter:
"""

        logger.info(f"Generating cover letter for {company} - {title}")
        
        # Generate with API
        res = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=250,
        )

        text = res.choices[0].message.content.strip()
        
        # Clean up common issues
        text = text.replace("[Your Name]", name)
        text = text.replace("[Company Name]", company)
        text = text.replace("[Position]", title)
        
        # Create safe filename
        safe_company = sanitize_filename(company, max_length=50)
        safe_title = sanitize_filename(title, max_length=50)
        fname = f"{safe_company}__{safe_title}.txt"
        
        path = os.path.join(output_dir, fname)
        
        # Prevent directory traversal
        # Ensure the final path is inside output_dir
        abs_output_dir = os.path.abspath(output_dir)
        abs_path = os.path.abspath(path)
        
        if not abs_path.startswith(abs_output_dir):
            logger.error(f"Attempted path traversal: {path}")
            raise ValueError("Invalid filename - path traversal detected")
        
        # Write file
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)
        
        logger.info(f"Cover letter saved: {fname}")
        return path
    
    except Exception as e:
        logger.error(f"Cover letter generation failed for {job.get('company')} - {job.get('title')}: {e}")
        raise


# ============================================
# CLI TESTING
# ============================================

if __name__ == "__main__":
    import json
    import sys
    
    if len(sys.argv) < 3:
        print("Usage: python cover_letter_generator.py <job.json> <profile.json>")
        sys.exit(1)
    
    try:
        # Load job
        with open(sys.argv[1], "r") as f:
            job = json.load(f)
        
        # Load profile
        with open(sys.argv[2], "r") as f:
            profile = json.load(f)
        
        # Generate
        output_dir = "output/cover_letters"
        path = generate_cover_letter(job, profile, output_dir)
        
        print(f"\n✅ Cover letter generated!")
        print(f"Saved to: {path}")
        
        # Show preview
        with open(path, "r") as f:
            print(f"\nPreview:\n{f.read()}")
    
    except Exception as e:
        print(f"\n❌ Error: {e}")
        logger.exception("Cover letter generation failed")
        sys.exit(1)
