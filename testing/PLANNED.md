# Decided, not yet built

Work that has been argued through and accepted, but is not in the code. Distinct from
[TO-TEST.md](TO-TEST.md), which holds things nobody has decided yet because nobody has
measured them.

An entry leaves this file only by being built, or by being moved to
[TESTED.md](TESTED.md)'s rejected section with a reason.

---

## P1 — Ship the truncation detector as a first-class command
Exists in the lab as a script; not yet wired into the CLI. It runs a second engine with
independent layout analysis and flags any accepted token that is a proper substring of what
that engine read at overlapping coordinates.

**Why it matters:** truncation is the majority of the residual error (7 of 7 observed
mistakes), and it is the one class the vote cannot see. Measured false positives on this
corpus: hyphenation 3, punctuation 0.

## P2 — `--md-sidecar` provenance header, with page markers
Specified in the README and partially implemented. The header carries the engine list,
the counts, the source hash and the sentence addressed to the reading model. Page markers
(`<!-- page 12 -->`) let a quotation be traced back without opening the PDF.

**Open decision:** whether unconfirmed spans are also marked inline. Marking them inline
makes the file self-describing but breaks byte-exact quotation, which is the property the
whole tool exists to provide. Current plan: header and separate index only, inline marking
behind a flag that is off by default.

## P3 — A single `scanquorum doctor`
Report which engines are installed, which are missing, what the tool will and will not do
in that configuration — and exit non-zero only when it genuinely cannot run.

**Constraint, learned the expensive way on a sibling project:** a status line that
contradicts its own exit code is worse than none. A partial install is a *supported* state
and must not be reported as a failure.

## P4 — Ports of the remaining lab tools
`quote_check` (given a phrase, tell me how many places in it need eyes and show the crops),
`quote_insert` (byte-exact substitution into a document, with refusal when unconfirmed
places remain), and the human review window. All three work in the lab; none has been
generalised past one corpus.

**Rule for the port, and it is not optional:** each must arrive with a parity fixture in
the same shape as `tests/test_vote_parity.py`. A hand transcription that nothing checks is
how measured behaviour quietly stops being the shipped behaviour.

## P5 — Rename the `adobe` voter
The code calls the pre-existing text layer `adobe` throughout. Measured on the sample set:
**19 of 23 scanned documents had their layer made by Visioneer PaperPort, not Adobe**, and
three more by LuraTech. The name is wrong for most inputs and misleads anyone reading the
evidence file.

Rename to `pdf_layer`. Deferred only because it changes the key in every recorded fixture
and must be done together with a fixture regeneration, not before it.

## P6 — Accept documents with no text layer at all
Today the pipeline aligns candidates against the existing layer's word boxes. A pure image
PDF has no such frame. The engines can supply the frame themselves, but the alignment code
assumes one exists.

**Why it is not urgent:** the tool's value case is documents that *have* a layer nobody
verified. A document with no layer is a plain OCR job, which many tools already do.

## P7 — Per-document reference standard before any batch output is published
Standing rule rather than a feature: no ensemble artefact goes into a folder of real
documents until that document class has a measured reference standard. An unmeasured
artefact in a legal folder looks exactly as authoritative as a measured one, and nothing
downstream can tell the difference.

---

## P8 — render a crop for every unconfirmed word

**Status: not started. Named here because the README promised it and did not deliver it.**

Until 0.2.0 the README said the tool "will render each one as a cropped image so a person can
look at it in three seconds", and two other passages leaned on that promise. No code path in
`build` renders an image. The renderer exists in the unpublished lab tree, where the reviewing
was done by hand at 900 dpi; it was never ported.

What it needs: for each entry in the unconfirmed index, render its bounding box from the page
at a readable dpi with a little padding, write it beside the index, and reference it from the
JSON. `scanquorum/verify_ai.py` already contains a working `_png(pdf, page, bbox, dpi, pad)`
that does exactly this for the vision-model path, so the work is wiring rather than invention.

Why it matters more than it looks: the human-review step is the entire justification for
refusing to guess. Coordinates are a promise that someone will open a PDF viewer. A crop is
three seconds.
