import json, re, html

raw = json.load(open("raw_comments.json"))

BOT_AUTHORS = {"AutoModerator", "NBA_MOD", "[deleted]"}
def clean_text(b):
    b = html.unescape(b)
    b = re.sub(r"https?://\S+", "", b)        # strip urls
    b = re.sub(r"/?u/\w+|/?r/\w+", "", b)      # strip user/sub mentions
    b = re.sub(r"&gt;.*", "", b)               # strip quote lines
    b = re.sub(r"[*_`>#]", "", b)              # strip md
    b = re.sub(r"\s+", " ", b).strip()
    return b

seen = set()
cands = []
for c in raw:
    body = c.get("body", "")
    if body in ("[deleted]", "[removed]", ""): continue
    if c.get("author") in BOT_AUTHORS: continue
    t = clean_text(body)
    if not t: continue
    if len(t) < 15: continue            # too short to be meaningful
    if len(t) > 600: t = t[:600]        # cap very long
    key = t.lower()[:80]
    if key in seen: continue
    seen.add(key)
    cands.append(t)

# Bucket by length to ensure variety
short  = [t for t in cands if len(t) < 60]
medium = [t for t in cands if 60 <= len(t) < 180]
longc  = [t for t in cands if len(t) >= 180]
print(f"Total clean candidates: {len(cands)}")
print(f"  short  (<60):    {len(short)}")
print(f"  medium (60-180): {len(medium)}")
print(f"  long   (>=180):  {len(longc)}")

json.dump(cands, open("candidates.json","w"))
print("\n--- 6 SHORT samples ---")
for t in short[:6]: print(" •", t)
print("\n--- 6 MEDIUM samples ---")
for t in medium[:6]: print(" •", t)
print("\n--- 5 LONG samples ---")
for t in longc[:5]: print(" •", t[:240])
