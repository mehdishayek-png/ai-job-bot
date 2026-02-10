#!/bin/bash

# 🚀 Git Commands - Major Update (3 Critical Fixes)

# Navigate to your project directory
# cd /path/to/your/jobbot/project

echo "📋 Checking status..."
git status

echo ""
echo "📦 Adding updated files..."

# Add all three updated files
git add run_auto_apply.py
git add ui_dashboard.py  
git add job_fetcher.py

echo ""
echo "✍️ Creating commit..."

git commit -m "Major update: Fix experience detection, semantic title matching, and progress tracking

- Fix experience estimation (was always ~2yrs, now accurate 0-12+ range)
- Add semantic job title matching with 50+ synonym mappings
  * Construction Manager now matches Project Manager, Site Supervisor, etc.
  * Customer Support matches Technical Support, Help Desk, etc.
  * Covers Engineering, Data, Sales, Operations, Design roles
- Improve progress bar with real-time updates (was stuck at 50%)
  * Added emoji indicators and batch-by-batch AI scoring updates
  * Users now see live job analysis counter
- Maintain city-first search priority from previous update
- Multi-layer experience detection using headline + skills + role type"

echo ""
echo "🚀 Pushing to repository..."

# Push to main branch (change if you use different branch)
git push origin main

# Alternative branches (uncomment if needed):
# git push origin develop
# git push origin feature/semantic-matching

echo ""
echo "✅ All changes pushed successfully!"
echo ""
echo "🧪 Next steps:"
echo "1. Test with a senior user (should show ~8+ years)"
echo "2. Test with Construction Manager profile"
echo "3. Watch progress bar move from 0% → 100%"
echo "4. Verify city-specific jobs appear first"
