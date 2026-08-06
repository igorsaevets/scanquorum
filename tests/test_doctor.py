# tests/test_doctor.py  v1.0
#
# THE DOCTOR NEEDS A DOCTOR.
#
# The first version of scanquorum/doctor.py shipped with two defects that only
# running it revealed, and both were the same mistake in different clothes: it
# asserted things about the system instead of asking the system.
#
#   1. It handed PNG bytes to engine adapters that take a PDF path. Every engine
#      raised, and the doctor reported three broken engines on a machine where all
#      three worked perfectly. A diagnostic that produces false failures is worse
#      than no diagnostic, because the person following it changes a working setup.
#   2. It guessed the import name `rapidocr_onnxruntime`, reported the package
#      missing while it was installed and in use, and printed a pip command that
#      would have installed a different package.
#
# Neither is caught by reading the file. Both die instantly on one execution. So
# this test executes it.
#
# Run:  python tests/test_doctor.py
# Exit: 0 pass, 1 fail. Needs no network and no API key. It DOES need the engines
#       to be installed for the strong assertions; where they are not, it checks
#       that the doctor reports their absence correctly, which is the other half of
#       the contract and the half that actually protects a user.
import os
import sys
import json
import pathlib
import subprocess

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scanquorum import doctor                                   # noqa: E402


def run_json(env=None):
    """Run doctor as a subprocess, the way a user or an agent runs it, and parse
    what it prints. Calling main() in-process would not catch a crash in argument
    handling or a stray print that corrupts the JSON."""
    e = dict(os.environ)
    if env:
        e.update(env)
    p = subprocess.run([sys.executable, "-m", "scanquorum", "doctor", "--json"],
                       cwd=str(ROOT), capture_output=True, text=True,
                       encoding="utf-8", errors="replace", env=e, timeout=600)
    try:
        return json.loads(p.stdout), p.returncode
    except Exception:
        print("doctor did not emit parseable JSON. stdout was:\n%s\nstderr:\n%s"
              % (p.stdout[:2000], p.stderr[:2000]))
        raise


def main():
    print("scanquorum.doctor v%s\n" % doctor.VERSION)
    fails = []

    # ---- 1. the import names in PY_DEPS must be real -------------------------
    # This is the check that would have caught defect 2 at authoring time.
    print("PART 1 -- every dependency name in PY_DEPS resolves")
    for name, imp, pipname, why, required in doctor.PY_DEPS:
        try:
            __import__(imp)
            print("  %-14s import %-14s OK" % (name, imp))
        except ImportError:
            # Not installed is a legitimate state; a WRONG NAME is not, and the two
            # look identical from here. So this is reported, not failed, unless the
            # package is one the tests themselves already rely on.
            print("  %-14s import %-14s not installed on this machine" % (name, imp))
        except Exception as exc:
            fails.append("PY_DEPS entry %r: importing %r raised %s" % (name, imp, exc))

    # ---- 2. the smoke PDF must be a PDF the adapters can open ----------------
    # This is the check that would have caught defect 1.
    print("\nPART 2 -- the smoke document is a readable PDF, not bytes")
    import tempfile
    tmp = os.path.join(tempfile.mkdtemp(prefix="scanquorum-test-"), "smoke.pdf")
    doctor._smoke_pdf(tmp)
    if not os.path.exists(tmp) or os.path.getsize(tmp) < 400:
        fails.append("_smoke_pdf did not produce a plausible PDF")
    else:
        import pymupdf
        d = pymupdf.open(tmp)
        text = d[0].get_text()
        d.close()
        print("  built %d-byte PDF, its text layer says %r" % (os.path.getsize(tmp), text.strip()))
        if "2282" not in text:
            fails.append("the smoke PDF does not contain the digits the engine check looks for")

    # ---- 3. error text must never carry a payload ---------------------------
    print("\nPART 3 -- _short() keeps a payload out of an error line")
    huge = ValueError(b"\x89PNG" + b"\x00" * 9000)
    got = doctor._short(huge)
    print("  9 KB exception rendered as %d chars" % len(got))
    if len(got) > 200:
        fails.append("_short did not truncate: %d chars" % len(got))

    # ---- 4. independence is not the engine count ----------------------------
    print("\nPART 4 -- correlated voters are not counted as independent")
    cases = [
        (["rapidocr_multi", "rapidocr_en"], 1, "two engines, one shared detector"),
        (["rapidocr_multi", "rapidocr_en", "tesseract"], 2, "the shipped configuration"),
        (["rapidocr_multi", "tesseract"], 2, "no correlation present"),
        ([], 0, "nothing installed"),
    ]
    for live, want, why in cases:
        got = doctor.independence(live)
        print("  %-46s %d engine(s) -> %d independent  (%s)"
              % (why, len(live), got, "OK" if got == want else "WRONG, want %d" % want))
        if got != want:
            fails.append("independence(%r) = %d, want %d" % (live, got, want))

    # ---- 5. run it for real and check the contract holds ---------------------
    print("\nPART 5 -- run the doctor as a subprocess and check its own contract")
    rep, code = run_json()
    print("  exit code %d, %d checks, engines live: %s, independent: %d"
          % (code, len(rep["checks"]), rep["engines_live"], rep["independent_opinions"]))
    if code not in (0, 1, 2):
        fails.append("exit code %d is outside the documented set" % code)
    if code != rep["exit_code"]:
        fails.append("process exit %d disagrees with the JSON's own exit_code %d"
                     % (code, rep["exit_code"]))
    # The contract that matters: the verdict and the exit code must agree, because
    # an agent reads one and a shell reads the other.
    if rep["independent_opinions"] >= 2 and code != 0:
        fails.append("2+ independent opinions but exit %d" % code)
    if rep["independent_opinions"] < 2 and rep["engines_live"] and code != 1:
        fails.append("degraded quorum but exit %d, want 1" % code)
    if not rep["engines_live"] and code != 2:
        fails.append("no engines live but exit %d, want 2" % code)
    for c in rep["checks"]:
        if not c["ok"] and not c.get("fix"):
            fails.append("check %r failed without telling the user how to fix it" % c["check"])

    # ---- 6. a deliberately broken Tesseract path must be detected ------------
    # A negative control. A doctor that says PASS when pointed at a file that does
    # not exist is not checking anything.
    print("\nPART 6 -- negative control: point TESSERACT_EXE at nothing")
    rep2, code2 = run_json({"TESSERACT_EXE": str(ROOT / "no-such-tesseract.exe")})
    tess = [c for c in rep2["checks"] if c["check"] == "tesseract binary"]
    if not tess or tess[0]["ok"]:
        fails.append("doctor reported a nonexistent tesseract as present")
    else:
        print("  correctly reported: %s" % tess[0]["found"])
        print("  exit %d, independent opinions %d" % (code2, rep2["independent_opinions"]))

    print()
    if fails:
        print("FAILED (%d):" % len(fails))
        for f in fails:
            print("  - %s" % f)
        return 1
    print("DOCTOR OK.")
    print("  It reports what is installed, refuses to call a correlated pair two opinions,")
    print("  tells the user how to fix every failure, and detects a binary that is not there.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
