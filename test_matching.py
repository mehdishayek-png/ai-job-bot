"""
Light Validation Tests for JobBot Matching Engine
==================================================
Focus: Accuracy validation with minimal API calls
NO stress testing or large-scale simulations
"""

import json
import sys
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, '.')

try:
    from matching_engine_enhanced import (
        enhanced_job_score,
        weighted_skill_match,
        title_similarity_score,
        has_negative_keywords,
        experience_mismatch_penalty,
        recency_boost
    )
    MATCHING_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Could not import matching_engine_enhanced: {e}")
    MATCHING_AVAILABLE = False


def test_skill_matching():
    """Test weighted skill matching logic"""
    print("\n--- Test: Skill Matching ---")
    
    test_cases = [
        {
            "job_text": "We need a payment operations manager with experience in fintech and vendor management",
            "skills": ["payment operations", "fintech", "vendor management", "customer success"],
            "expected_min_score": 20,
            "expected_min_matches": 2
        },
        {
            "job_text": "Software engineer role with Python, Django, and React experience",
            "skills": ["python", "django", "react", "javascript"],
            "expected_min_score": 25,
            "expected_min_matches": 3
        },
        {
            "job_text": "Sales representative position for B2B SaaS company",
            "skills": ["sales", "b2b", "saas", "crm"],
            "expected_min_score": 15,
            "expected_min_matches": 3
        }
    ]
    
    passed = 0
    for i, test in enumerate(test_cases, 1):
        score, matched = weighted_skill_match(test["job_text"], test["skills"])
        
        success = (score >= test["expected_min_score"] and 
                  len(matched) >= test["expected_min_matches"])
        
        status = "✓" if success else "✗"
        print(f"{status} Case {i}: score={score} (min {test['expected_min_score']}), "
              f"matched={len(matched)} (min {test['expected_min_matches']})")
        print(f"  Matched skills: {matched}")
        
        if success:
            passed += 1
    
    print(f"\nResult: {passed}/{len(test_cases)} passed")
    return passed == len(test_cases)


def test_title_similarity():
    """Test job title similarity scoring"""
    print("\n--- Test: Title Similarity ---")
    
    test_cases = [
        ("Business Operations Manager", "Operations Manager - Fintech", 30),
        ("Software Engineer", "Senior Software Engineer", 40),
        ("Data Analyst", "Business Intelligence Analyst", 20),
        ("Product Manager", "Engineering Manager", 15),
        ("DevOps Engineer", "Site Reliability Engineer", 10),
    ]
    
    passed = 0
    for profile_title, job_title, expected_min in test_cases:
        score = title_similarity_score(profile_title, job_title)
        success = score >= expected_min
        
        status = "✓" if success else "✗"
        print(f"{status} '{profile_title}' vs '{job_title}': {score}% (min {expected_min}%)")
        
        if success:
            passed += 1
    
    print(f"\nResult: {passed}/{len(test_cases)} passed")
    return passed == len(test_cases)


def test_negative_filtering():
    """Test negative keyword detection"""
    print("\n--- Test: Negative Keyword Filtering ---")
    
    test_jobs = [
        ({"title": "Operations Manager", "summary": "Manage operations"}, False, "Good job"),
        ({"title": "CEO Position", "summary": "Lead company as CEO"}, True, "CEO role"),
        ({"title": "Developer", "summary": "Work on crypto and NFT projects"}, True, "Crypto job"),
        ({"title": "Senior Developer", "summary": "Python development"}, False, "Good job"),
        ({"title": "VP of Engineering", "summary": "Lead engineering team"}, True, "VP role"),
    ]
    
    passed = 0
    for job, should_filter, description in test_jobs:
        is_filtered = has_negative_keywords(job)
        success = is_filtered == should_filter
        
        status = "✓" if success else "✗"
        action = "filtered" if is_filtered else "passed"
        print(f"{status} {description}: {action} (expected: {'filter' if should_filter else 'pass'})")
        
        if success:
            passed += 1
    
    print(f"\nResult: {passed}/{len(test_jobs)} passed")
    return passed == len(test_jobs)


def test_experience_alignment():
    """Test experience mismatch penalty calculation"""
    print("\n--- Test: Experience Alignment ---")
    
    test_cases = [
        (2, "Junior Developer", 0, "Junior candidate, junior role"),
        (2, "Senior Engineering Manager", 30, "Junior candidate, senior role"),
        (10, "Associate Developer", 15, "Senior candidate, junior role"),
        (5, "Senior Developer", 0, "Mid candidate, mid-senior role"),
    ]
    
    passed = 0
    for years, job_title, expected_penalty, description in test_cases:
        penalty = experience_mismatch_penalty(years, job_title)
        success = penalty == expected_penalty
        
        status = "✓" if success else "✗"
        print(f"{status} {description}: penalty={penalty} (expected {expected_penalty})")
        
        if success:
            passed += 1
    
    print(f"\nResult: {passed}/{len(test_cases)} passed")
    return passed == len(test_cases)


