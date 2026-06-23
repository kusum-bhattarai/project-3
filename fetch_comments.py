import json, urllib.request, urllib.parse, time, re

BASE = "https://arctic-shift.photon-reddit.com/api/comments/search"

def fetch(params):
    url = BASE + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": "TakeMeter-edu/0.1"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)["data"]

# Pull across several time windows (2023-2024 seasons) for variety.
windows = [
    ("2024-01-01", "2024-01-15"),
    ("2024-03-01", "2024-03-15"),
    ("2024-05-01", "2024-05-20"),  # playoffs
    ("2023-12-01", "2023-12-15"),
    ("2024-06-01", "2024-06-20"),  # finals
    ("2024-02-01", "2024-02-15"),
]

raw = []
for after, before in windows:
    try:
        data = fetch({"subreddit": "nba", "after": after, "before": before,
                      "limit": 100, "sort": "desc"})
        raw.extend(data)
        print(f"  {after}..{before}: +{len(data)} (total {len(raw)})")
        time.sleep(1)
    except Exception as e:
        print(f"  {after}..{before}: ERROR {e}")

with open("raw_comments.json", "w") as f:
    json.dump(raw, f)
print(f"Saved {len(raw)} raw comments")
