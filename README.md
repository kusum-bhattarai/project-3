# TakeMeter — A Discourse-Quality Classifier for r/nba

TakeMeter is a fine-tuned text classifier that scores the *quality of discourse* in r/nba comments.
It sorts a comment into one of three categories — **breakdown**, **take**, or **reaction** — based on
**how** it argues (does it reason, assert, or just emote?), not on whether the opinion is correct.

> This README is the final report. The design notes, decision rules, and working detail behind every
> choice live in [`planning.md`](./planning.md).

> **Headline result (test set, n=42):** zero-shot Groq baseline **0.810** vs. fine-tuned DistilBERT
> **0.571** — fine-tuning *regressed*, because the model never learned the minority `breakdown` class
> (§6.3, §7). A handful of per-example blanks (`‹…›`) in §6.2/§6.4/§6.5 are filled from two on-screen
> notebook outputs (baseline per-class report + wrong-predictions list).

---

## 1. Community choice and reasoning

**Community: [r/nba](https://www.reddit.com/r/nba/).**

r/nba is a huge, text-heavy community where the quality of "takes" varies wildly inside a single
thread — a 400-word tactical breakdown citing on/off splits can sit two comments above "LETS GOOOO"
and a flat "Embiid will never win a chip." Crucially, **the community already polices this
distinction out loud** ("source?", "that's just a hot take," "actual analysis for once"), so the
thing I'm modeling is a real, native norm rather than something I imposed. That makes it a good
classification target: high variance (non-trivial), recognizable categories (labelable), and a
genuinely hard middle ground (an opinion with one decorative stat) that keeps it from being a
keyword-matching exercise.

---

## 2. Label taxonomy

Three labels on one axis — **how much the comment reasons vs. asserts vs. emotes.** The sharp line is
between the first two: *would the evidence support the claim on its own?*

> Naming note: the project's *illustrative* example was `analysis / hot_take / reaction`. I renamed
> two of the three and rewrote the definitions around an explicit, testable evidence rule so the
> taxonomy is my own.

### `breakdown`
A basketball claim **supported by specific, checkable reasoning**: a stat, an efficiency/on-off
number, a film or tactical observation, a historical comparison, or roster/contract/cap logic. The
support is the point — strip the opinion and real reasoning remains.
- *"Durant's playoff TS% jumped 12 points when he left OKC for Golden State, and the two highest marks of his career came next to Curry."*
- *"Trey was +32 (best on the team) and Jaxson was −28 (2nd worst) over the series — benching Trey was a bad call, and he was sitting behind Garrett Temple, who also had all-time bad on/off effects."*

### `take`
A confident basketball opinion **asserted with little or no real evidence**. It may name a fact in
passing, but the fact is decorative, not load-bearing. The classic hot take.
- *"He will suck if he goes to Philly. Loser mentality has infected that team."*
- *"I think it's gonna be consensus by around the third season that he's the best player in the league."*

### `reaction`
An **in-the-moment emotional response, joke, trash talk, meme, or fandom expression**. No basketball
claim is really being argued.
- *"LETS GOOOO BABY this game is amazing"*
- *"Knicks fans in tears, you actually lost the series 5-3 because the Pacers won game 1."*

**Tie-break order when two rules seem to apply:** `breakdown` > `take` > `reaction` (genuine evidence
is the rarest, most informative signal; an actual claim beats pure emotion).

---

## 3. Dataset

### Source & collection
- **280 real public comments from r/nba**, retrieved via the **Arctic Shift** Reddit archive API
  (`arctic-shift.photon-reddit.com`). Reddit's own `.json` endpoints now return **403** to non-OAuth
  clients, so the public archive was the practical source. Public data only.
- Sampled across **multiple date windows** spanning the 2023–24 and 2024–25 seasons and playoffs, so
  the data isn't dominated by one storyline.
- **Cleaning:** dropped `[deleted]`/`[removed]`/bot comments; stripped URLs, user/sub mentions, quote
  lines, and markdown; deduped; dropped < 15 chars; capped at 600 chars. (Scripts:
  `fetch_comments.py`, `clean_comments.py`, `build_dataset.py`.)
- Stored in [`takemeter_dataset.csv`](./takemeter_dataset.csv) with columns: `text`, `label`,
  `prelabel` (the AI pre-label, for the disclosure trail), `notes` (flagged hard cases).

### Labeling process
Labels were **pre-assigned by an LLM (Claude) against the §2 definitions, then reviewed comment-by-comment by me** and corrected where I disagreed (disclosed in [§9](#9-ai-usage)). Because substantive
comments are genuinely rare on r/nba, an initial pass came out at only ~15% `breakdown`; following the
plan in `planning.md §4`, I pulled **more long comments** from the reserve and labeled the genuine
breakdowns (and some long `take`s, so the model wouldn't just learn "long = breakdown") until every
class cleared 20%.

### Label distribution (n = 280)
| Label | Count | Share |
|---|---:|---:|
| `breakdown` | 59 | 21.1% |
| `take` | 100 | 35.7% |
| `reaction` | 121 | 43.2% |

No label exceeds 70%; every label clears the 20% aim. The notebook splits this **70/15/15, stratified**
→ ~196 train / ~42 val / ~42 test (test ≈ 9 `breakdown` / 15 `take` / 18 `reaction`).

### Three genuinely difficult examples (and my decisions)
1. **"…Jaylen probably has one of the lowest assist averages of previous FMVP too"** — names a stat,
   so it flirts with `breakdown`, but the stat is vague/unverified and used as a jab. → **`take`**
   (decorative, not load-bearing evidence).
2. **"A friendly reminder that this exact top 5 +Plumlee + Oubre made the play-ins two seasons ago.
   This team is a mindfuck"** — the roster history is real and specific, but the actual conclusion is
   an emotional verdict the fact doesn't *argue for*. → **`take`**.
3. **"Those 10 players are either hurt (Ingram, Dick, Mogbo…), nursing an injury (IQ), [or] having a
   day off… That isn't close to sitting out 10 guys for rest."** — reads like banter on a skim, but
   methodically rebuts a "they rested 10 guys" claim with each player's status. → **`breakdown`**
   (evidence is load-bearing even with no stats).

_(A fourth — a numbers-free film read of LeBron's finishing — is documented in `planning.md §7`, kept
deliberately so the model doesn't equate "stats" with `breakdown`.)_

---

## 4. Fine-tuning approach

- **Base model:** `distilbert-base-uncased` (HuggingFace) with a 3-class sequence-classification head.
- **Pipeline:** the provided Colab notebook ([`ai201_project3_takemeter.ipynb`](./ai201_project3_takemeter.ipynb))
  — tokenize (max_len 256) → `Trainer` fine-tune → evaluate on the locked test set → confusion matrix
  → Groq baseline → comparison/export.
- **Training setup:** 3 epochs, learning rate 2e-5, train batch size 16, weight decay 0.01, 50 warmup
  steps, `load_best_model_at_end` on validation accuracy.

**Hyperparameter decision (epochs):** I kept **3 epochs**. With only ~196 training examples and a
hard, subjective boundary, more epochs mainly risk memorizing the train set — and since `breakdown` is
the smallest class (~41 train examples), an overfit model would most likely "win" by leaning on the
`reaction`/`take` majority and starving `breakdown` recall, which is the exact metric I care about
(`planning.md §5`). 3 epochs with best-on-validation checkpointing was the conservative choice for a
small, imbalanced set. **In hindsight this conservatism backfired:** with `breakdown` so
underrepresented, the safe-default run let the model drop the class entirely (§6.3) — a case where
class weighting or oversampling would likely have mattered more than the epoch count. I ran the stock
hyperparameters (3 epochs / lr 2e-5 / batch 16); I did not change them.

---

## 5. Baseline (zero-shot Groq)

- **Model:** `llama-3.3-70b-versatile` (Groq free tier), `temperature=0`, `max_tokens=20`.
- **Method:** each test comment is sent with a system prompt containing the §2 definitions, one
  example per label, the decision rules, and an instruction to output **only** one label word; the
  notebook parses the response and flags anything unparseable. Full prompt is in notebook Section 5.
- This is a fair "how hard is the task for a strong general model with no training?" reference point.

---

## 6. Evaluation report

> All numbers below come from `evaluation_results.json` / `confusion_matrix.png` produced by the
> notebook on the test set.

### 6.1 Headline accuracy
| Model | Accuracy |
|---|---:|
| **Zero-shot baseline (Groq llama-3.3-70b)** | **0.810** |
| Fine-tuned DistilBERT | 0.571 |
| Random (3-class reference) | 0.333 |

**Takeaway: fine-tuning made things *worse* — a 24-point regression (−0.238).** The zero-shot baseline
was the better classifier. This is a real, diagnosable result, not a tuning failure to paper over (see
§6.3 and §7). It also means **none** of my `planning.md §6` success criteria were met (accuracy ≥0.70,
every per-class F1 ≥0.55, `breakdown` recall ≥0.60, and "beat the baseline") — I'll own that in §7.

### 6.2 Per-class metrics (precision / recall / F1)
**Baseline (Groq):** evaluated on `‹X›/42` parseable responses.
| Label | P | R | F1 |
|---|---:|---:|---:|
| breakdown | ‹from Section 5 printout› | ‹› | ‹› |
| take | ‹› | ‹› | ‹› |
| reaction | ‹› | ‹› | ‹› |
| **macro avg** | ‹› | ‹› | ‹› |

**Fine-tuned DistilBERT** (computed from the confusion matrix below):
| Label | P | R | F1 | support |
|---|---:|---:|---:|---:|
| breakdown | 0.000 | 0.000 | 0.000 | 9 |
| take | 0.429 | 0.600 | 0.500 | 15 |
| reaction | 0.714 | 0.833 | 0.769 | 18 |
| **macro avg** | 0.381 | 0.478 | 0.423 | 42 |

### 6.3 Confusion matrix — fine-tuned model (rows = true, cols = predicted)
(Committed as `confusion_matrix.png`.)
| true ↓ / pred → | breakdown | take | reaction |
|---|---:|---:|---:|
| **breakdown** | **0** | **9** | 0 |
| **take** | 0 | 9 | 6 |
| **reaction** | 0 | 3 | 15 |

**The single biggest signal: the entire `breakdown` *prediction* column is zero — the fine-tuned model
never predicts `breakdown` for any test example.** All 9 true breakdowns were sent to `take`
(`breakdown`→`take` is the dominant error). The model effectively collapsed the 3-class problem into a
2-class one (`take` vs `reaction`) and folded "claim *with* load-bearing evidence" into the broader
"claim" bucket. Even within the two classes it still does keep, it leans majority: `reaction` recall
(0.83) > `take` recall (0.60).

**Why this happened — class imbalance + tiny data on the hardest class.** `breakdown` had only ~41
training examples (vs ~70 `take`, ~85 `reaction`), and it's the *subtlest* distinction (a `take` and a
`breakdown` look similar — both make a claim; the only difference is whether the evidence is
load-bearing). With so few examples and 3 epochs, the loss is minimized by simply never committing to
the rare, hard class. **Why the baseline wins:** llama-3.3-70b carries real basketball knowledge and
reasoning, so given the definitions in-context it can actually tell a stat-backed argument from a bare
opinion — something a 66M-param DistilBERT can't learn from ~41 examples. This is a labeling-is-fine /
data-quantity-and-balance problem, not an annotation-consistency problem (the leakage check was clean,
§3).

### 6.4 Three wrong predictions, analyzed
All three are drawn from the **9 `breakdown`→`take` errors** — the model's defining failure (every
true `breakdown` in the test set was called `take`). Quotes/confidences from the Section 4
wrong-predictions cell.

1. **`‹breakdown comment text›`** — true **breakdown** / pred **take** (conf `‹›`).
   *Why:* this comment makes a claim *and* backs it with load-bearing evidence (a stat / on-off number /
   film read), but the model has no learned representation of "breakdown" to assign it to, so it lands
   in the nearest class it *did* learn — `take` (also a claim, minus the evidence requirement). It's a
   **`breakdown`↔`take` boundary** failure caused by the rare class never being predicted, not by the
   comment being mislabeled.
2. **`‹breakdown comment text›`** — true **breakdown** / pred **take** (conf `‹›`).
   *Why:* `‹is the evidence numbers-free (a film/tactical read)? those are the breakdowns most easily mistaken for opinion, since there's no digit token to lean on›`
3. **`‹breakdown comment text›`** — true **breakdown** / pred **take** (conf `‹›`).
   *Why:* `‹note the confidence — if it's only moderate, the model is "unsure but defaulting to take"; if it's high, it has confidently merged the two classes›`

> Pattern (verify against the printout): is the model's confidence on these mislabeled breakdowns
> *lower* than on its correct reactions? If so, the errors are at least "uncertain," which matters for §
> the deployment story (low-confidence predictions could be deferred to a human).

### 6.5 Sample classifications (fine-tuned model)
3–5 test comments with the model's prediction + confidence (from the Section 4 output / wrong-preds cell).

| Comment (truncated) | Predicted | Confidence | True | Correct? |
|---|---|---:|---|:--:|
| ‹a reaction it got right› | reaction | ‹0.9x› | reaction | ✅ |
| ‹a take it got right› | take | ‹› | take | ✅ |
| ‹a breakdown it missed› | take | ‹› | breakdown | ❌ |
| ‹optional 4th› | ‹› | ‹› | ‹› | ‹› |
| ‹optional 5th› | ‹› | ‹› | ‹› | ‹› |

*Why the correct one is reasonable:* the `reaction` prediction is the model's strongest skill (F1 0.77)
— `reaction` comments have a distinctive surface signature (short, exclamatory, slang, no claim) that a
small model learns easily, so a high-confidence `reaction` call on an emotional one-liner is exactly
what we'd expect it to get right.

---

## 7. Reflection — what the model learned vs. what I intended

I intended a **three-way** distinction along an *evidence* axis: `reaction` (no claim) → `take` (claim,
no real evidence) → `breakdown` (claim with load-bearing evidence). The whole intellectual point of the
taxonomy was that last boundary — whether a comment's evidence actually *supports* its claim.

**What the model actually learned was a two-way distinction, and it threw away the dimension I cared
about most.** Its decision boundary is essentially *"is this emotional banter (`reaction`) or is it a
basketball claim (→ `take`)?"* The evidence axis — `breakdown` vs `take` — was never learned at all:
the model predicts `breakdown` **zero** times (§6.3). So the part of "discourse quality" I set out to
measure (is the take *backed up*?) is exactly the part the model is blind to.

- **What it overfit to / leaned on:** the surface signature of `reaction` — short, exclamatory, slangy,
  claim-free text — which is why `reaction` is its best class (F1 0.77). And it learned that "anything
  that makes a basketball claim" defaults to `take`.
- **What it missed:** the entire `breakdown` class. Notably it did *not* even use the obvious surface
  proxy (digits/stats → breakdown) that I half-expected it to overfit to — with only ~41 examples, the
  minority-class collapse overwhelmed any weak signal, so it gave up on the class entirely rather than
  over-predicting it. That's a subtler lesson than I anticipated: too-little data on a hard class
  doesn't produce a *noisy* version of that class, it produces *silence*.
- **Where the real difficulty lives:** `reaction` is easy (distinct form); the `breakdown`↔`take`
  boundary is hard because the two are *semantically* similar (both assert a basketball claim) and
  differ only on whether the supporting evidence is load-bearing — a judgment that needs real reasoning.
  The 70B baseline can do that judgment from world knowledge; a tiny fine-tune on ~41 positives cannot.

**The honest gap:** my labels encode a distinction a human (and a large LLM) can make, but that a small
model can't learn at this data scale. What would close it: many more `breakdown` examples (ideally
150–200+), class weighting or oversampling to stop the collapse, and likely a larger base model —
**or** accepting that at this scale the achievable task is the 2-class one (`substantive claim` vs
`banter`) and redefining the taxonomy to match what's actually learnable. Either way, the failure is
informative precisely because it pinpoints *which* distinction was too hard and *why*.

---

## 8. Spec reflection
- **One way the spec (`planning.md`) helped:** the §3 "would the evidence support the claim on its
  own?" rule, written *before* labeling, is what let me resolve the decorative-stat cases consistently
  instead of labeling on vibes — and it directly became the Groq prompt's decision rules.
- **One way the implementation diverged:** my plan assumed ~27% `breakdown`, but real r/nba runs far
  more emotional than that — the first labeling pass came out at ~15%. I diverged by going back to
  collect **more long comments** to lift `breakdown` past 20% (and added long `take`s so the model
  wouldn't learn "long = breakdown"), rather than relabeling existing comments to force balance.

---

## 9. AI usage
- **Label stress-testing:** I had Claude generate boundary cases between `take`/`breakdown` and
  `take`/`reaction`. Cases it couldn't classify cleanly drove me to add the "evidence must be
  load-bearing" rule before annotating. *(I kept the rule; discarded a few of its generated examples
  that were too artificial to be realistic r/nba comments.)*
- **Annotation assistance (disclosed):** Claude **pre-labeled** the cleaned comment pool against my
  §2 definitions; I reviewed every comment and corrected disagreements. The `prelabel` column in the
  CSV preserves the model's original guess. I overrode it on the borderline decorative-stat cases
  (it over-called `breakdown` whenever a number appeared — exactly the failure mode I expect from the
  model too).
- **Failure analysis:** I gave the confusion matrix and per-class numbers to an LLM to characterize the
  failure. It identified the systematic pattern — `breakdown` is never predicted; all 9 true breakdowns
  collapse into `take` — and tied it to minority-class imbalance (~41 training examples) plus the
  semantic closeness of `take`/`breakdown`. I verified this directly against the matrix (the `breakdown`
  prediction column is all zeros) before writing §6.3/§7. I did *not* accept the LLM's secondary guess
  that the model was "keying on digit tokens" — the data contradicts it (it doesn't over-predict
  breakdown on numeric comments; it predicts it *never*), so I dropped that claim.

---

## How to reproduce
1. Open `ai201_project3_takemeter.ipynb` in Google Colab; **Runtime → Change runtime type → T4 GPU**.
2. Add `GROQ_API_KEY` in the Colab **Secrets** panel (🔑). Never commit the key.
3. **Section 1:** the label map is already set (`breakdown/take/reaction`); run it and upload
   `takemeter_dataset.csv` when prompted.
4. **Section 2:** run the split + tokenize (label map and prompt are pre-filled).
5. **Section 5 then 3, 4, 6** (baseline first per the project flow, or just run top-to-bottom).
6. Download `evaluation_results.json` and `confusion_matrix.png`, commit them, and fill the
   `‹FILL AFTER COLAB›` blanks in §6/§7 from the JSON.

## Repo contents
| File | What it is |
|---|---|
| `planning.md` | Design spec: labels, decision rules, data plan, metrics, AI plan, hard cases |
| `takemeter_dataset.csv` | 280 labeled r/nba comments (`text,label,prelabel,notes`) |
| `ai201_project3_takemeter.ipynb` | Fine-tuning + baseline notebook (label map & Groq prompt pre-filled) |
| `fetch_comments.py`, `fetch_more.py`, `clean_comments.py`, `select_pool.py`, `build_dataset.py` | Data collection/cleaning/assembly scripts |
| `evaluation_results.json`, `confusion_matrix.png` | Model outputs (added after the Colab run) |
