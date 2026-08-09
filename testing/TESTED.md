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

Measured by `riskcov.py` v1.2 (lab), replayed publicly by `tests/test_riskcov.py` from
`tests/fixtures/index_census.json`, then audited by nine external channels (round 5 below).
Design: every one of the 29,853 recorded candidate sets is re-decided by the shipped
`vote.decide`; coverage per policy is a census, exact; accuracy among accepted tokens is a
Hajek ratio over the 56 gold crops. **The weights are post-stratification by the REBUILT
three-voice stratum (N_h/n_h), not draw-time inclusion probabilities** — the draw-time
evidence no longer exists, the strata moved under the sample when two pipeline bugs were
fixed (quota said СПОР 16, SEP 12; the rebuilt joins say СПОР 6, SEP 19), and if migration
correlates with difficulty the estimates carry an unquantified bias whose sign is unknown.
This is the same convention behind the published 99.15 %, which the machinery reproduces
from recorded choices before anything new is computed. Chain of custody: the raw engine
outputs were cached on 2026-08-05 at 14:11–14:25, BEFORE the gold draw and both rebuilds, so
the rebuilds re-tabulated cached OCR — no engine ever ran twice.

### T12 — the risk-coverage curve: coverage is nearly free, and the sample cannot prove more

| policy | coverage | acc (Hajek) | correct-token yield | honest uncertainty |
|---|---:|---:|---:|---|
| unanimity only (VOTE4/4) | 77.3 % | 100 % | 77.3 % | **0 errors in 7 crops (n_eff 7); unweighted Wilson floor 64.6 %** |
| VOTE>=3 +SEP/NUM | 95.3 % | 99.4 % | 94.7 % | CI [98.1, 100] |
| VOTE>=2 +SEP/NUM +LEX/PATTERN | 97.6 % | 99.4 % | 97.0 % | CI [98.2, 100] |
| everything emitted (+flags) | 98.9 % | 99.3 % | 98.2 % | CI [97.9, 100]; Manski [97.7, 99.3] |

Measured accuracy **does not collapse** as coverage rises: the cascade's later rules add ~14
points of coverage while the point estimates move less than 0.2 points. The sample cannot
distinguish the policies from each other (intervals overlap heavily), so the supported claim
is "no collapse", not "flat". The yield column is why the cascade exists at all: unanimity
delivers 77.3 % of the document correct; the default delivers 98.2 %.

The small print, all of it. Strata with one crop (NUM, МЕДОИД-ФЛАГ) contribute zero bootstrap
variance, so CIs are understated wherever they carry weight — and the dominant stratum has
n=8 behind 79 % of the corpus, which is the real ceiling on precision here. **560 tokens
(1.9 %)** sit in strata with no gold crop at all and enter only the Manski bands (an earlier
draft said 597 and was caught by three reviewers against the script's own printout: NUM has
one crop and is covered). Wilson floors on zero-error rows are unweighted sample statements,
not design CIs; where the accepted crops span unequal strata the effective sample size is
printed and the floor at n_eff is the honest one (28 crops -> n_eff 9, floor 70.1 %, not
87.9 %). Manski bands are plug-in at the point estimate, not confidence bands; the
CI-combined envelope is in `testing/riskcov_results.json`.

Sensitivity, measured rather than argued (`riskcov_sens.py` v1.1, lab):
- **BAD_BOX counted as errors** (two reviewers assumed this craters the curve): the four
  unusable-frame crops sit in СПОР×2/VOTE2/3/LEX, not in the dominant stratum. The
  full-coverage point drops 99.27 % -> 98.73 %; the unanimity point does not move. The
  exclusion is a convention, not a load-bearing trick — but unanimity is exactly the regime
  where frame errors hide (G2), and no crop-level standard can price that.
- **Lexicon ablation** (one reviewer suspected the curve rests on it): with an EMPTY lexicon,
  109 LEX tokens redistribute to DISPUTED/MEDOID, coverage of the full policy drops
  98.93 % -> 98.63 %, headline accuracies move by <=0.01. Four gold crops flip. The curve
  does not rest on the lexicon.
