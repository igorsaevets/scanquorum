# Changelog

## 0.2.2 - 2026-08-17

A silent-failure bug found while using this tool on a corpus it was not built
for: PDFs with NO existing text layer.

`build.py` was anchored to the PDF's own words as landmarks -- the whole
voting loop iterates over `pg.get_text("words")`. On a pure scan that list is
empty, `layout.assign(frame, [])` returns an empty owner map, every `for bi in
order` iteration then reads `owner.get(bi, []) == []` and emits nothing. The
fallback "words the frame did not cover" loop iterates the same empty list a
second time. The .md file comes back with a valid YAML header, a warning that
says "0 unconfirmed" (technically true and materially false: the unconfirmed
count only exists relative to what was emitted, and nothing was), and an
empty body. Every OCR engine has already run to completion and its boxes are
thrown away.

Found on Igor Saevets' I-485 exhibit corpus on 2026-08-17. Five of five
pilot SCAN documents (`EAD.pdf`, `SSN.pdf`, `SEVIS Records.pdf`, `B-01
Passport.pdf`, `Donation screenshot.pdf`) came back with 0 emitted rows from
the OCR half of the pipeline. Three of the five still emitted 10-19 rows,
but only because a `Exhibit D-02 - SEVIS Records` stamp had been added to
the PDF layer by the packaging tool -- so the "OCR output" was that one stamp
line read three times, not the document read once. If the stamps had not
been there, the count would have been zero for all five.

The consequence is exactly the failure mode this project exists to catch: a
report that says nothing needed a person's attention while producing an
artifact that was invisibly hollow. The bug is at build.py:150-268 in the
pre-fix code and had never fired in the paper's corpus because every EOIR
document there had a text layer.

### Fixed

- **New pure-scan emission path** in build.py (`_emit_pure_scan_page`). Runs
  when `pg.get_text("words") == []` and at least one engine produced boxes for
  the page. Voting is line-to-line rather than word-to-word (there is nothing
  in the PDF to anchor to), using the same `vote.decide` cascade the word path
  uses -- so LEX still refuses Capitalised tokens, PATTERN still requires
  digit-match from at least one other engine, and MEDOID still flags rather
  than accepts. IoU threshold 0.30, matching the workaround pilot
  (`ocr_pilot_v2.py`) that first characterised the bug on real files.
- Every rule tag on this path is suffixed with `|NO_LAYER`. `classify()`
  splits on `|` and reads the base, so the four accounting buckets are
  unaffected; the suffix exists so a reviewer scanning `evidence.json` can
  tell at a glance which rows came from OCR only.
- **New header field `pure_scan_pages`** with the count of pages that fell
  into this path. A run's header is where a downstream reader looks first,
  and the count being zero versus non-zero changes what "line granularity"
  means for the rest of the numbers on this page.
- **Header warning** prepends a "NOTE: N of M pages had no existing text
  layer" clause when the count is non-zero. Explains the coarser SEP/NUM
  behaviour so nobody has to reverse-engineer the difference.

### Tested

- `tests/test_purescan.py` builds a minimal pure-scan PDF fixture from a PIL
  render (no text layer at all, verified inline), runs `build()`, and asserts
  the .md body is non-empty and `pure_scan_pages` is at least 1. It also
  asserts that at least two rendered tokens survive round-trip through OCR,
  as a coarse sanity check that the emitted body reflects the image content.
  Skips if PIL / rapidocr / onnxruntime are missing, matching the doctor
  suite's philosophy that missing-engine paths must fail explicitly rather
  than silently.
- `test_vote_parity.py`, `test_goldset.py`, `test_riskcov.py`,
  `test_safety.py`, `test_doctor.py` -- unchanged, unaffected. This is a new
  code path, not a change to any rule.
- Smoke run on the original 5 pilot documents: rows emitted per file rose
  from `0-19` to `16-69`, matching what the pilot's workaround already
  produced. See the OCR report at
  `07-Исследования-и-рецензии/OCR-exhibits-2026-08-17/OCR-EXHIBITS-НАХОДКИ.md`
  (private repository) for the per-file counts.

### Not fixed

