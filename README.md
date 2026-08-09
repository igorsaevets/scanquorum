# ScanQuorum

**Your scanned PDF contains invisible text. Your AI reads that, not the paper.**

Every scanned document you own — a contract, a filed decision, a bank statement, a deed —
carries a hidden layer of text that some OCR program guessed at, sometimes decades ago. You
never see it. Your search tool reads it. Your AI quotes it. Nobody ever checked whether it
matches the page.

**ScanQuorum reads the same page with several independent OCR engines and accepts a word only
when they agree.** Where they disagree it does not pick a winner quietly — it tells you which
words to look at, and shows you the picture.

No language model is allowed anywhere near the transcription. That is the point, and it is
enforced in code rather than promised in a prompt.

---

## Why this exists

A page of a 1974 immigration decision has this in its text layer:

```
Decided by Regional Commissioner May 1, .1974
```

That stray full stop was put there by an OCR program in the year 2000 and has been sitting in
the file ever since. It is harmless. Four lines away, in the same class of document, the
citation `12-855` had been recorded as `12369`.

That one is not harmless. It is a pointer to a different decision — and it looks exactly as
authoritative as the correct one, because a text layer carries no confidence, no provenance
and no warning. It is just text.

Now put a modern AI in front of that file. Ask it to quote the decision. It will quote it
perfectly — perfectly reproducing the wrong citation, and adding a fluent explanation of what
that decision held. Every hallucination check you run will pass, because the model did not
hallucinate. It read what was in the file.

> **The document was corrupted twenty-five years before the AI ever saw it.**

That is the failure this tool exists to catch, and it is invisible to every tool that checks
whether an AI made something up.

---

## What it actually does

**1. Reads the page several times, independently.** Four engines by default: the text layer
already in your PDF, two neural OCR models, and a classical one. They fail differently, which
is the entire reason to run more than one.

**2. Accepts a word only on a quorum.** A word is marked as confirmed when at least two
independent engines read it **identically**. On a 41-page government index that is **86.55 %
of 29,853 words**.

**3. Says exactly what happened to the other 13.45 %,** because a tool that refuses to guess
has to account for every word it did not vote on. It is not one bucket, it is three, and they
are not the same strength of evidence:

| what happened | words | share |
|---|---:|---:|
| read identically by two or more independent engines | 25,838 | 86.55 % |
| same digits, different punctuation (`12-869` against `12 869`) | 3,211 | 10.76 % |
| chosen by dictionary or pattern, **no second engine agreed** | 111 | 0.37 % |
| not confirmed at all: disputed, or seen by only one engine | 693 | 2.32 % |

Those four sum to 29,853, and `build.py` asserts it on every run rather than trusting it. The
last row is written to a side file with page and coordinates for each word.

> An earlier version of this README reported one number, `accepted_by_quorum: 97.68 %`, that
> folded the first three rows together. That counted a dictionary lookup as though it were a
> second engine agreeing, and overstated the only claim this project makes by eleven points.
> It was found by an outside reviewer. See [CHANGELOG.md](CHANGELOG.md).

**4. Never invents a character.** Every rule in the decision engine returns a candidate that
some engine actually proposed, or nothing. There is no code path that composes text. This is
the property that makes the output safe to paste into a filing, and it is verified by a test
you can run yourself.

**5. Writes a Markdown file next to the PDF.** Because your search tool cannot read a PDF and
never told you, and because an AI given a `.md` file with a provenance header behaves very
differently from one handed a PDF.

---

## Measured

On the EOIR Cumulative Index (41 pages, U.S. Department of Justice), reference standard =
the page rendered at 900 dpi and read by a human:

| | existing text layer | ScanQuorum |
|---|---:|---:|
| words | 29,829 | 29,845 |
| citations of the form `12-855` found | 2,583 | **3,182** |
| distinct citations found | 1,629 | **1,825** |

