# Contributing to ScanQuorum

Thanks for your interest. ScanQuorum detects invisible or mismatched text layers in scanned PDFs before an AI quotes them as fact. Small tool, deliberate scope.

## Ground rules

- Open an issue first for new engines or new output formats.
- One change per PR, with a test under `tests/`.
- AI-assisted contributions are welcome and must be declared in the PR template.

## Dev setup

Python 3.9 or newer (CI measures 3.9, 3.12, 3.14). Follow [INSTALL.md](./INSTALL.md) for system
prerequisites (Tesseract binary, ONNX weights cache), then:

```bash
pip install -e .
python -m scanquorum doctor        # must exit 0 before you run anything else

# The test suite is not pytest. Every file is a plain sys.exit(0/1) script — run each:
python tests/test_vote_parity.py
python tests/test_safety.py
python tests/test_goldset.py
python tests/test_riskcov.py
python tests/test_doctor.py
```

`tests/fixtures/` holds small synthetic samples; `tests/make_fixture.py` is **runnable only on
the machine that has the original lab tree** (see the note at the top of the file). Do not add
real-world scanned documents as fixtures — they tend to contain personal data.

## What makes a PR easy to accept

1. A failing test or fixture first.
2. The smallest change that fixes it.
3. All five `tests/test_*.py` scripts exit 0.

## Security

Never report vulnerabilities in public issues. See [SECURITY.md](./SECURITY.md).
