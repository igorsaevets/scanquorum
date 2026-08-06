# Changelog

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
