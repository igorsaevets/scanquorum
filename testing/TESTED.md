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
