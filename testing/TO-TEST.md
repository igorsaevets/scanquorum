# Hypotheses not yet measured

Nothing here is a claim. Each entry states what would have to be measured to move it to
[TESTED.md](TESTED.md), and what result would kill it.

Ordered by how much the answer would change the tool.

---

## G1 — 🔴 There is no pixel-level reference standard except on one document
**The largest known gap.** The 98.65 % / 99.15 % figures are measured on the 41-page
EOIR index alone. Every other document type — full-width decision pages, two-column
reports, Supreme Court volumes with a different scanner — is unmeasured.

**To measure:** build a stratified crop set on a full-width decision page, sampled by
which rule fired, and score against 900 dpi renders.
**Would kill the claim if:** accuracy on running text is materially below the index. The
index has short, numeric, well-separated tokens; running prose is a different problem and
may well be easier or harder. Nobody knows which.

## G2 — 🔴 The reference standard cannot see truncation, by construction
Both the tool and its measurement inherit the same box. Of 24 disagreements checked by
eye, all 7 errors were truncations.

**To measure:** a reference standard built from *page*-level human transcription rather
than crop-level, on a small number of pages, so that text lost to a bad box is visible as
a miss.
**Expected cost:** high — this is the only defect class that requires reading whole pages.
**Would change the headline if:** page-level accuracy is materially below crop-level, which
it almost certainly is. The current figure should be read as an upper bound.

## G3 — End-to-end test on real quotation requests
Fifty realistic "find and quote this passage" tasks driven through the whole pipeline
including the *locating* step, not just the decision step.

**Why it matters:** the token-duplication defect (T4) would have been caught by
construction on the first such test, and instead survived two rounds of code review. Every
test we have exercises a component; none exercises the task.

## G4 — Break a 2:2 split with the CTC lattice instead of calling it a dispute
Tesseract's `lstm_choice_mode=2` emits per-character alternatives with confidences —
**61 % of character positions have a second candidate.** A 2:2 split could be resolved by
asking whether either reading appears in the lattice at all.

**To measure:** how many of the current disputes the lattice resolves, and how often it
resolves them *wrongly* — the second number is the one that decides it.
**Would kill it if:** it resolves disputes wrongly more than about 1 in 20, since a
dispute shown to a human costs three seconds and a wrong citation costs far more.

## G5 — Does the `.md` provenance header actually change model behaviour?
The header tells the reading model which words are unconfirmed. That is an *assumption*
about how models respond to it, and it is the cheapest claim in the README to test.

**To measure:** same document, same questions, with and without the header; count how
often the model quotes an unconfirmed token without flagging it.
**Would kill the feature if:** no measurable difference. Then it is decoration.

## G6 — Is the whitespace-gutter column detector safe outside this corpus?
Two-column detection is a heuristic. It is right on the index. Reading order is not checked
by anything.

**To measure:** run it over documents with pull quotes, footnotes, marginal notes and
tables, and count reading-order inversions.

## G7 — How much does a fifth engine add, and at what point does adding engines stop paying?
T2 showed independence beats strength. That implies a diminishing return but does not
locate it.

**To measure:** add one engine from a genuinely different family and re-run the gold set.
**Prediction to be falsified:** an engine sharing a detector with an existing one adds
approximately nothing.

## G8 — Does this generalise past English legal print from 1950–2010?
Everything measured here is one language, one register, one era, one scanner generation.
Modern colour scans, non-Latin scripts and born-digital-then-rescanned documents are
entirely untested.

## G9 — Cost and speed have never been measured properly
No figure exists for pages per minute, memory, or how it degrades on a laptop without a
GPU. Anyone deciding whether to run this on 10,000 documents currently has nothing to go
on.