**Nearly 200 citations that were in the document could not be found in its own text layer.**
Not misspelled — unfindable. Every search for them returned nothing, and returned it
confidently.

### Every voter against the pixels, on the same crops

Sixty crops were labelled by a human from the page rendered at 900 dpi. Four of them turned
out to have an unusable frame (see below), leaving **56** scored. This table is produced by
`python tests/test_goldset.py`, from a fixture that ships in this repository, so you can
recompute every cell:

| voter | agrees with the page | 95 % interval |
|---|---:|---|
| the PDF's own text layer | 46.4 % | [34.0, 59.3] |
| `rapidocr_multi` | 78.6 % | [66.2, 87.3] |
| `rapidocr_en` | 60.4 % | [46.9, 72.4] |
| **the ensemble** | **94.6 %** | **[85.4, 98.2]** |

> **These are not document accuracy and must not be quoted as such.** The sample is
> *stratified*: contested decisions are deliberately over-represented, because in a document
> where 96 % of tokens are unanimous a random sample spends nearly all its labelling effort
> confirming easy words. The table says the ensemble is right on **hard** cases far more often
> than any single voter, which is what it is for. It does not say the document is 94.6 %
> correct.

Extrapolated to the whole document with a Horvitz–Thompson estimator, the figure is **98.65 %
with three engines and 99.15 % with four**. Read the two warnings below before using either.

> 🔴 **Read that as an UPPER BOUND, not as the accuracy.** The reference standard was
> built by rendering each token's own box and reading it, so when the box itself is
> wrong the standard is wrong in exactly the same way. Truncation — the largest known
> residual error class, and 7 of 7 observed mistakes — is invisible to it by
> construction. Page-level accuracy is necessarily lower and has not been measured.
>
> This is not hypothetical: **4 of the 60 labelled crops are exactly this failure.** The word
> box inherited from the PDF cut a glyph or framed typographic debris, every engine read
> inside the same wrong box, and all of them agreed. `tests/test_goldset.py` prints those four
> and excludes them. Unanimity there is not evidence, it *is* the error.

> 🔴 **The whole measurement is one document, in English legal print, from 2002.** Nothing
> here establishes that any of it transfers to another genre, another language, or a worse
> scan. See `testing/TO-TEST.md`, gap G1.

> 🔴 **And that improvement is not statistically significant.** Exact McNemar on the 4
> discordant pairs gives **p = 0.125**. Four engines beat three on this document, by a margin
> this sample cannot distinguish from luck. It is reported because it was measured, not
> because it is proven.

### The curve, not one point

Every reviewer of the accompanying paper asked for the same two measurements, so both are now
in the repository and recomputable by a stranger: vary the acceptance rule and plot
accepted-token accuracy against coverage, and threshold the best single engine on its own
confidence to the same coverage. `python tests/test_riskcov.py` recomputes every point from a
shipped fixture of cross-tabulations; no engine, no network.

Three cells of that table earn their space here. Accepting only full unanimity keeps 77.3 %
of the document with zero errors observed in its gold crops — which is 0 in 7, a Wilson floor
of 64.6 %, and must not be read as "100 %". The default cascade reaches 98.9 % coverage at an
estimated 99.3 % accepted-token accuracy. And the best single engine, thresholded on its own
line confidence, stays near 96–98 % at *every* coverage — its confidence barely sorts its own
errors (95.9 % accurate at 99 % coverage, 97.4 % at 14 %), so at every matched coverage point
the ensemble sits above it. Point estimates from 56 crops; most per-point intervals overlap;
`testing/TESTED.md` round 4 states exactly what is and is not significant here.

Everything above is reproducible from this repository: `samples/` contains all five documents,
`testing/` records what was tried and what was rejected.

---

## The .md sidecar, and why it has a header

This is real output, copied from a run of `samples/02-...pdf`, not an illustration:

