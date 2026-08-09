# Install

**If you are an AI coding agent** (Claude Code, Codex, Cursor, or similar) and someone
pointed you at this repository: read [AGENTS.md](AGENTS.md) first. It is written for you and
it is shorter than this file. Then come back here for the platform-specific commands.

Everything below ends with the same check, and that check is the point:

```
python -m scanquorum doctor
```

`doctor` exits **0** when the tool can do what it claims, **1** when it will run but produce
weaker evidence than the engine count suggests, and **2** when it cannot run. Do not skip it.
It exists because a run with a missing engine produces a complete, confident, well-formed
file that looks exactly like a good one.

---

## What you are installing

Four voters read every page. Three come from Python packages; one is a native binary.

| voter | comes from | required? |
|---|---|---|
| the PDF's own text layer | `pymupdf` | yes |
| RapidOCR, multilingual recogniser | `rapidocr` + `onnxruntime` | yes |
| RapidOCR, English recogniser | same package, different weights | yes |
| Tesseract 5 | **a native binary, `pip` cannot install it** | strongly recommended |

**Why Tesseract is not optional in practice.** The two RapidOCR voters share one text
detector: on a measured page set, 2,921 of 3,006 boxes were identical. They are closer to one
opinion than two. Tesseract draws its own boxes, so it is the only voter that can disagree
about *where* a word is, not merely about what it says. Without it you have **one**
independent OCR opinion and a quorum that mostly agrees with itself.

---

## 1. Python

Python **3.9 or newer**. Measured on **3.14.6**.

```bash
python --version
```

## 2. Python packages

```bash
python -m pip install -r requirements.txt
```

The versions are pinned. [requirements.txt](requirements.txt) explains why: this repository
publishes accuracy numbers, and RapidOCR picks its model weights by enum, so an upstream
patch release can move the models under a published figure without changing any code here.

**First run downloads model weights.** RapidOCR fetches its ONNX models on first use, so the
first page is slow and needs a network connection. A machine that installed the package
offline will import it successfully and then read nothing. `doctor` catches exactly this: it
runs each engine on a generated page and checks it reads back the text that is on it.

## 3. Tesseract

### Windows

Installer or portable build from the UB Mannheim project:
<https://github.com/UB-Mannheim/tesseract/wiki>

Then either put it on `PATH`, or point at it directly:

```powershell
$env:TESSERACT_EXE = "C:\Program Files\Tesseract-OCR\tesseract.exe"
```

To make that permanent for your user:

```powershell
[Environment]::SetEnvironmentVariable("TESSERACT_EXE", "C:\Program Files\Tesseract-OCR\tesseract.exe", "User")
```

A portable unzip works fine; nothing here needs it installed system-wide.

### macOS

```bash
brew install tesseract
```

### Debian / Ubuntu

```bash
sudo apt install tesseract-ocr tesseract-ocr-eng
```

The `-eng` package is separate and is **not** pulled in automatically on every distribution.
The binary without language data reads nothing at all, which is why `doctor` checks the
language list and not just the binary.

### Fedora / RHEL

```bash
sudo dnf install tesseract tesseract-langpack-eng
```

## 4. Verify

```bash
python -m scanquorum doctor
```

Expected on a complete install:

```
READY. 3 OCR engine(s) live, 2 independent opinion(s), plus the PDF's own text
layer as a further voter.
```

For a machine-readable answer, which is what an agent should parse:

```bash
python -m scanquorum doctor --json
```

## 5. Run the tests

No network, no API key, no OCR engine needed. These are pure replay:

```bash
python tests/test_vote_parity.py
python tests/test_safety.py
python tests/test_goldset.py
python tests/test_riskcov.py
python tests/test_doctor.py
```

`test_goldset.py` recomputes the published accuracy table from the shipped 60-crop gold set,
and `test_riskcov.py` recomputes the full risk-coverage curve and the single-engine
confidence baseline from a shipped fixture of cross-tabulations.

`test_vote_parity.py` replays 11,780 real decisions recorded from the implementation the
published numbers were measured with, and requires this code to reproduce every one that the
original decided deterministically. That is what ties the published figures to the published
code. See [README.md](README.md) for what the other 165 are and why they are allowed to
differ.

## 6. Run it on a real document

```bash
python -m scanquorum build samples/02-matter-of-gaglioti-14-IN-Dec-677.pdf --out-dir out
```

You get three files:

- `NAME.md` with a YAML provenance header addressed to whatever reads it next
- `NAME.unconfirmed.json`, every word that did not survive the quorum, with page and coordinates
- `NAME.evidence.json`, what every engine read for every word and which rule decided it

---

## Optional: the vision-model verifier

`scanquorum verify-ai` asks a vision model about the words the engines could not agree on. It
is optional, it needs an OpenRouter key, and it is the only part of this project that sends
anything anywhere.

```bash
export OPENROUTER_API_KEY=...        # never printed, never written to any output file
python -m scanquorum verify-ai --pending pending.json --model qwen/qwen3.8-vl-max
```

The model may only **choose among readings the engines already produced, or abstain**. It
cannot transcribe. That is enforced by a parser that discards anything which is not an index,
not by an instruction in a prompt. Read the header of
[scanquorum/verify_ai.py](scanquorum/verify_ai.py) before using it, in particular the part
about negative controls: on this project's own queue one model abstained on 95 % of controls
and another on 46 %, same task and same prompt, so the safety property belongs to the model
and has to be re-measured for each one.

---

## Troubleshooting

**`doctor` says an engine "ran but read NOTHING".** The model weights are missing or only
partly downloaded. Delete the RapidOCR model cache and let it fetch again with a network
connection.

**`doctor` says "tesseract binary NOT FOUND" but you installed it.** It is not on `PATH` for
*this* shell. Set `TESSERACT_EXE` to the full path of the executable. On Windows a new
`PATH` entry does not reach an already-open terminal.

**A run reports fewer engines than you installed.** That is the intended behaviour and the
run says so in the console and in `engines_unavailable` in the sidecar header. Fix the engine
and run again; do not use output produced with a degraded quorum and then quote its numbers.

**Everything installs but the numbers differ from the README.** Check `doctor` first, then
check that you have all four voters. Three engines instead of four moved one sample document
from 856 exactly-agreed words to 848, and moved unconfirmed words from 28 to 36.
