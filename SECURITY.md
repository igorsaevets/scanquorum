# Security

## Reporting a vulnerability

Use GitHub's **[private advisory form](../../security/advisories/new)**. Please do not open a
public issue for a security problem.

That link is checked, not assumed. A sibling project once told researchers to use this button
while private vulnerability reporting was disabled on the repository, so the button was not
there and anyone following the published instruction found nothing. A documented channel is
not a live channel until something outside the document says so.

## What this project touches

- **It reads PDFs you point it at.** It does not upload them anywhere.
- **No network access at all** in the default path: `build`, the vote engine and both test
  suites run entirely offline and need no key.
- **One optional command sends data off the machine.** `verify-ai` transmits a cropped image
  and, if you pass `--pages`, surrounding page text to a model API. It will not run without
  `OPENROUTER_API_KEY` in the environment. Treat that command as publication: whatever is in
  those pages reaches a third-party vendor.
- **The API key is never printed, logged, or written to any output file.** Only its presence
  and length are ever reported.

## If your documents are confidential

Run `build` and the tests; do not run `verify-ai`. The tool is fully functional without it —
`verify-ai` only offers to answer the questions a person would otherwise answer by looking at
a crop, and a person looking at a crop sends nothing anywhere.