```markdown
---
source_pdf: 02-matter-of-gaglioti-14-IN-Dec-677.pdf
source_sha256: 12ed016f49855cfce9561ae6214eb7baa395113c778b228c4ea75b3bd306b705
pages: 2
engines: ["pdf_layer", "rapidocr_en", "rapidocr_multi", "tesseract"]
engines_unavailable: []
frame_engine: rapidocr_en
words: 885
agreed_exactly: 856
agreed_on_digits_not_punctuation: 1
chosen_by_rule_no_second_engine: 0
unconfirmed: 28
agreed_exactly_from_correlated_voters_only: 4
unconfirmed_index: 02-matter-of-gaglioti-14-IN-Dec-677.unconfirmed.json
existing_layer_producer: Acrobat PDFWriter 4.0 for Windows NT
generated_by: scanquorum 0.1.0 (build.py v1.1)
warning: >
  Of the 885 words in this file, 856 were read IDENTICALLY by at least two
  independent OCR engines. A further 1 were read with the same digits but
  different punctuation ... Another 0 were chosen by dictionary or by pattern
  with NO second engine agreeing. The remaining 28 are not confirmed at all and
  are listed in ...unconfirmed.json with page and coordinates. ...
---
```

Three fields there are worth more than the rest.

`agreed_exactly_from_correlated_voters_only: 4` says that four of the confirmed words were
carried **only** by `rapidocr_multi` and `rapidocr_en`, which share a text detector. That is
one opinion agreeing with itself, and the header says so instead of counting it as two.

`engines_unavailable` is empty here. If an engine had failed to load, the run would still have
produced this file, complete and confident, with fewer voters. That field and the console
warning are the only places it would show.

The four count fields **sum to `words`**, and the code asserts it. `unconfirmed` is also
asserted to equal the number of entries in the file it names, so the sentence "listed in X" is
a fact rather than a caption.

Note what the header does **not** do: unconfirmed words are **not marked inline** in the body.
That is deliberate, because inline markers would break the byte-for-byte quotation this tool
exists to make possible, but it means the index is not optional.

That last field is addressed to the AI that will read the file. It is the cheapest useful
thing in this project: a model handed a document that states its own uncertainty stops
presenting guesses as quotations. The body below the header is clean text — greppable,
quotable byte-for-byte, with `<!-- page 12 -->` markers so any quotation can be traced back to
a page.

---

## Install

```bash
git clone https://github.com/igorsaevets/scanquorum
cd scanquorum
python -m pip install -r requirements.txt
python -m scanquorum doctor        # <- run this before anything else
python -m scanquorum build samples/02-matter-of-gaglioti-14-IN-Dec-677.pdf
```

`doctor` exits **0** when the tool can do what it claims, **1** when it will run but with
fewer independent opinions than it needs, and **2** when it cannot run. Every failing check
prints the exact command that fixes it. It exists because a run with a missing engine produces
a complete, well-formed file that looks exactly like a good one.

**Tesseract is a native binary and `pip` cannot install it.** Full platform instructions are
in [INSTALL.md](INSTALL.md). Without it you are left with one independent OCR opinion, because
the two RapidOCR voters share a detector.

**If you are handing this to an AI coding agent,** point it at [AGENTS.md](AGENTS.md). It is
written to be executed and it lists the five things that will otherwise mislead it.

No account and no API key: `build`, the vote engine and both test suites run entirely
offline. (One optional command, `verify-ai`, does send a crop to a model API — it refuses to
run without a key, and you never need it. See [SECURITY.md](SECURITY.md).) Tesseract is optional — it is the fourth
engine, and the tool says so when it runs with three.

**Check that the code here is the code that was measured** — one second, no dependencies:

```bash
python tests/test_vote_parity.py
```

It replays 11,780 real decisions recorded from the measured run and requires this repository to
reproduce every one of them.

---

## The five test documents, and where they came from

