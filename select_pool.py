import json, random
cands = json.load(open("candidates.json"))
random.seed(42)
short  = [t for t in cands if len(t) < 60]
medium = [t for t in cands if 60 <= len(t) < 180]
longc  = [t for t in cands if len(t) >= 180]
random.shuffle(short); random.shuffle(medium); random.shuffle(longc)
pool = short[:80] + medium[:95] + longc[:70]
random.shuffle(pool)
json.dump(pool, open("pool.json","w"))
print(f"POOL SIZE: {len(pool)}")
for i,t in enumerate(pool):
    print(f"[{i}] {t}")
