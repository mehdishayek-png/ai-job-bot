import feedparser
import requests
import json
import os

OUTPUT_DEFAULT = "data/jobs.json"

WWR_FEEDS = [
    "https://weworkremotely.com/categories/remote-programming-jobs.rss",
    "https://weworkremotely.com/categories/remote-design-jobs.rss",
    "https://weworkremotely.com/categories/remote-marketing-jobs.rss",
    "https://weworkremotely.com/categories/remote-customer-support-jobs.rss",
]

REMOTEOK = "https://remoteok.com/remote-jobs.rss"


def parse_rss(url, source):

    jobs = []
    feed = feedparser.parse(url)

    for entry in feed.entries:
        jobs.append({
            "title": entry.get("title",""),
            "company": entry.get("author","Unknown"),
            "summary": entry.get("summary",""),
            "apply_url": entry.get("link",""),
            "source": source,
        })

    return jobs


def fetch_all(output_path=None):

    output_path = output_path or OUTPUT_DEFAULT
    all_jobs = []

    for feed in WWR_FEEDS:
        all_jobs.extend(parse_rss(feed, "WeWorkRemotely"))

    all_jobs.extend(parse_rss(REMOTEOK, "RemoteOK"))

    # Remotive API
    try:
        res = requests.get("https://remotive.com/api/remote-jobs")
        data = res.json()

        for j in data["jobs"]:
            all_jobs.append({
                "title": j["title"],
                "company": j["company_name"],
                "summary": j["description"][:500],
                "apply_url": j["url"],
                "source": "Remotive",
            })
    except:
        pass

    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    with open(output_path,"w") as f:
        json.dump(all_jobs,f,indent=2)

    return all_jobs


if __name__ == "__main__":
    fetch_all()
