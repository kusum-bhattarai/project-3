# TakeMeter — Planning

> AI201 · Project 3 — a fine-tuned classifier that scores discourse quality in an online community.
> This document is my working spec: it was written **before** I labeled any data, and it is the
> source of truth for my label definitions, edge-case rules, data plan, and evaluation criteria.

---

## 1. Community

**Chosen community: r/nba (the NBA subreddit).**

r/nba is one of the largest sports communities on the internet, and its comment sections are a
near-perfect testbed for a discourse-quality classifier for three reasons:

1. **The quality range is enormous and obvious to regulars.** In a single thread you'll find a
   400-word tactical breakdown citing on/off splits sitting two comments above "LETS GOOOO" and a
   one-line "Embiid will never win a chip." The community itself constantly polices this — "source?",
   "that's just a hot take," "actual analysis for once" are recurring replies. The distinction I'm
   modeling is one the community *already* makes out loud.
2. **It's text-heavy and high-volume.** I can collect hundreds of real public comments easily, with
   natural variety in length and substance.
3. **The "hot take vs. real analysis" axis is the single most-discussed meta-topic in the sub.**
   That makes the label boundary *grounded in community norms*, not something I invented.

**Why it's a good fit for classification specifically:** the variance is high (so the task isn't
trivial), but the categories are recognizable (so labeling is tractable), and the hardest cases —
an opinion with one decorative stat bolted on — are exactly the ambiguous middle that makes the
modeling problem interesting rather than a keyword-matching exercise.

---

## 2. Labels

Three labels, on a single axis: **how much the comment reasons vs. asserts vs. emotes.**

> Note on naming: the project page uses `analysis / hot_take / reaction` as its *illustrative*
> example and explicitly says submitting it unchanged won't pass. I renamed two of the three and
> rewrote the definitions and decision rules to be my own. My axis is deliberately
> **evidence-centric**: the line between the first two labels is *"would the evidence support the
> claim on its own?"*, which is a sharper, more testable boundary than "good vs. bad."

### `breakdown` — a claim supported by specific, checkable reasoning
A comment that makes a basketball claim **and** backs it with concrete, verifiable support: a stat,
an on/off or efficiency number, a film/tactical observation, a historical comparison, or
roster/contract/cap logic. The support is the *point* of the comment — remove the opinion framing
and a piece of actual reasoning still stands.

- *Example A:* "Durant joined a 73-win team. His playoff TS% jumped 12 points when he left OKC for
  Golden State, and the two highest marks of his career are next to Curry."
- *Example B:* "Trey was +32 (best on the team) and Jaxson was −28 (2nd worst) over the series.
  Benching Trey was a bad decision — and he was sitting behind Garrett Temple, who also had all-time
  bad on/off effects."

### `take` — a confident basketball opinion asserted with little or no real evidence
A genuine claim/judgment about the game, a player, or a team, but argued **by assertion**, not by
evidence. It might be correct; it might even mention a fact in passing — but the fact is decorative,
not load-bearing. This is the classic "hot take."

- *Example A:* "He will suck if he goes to Philly. Loser mentality has infected that team."
- *Example B:* "I think it's gonna be consensus by around the third season that he's the best player
  in the league."

### `reaction` — an in-the-moment emotional response, joke, or banter
No basketball *claim* is really being argued. The comment is venting, celebrating, trash-talking,
joking, meming, or expressing fandom. Removing the emotion leaves nothing to evaluate.

- *Example A:* "LETS GOOOO BABY this game is amazing"
- *Example B:* "Knicks fans in tears, you actually lost the series 5-3 because the Pacers won game 1."

### Label distribution target
Each label ≥ 20% of the dataset; no label > 70% (project rule). On a casual read of r/nba, `reaction`
is the natural majority and `breakdown` the natural minority, so during collection I deliberately
over-sampled **longer** comments (which skew toward `take`/`breakdown`) to keep `breakdown` from
collapsing below ~20%.

---

## 3. Hard edge cases (and the decision rules I'll use)

These rules were written before annotation and applied consistently. The three cases below are the
ones I expected to be hardest; the concrete examples I actually hit during labeling are recorded in
§7.

### Edge case 1 — `take` vs `breakdown`: the "one decorative stat" problem
A confident opinion with a single stat or fact attached. *Is the stat load-bearing or ornamental?*