All five are U.S. federal government publications, in the public domain under 17 U.S.C. § 105.
**Each is byte-for-byte identical to the copy on the government's own server** — verified by
SHA-256, not asserted. The URLs and hashes are in [`samples/MANIFEST.json`](samples/MANIFEST.json).

They deliberately span three unrelated OCR vendors across 25 years:

| document | pp | who made its text layer |
|---|---:|---|
| Matter of Arai, 13 I&N Dec. 494 (BIA 1970) | 3 | Visioneer PaperPort LE → Acrobat PDFWriter 4.0, 2004 |
| Matter of Gaglioti, 14 I&N Dec. 677 (1974) | 2 | Visioneer PaperPort LE → Acrobat PDFWriter 4.0, 2000 |
| Matter of Vindman, 16 I&N Dec. 131 (1977) | 3 | Visioneer PaperPort LE → Acrobat PDFWriter 4.0, 2000 |
| INS v. Bagamasbad, 429 U.S. 24 (1976) | 4 | LuraTech PDF Compressor, 2009 |
| EOIR Cumulative Index, Vols. 1–15, A–E | 41 | Acrobat PDFWriter 4.0 for Windows NT |

The defects each one exhibits are catalogued in [`artifacts/ARTIFACTS.md`](artifacts/ARTIFACTS.md)
— what goes wrong, why, and which ones this tool does *not* catch.

---

## Who this is for

- **Legal departments and firms.** A quotation of authority is either the words in the source
  or it is not. This tells you which words in your source are guesses.
- **Finance, audit and compliance.** Scanned statements, invoices and contracts feeding a
  reconciliation or an LLM pipeline. A digit read wrong by a 2003 scanner does not announce
  itself.
- **Founders and small teams** building anything that reads documents with AI. The expensive
  failure is not the model inventing text; it is the model faithfully repeating text that was
  already wrong.
- **Anyone assembling a corpus for RAG.** Retrieval cannot find what OCR did not record. The
  200 missing citations above were a 12 % recall loss nobody would ever have noticed.

---

## What it does not do, said plainly

- **It does not tell you the truth about the page.** It tells you where independent engines
  agree. Engines can agree and be wrong together — most often when the word is inside a box
  that was cut off before any of them saw it. Measured on this corpus: of 24 disagreements
  checked by eye, the tool was right on 17 and wrong on 7, and **all 7 were truncations**. A
  crop-relative reference standard cannot see that class by construction, so the headline
  accuracy above does not cover it.
- **It is not a reader for handwriting, tables or forms.** It votes on words in running text.
- **It does not know what your document means.** It answers one question: which words on this
  page can be relied on.
- **Four engines are not four independent opinions.** Two of the default engines share a text
  detector — 2,921 of 3,006 boxes identical — so "four voices" is nearer three. This is why the
  fourth engine helped at all: it was added for independence, not for strength, and it is the
  weakest of the four.
- **A flag can mean the tool is wrong.** Before correcting a document because ScanQuorum
  flagged it, look at the page yourself. Every entry in the unconfirmed index carries the page
  number and the bounding box, so the place is one lookup away.

  > An earlier version of this README said the tool "will render each one as a cropped image
  > so a person can look at it in three seconds." **It does not.** No code path in `build`
  > renders a crop. The claim was written for a feature that exists only in the unpublished
  > lab tooling. It is listed in `testing/PLANNED.md` as P8; until it ships, the coordinates
  > are what you get.

---

## Prior art

**Almost nothing here is new, and the parts that are, are small.** An earlier version of this
section claimed novelty on the basis of not having found prior work, which is exactly the
reasoning this project rejects everywhere else. Six independent reviewers were then asked to
find the prior art. They found a great deal.