- On a pure-scan page the pipeline still emits at LINE granularity. That is
  not a workaround; it is a consequence of having no per-word anchors. A
  future release could add per-word bounding boxes from an engine that
  reports them (Tesseract does) and vote per-word inside each line, but that
  is a design change, not a bug fix, and the coarser SEP/NUM behaviour is
  reported honestly here rather than hidden.
- The mixed case -- a page with a partial text layer, e.g. the stamped SEVIS
  document above -- still runs the word-anchored path and misses whatever is
  in the image but not in the layer. This is a separate problem (MIXED, not
  SCAN, in the classifier) and would need a different fix: emitting from both
  paths on the same page and reconciling their overlap. Scoped as a follow-up.

## 0.2.1 - 2026-08-09

The two measurements every reviewer of the paper asked for, now shipped and recomputable.
No change to the voter; the parity fixture still replays byte for byte.

- **The risk-coverage curve** (`tests/test_riskcov.py`, fixture
  `tests/fixtures/index_census.json`): accepted-token accuracy against coverage for
  fourteen acceptance policies, from unanimity-only (77.3 % coverage, 0 errors in 7 gold
  crops, unweighted Wilson floor 64.6 %) to everything-emitted (98.9 % coverage, estimated
  99.3 %, Manski band [97.7, 99.3]).
- **The single-engine confidence baseline**: `rapidocr_multi` alone, thresholded on its own
  line-level confidence, spans 95.9–98.7 % across coverages and barely sorts its own errors.
  The ensemble's point estimate is above it at all fourteen policies matched in both
  directions, and the paired per-resample difference excludes zero at every point; the fair
  word-level challenger (Tesseract) is indistinguishable at the ≤ 83 % coverage it can reach
  and cannot go higher. Round-3 corrections folded in same day: the never-sampled mass is
  560 tokens (1.9 %), not 597; the original head-to-head matched only upward, which flattered
  the ensemble. "No change to the voter" below means no change between 0.2.0 and 0.2.1; the
  34 divergences the replay reports are recorded lab evidence vs shipped code, documented
  since 0.2.0.
- The measuring script's **first version was itself wrong** — it divided an estimated
  numerator by an exact denominator and printed accuracies above 140 %. Recorded in
  `testing/TESTED.md` round 4 with the fix (a Hájek ratio), because a rejected instrument
  that vanishes is an instrument someone rebuilds.