- **Residual errors, by crop**: under the default policy the accepted-and-wrong crops are
  **#8** (VOTE3/4, read 'et.', truth 'ct.') and **#24** (MEDOID_FLAG, flagged emission,
  truth '3—275;'); **#27** and **#38** are refused (DISPUTED). That is the entire observed
  error set behind every number above.

### T13 — the single-engine baselines: line confidence sorts nothing, word confidence cannot reach

`rapidocr_multi` thresholded on its own confidence — which is **line-level**, every word
inherits its line's score (26 of 27 same-line neighbour pairs identical, this document) — is
a lower bound on single-engine confidence sorting, and it barely sorts: 95.9 % accurate at
99 % coverage, 97.4 % at 14 %. Against that baseline the ensemble's point estimate is above
at all 14 policies, matched at nearest coverage **in both directions** (the first cut of this
comparison matched only upward, which hands the baseline extra low-confidence tokens and
flatters the ensemble — caught by three reviewers). Marginal per-point intervals overlap at
every point; the **paired per-resample difference — the statistically correct form on shared
crops — excludes zero at all 14 points in both matching directions** (lower bounds +0.4 to
+1.2 points).

The fair challenger is **Tesseract, whose confidence is per word**: at τ=0.85 it reaches
99.2 % accuracy at 80.6 % coverage (20/21 gold crops — treat accordingly), and there the
paired difference against the ensemble is NOT significant on this sample (lower bounds
exactly 0.0). Its curve then collapses — below τ=0.8 accuracy falls to 86.7 % — so it cannot
deliver more than ~83 % coverage at comparable accuracy. The measured claim, in one sentence:
**no single engine's confidence in this stack delivers 95–99 % coverage at ~99 % accuracy,
and 95–99 % coverage is where a quotation tool operates; at the coverages the best single
engine can reach, this sample cannot separate it from the ensemble.**

### T14 — the full-corpus replay caught what the distinct-set parity replay could not

Replaying all 29,853 records (not the 11,780 distinct sets) against the recorded evidence:
34 rule differences — the 33 tie-policy moves recorded in T8 plus translation — and two gold
crops where the shipped code refuses where the lab code guessed: **#27** (guess was wrong;
refusing is strictly better) and **#38** (guess was right; refusing costs one **correct
token in 56 gold crops** — a gold-set ratio, not a document rate). Reconciliation a reviewer
demanded: **99.15 % describes the recorded lab pipeline (HT, recorded choices); 99.27 % is
the shipped voter's full-emission point (Hajek, replayed choices); the difference is the 322
tokens where the shipped code refuses instead of guessing.** Related census note: the
recorded evidence contains one duplicated frame — page 17, one speckle region emitted as
three pseudo-tokens by the union-frame branch — worth <=2 tokens of 29,853; found by a
reviewer's suggested check, kept because a census that hides its own defects is not a census.

### R7 — REJECTED: the first version of the measuring script itself

`riskcov.py` v1.0 divided an HT-estimated numerator by the exact accepted count and printed
accuracies of 143 % — the dominant stratum has 23,585 tokens behind 8 crops, and which crops
fall inside a policy is sampling noise worth ~2,948 tokens each; against an exact denominator
it does not cancel. Fixed by the Hajek ratio (numerator and denominator from the same sample).
Kept as `riskcov_v1.0.py` in the lab tree. Sixth broken instrument across these sessions, and
the second one caught by its own output being impossible.

### R8 — REJECTED with proof: a reviewer's "cleaner" Manski plug-in

Round-3 reviewer kimik3 argued the Manski band should plug in the raw HT numerator instead
of `acc × den_cov`, calling the latter an estimated/exact hybrid of the v1.0 class. Tried:
the band printed [89.4 %, 89.4 %] on a policy whose every scored crop is correct. The algebra
says why: `acc × den_cov = num × (den_cov/dht)`, and that factor is exactly the correction
that cancels the which-crops-were-accepted noise in `num`; the raw numerator REINTRODUCES the
v1.0 disease into the band. The same reviewer's other three findings on this file were real
and are fixed above — reliability is per-claim, not per-channel.
