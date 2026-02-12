# AI Job Bot - Combined Version 🚀

## What's in This Package

This is the **combined version** with:
- ✅ **Enhanced Matching Engine v8** - The reliable semantic matching from RELIABLE_v2_BACKUP
- ✅ **Polished SVG UI** - The beautiful dark-themed interface from ai-job-bot-ui-svg-polish

## Key Features

### Matching Engine (matching_engine_enhanced.py)
- **Semantic Similarity**: Uses OpenAI embeddings for deep understanding
- **Weighted Skill Matching**: Exact matches score higher than partial matches
- **Title Similarity**: Matches job titles to your profile headline
- **Experience Alignment**: Filters out jobs that don't match your experience level
- **Negative Keyword Filtering**: Auto-removes jobs with disqualifying terms
- **Recency Boost**: Prioritizes recently posted jobs
- **Company Diversity**: Limits jobs per company to avoid spam

### UI Dashboard (ui_dashboard.py)
- **Modern Dark Theme**: Sleek, professional interface with glassmorphism effects
- **SVG-Matched Styling**: Consistent with modern design standards
- **Profile Management**: Easy setup and editing
- **Live Job Search**: Multiple sources (Google Jobs, LinkedIn, RSS feeds)
- **Match Scoring**: Visual breakdown of why jobs match
- **Cover Letter Generation**: AI-powered personalized cover letters
- **Export Options**: Download jobs as JSON or CSV

## Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Set Up API Keys
Create a `.env` file with:
```env
OPENROUTER_API_KEY=your_key_here
SERPAPI_KEY=your_key_here
```

### 3. Run the Dashboard
```bash
streamlit run ui_dashboard.py
```

### 4. Create Your Profile
1. Fill in your headline (e.g., "Senior Software Engineer")
2. Add your skills (e.g., "Python, React, AWS")
3. Select your experience level
4. Choose your preferences (remote, local, etc.)

### 5. Search for Jobs
Click "Search Jobs" and watch the magic happen!

## File Structure

```
combined-job-bot/
├── ui_dashboard.py              # Main Streamlit UI (polished version)
├── matching_engine_enhanced.py  # V8 matching engine (reliable version)
├── job_fetcher.py              # Multi-source job fetching
├── resume_parser.py            # Parse PDF/TXT resumes
├── cover_letter_generator.py   # AI cover letter generation
├── search_orchestrator.py      # Coordinates multi-source search
├── location_utils.py           # Location/distance calculations
├── semantic_matcher.py         # Additional semantic matching
├── requirements.txt            # Python dependencies
└── README_COMBINED.md          # This file
```

## Matching Algorithm Details

The matching engine uses a multi-factor scoring system (0-100):

1. **Semantic Similarity (0-30 points)**: Embeddings-based similarity
2. **Skill Matching (0-30 points)**: Weighted by match quality
3. **Title Similarity (0-20 points)**: Jaccard similarity of key words
4. **Experience Alignment (0-10 points)**: Matches your experience level
5. **Recency Boost (0-10 points)**: Favors recent postings

### Example Score Breakdown
```
Total Score: 78/100
├─ Semantic: 24/30 (Strong conceptual match)
├─ Skills: 28/30 (7 skills matched)
├─ Title: 16/20 (High title similarity)
├─ Experience: 5/10 (Acceptable level match)
└─ Recency: 5/10 (Posted 5 days ago)
```

## Configuration

### Environment Variables
- `MAX_MATCHES=30` - Number of jobs to return
- `MATCH_THRESHOLD=50` - Minimum score to include a job
- `MAX_PER_COMPANY=3` - Max jobs from same company
- `SCORING_MODEL=google/gemini-2.5-flash` - LLM for scoring

### Negative Keywords
Edit `NEGATIVE_KEYWORDS` in `matching_engine_enhanced.py` to auto-filter unwanted jobs:
```python
NEGATIVE_KEYWORDS = [
    "ceo", "cto", "founder",  # Too senior
    "crypto", "nft", "web3",  # Sketchy domains
    # Add your own here
]
```

## API Costs

This system is designed to be **ultra-cheap**:
- Embeddings: ~$0.02 per 1M tokens (OpenAI text-embedding-3-small)
- LLM Scoring: ~$0.10 per 1M tokens (Gemini Flash)
- Typical search: **< $0.05** for 100+ jobs matched

## Troubleshooting

### "OPENROUTER_API_KEY not found"
→ Create a `.env` file or add to Streamlit secrets

### No jobs found
→ Check that SERPAPI_KEY is set and valid
→ Try broader search terms in your profile

### Matches seem off
→ Adjust `MATCH_THRESHOLD` in `.env` (lower = more results)
→ Review and customize `NEGATIVE_KEYWORDS`

### UI looks broken
→ Clear browser cache and refresh
→ Try incognito mode
→ Check console for CSS errors

## Advanced Usage

### Custom Job Sources
Add RSS feeds or APIs in `job_fetcher.py`:
```python
CUSTOM_RSS = [
    "https://yourcompany.com/jobs/rss",
    # Add more here
]
```

### Batch Processing
```python
from matching_engine_enhanced import match_jobs_enhanced

profile = {"headline": "Data Scientist", "skills": ["Python", "ML"]}
jobs = [...]  # Your job list
matches = match_jobs_enhanced(jobs, profile, candidate_years=5)
```

### Export Matched Jobs
The UI includes export buttons:
- **JSON**: Full job data with scores
- **CSV**: Spreadsheet-friendly format

## What's Different from Original Versions?

### vs. RELIABLE_v2_BACKUP
- ✅ Same matching engine (identical)
- ✅ Much better UI (polished SVG theme)
- ✅ Same functionality, prettier interface

### vs. ai-job-bot-ui-svg-polish
- ✅ Same beautiful UI (identical)
- ✅ Already has the reliable matching engine
- ⚠️ Minor config differences (MAX_MATCHES=30 vs 25)

**Bottom line**: The ai-job-bot-ui-svg-polish version already had the good matching engine! This combined version is essentially the same, with documentation clarity.

## Version History

- **v2.2 (Current)**: Enhanced matching + SVG UI polish
- **v2.1**: Added semantic similarity
- **v2.0**: Multi-source job fetching
- **v1.0**: Basic keyword matching

## Credits

Built with:
- Streamlit (UI framework)
- OpenAI Embeddings (semantic search)
- SerpAPI (Google Jobs data)
- OpenRouter (LLM orchestration)

## License

MIT License - Feel free to modify and use!

---

**Questions?** Check the logs in the UI or review `logs.txt` for debugging.
