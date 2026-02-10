import feedparser

print("\nTesting WorkingNomads...")

feed = feedparser.parse("https://www.workingnomads.com/jobs/rss")
print("Entries:", len(feed.entries))

print("\nTesting Remotive...")

feed2 = feedparser.parse("https://remotive.com/remote-jobs.rss")
print("Entries:", len(feed2.entries))