> **Decision rule:** Label `breakdown` **only if the evidence would support the claim on its own** —
> i.e., strip the opinion framing and a genuine piece of reasoning remains. If the stat is
> cherry-picked, vague, or just enough to sound credible ("he's washed, shooting like 40%"), label
> `take`. *"LeBron is overrated — his playoff win rate vs top seeds is below .500"* → `take` (one
> selected stat used as a rhetorical weapon, not an argument).

### Edge case 2 — `take` vs `reaction`: judgment vs venting
A short, emotional line that still contains a basketball opinion, e.g. "Embiid is so soft."

> **Decision rule:** If there's a **generalizable basketball judgment** (about a player's ability, a
> team's outlook, a decision), it's a `take`, even if it's emotional. If it's purely venting about a
> single moment with **no general claim** ("THAT REF IS BLIND"), it's a `reaction`.

### Edge case 3 — argument with evidence that is actually just narration
A long comment that *recounts* what happened ("he came down, guarded the center one-on-one, then
switched...") without making a claim.

> **Decision rule:** Length and detail alone do not make a `breakdown`. There must be a **claim** the
> evidence supports. Pure play-by-play narration with no thesis → `reaction` if it's emotive, `take`
> if it ends in an unsupported judgment.

### Tie-break order (when two rules seem to apply)
`breakdown` > `take` > `reaction`. Rationale: presence of genuine evidence is the rarest and most
informative signal, so it wins; an actual claim beats pure emotion.

---

## 4. Data collection plan

- **Source:** real public comments from r/nba, retrieved via the **Arctic Shift** Reddit archive API
  (`arctic-shift.photon-reddit.com`). Reddit's own `.json` endpoints now return 403 to
  non-OAuth clients, so the archive is the practical public source. **Public data only** — no private
  channels, no authenticated content.
- **Windows:** comments sampled across six date ranges spanning the 2023–24 regular season and
  playoffs (Dec 2023 – Jun 2024) so the data isn't dominated by one storyline.
- **Cleaning:** dropped `[deleted]`/`[removed]`/bot/AutoModerator comments; stripped URLs, user/sub
  mentions, quote lines, and markdown; deduped; dropped anything < 15 chars; capped at 600 chars.
  600 raw → **542 clean candidates**.
- **Volume / per-label target:** label **220+** examples, aiming roughly for `reaction` ~35%,
  `take` ~38%, `breakdown` ~27% — every label comfortably in the 20–70% band.
- **If a label is underrepresented after the first pass:** I still have ~300 unused clean candidates
  in `candidates.json`. I'll pull more **long** comments (for `breakdown`) or more **short** ones
  (for `reaction`) from that reserve and label them, rather than relabeling existing examples to
  force balance.

---

## 5. Evaluation metrics

Accuracy alone is **not** sufficient here, because the classes are intentionally imbalanced — a model
that always guessed the majority class would post a deceptively non-trivial accuracy. So I'll report:

- **Overall accuracy** — headline number, and the direct fine-tuned-vs-baseline comparison.
- **Per-class precision, recall, and F1** — the real story. I care most about:
  - **`breakdown` recall** — does the model actually *find* the substantive comments? This is the
    class the tool exists to surface, so missing them is the costly error.
  - **`take` vs `breakdown` confusion specifically** — this is the hard boundary; I'll read it
    directly off the confusion matrix.
- **Confusion matrix** — to see *direction* of errors (is it calling `breakdown`→`take`, or the
  reverse?), which tells me which boundary the model failed to learn.
- **Macro-F1** as the single fairness-weighted summary across the three classes.

**Why these and not others:** the cost of errors is asymmetric (missing a `breakdown` matters more
than mislabeling banter), and the class imbalance means accuracy can lie — per-class recall + the
confusion matrix are what actually tell me whether the model learned the *distinction* or just the
*base rates*.

---

## 6. Definition of success

- **Minimum bar (fine-tuning did something real):** fine-tuned overall accuracy meaningfully beats
  both the 3-class random baseline (~33%) **and** the Groq zero-shot baseline. If it can't beat a
  general model with no training, fine-tuning added nothing.
- **"Good enough" / genuinely useful threshold:** overall accuracy **≥ 0.70**, **every** per-class
  F1 **≥ 0.55**, and `breakdown` recall **≥ 0.60** (the tool's whole job is surfacing substance, so
  I won't accept a model that can't find it even if overall accuracy looks fine).
- **Deployment-worthy in a real community tool:** I'd want `breakdown` precision high enough that a
  "top takes" feed isn't polluted by hot takes — call it `breakdown` F1 ≥ 0.70 — plus calibrated
  confidence so low-confidence predictions can be deferred to a human. I don't expect to fully hit
  this on 220 examples, and saying so honestly is part of the evaluation.

These thresholds are deliberately specific so that at the end I can objectively state whether I hit
them, rather than hand-waving "it works well."

---

## 7. Hard annotation decisions (filled during Milestone 3)

> Concrete examples that gave me genuine pause while labeling, the labels they could plausibly take,
> and what I decided per the §3 rules. These are flagged in the `notes` column of
> `takemeter_dataset.csv`.

**1. The "decorative stat" case → `take` (Edge case 1).**
> *"you think previous FMVPs cannibalized their team's players? LOL Jaylen probably has one of the
> lowest assist averages of previous FMVP too"*
Could be `breakdown` (it names a stat — assist average) or `take`. **Decided `take`:** the stat is
vague ("probably one of the lowest"), unverified, and used as a mocking jab, not as an argument. Strip
the opinion and no real reasoning survives.

**2. A real historical fact, but the conclusion is a vibe → `take`.**
> *"A friendly reminder that this exact top 5 +Mason Plumlee + Kelly Oubre made the play-ins two
> seasons ago. This team is a mindfuck"*
The roster history is accurate and specific (pulls toward `breakdown`), but the actual claim — "this
team is a mindfuck" — is an emotional verdict, not something the fact *argues for*. **Decided `take`.**
This case sharpened my rule: evidence has to support a *claim*, not just be present.

**3. Looks like a `reaction` list, but is actually a factual rebuttal → `breakdown`.**
> *"Those 10 players are either hurt (Ingram, Dick, Mogbo, Walter, Chomche), nursing an injury (IQ),
> having a day off for the anniversary of his late brother (RJ), or playing with injuries and
> questionable (Scottie + Ocahi). That isn't close to sitting out 10 guys for rest."*
On a skim it reads like banter, but it methodically refutes a "they rested 10 guys" claim by giving
each player's actual status. The evidence is load-bearing. **Decided `breakdown`** — and it's a good
reminder that `breakdown` isn't about tone or stats specifically, it's about whether real support is
doing the work.

**4. `breakdown` with no numbers at all.**
> *"I think LeBron tries to get layups instead of dunks now... Giannis goes up with force to jam it...
> LeBron only tries to dunk if the defense fell asleep... that extra aggression gets rewarded more
> than a soft touch off the glass."*
No stats, so it's tempting to call it a `take`. **Decided `breakdown`:** it's a specific, checkable
*film observation* that directly supports the claim — exactly what my §2 definition allows beyond
stats. This is the kind of example I deliberately kept so the model doesn't learn "numbers =
breakdown."

---

## 8. AI Tool Plan

This project has no application code to generate, so AI assistance shows up in three specific places.
For each, I made an explicit decision:

### a) Label stress-testing — **YES**
Before locking the taxonomy I had Claude generate boundary cases between `take` and `breakdown`
(opinions with one stat attached) and between `take` and `reaction` (emotional one-liners that still
contain a judgment). Where I couldn't classify the generated post cleanly, I tightened the §3
decision rules (this is where the "would the evidence support the claim on its own?" test came from).

### b) Annotation assistance — **YES, with mandatory human review (disclosed)**
I used Claude to **pre-label** the cleaned candidate pool against the §2 definitions, with a `notes`
column flagging any example it found ambiguous. **Every pre-assigned label is reviewed and corrected
by me** before training — pre-labeling is a speedup, not a substitute for reading each comment. The
CSV carries a `prelabel` column (the model's original guess) alongside the final `label` so the
review trail is visible and the assistance is fully disclosed (also noted in the README AI-usage
section).

### c) Failure analysis — **YES, verified by hand**
After fine-tuning, I'll paste the list of misclassified test examples into Claude and ask it to find
systematic patterns (e.g., "confuses `take`→`breakdown` on long comments", "misses sarcasm",
"short comments default to `reaction`"). I will then **re-read those examples myself to confirm the
pattern is real** before putting it in the evaluation report, and I'll note anything the model
suggested that I had to discard as a false pattern.

---

## 9. Stretch features (decide before starting each)
- _Not started. Candidates: inter-annotator agreement (have a second person label 30+), confidence
  calibration, systematic error-pattern analysis, and a small deployed interface. Will update this
  section before attempting any._
