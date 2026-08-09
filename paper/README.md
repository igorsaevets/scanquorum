# The paper

`scanquorum.tex` is a six page preprint about the determinism audit in
[`testing/TESTED.md`](../testing/TESTED.md). `scanquorum.pdf` is the compiled output.

## Building it

There is no LaTeX toolchain on the machine this was written on, and there does not need to be
one on yours. [tectonic](https://tectonic-typesetting.github.io/) is a single executable with no
installer and no TeX distribution:

```bash
tectonic paper/scanquorum.tex
```

It downloads the packages and fonts it needs on first run and caches them, so the first compile
needs a network connection and later ones do not. On Windows it prints
`Fontconfig error: Cannot load default config file` on every run. That is cosmetic and the PDF
is produced anyway.

The source deliberately uses only `amsmath`, `booktabs`, `url`, `hyperref` and `geometry`, and a
hand-written `thebibliography` rather than BibTeX. A build failure on a submission server costs
far more than a plainer document does.

## Status: not submitted anywhere

Read this before assuming otherwise.

**Six independent models reviewed the system and agreed on the framing.** None of them
recommended a main conference track. The voting technique is thirty years old (ROVER 1997, the
ISRI/UNLV toolkit, Lund and Ringger, Handley 1998) and abstention is older still (Chow 1957).
What is left is a systems report plus one measurement that nobody found a precedent for. The
paper says so in those words rather than dressing it up.

**arXiv is not currently open to this author.** The endorsement policy changed on 2026-01-21: an
institutional email address is no longer sufficient on its own. A new submitter needs either an
institutional address *and* prior authorship on an accepted paper in the same endorsement
domain, or a personal endorsement from an established author in it. Alternatives that have no
endorsement gate: Zenodo (DOI, immediate), JOSS (for the software, and four of six reviewers
named it), TechRxiv, SSRN, OSF Preprints, or an ICDAR / DAS workshop.

**The tool disclosure in the paper is not optional if it goes to arXiv.** Their content
moderation policy requires that significant use of text-to-text generative AI be reported
"consistent with subject standards for methodology", and states that authors take full
responsibility for all contents "irrespective of how the contents were generated". Section 7
carries that disclosure. Removing it would violate the policy of the one venue that has the
rule; it is written to be accurate and brief rather than apologetic.

## What the paper does not yet contain

These are the experiments reviewers asked for, in the order they would improve it most. They are
tracked in [`testing/TO-TEST.md`](../testing/TO-TEST.md).

1. ~~A risk-coverage curve rather than one operating point.~~ **Measured 2026-08-09** —
   `tests/test_riskcov.py` recomputes it from a shipped fixture; `testing/TESTED.md` round 4
   has the honest caveats. Not yet folded into the paper's text.
2. ~~A single-engine confidence baseline thresholded to the same coverage.~~ **Measured
   2026-08-09**, same place. The ensemble sits above the single-engine curve at all fourteen
   matched coverage points (point estimates; most per-point intervals overlap). Not yet in
   the paper's text.
3. A second corpus in a different genre.
4. A downstream experiment: does a model given the sidecar actually fabricate fewer citations
   than one given raw OCR? That is the motivating claim and it is untested.
5. A comparison against OCR-D's alignment and voting component, which is the obvious external
   baseline and is available.
