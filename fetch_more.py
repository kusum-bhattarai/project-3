import json, urllib.request, urllib.parse, time, re, html
BASE = "https://arctic-shift.photon-reddit.com/api/comments/search"
def fetch(params):
    url = BASE + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": "TakeMeter-edu/0.1"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)["data"]
windows = [
    ("2025-01-05","2025-01-12"),("2025-02-05","2025-02-12"),
    ("2025-03-05","2025-03-12"),("2024-11-05","2024-11-12"),
    ("2024-04-20","2024-04-28"),("2024-12-20","2024-12-27"),
    ("2025-04-20","2025-04-28"),("2024-10-25","2024-11-01"),
]
raw=[]
for a,b in windows:
    try:
        d=fetch({"subreddit":"nba","after":a,"before":b,"limit":100,"sort":"desc"})
        raw.extend(d); print(f"  {a}: +{len(d)} ({len(raw)})"); time.sleep(1)
    except Exception as e: print(f"  {a}: ERR {e}")

def clean(b):
    b=html.unescape(b); b=re.sub(r"https?://\S+","",b)
    b=re.sub(r"/?u/\w+|/?r/\w+","",b); b=re.sub(r"&gt;.*","",b)
    b=re.sub(r"[*_`>#]","",b); b=re.sub(r"\s+"," ",b).strip(); return b

prev=set(json.load(open('candidates.json')))
seen=set(t.lower()[:80] for t in prev)
new_long=[]
for c in raw:
    body=c.get('body','')
    if body in ('[deleted]','[removed]',''): continue
    if c.get('author') in {'AutoModerator','[deleted]'}: continue
    t=clean(body)
    if len(t)<180: continue          # focus: long comments only (breakdown-rich)
    if len(t)>600: t=t[:600]
    k=t.lower()[:80]
    if k in seen: continue
    seen.add(k); new_long.append(t)
json.dump(new_long, open('new_long.json','w'))
print(f"NEW LONG candidates: {len(new_long)}")
