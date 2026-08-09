# Hypotheses tested — adopted and rejected

One row per hypothesis that was actually measured. A hypothesis with no measurement
belongs in [TO-TEST.md](TO-TEST.md), not here.

**Rule of this file:** a rejected hypothesis keeps its entry forever, with the reason.
Deleting rejected work is how a team tries the same bad idea twice.

---

## ✅ Adopted

### T1 — Several engines voting beat picking the best single engine
**Measured:** 56 hand-checked crops, reference standard = the page at 900 dpi read by eye.
Existing layer 91.5 %, best single neural engine 95.9 %, second neural engine 93.5 %,
**quorum 97.5 %** (weighted by rule share). Adopted. This is the whole product.

### T2 — A fourth engine helps because it is *independent*, not because it is good
**Hypothesis:** adding Tesseract — the weakest of the four — would not help.
**Measured:** 49/56 → **53/56**. It helped 4 times, hurt 0. In one case the correct
reading was proposed by *no* other engine (`inay` / `nay` / `mnay` from the other three,
`may` from Tesseract).
**Why:** the two neural engines share a text detector — 2,921 of 3,006 boxes identical.
"Three voices" was closer to two. Adopted, with the caveat in T3.

### T3 — …but that improvement is not statistically significant
**Measured:** exact McNemar on the 4 discordant pairs, all one-way: **p = 0.125**.
**Verdict:** adopted the engine, **rejected the claim**. The README says the improvement
is not significant. A real effect and an unproven effect can be the same number.

### T4 — One word must belong to exactly one OCR line
**Found by:** using the tool to pull a real quotation, which came back as
`On On On November November November`.
**Measured:** overlapping line boxes inflated full-width pages by **1.29×** — 4,801
surplus tokens in one decision. On the narrow-column index: 7 cases in 29,858, which is
why two rounds of code review missed it.
**Adopted:** each word is assigned to the single line whose vertical centre is nearest.
**Lesson recorded:** reading code did not find this; applying the artefact did.

### T5 — The medoid should flag, not decide
**Raised by:** an outside reviewer, as a fabrication path.
**Measured:** the rule was accepting 87 tokens that no two engines had ever agreed on.
**Adopted:** it now proposes and marks unconfirmed. Review queue grew from 0.73 % to
1.05 %. Accuracy unchanged. Correct trade for a legal quotation.

### T6 — Citation *shape* must not be trusted without matching *digits*
**Raised by:** an outside reviewer. `12-856` matches the citation pattern exactly as well
as `12-855`. **Adopted:** the PATTERN rule additionally requires the digits to match at
least one other engine — shape from one, digits from two.

### T7 — The lexicon must never touch a capitalised token
**Risk:** a real surname absent from the lexicon (`Smythe`) replaced by a frequent one
(`Smith`). **Measured cost of the restriction: zero** — every LEX firing in the gold set
was lower-case, accuracy 10/10 unchanged. Adopted.