**Voting across recognisers is thirty years old.** ROVER (Fiscus, *IEEE ASRU* 1997) aligns
several recognisers into a word transition network and votes with confidence weighting. The
ISRI/UNLV toolkit (Rice, Kanai and Nartker, 1994 onward; Nartker, Rice and Lumos, *DRR XII*
2005) shipped `synctext` and `vote` — and `vote` already broke ties with heuristics, which is
the very place our own bug lived. Lund and Ringger (*JCDL* 2009) align multiple engines into a
lattice with an A\* heuristic; Lund, Walker and Ringger (*ICDAR* 2011) add discriminative
selection and report a 24.6 % relative improvement over the best single engine. Handley's
survey (*IEEE SMC* 1998) had already laid out the taxonomy.

**Abstention is older still, and better formalised elsewhere.** Chow (1957, and *IEEE Trans.
Inf. Theory* 1970) is the reject option, with an optimal threshold derived from a cost model.
Modern selective prediction (El-Yaniv and Wiener, *JMLR* 2010; Geifman and El-Yaniv, *NeurIPS*
2017) reports a **risk-coverage curve**. As of round 4 we report that curve too
(`python tests/test_riskcov.py`); what we still lack is calibrated confidence.
Conformal prediction would give distribution-free coverage
guarantees for the set of readings we already produce; we do not currently make that claim.

**Voting inside one engine is a live alternative.** Calamari (Wick, Reul and Puppe, 2018) votes
across cross-fold-trained models of one architecture and reaches far lower character error
rates than anything here, on cleaner corpora. Our argument for *architecture* diversity rather
than model-instance diversity is the 2,921-of-3,006 measurement below, not a general claim.

**Ensemble OCR as working software also exists**: OCR-D's `ocrd-cor-asv-ann-align` does n-ary
alignment with majority or confidence voting, and is the most direct baseline we should be
compared against. We have not yet run that comparison.

So what is actually left:

1. **Refusal as the primary output.** Prior systems align and vote in order to emit one best
   string. Here the disagreements are the deliverable, enumerated with page and coordinates,
   and the accepted text carries a header saying how much of it is unverified. Reviewers split
   on whether this is a contribution or a packaging decision; two called it real, one said a
   competent engineer could add it to an existing voter in an evening. Both are fair.
2. **A determinism audit of the tie-breaks.** We replayed 11,780 recorded decisions under every
   permutation of engine ordering and found **1.40 % order-dependent, 29 of them changing a
   digit**. Six reviewers looked for prior work doing this to an OCR ensemble; three documented
   their search terms and all six came back empty. That is evidence of absence of *found*
   work, not proof of absence. The narrow, defensible claim: the literature has always known
   ties need breaking, and we found no work that measures what it costs to leave the tie-break
   order-dependent.

If you know of prior work we have misread or missed, please open an issue. Using an existing
tool would be less work than maintaining this one.

---

## Found a bug? Want a feature?

| what | where |
|---|---|
| a word was decided wrongly | [open an issue](../../issues) — include the crop, the candidates and the verdict you expected |
| an idea, a question, a document class you want supported | [discussions](../../discussions) |
| a security problem | [private advisory](../../security/advisories/new) — **not** a public issue |
| collaboration or consulting | [LinkedIn](https://www.linkedin.com/in/igorsaevets/) · [GitHub](https://github.com/igorsaevets) |

**There is deliberately no contact email.** The address on this repository's commits is
GitHub's no-reply relay: it attributes commits correctly and has no mail exchanger at all, so
mail sent to it is discarded without a bounce. A channel that silently swallows a bug report is
worse than an absent one.

Related tool, same author, the step after this one:
[**krokai-law**](https://github.com/igorsaevets/krokai-law) checks that quotations in your
documents really appear in your sources. ScanQuorum is what makes those sources trustworthy in
the first place — `krokai` verifies against the copy on your disk, and this is how you find out
whether that copy says what the paper says.

Maintained by **Igor Saevets** ([@igorsaevets](https://github.com/igorsaevets)), Los Angeles.
Licence: MIT. Nothing here contacts a vendor, and no test needs a key.
