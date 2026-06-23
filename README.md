# TakeMeter — A Discourse-Quality Classifier for r/nba

TakeMeter is a fine-tuned text classifier that scores the *quality of discourse* in r/nba comments.
It sorts a comment into one of three categories — **breakdown**, **take**, or **reaction** — based on
**how** it argues (does it reason, assert, or just emote?), not on whether the opinion is correct.

> This README is the final report. The design notes, decision rules, and working detail behind every
> choice live in [`planning.md`](./planning.md).

> ⚠️ **Status:** everything up to the model run is complete (data, labels, prompt, pipeline). The
> metrics sections marked **`‹FILL AFTER COLAB›`** are filled in after running the notebook on a T4
> GPU — see [How to reproduce](#how-to-reproduce). The numbers come straight out of
> `evaluation_results.json`.

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
small, imbalanced set. _‹If you change anything during the run, update this paragraph.›_

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
| Zero-shot baseline (Groq llama-3.3-70b) | **`‹FILL AFTER COLAB›`** |
| Fine-tuned DistilBERT | **`‹FILL AFTER COLAB›`** |
| Random (3-class reference) | 0.333 |

_One-line takeaway:_ `‹did fine-tuning beat the baseline, and by how much?›`

### 6.2 Per-class metrics (precision / recall / F1)
**Baseline (Groq):**
| Label | P | R | F1 |
|---|---:|---:|---:|
| breakdown | ‹› | ‹› | ‹› |
| take | ‹› | ‹› | ‹› |
| reaction | ‹› | ‹› | ‹› |
| **macro avg** | ‹› | ‹› | ‹› |

**Fine-tuned DistilBERT:**
| Label | P | R | F1 |
|---|---:|---:|---:|
| breakdown | ‹› | ‹› | ‹› |
| take | ‹› | ‹› | ‹› |
| reaction | ‹› | ‹› | ‹› |
| **macro avg** | ‹› | ‹› | ‹› |

### 6.3 Confusion matrix — fine-tuned model (rows = true, cols = predicted)
_Fill from `finetuned_confusion_matrix` in the JSON (also committed as `confusion_matrix.png`)._
| true ↓ / pred → | breakdown | take | reaction |
|---|---:|---:|---:|
| **breakdown** | ‹› | ‹› | ‹› |
| **take** | ‹› | ‹› | ‹› |
| **reaction** | ‹› | ‹› | ‹› |

_Which boundary is hardest?_ `‹e.g. "most errors are breakdown→take: the model finds the stat but not whether it's load-bearing"›`

### 6.4 Three wrong predictions, analyzed
> Pull these from the notebook's "wrong predictions" cell (Section 4). For each: quote it, give
> true/pred + confidence, and explain *why* using the §6.3 guiding questions — which boundary, why it's
> hard, and whether it's a labeling problem or a data problem.

1. **`‹text›`** — true `‹›` / pred `‹›` (conf `‹›`). *Why:* `‹›`
2. **`‹text›`** — true `‹›` / pred `‹›` (conf `‹›`). *Why:* `‹›`
3. **`‹text›`** — true `‹›` / pred `‹›` (conf `‹›`). *Why:* `‹›`

### 6.5 Sample classifications (fine-tuned model)
> 3–5 example comments run through the model with predicted label + confidence; explain at least one
> correct one. _(You can reuse the Section 4 output, or run a few new strings through `trainer.predict`.)_

| Comment (truncated) | Predicted | Confidence | True |
|---|---|---:|---|
| ‹› | ‹› | ‹› | ‹› |
| ‹› | ‹› | ‹› | ‹› |
| ‹› | ‹› | ‹› | ‹› |

*Why the correct one is reasonable:* `‹e.g. "It cites a concrete on/off number that supports the claim — exactly the breakdown signal, and the model is 0.9+ confident."›`

---

## 7. Reflection — what the model learned vs. what I intended

> Write this *after* seeing the results. Intended target: the `breakdown`↔`take` line is about whether
> evidence is **load-bearing**. Likely reality: the model latches onto surface proxies —
> **presence of digits / player-stat tokens**, **comment length**, **hedge words** — rather than
> whether the evidence actually supports the claim. Address specifically:
> - What surface feature did it likely **overfit** to (e.g. "any comment with a number → breakdown")?
> - What did it **miss** (e.g. numbers-free film breakdowns; decorative-stat takes)?
> - Is `reaction` "easy" (distinct vocabulary/length) while `breakdown`↔`take` stays hard? What does
>   that say about where the *real* difficulty lives?

`‹your reflection›`

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
- **Failure analysis (planned):** after the run I'll paste the misclassified test examples into an LLM
  to surface systematic patterns, then re-read them to confirm before writing §6.4/§7, noting any
  pattern I had to discard. _‹Fill in what it found and what you corrected.›_

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
