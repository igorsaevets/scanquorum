# scanquorum/doctor.py  v1.0
#
# WHAT IS INSTALLED, WHAT IS MISSING, AND EXACTLY HOW TO FIX IT.
#
# This exists because of a measured failure, not as a courtesy. Running the
# pipeline on this machine with Tesseract present but not on PATH produced a
# complete, confident, well-formed result -- built from three engines instead of
# four, of which only ONE was an independent OCR opinion, because the two RapidOCR
# voters share a text detector. The output looked exactly like a good run. Nothing
# in the file said "the fourth voice was missing"; the numbers simply came out
# weaker and no one had a baseline to compare them against.
#
# A tool whose entire premise is "do not trust an unverified claim" cannot ship a
# setup step whose failure mode is silence. So:
#
#   - every dependency is probed by IMPORTING it and reading its version,
#   - every engine is probed by actually RUNNING it on a generated image,
#   - the exit code is nonzero when the quorum would be degraded,
#   - and every failure prints the exact command that fixes it, per platform.
#
# Run:  python -m scanquorum doctor
#       python -m scanquorum doctor --json     (for an agent to parse)
#
# Exit codes:  0 = full quorum available
#              1 = runs, but with fewer independent opinions than intended
#              2 = cannot run at all

import os
import sys
import json
import shutil
import platform
import subprocess

VERSION = "1.0"

MIN_PYTHON = (3, 9)

# name -> (import name, pip name, why it is needed, is it required)
PY_DEPS = [
    ("pymupdf", "pymupdf", "pymupdf", "reads the PDF, its text layer and page images", True),
    # 🔴 The import name is `rapidocr`, NOT `rapidocr_onnxruntime`. The first version
    # of this file guessed the latter, reported the package missing on a machine
    # where it was installed and working, and printed a pip command that would have
    # installed a different, older package. A doctor that misdiagnoses is worse than
    # no doctor, so every name here was checked against the adapter that imports it.
    ("rapidocr", "rapidocr", "rapidocr onnxruntime",
     "two of the four voters; without it only the PDF layer and Tesseract vote", True),
    ("onnxruntime", "onnxruntime", "onnxruntime", "runs the RapidOCR models", True),
    ("numpy", "numpy", "numpy", "box arithmetic and the image buffer handed to RapidOCR", True),
]

TESSERACT_URLS = {
    "Windows": "https://github.com/UB-Mannheim/tesseract/wiki  (installer, or a portable zip)",
    "Darwin": "brew install tesseract",
    "Linux": "sudo apt install tesseract-ocr   (Debian/Ubuntu)  |  sudo dnf install tesseract",
}


def _v(mod):
    for attr in ("__version__", "VERSION", "version"):
        got = getattr(mod, attr, None)
        if isinstance(got, str):
            return got
    return "unknown"


def check_python(rep):
    ok = sys.version_info[:2] >= MIN_PYTHON
    rep.append({
        "check": "python", "ok": ok, "found": platform.python_version(),
        "want": ">= %d.%d" % MIN_PYTHON,
        "fix": "" if ok else "Install Python %d.%d or newer and re-create the environment." % MIN_PYTHON,
    })
    return ok


def check_deps(rep):
    all_ok = True
    for name, imp, pipname, why, required in PY_DEPS:
        try:
            mod = __import__(imp)
            rep.append({"check": "python package: " + name, "ok": True,
                        "found": _v(mod), "want": "any", "note": why, "fix": ""})
        except Exception as exc:
            if required:
                all_ok = False
            rep.append({"check": "python package: " + name, "ok": not required,
                        "found": "NOT INSTALLED (%s)" % type(exc).__name__,
                        "want": "any", "note": why,
                        "fix": "%s -m pip install %s" % (sys.executable, pipname)})
    return all_ok