### T8 — 🔴 Ties resolved by dict ordering (found while publishing)
**Measured:** 165 of 11,780 distinct decisions (**1.40 %**) changed answer when the
engines were reordered; **29 changed a digit**. Four separate sites; one had already been
found and fixed in 2026-08, and the other three were missed.
**Adopted:** punctuation-only ties get a stated deterministic rule; digit-level ties become
disputes. 33 decisions moved from guessed to shown. **No gold-set crop changed**, so the
published accuracy still holds. Details in [../artifacts/ARTIFACTS.md](../artifacts/ARTIFACTS.md#c2).

### T9 — A vision model may choose among readings, never produce them
**Measured, negative controls** (correct answer removed from the list, only defensible
answer is "none"): one model abstained on **95 %**, another on **46 %**. Same task, same
prompt.
**Adopted:** the safety property belongs to the *model*, not the harness, so
`verify_ai.py` runs negative controls on every run and prints the abstention rate. The
reply parser accepts only an index or an abstention — enforcement in code, not in a prompt.

---

## ❌ Tested and rejected

### R1 — "Take numbers from one engine, letters from another"
**Rejected.** The rule was derived from a broken measurement: the regex used to count
citations did not accept the long dash that one engine uses as a separator, so that
engine's citations appeared to vanish. Re-measured properly: that engine found **more**
citations than the existing layer, not fewer. A voting scheme does not depend on that
error at all.
**Lesson:** the hypothesis was invented to explain an artefact of the measuring
instrument.

### R2 — Report a document-level "probability the whole quotation is clean"
**Rejected after all four outside reviewers called it invalid.** The metric multiplied
per-token Wilson lower bounds. By the Fréchet inequality the true lower bound of a
conjunction of 13 events with those marginals is `max(0, 9.52 − 12) = 0`. The product has
no coverage property at all. The tool had been printing "P ≥ 0.4 %" next to "✅ CLEAN".
**The metric was deleted rather than corrected.** A number that is wrong in an unknown
direction is worse than no number.

### R3 — Re-weight the original stratified sample by the *new* rules' shares
**Rejected — and this one had already produced a false result.** Horvitz–Thompson
inclusion probabilities come from the stratification actually used when sampling. Weighting
by the new rule shares is not an estimator of anything. It is how 98.65 % was briefly
reported as a different number. Two reviewers disagreed about this; the disagreement was
settled by computing it both ways rather than by argument.

### R4 — "The review queue can be skipped; it is mostly noise"
**Rejected on measurement.** 14 % of the queue was citation-critical — the index *is* the
source of the citations being looked up. Claim withdrawn.

### R5 — Let the vision model transcribe the disputed region directly
**Rejected on principle and kept rejected after measurement.** It is the fastest way to
resolve a dispute and it reintroduces exactly the failure this project exists to prevent.
See T9 for what the measurement showed about trusting models to abstain.

### R6 — Build ensemble PDFs for the full working corpus and file them
**Rejected for now.** There is no pixel-level reference standard for those documents; the
99.15 % figure is measured on one document and does not transfer. An unmeasured artefact
sitting in a folder of legal documents looks exactly as authoritative as a measured one.
Moved to [TO-TEST.md](TO-TEST.md) as G1.

---

## Round 3 (2026-08-06): six external reviewers, and what execution said afterwards

### T7 — the header's `accepted_by_quorum` overstated by eleven points

**Hypothesis:** the field means what it says.
**Method:** counted the rules it includes against the rule census of `merged_evidence.json`
(29,853 records, the 41-page EOIR index).
**Result:** it counted `VOTE*` together with `SEP`/`NUM`/`LEX`/`PATTERN`, giving 29,160 (97.68 %)
as "read identically by at least two independent OCR engines". The number that actually won a
vote is 25,838 (86.55 %). `LEX` picks whichever candidate is in a dictionary, which is a lookup
breaking a tie, not a second engine agreeing.
**Adopted:** four fields that partition the corpus, with an assert. `classify()` raises on an
unknown rule rather than assigning one.
**Verified by running it:** on `samples/02`, 856 + 1 + 0 + 28 = 885. Both asserts hold.

### T8 — the gold set is 60 and the denominator is 56, and nobody had said why

**Method:** exported the labelled set and counted.
**Result:** 60 crops labelled, **4 are `BAD_BOX`** (the word box inherited from the PDF does not
correspond to a token), 56 scored. Both numbers were correct and neither was explained.
**Adopted:** published as `tests/fixtures/goldset.json`; `tests/test_goldset.py` recomputes
everything the README quotes.

### T9 — every voter against the pixels, with intervals

| voter | agrees | 95 % Wilson |
|---|---:|---|
| PDF text layer | 46.4 % | [34.0, 59.3] |
| `rapidocr_multi` | 78.6 % | [66.2, 87.3] |
| `rapidocr_en` | 60.4 % | [46.9, 72.4] |
| **ensemble** | **94.6 %** | [85.4, 98.2] |

n = 56, **stratified toward contested decisions**, so these are not document accuracies. The
16-point gap between the ensemble and the best single voter is the finding; the absolute values
are not.

### T10 — the fourth engine, measured end to end rather than argued about

Two external reviewers disagreed about which engine the fourth is and therefore about whether
the 3-vs-4 comparison means anything. Settled by running both on `samples/02`:

| | 3 engines | 4 engines (+ Tesseract) |
|---|---:|---:|
| read identically by >= 2 | 848 | **856** |
| not confirmed | 36 | **28** |
| carried only by the correlated pair | 7 | **4** |
| independent OCR opinions | **1** | **2** |

The fourth engine is Tesseract, and it is the only one with its own layout analysis. Without it
the two RapidOCR voters share a detector and there is one independent opinion, not two.

### T11 — `doctor` catches the silent degradation, and was itself wrong twice

**Method:** ran the pipeline with Tesseract present but not on `PATH`.
**Result:** a complete, confident, well-formed output built from a degraded quorum, with nothing
in the file saying the fourth voice was missing.
**Adopted:** `scanquorum doctor`, exit 0/1/2, remediation per failure.
**Its own defects, both dead on first execution:** it handed PNG bytes to adapters that take a
PDF path (reported three broken engines on a machine where all three worked), and it guessed the
import name `rapidocr_onnxruntime`, which does not exist. `tests/test_doctor.py` now covers both,
plus a negative control that points `TESSERACT_EXE` at a file that is not there.

### R3 — REJECTED: claiming novelty from a failed search

The README said "what we did not find was the combination this repository implements". Six
reviewers were then asked to find prior art and found ROVER, ISRI `vote` (which already broke
ties with heuristics), Lund and Ringger, Handley, Chow, selective prediction, Calamari and
OCR-D. The section was rewritten to say most of this is thirty years old.

The narrow claim that survived: **no reviewer found prior work that tests an OCR ensemble's tie
breaks for determinism under permutation of engine order.** Three of the six documented their
search terms; the other three asserted it without showing their work, and one had no search
tools at all. So the claim rests on three documented negatives, and it is stated that way.

---

## Round 4 (2026-08-09): the two experiments every reviewer ranked first

Measured by `riskcov.py` v1.1 (lab), replayed publicly by `tests/test_riskcov.py` from
`tests/fixtures/index_census.json`. Design: every one of the 29,853 recorded candidate sets is
re-decided by the shipped `vote.decide`; coverage per policy is a census, exact; accuracy among
accepted tokens is a Hajek ratio over the 56 gold crops with post-stratification weights
N_h/n_h by three-voice stratum, per the convention `ht_estimate.py` set for the published
99.15 %. The machinery reproduces that 99.15 % from recorded choices before anything new is
computed.

### T12 — the risk-coverage curve: the cascade's extra coverage costs ~0.7 points

| policy | coverage | acc (Hajek) | honest uncertainty |
|---|---:|---:|---|
| unanimity only (VOTE4/4) | 77.3 % | 100 % | **0 errors in 7 crops; Wilson floor 64.6 %** |
| VOTE>=3 +SEP/NUM | 95.3 % | 99.4 % | CI [98.1, 100] |
| VOTE>=2 +SEP/NUM +LEX/PATTERN | 97.6 % | 99.4 % | CI [98.2, 100] |
| everything emitted (+flags) | 98.9 % | 99.3 % | CI [97.9, 100]; Manski [97.7, 99.3] |

Accuracy is remarkably flat from VOTE>=3 outward: the cascade's later rules add ~14 points of
coverage while the measured accuracy moves less than 0.2 points. The sample cannot distinguish
the policies from each other (CIs overlap heavily); what it does support is that no policy on
the grid collapses. Strata with one crop (NUM, МЕДОИД-ФЛАГ) contribute zero bootstrap
variance, so CIs are understated wherever they carry weight; 597 tokens (2.0 %) sit in strata
with no gold crop at all and enter only the Manski bands.

### T13 — the single-engine baseline: its confidence barely sorts its errors

`rapidocr_multi` alone, thresholded on its own line-level confidence (words inherit their
line's score; 26 of 27 same-line neighbour pairs share it): accuracy stays in a narrow band —
95.9 % at 99 % coverage, 97.1 % at 91 %, 97.4 % at 14 % coverage. Throwing away five sixths of
the document buys about 1.5 points. **At every one of the 14 matched-coverage points the
ensemble sits above the single-engine curve.** Point estimates; most per-point intervals
overlap, so this is a consistent pattern, not 14 independent significant wins — but it answers
the reviewer's question ("if the ensemble does not dominate this curve, the premise collapses")
in the direction the premise needed.

### T14 — the full-corpus replay caught what the distinct-set parity replay could not

Replaying all 29,853 records (not the 11,780 distinct sets) against the recorded evidence:
34 rule differences — the 33 tie-policy moves recorded in T8 plus translation — and two gold
crops where the shipped code refuses where the lab code guessed: **#27** (guess was wrong;
refusing is strictly better) and **#38** (guess was right; refusing costs one correct token).
The safety trade has a measured price now, and it is one token in 56.

### R7 — REJECTED: the first version of the measuring script itself

`riskcov.py` v1.0 divided an HT-estimated numerator by the exact accepted count and printed
accuracies of 143 % — the dominant stratum has 23,585 tokens behind 8 crops, and which crops
fall inside a policy is sampling noise worth ~2,948 tokens each; against an exact denominator
it does not cancel. Fixed by the Hajek ratio (numerator and denominator from the same sample).
Kept as `riskcov_v1.0.py` in the lab tree. Sixth broken instrument across these sessions, and
the second one caught by its own output being impossible.
