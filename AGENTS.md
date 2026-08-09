# For the AI agent setting this up

Someone gave you this repository and asked you to install and run it. This file is the whole
job. It is written to be executed, not interpreted.

## Do this

```bash
# 1. Python 3.9+ (measured on 3.14.6)
python --version

# 2. Pinned dependencies
python -m pip install -r requirements.txt

# 3. Tesseract. pip CANNOT install this. Pick your platform:
#    Windows : https://github.com/UB-Mannheim/tesseract/wiki   then set TESSERACT_EXE
#    macOS   : brew install tesseract
#    Debian  : sudo apt install tesseract-ocr tesseract-ocr-eng
#    Fedora  : sudo dnf install tesseract tesseract-langpack-eng

# 4. THE CHECK. Parse this, do not eyeball it.
python -m scanquorum doctor --json
```

`doctor` exit codes: **0** ready, **1** runs but the quorum is degraded, **2** cannot run.
Every failing check carries a `fix` field with the exact command. Apply them and re-run.

**Do not report success on exit 1.** Exit 1 means the tool will produce output that looks
identical to a good result and is weaker evidence than it appears. Tell the human that
Tesseract is missing and what it costs them.

Then confirm the tests pass. They need no network, no key and no OCR engine:

```bash
python tests/test_vote_parity.py && python tests/test_safety.py && python tests/test_goldset.py && python tests/test_riskcov.py && python tests/test_doctor.py
```

## Five things that will mislead you if you do not know them

1. **The engine count is not the number of opinions.** `rapidocr_multi` and `rapidocr_en`
   share one PP-OCRv6 text detector; on a measured page set 2,921 of 3,006 of their boxes
   were identical. Three engines running can mean **one** independent OCR opinion. `doctor`
   reports `independent_opinions` separately, and that is the number that matters.

2. **A missing engine does not fail the run.** It degrades it. The console says so and the
   sidecar header lists `engines_unavailable`, but the `.md` output is complete and
   well-formed either way. This is the single easiest way to produce a result that looks fine
   and is not.

3. **RapidOCR downloads its weights on first use.** Installing offline succeeds and then
   reads nothing. `doctor` runs each engine on a generated page and checks it reads back the
   text that is on it, precisely so that this does not pass.

4. **The header fields are not a summary, they are a partition.** `agreed_exactly`,
   `agreed_on_digits_not_punctuation`, `chosen_by_rule_no_second_engine` and `unconfirmed`
   sum to `words`, and an assertion in the code enforces it. Only the first is a claim that
   two independent engines read the same thing. An earlier version folded all four into one
   field called `accepted_by_quorum` and overstated by eleven points; see CHANGELOG.md.

5. **`verify-ai` is the only part that sends anything anywhere.** `build` is entirely local.
   If you are setting this up for someone who cares about that distinction, say which command
   you ran.

## If you are asked to change the voting code

`scanquorum/vote.py` is covered by a replay fixture: `tests/test_vote_parity.py` re-runs
11,780 real decisions recorded from the implementation the published numbers came from, and
also permutes the engine ordering on every one of them to prove the result does not depend on
it. **Run it after any change to `vote.py`.** A change that alters a decision is not
necessarily wrong, but it must be deliberate and it must be recorded in `testing/TESTED.md`.

The fixture itself cannot be regenerated outside the original machine; `tests/make_fixture.py`
says so at the top. Treat `tests/fixtures/decisions.jsonl` as data, not as something to
rebuild.

## What this project will not do

It will not correct text. It will not let a language model transcribe anything. Where the
engines disagree it refuses and writes the disagreement to a side file. If a request amounts
to "just pick the most likely reading", the answer is that the tool exists specifically to
not do that, and `artifacts/ARTIFACTS.md` lists the error classes that survive anyway.
