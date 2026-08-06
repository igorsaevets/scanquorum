# tests/test_safety.py  v1.0
#
# Tests the boundary that makes the central safety claim TRUE rather than merely
# requested: a vision model's reply can only ever select one of the readings the
# OCR engines already produced, or abstain. There is no path by which text
# authored by a language model enters a document.
#
# The prompt asks for that. Prompts are wishes. `_parse_choice` is the enforcement,
# so it is the thing worth testing -- and the cases below are all the ways a model
# actually replies when it decides to be helpful instead of obedient.
#
# Run: python tests/test_safety.py
import sys
import pathlib

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from scanquorum.verify_ai import _parse_choice                 # noqa: E402

N = 3   # three candidates were offered in every case below

CASES = [
    # (model reply, expected index or None, what this case is about)
    ("CHOICE: 2", 2, "the format that was asked for"),
    ("choice: 2", 2, "lower case"),
    ("CHOICE 2", 2, "colon dropped"),
    ("CHOICE: 2\nThe text reads 12-855.", 2, "obeyed, then chattered"),
    ("NONE", None, "clean abstention"),
    ("None of these match the image.", None, "prose abstention"),

    # --- the dangerous ones: a model supplying TEXT instead of an index -------
    ("The text reads 12-855", None, "🔴 transcribed instead of choosing"),
    ('The correct reading is "Matter of Blas".', None, "🔴 supplied a case name"),
    ("CHOICE: 12-855", None, "🔴 put TEXT where the index goes"),
    ("2", None, "bare number -- ambiguous, so refused"),
    ("I think it is option two.", None, "spelled the number out"),

    # --- out of range, which is how a hallucinated index shows up ------------
    ("CHOICE: 0", None, "index below range"),
    ("CHOICE: 4", None, "index above range -- candidate does not exist"),
    ("CHOICE: 99", None, "wildly out of range"),

    # --- degenerate input ---------------------------------------------------
    ("", None, "empty reply"),
    (None, None, "no reply at all"),
    ("   \n\n", None, "whitespace"),
]


def main():
    print("scanquorum safety boundary: _parse_choice\n")
    bad = 0
    for reply, want, why in CASES:
        got = _parse_choice(reply, N)
        ok = got == want
        if not ok:
            bad += 1
        print("  %s  %-34r -> %-5r  %s" % ("ok " if ok else "FAIL", reply, got, why))

    # The property that matters, stated as a property rather than as examples:
    # whatever the model says, the result is either a valid index or None. It is
    # never a string, so it can never become text in a document.
    fuzz = ["CHOICE: -1", "CHOICE:2.5", "choice: 003", "CHOICE: 2; CHOICE: 3",
            "```json\n{\"choice\": 2}\n```", "выбор: 2", "CHOICE: two",
            "<answer>2</answer>", "CHOICE:\t1", "NONE\nCHOICE: 3"]
    for reply in fuzz:
        got = _parse_choice(reply, N)
        if not (got is None or (isinstance(got, int) and 1 <= got <= N)):
            print("  FAIL  %r escaped the boundary -> %r" % (reply, got))
            bad += 1
    print("\n  %d fuzz replies, all constrained to an index or None" % len(fuzz))

    if bad:
        print("\n%d FAILURES -- the safety boundary leaks." % bad)
        return 1
    print("\nSAFETY OK -- no model reply can produce text; only a choice or an abstention.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
