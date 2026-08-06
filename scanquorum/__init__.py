"""ScanQuorum -- accept a word from a scanned page only when independent OCR
engines agree, and show you the ones they do not.

No language model is involved in transcription. See README.md.
"""
__version__ = "0.2.0"

# A Windows console defaults to a legacy code page (cp1251, cp866, cp1252...) and
# raises UnicodeEncodeError the first time anything prints a character outside it.
# Measured on the first end-to-end run: this tool died on its own "engine not
# available" warning, because that line carries a red-circle emoji -- so the crash
# destroyed the diagnostic it was trying to deliver, and the traceback pointed at
# the print rather than at the real problem. Reconfiguring here, once, covers every
# entry point.
#
# errors="replace" rather than "strict": a report that prints "?" is still a
# report; a report that raises is not. No glyph here is worth losing a run over.
import sys as _sys

for _s in (_sys.stdout, _sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
