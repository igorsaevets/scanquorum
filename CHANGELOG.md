# Changelog

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
