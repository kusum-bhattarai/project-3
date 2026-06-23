import json, csv

pool  = json.load(open("pool.json"))        # 245, indices 0-244
extra = json.load(open("extra_long.json"))   # 27,  E0-E26
newl  = json.load(open("new_long.json"))     # 140, N0-N139

# ---- Pool labels (my read of indices 0-244) ----
B = {1,9,15,16,26,28,33,35,40,47,50,55,60,69,75,86,87,104,105,110,118,121,
     126,128,138,150,156,157,176,177,182,191,212,230,239,243}
T = {3,5,7,8,10,11,13,14,17,18,19,21,24,27,32,34,38,41,42,48,51,53,54,56,59,
     61,62,68,70,72,77,78,82,83,91,92,93,95,98,99,100,103,108,109,116,122,130,
     135,136,137,139,141,149,153,158,160,163,164,167,178,183,184,188,190,199,
     201,202,203,205,207,208,210,213,214,215,216,217,219,221,223,225,226,227,
     232,236,238,240,242}

# ---- Extra-long additions: breakdowns only ----
extra_B = {2,7,8,10,13,14,16}

# ---- New-long additions ----
new_B = {3,4,10,16,39,43,47,49,50,63,78,84,106,107,108,125}
new_T = {18,22,66,70,75,85,90,101,112,113,126,127}

# ---- Notes on genuinely difficult cases (feed planning.md §7) ----
notes = {
 ("pool",8):  "take vs breakdown: cites 'lowest assist avg' but stat is vague/decorative -> take",
 ("pool",17): "take vs breakdown: real historical roster fact, but conclusion is a vibe ('mindfuck') -> take",
 ("pool",54): "take vs breakdown: argues about efficiency methodology but offers no numbers of its own -> take",
 ("pool",130):"take vs breakdown: 'hockey assists' reasoning is conceptual, no verifiable evidence -> take",
 ("new",10): "breakdown w/o numbers: detailed role/film reasoning on Kobe's defense -> breakdown (evidence is observational)",
 ("new",50): "reaction vs breakdown: looks like a list, but factually rebuts 'rested 10 guys' with each player's status -> breakdown",
 ("new",87): "take vs breakdown: vivid tactical description of OKC's offense, no numbers -> breakdown (load-bearing observation)",
 ("extra",14):"take vs breakdown: opinion on shooting, but 'double the attempts' is real load-bearing evidence -> breakdown",
}

rows = []  # (text, label, prelabel, notes)
def lbl(i, Bset, Tset):
    return "breakdown" if i in Bset else ("take" if i in Tset else "reaction")

for i, t in enumerate(pool):
    l = lbl(i, B, T)
    rows.append((t, l, l, notes.get(("pool",i), "")))

for i in sorted(extra_B):
    rows.append((extra[i], "breakdown", "breakdown", notes.get(("extra",i), "")))

for i in sorted(new_B | new_T):
    l = "breakdown" if i in new_B else "take"
    rows.append((newl[i], l, l, notes.get(("new",i), "")))

# de-dupe by text just in case
seen=set(); final=[]
for r in rows:
    k=r[0].lower()[:80]
    if k in seen: continue
    seen.add(k); final.append(r)

with open("takemeter_dataset.csv","w",newline="") as f:
    w=csv.writer(f)
    w.writerow(["text","label","prelabel","notes"])
    w.writerows(final)

from collections import Counter
c=Counter(r[1] for r in final)
tot=len(final)
print(f"TOTAL: {tot}")
for k in ("breakdown","take","reaction"):
    print(f"  {k:10s} {c[k]:3d}  {c[k]/tot*100:.1f}%")
print(f"  flagged-difficult notes: {sum(1 for r in final if r[3])}")