def check_tesseract(rep):
    """Tesseract is the ONLY voter that draws its own word boxes, so its absence
    does not merely remove a vote -- it removes the independence of the vote that
    remains. That is why this check reports a degraded quorum rather than a
    missing optional extra."""
    exe = os.environ.get("TESSERACT_EXE") or shutil.which("tesseract")
    if not exe or not os.path.exists(exe):
        rep.append({
            "check": "tesseract binary", "ok": False, "found": "NOT FOUND",
            "want": "tesseract 4 or 5 on PATH, or TESSERACT_EXE set",
            "note": "the only voter with its own layout analysis",
            "fix": ("Install it: %s\nThen either add it to PATH, or set the variable:\n"
                    "  Windows PowerShell:  $env:TESSERACT_EXE = 'C:\\path\\to\\tesseract.exe'\n"
                    "  bash:                export TESSERACT_EXE=/usr/bin/tesseract"
                    % TESSERACT_URLS.get(platform.system(), TESSERACT_URLS["Linux"])),
        })
        return False
    try:
        out = subprocess.run([exe, "--version"], capture_output=True, text=True, timeout=30)
        ver = (out.stdout or out.stderr).splitlines()[0].strip()
    except Exception as exc:
        rep.append({"check": "tesseract binary", "ok": False, "found": "found but would not run: %r" % exc,
                    "want": "runnable", "fix": "Check the file is not blocked by antivirus or quarantine."})
        return False
    # `--list-langs` prints a header line ("List of available languages in ...")
    # and then one language per line. Splitting the whole blob on whitespace and
    # dropping the first token, as this did at first, yields the header's own words
    # as language names.
    langs = []
    try:
        lo = subprocess.run([exe, "--list-langs"], capture_output=True, text=True, timeout=30)
        lines = [l.strip() for l in ((lo.stdout or "") + (lo.stderr or "")).splitlines()]
        langs = [l for l in lines if l and " " not in l and not l.endswith(":")]
    except Exception:
        pass
    has_eng = "eng" in langs
    rep.append({"check": "tesseract binary", "ok": True, "found": "%s  [%s]" % (ver, exe),
                "want": "4 or 5", "note": "languages: " + (" ".join(langs) or "could not list"),
                "fix": ""})
    if not has_eng:
        rep.append({"check": "tesseract language data: eng", "ok": False,
                    "found": "MISSING", "want": "eng.traineddata",
                    "fix": "Install the English language pack (apt: tesseract-ocr-eng). "
                           "The binary alone reads nothing."})
        return False
    return True


SMOKE_TEXT = "Interim Decision 2282"


def _smoke_pdf(path):
    """A one-page PDF whose text we know, because the adapters take a PDF PATH and
    not an image. The first version of this function handed them PNG bytes; every
    engine raised, and the doctor reported three broken engines on a machine where
    all three worked. It also printed the whole 6 KB PNG into the error line. Both
    are fixed below, and both are the reason this file gets exercised by
    tests/test_doctor.py rather than trusted."""
    import pymupdf
    doc = pymupdf.open()
    page = doc.new_page(width=430, height=110)
    page.insert_text((22, 62), SMOKE_TEXT, fontsize=20)
    doc.save(path)
    doc.close()


def _short(exc, n=180):
    """Never let a payload into an error line. The binary dump that appeared here
    once made the real message unreadable."""
    s = "%s: %s" % (type(exc).__name__, exc)
    s = " ".join(s.split())
    return s if len(s) <= n else s[:n] + " ...[truncated]"


