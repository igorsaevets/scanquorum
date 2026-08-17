# Contributing to ScanQuorum

Thanks for your interest. ScanQuorum detects invisible or mismatched text layers in scanned PDFs before an AI quotes them as fact. Small tool, deliberate scope.

## Ground rules

- Open an issue first for new engines or new output formats.
- One change per PR, with a test under `tests/`.
- AI-assisted contributions are welcome and must be declared in the PR template.

## Dev setup

Python 3.11 or newer. Follow [INSTALL.md](./INSTALL.md) for system prerequisites, then:

```bash
pip install -e .
pytest
```

`tests/fixtures/` holds small synthetic samples; `tests/make_fixture.py` regenerates them. Please do not add real-world scanned documents as fixtures: they tend to contain personal data.

## What makes a PR easy to accept

1. A failing test or fixture first.
2. The smallest change that fixes it.
3. `pytest` green.

## Security

Never report vulnerabilities in public issues. See [SECURITY.md](./SECURITY.md).