- Replaying all 29,853 recorded decisions through the shipped voter (not just the 11,780
  distinct sets) found the recorded evidence and the shipped code disagree on 34 rules —
  the 33 tie-policy moves plus name translation — and on two gold crops (#27, #38) where
  the shipped code now refuses instead of guessing; #27's guess was wrong, #38's was right.

## 0.2.0 - 2026-08-06

A second round of outside review, this time by six independent models with live web search.
Everything below is a correction. Nothing new was added to the voter.

### The header overstated the only claim this project makes

`accepted_by_quorum` counted `VOTE*` together with `SEP`, `NUM`, `LEX` and `PATTERN`. On the
41-page EOIR index that reports **29,160 of 29,853 words (97.68 %)** as "read identically by at
least two independent OCR engines", when the number that actually won a vote is **25,838
(86.55 %)**. An eleven-point overstatement, in the machine-readable header, in the field a
downstream model is most likely to trust.

`LEX` is the clearest case: it picks whichever candidate is in a dictionary. That is a lookup
breaking a tie, not a second engine agreeing.

Replaced by four fields that **partition** the corpus, with an assertion enforcing it:

- `agreed_exactly` — two or more independent engines produced the same string
- `agreed_on_digits_not_punctuation` — same digits, different separator. `12-869` against
  `12 869` is the difference between two case citations
- `chosen_by_rule_no_second_engine` — dictionary or pattern, no corroboration
- `unconfirmed` — disputed, medoid-flagged, or seen by one engine only

`unconfirmed` is separately asserted to equal the number of records in the index file it names,
so "listed in X" is a fact rather than a caption. `classify()` raises on an unrecognised rule
instead of assigning one, because the original failure was a rule quietly landing on the
flattering side of the line.

### Claims removed because they were not true

- **`--detect-truncation` was described in `artifacts/ARTIFACTS.md` as "shipped".** It does not
  exist. The flag is in no code path. It told readers the largest known residual error class
  already had a defence.
- **The README said unconfirmed words are rendered as cropped images.** No code renders a crop.
- **The README's sidecar example was a hand-written illustration** showing a superseded warning
  string, a wrong version, and engine names (`rapidocr-v6-multi`, `tesseract-5.5-lstm`) that no
  code path produces. It is now real output, pasted from a run.
- **The producer of the main test document was wrong.** README said `Adobe Acrobat 25 Paper
  Capture`; the file's own metadata says `Acrobat PDFWriter 4.0 for Windows NT`, matching
  `samples/MANIFEST.json`. Found by an outside reviewer that read both files.
- **Prior art was dismissed on a negative search** ("what we did not find was..."). Rewritten
  with the actual literature: ROVER, ISRI/UNLV `vote`, Lund and Ringger, Handley, Chow,
  selective prediction, Calamari, OCR-D. Most of this system is thirty years old and the
  README now says so.

### The accuracy figures are now recomputable by a stranger

`tests/fixtures/goldset.json` ships the reference standard: 60 crops from the EOIR index, each
with what a human read from the page at 900 dpi and what each voter read. `tests/test_goldset.py`
scores it, prints Wilson intervals beside every point estimate, and reports per-rule accuracy.

This also resolves a discrepancy nobody had explained: **60 crops were labelled, 4 have an
unusable frame (`BAD_BOX`), 56 are scored.** Both numbers appeared in different documents and
neither said why.

The test carries a permanent check on its own reference standard: *if every engine agrees and
the human disagrees, suspect the human.* An earlier version of the labels was read from a
contact sheet whose padding caught the neighbouring line, and five of sixty were wrong.

### Install became checkable instead of hopeful

- `scanquorum doctor` — probes every dependency by importing it, every engine by running it on
  a generated page and checking it reads back the text that is on it. Exits 0 ready, 1 degraded,
  2 broken. Every failure prints the exact command that fixes it.
- `requirements.txt` with `==` pins, because RapidOCR selects model weights by enum and an
  upstream patch release can move the models under a published number.
- `INSTALL.md` with per-platform Tesseract instructions, `AGENTS.md` for an AI agent asked to
  set this up, and CI that verifies the degraded case rather than only the happy one.

`doctor` was itself written wrong twice and both defects died on first execution: it handed PNG
bytes to adapters that take a PDF path, and it guessed an import name that does not exist. It
now has its own test suite, including a negative control.

## 0.1.0 - 2026-08-06

First public release.

### Included
- `scanquorum.vote` - the decision cascade. Every rule returns a candidate some engine
  proposed, or nothing. No rule composes text.
- `scanquorum build` - full pipeline: PDF in, Markdown sidecar with a provenance header,
  an index of unconfirmed places, and the full evidence record out.
- Four engine adapters: the PDF's existing text layer, two RapidOCR configurations and
  Tesseract 5.
- `scanquorum verify-ai` - a vision model may CHOOSE among engine readings or abstain. It
  cannot supply text; that is enforced in the parser, not requested in the prompt. Every run
  includes negative controls and prints the abstention rate.
- `tests/test_vote_parity.py` - replays 11,780 real decisions recorded from the measured run.
- `tests/test_safety.py` - the model-reply boundary.
- Five sample documents, each verified byte-for-byte against the government's own copy.

### Fixed before release
- **Ties resolved by dictionary ordering, in four places.** 165 of 11,780 distinct decisions
  (1.40 %) changed answer when the engines were reordered; 29 changed a digit. Found by the
  parity test. Punctuation-only ties now use a stated rule; digit-level ties become disputes.
  No gold-set crop changed, so the published accuracy still describes this code.
- **Neural OCR line boxes looked up as word boxes**, which silently muted two of four voters:
  `VOTE4/4` collapsed from 77 % to 0.3 % while the output still looked healthy. Adapters now
  declare their granularity.
- **Crash on a Windows console** using a legacy code page - the tool died on its own
  "engine not available" warning, destroying the diagnostic it was delivering.
- **`_parse_choice` crashed on a blank model reply**, and accepted `CHOICE: 12-855` as
  index 12 whenever twelve or more candidates were offered.
- `--out-dir` did not create the directory it was given.