def check_engines(rep):
    """Import each adapter and RUN it on a generated PDF. Importing proves the
    module loads; only running proves the model weights are present and the binary
    answers. RapidOCR downloads its weights on first use, so a machine with no
    network can import the package and still fail on the first real page.

    The check is not "did it return something" but "did it return the RIGHT thing":
    an engine that reads a blank page returns a clean empty result, which is
    indistinguishable from success unless you know what the page said."""
    import tempfile
    tmp = os.path.join(tempfile.mkdtemp(prefix="scanquorum-doctor-"), "smoke.pdf")
    try:
        _smoke_pdf(tmp)
    except Exception as exc:
        rep.append({"check": "engine smoke test", "ok": False,
                    "found": "could not build the test PDF: " + _short(exc),
                    "want": "pymupdf works", "fix": "fix the pymupdf row above first"})
        return 0, []

    live = []
    for name in ("rapidocr_multi", "rapidocr_en", "tesseract"):
        try:
            mod = __import__("scanquorum.engines." + name, fromlist=["run", "GRANULARITY"])
        except Exception as exc:
            rep.append({"check": "engine: " + name, "ok": False,
                        "found": "adapter did not load: " + _short(exc),
                        "want": "loads and runs", "fix": "see the rows above"})
            continue
        try:
            out = mod.run(tmp)
            boxes = (out or {}).get("0", {}).get("boxes", [])
            text = " ".join(b.get("t", "") for b in boxes)
            # "2282" is the part that matters: a digit sequence is what this whole
            # project is about getting right, and it is what a half-loaded model
            # gets wrong first.
            read_it = "2282" in text.replace(" ", "")
            rep.append({
                "check": "engine: " + name, "ok": read_it,
                "found": ("read %r" % text[:60]) if boxes else "ran but read NOTHING",
                "want": "text containing 2282",
                "note": "granularity: %s" % getattr(mod, "GRANULARITY", "?"),
                "fix": "" if read_it else
                       ("The engine ran but did not read the test page correctly. For RapidOCR "
                        "this usually means the model weights are missing or only partly "
                        "downloaded: delete the model cache and let it fetch again with a "
                        "network connection."),
            })
            if read_it:
                live.append(name)
        except Exception as exc:
            rep.append({"check": "engine: " + name, "ok": False,
                        "found": "raised " + _short(exc),
                        "want": "runs", "fix": "see the rows above"})
    return len(live), live


def independence(live):
    """How many genuinely independent OCR opinions the live engines represent.
    This is the number that decides whether a vote means anything, and it is NOT
    the engine count: rapidocr_multi and rapidocr_en share a PP-OCRv6 detector."""
    correlated = [{"rapidocr_multi", "rapidocr_en"}]
    n = len(live)
    for group in correlated:
        overlap = group & set(live)
        if len(overlap) > 1:
            n -= len(overlap) - 1
    return n


def main(argv=None):
    as_json = "--json" in (argv or sys.argv[1:])
    rep = []
    hard_ok = check_python(rep)
    hard_ok = check_deps(rep) and hard_ok
    check_tesseract(rep)
    n_live, live = check_engines(rep)
    indep = independence(live)

    verdict_code = 0
    if not hard_ok or n_live == 0:
        verdict_code = 2
        verdict = ("CANNOT RUN. Fix the rows marked FAIL above, in order; each one prints "
                   "the exact command.")
    elif indep < 2:
        verdict_code = 1
        verdict = ("RUNS, BUT THE QUORUM IS DEGRADED. %d engine(s) live, but only %d "
                   "INDEPENDENT OCR opinion(s). Two engines that share a text detector are "
                   "nearer one voter than two, so agreement between them is weaker evidence "
                   "than the count suggests. Install Tesseract for a voter that draws its own "
                   "boxes." % (n_live, indep))
    else:
        verdict = ("READY. %d OCR engine(s) live, %d independent opinion(s), plus the PDF's "
                   "own text layer as a further voter." % (n_live, indep))

    if as_json:
        print(json.dumps({"version": VERSION, "checks": rep, "engines_live": live,
                          "independent_opinions": indep, "exit_code": verdict_code,
                          "verdict": verdict}, ensure_ascii=False, indent=1))
        return verdict_code

    print("scanquorum doctor v%s   python %s on %s\n"
          % (VERSION, platform.python_version(), platform.platform()))
    for r in rep:
        print("  [%s] %-32s %s" % ("PASS" if r["ok"] else "FAIL", r["check"], r["found"]))
        if r.get("note"):
            print("         %s" % r["note"])
        if not r["ok"] and r.get("fix"):
            for line in r["fix"].splitlines():
                print("         -> %s" % line)
    print("\n" + "=" * 74)
    print(verdict)
    print("=" * 74)
    return verdict_code


if __name__ == "__main__":
    sys.exit(main())
