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

**2. Accepts a word only on a quorum.** A word enters the output when at least two independent
engines read it the same way. On a 41-page government index: **86.55 % of 29,853 words** were
accepted by quorum.

**3. Refuses to guess the rest.** **1.18 % — 353 words** — could not be reconciled. Those are
not silently filled in with a best guess. They are listed, with page and coordinates, and the
tool will render each one as a cropped image so a person can look at it in three seconds.

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

Accuracy on a stratified sample of 56 hand-checked crops, extrapolated to the document with a
Horvitz–Thompson estimator: **98.65 % with three engines, 99.15 % with four.**

> 🔴 **And that improvement is not statistically significant.** Exact McNemar on the 4
> discordant pairs gives **p = 0.125**. Four engines beat three on this document, by a margin
> this sample cannot distinguish from luck. It is reported because it was measured, not
> because it is proven.

Everything above is reproducible from this repository: `samples/` contains all five documents,
`testing/` records what was tried and what was rejected.

---

## The .md sidecar, and why it has a header

```markdown
---
source_pdf: 05-eoir-cumulative-index-vol1-15-AE.pdf
source_sha256: 8f2a...
engines: [pdf-text-layer, rapidocr-v6-multi, rapidocr-v6-en, tesseract-5.5-lstm]
words: 29853
accepted_by_quorum: 25838
unconfirmed: 353
unconfirmed_index: 05-eoir-cumulative-index.unconfirmed.json
generated_by: scanquorum 0.1.0
warning: >
  Every word in this file was read identically by at least two independent OCR
  engines, EXCEPT the 353 listed in the unconfirmed index. No language model
  wrote or corrected any character here. Where a word is unconfirmed, say so
  rather than quoting it.
---
```

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
pip install pymupdf rapidocr-onnxruntime pillow
python -m scanquorum build samples/02-matter-of-gaglioti-14-IN-Dec-677.pdf
```

No account, no API key, nothing leaves your machine. Tesseract is optional — it is the fourth
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
| EOIR Cumulative Index, Vols. 1–15, A–E | 41 | Adobe Acrobat 25 Paper Capture |

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
  flagged it, look at the crop. That is why the crop is produced.

---

## Prior art

Multi-engine OCR voting is not new. The classical method is
[ROVER](https://ieeexplore.ieee.org/document/659110) (Fiscus, 1997), developed for speech
recognition and applied to OCR many times since; [ocropus](https://github.com/ocropus),
[OCR-D](https://ocr-d.de/) and several academic ensembles do related work. Commercial document
platforms run multiple engines internally.

What we did not find was the combination this repository implements: **voting whose refusals
are a first-class output, with the unresolved places rendered as images for a human, and a hard
architectural bar on any language model touching the transcription.** If you know of one,
please open an issue — using it would be less work than maintaining this.

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