def test_recency_boost():
    """Test recency scoring"""
    print("\n--- Test: Recency Boost ---")
    
    from datetime import timedelta
    now = datetime.now()
    
    test_cases = [
        ({"posted_date": now.isoformat()}, 15, "Posted today"),
        ({"posted_date": (now - timedelta(hours=12)).isoformat()}, 15, "Posted 12h ago"),
        ({"posted_date": (now - timedelta(days=2)).isoformat()}, 10, "Posted 2 days ago"),
        ({"posted_date": (now - timedelta(days=5)).isoformat()}, 5, "Posted 5 days ago"),
        ({"posted_date": (now - timedelta(days=10)).isoformat()}, 0, "Posted 10 days ago"),
        ({"posted_date": None}, 0, "No date"),
    ]
    
    passed = 0
    for job, expected_boost, description in test_cases:
        boost = recency_boost(job)
        success = boost == expected_boost
        
        status = "✓" if success else "✗"
        print(f"{status} {description}: boost={boost} (expected {expected_boost})")
        
        if success:
            passed += 1
    
    print(f"\nResult: {passed}/{len(test_cases)} passed")
    return passed == len(test_cases)


def test_end_to_end_scoring():
    """Test complete scoring pipeline (NO API calls - cache only)"""
    print("\n--- Test: End-to-End Scoring ---")
    
    profile = {
        "headline": "Business Operations Lead",
        "skills": ["fintech operations", "payment gateway", "vendor management"],
        "experience": "3–6 years"
    }
    
    test_jobs = [
        {
            "job": {
                "title": "Operations Manager - Payments",
                "company": "PaymentCo",
                "summary": "Looking for operations manager in fintech space. Must have payment and vendor experience.",
                "posted_date": datetime.now().isoformat()
            },
            "expected_min": 50,
            "description": "Strong match"
        },
        {
            "job": {
                "title": "Software Engineer",
                "company": "TechCorp",
                "summary": "Python and Java development",
                "posted_date": datetime.now().isoformat()
            },
            "expected_max": 40,
            "description": "Weak match"
        }
    ]
    
    cache = {}
    passed = 0
    
    for test in test_jobs:
        job = test["job"]
        result = enhanced_job_score(job, profile, 4, cache)
        score = result["total_score"]
        
        if "expected_min" in test:
            success = score >= test["expected_min"]
            print(f"{'✓' if success else '✗'} {test['description']}: {score} "
                  f"(min {test['expected_min']})")
        else:
            success = score <= test["expected_max"]
            print(f"{'✓' if success else '✗'} {test['description']}: {score} "
                  f"(max {test['expected_max']})")
        
        print(f"  Breakdown: {result['breakdown']}")
        
        if success:
            passed += 1
    
    print(f"\nResult: {passed}/{len(test_jobs)} passed")
    return passed == len(test_jobs)


def run_all_tests():
    """Run all validation tests"""
    print("=" * 60)
    print("JobBot Matching Engine - Validation Tests")
    print("=" * 60)
    
    if not MATCHING_AVAILABLE:
        print("\n❌ ERROR: matching_engine_enhanced.py not available")
        print("Make sure the file is in the same directory or PYTHONPATH")
        return False
    
    tests = [
        ("Skill Matching", test_skill_matching),
        ("Title Similarity", test_title_similarity),
        ("Negative Filtering", test_negative_filtering),
        ("Experience Alignment", test_experience_alignment),
        ("Recency Boost", test_recency_boost),
        ("End-to-End Scoring", test_end_to_end_scoring),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            passed = test_func()
            results.append((name, passed))
        except Exception as e:
            print(f"\n❌ {name} failed with error: {e}")
            import traceback
            traceback.print_exc()
            results.append((name, False))
    
    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    
    passed_count = sum(1 for _, passed in results if passed)
    total_count = len(results)
    
    for name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} - {name}")
    
    print(f"\nOverall: {passed_count}/{total_count} test suites passed")
    
    if passed_count == total_count:
        print("\n🎉 All tests passed! Matching engine is working correctly.")
        return True
    else:
        print(f"\n⚠️  {total_count - passed_count} test suite(s) failed. Review errors above.")
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
