@AGENTS.md

## Claude Code specifics

- Run `python -m scanquorum doctor --json` and parse it. Do not decide from the prose output.
- Long OCR runs print progress with an ETA. A 41-page document takes minutes, not seconds; do
  not assume a run has hung because it is quiet between page counters.
- `samples/` holds five real government PDFs with their SHA-256 and source URLs in
  `samples/MANIFEST.json`. They are checked in deliberately so results are reproducible. Do
  not regenerate or "clean" them.
- Never commit anything from `out/`, `reviews/`, or any file matching `.brief-*`.
