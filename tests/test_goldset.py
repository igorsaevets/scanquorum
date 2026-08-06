# tests/test_goldset.py  v1.0
#
# THE ACCURACY NUMBER, RECOMPUTABLE BY A STRANGER.
#
# Until this file existed, README.md quoted accuracy figures that nobody outside
# this machine could check: the reference standard lived in a lab directory that is
# not published. An external reviewer put it plainly -- a repository that states a
# percentage and ships no way to recompute it is asking to be believed, which is
# the exact posture this project criticises everywhere else.
#
# So `tests/fixtures/goldset.json` now travels with the code: 60 crops from the
# 41-page EOIR Cumulative Index, each with what a human read from the page rendered
# at 900 dpi, and each with what every engine read.
#
# ============================ READ THIS BEFORE QUOTING ANY NUMBER =============
#
# 1. THE SAMPLE IS STRATIFIED, NOT RANDOM. Contested decisions are deliberately
#    over-represented, because a random sample of a document where 96 % of tokens
#    are unanimous spends almost all of its labelling effort confirming the easy
#    ones. Raw percentages from this file are therefore NOT the document's accuracy
#    and this script refuses to print them as such.
#
# 2. FOUR OF THE 60 ARE `BAD_BOX`. The word box inherited from the PDF's own text
#    layer does not correspond to a token: it cuts a glyph, or it frames
#    typographic debris. Every engine then reads inside the same wrong box and
#    agrees. That is a SEGMENTATION failure, it is inherited by the whole ensemble,
#    and agreement cannot detect it. They are excluded from accuracy and counted
#    separately, which is why the corpus is 60 and the denominator is 56.
#
# 3. THE REFERENCE STANDARD WAS WRONG ONCE, IN A WAY WORTH KNOWING. Its first
#    version was read from a contact sheet whose vertical padding caught the
#    neighbouring line, and FIVE of the 60 labels came from the wrong line. It was
#    caught by an automatic rule, which is now permanent and runs below:
#
#        IF EVERY ENGINE AGREES AND THE HUMAN DISAGREES, SUSPECT THE HUMAN.
#
#    That check is part of the test. A reference standard is an instrument, and an
#    instrument that is never calibrated is a source of confident error.
#
# Run:  python tests/test_goldset.py
# Exit: 0 pass, 1 fail. No network, no engine, no key.
import re
import sys
import json
import pathlib
import collections
import unicodedata

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

GOLD = ROOT / "tests" / "fixtures" / "goldset.json"

# Normalisation, and why each class is here. Every one of these was added because
# a CORRECT reading was scored as a miss against the reference standard -- a defect
# in the measurement, not in the engine.
DASHES = "‐‑‒–—―−­⁃·•‧・－"
QUOTES = {ord(c): '"' for c in "“”„«»‟"}
QUOTES.update({ord(c): "'" for c in "‘’‚‛"})
TBL = {ord(c): "-" for c in DASHES}
TBL.update(QUOTES)
STRIP = ".,;:()[]{}'\"`«»“”‘’"


def n1(t):
    """Strict: characters must match, once dashes and typographic quotes are folded."""
    if t is None:
        return None
    return re.sub(r"-{2,}", "-", unicodedata.normalize("NFKC", str(t)).translate(TBL))


def n2(t):
    """Core: as above, ignoring surrounding punctuation. Reported separately because
    a crop does not always make it visible whether a trailing period is inside the
    box, and scoring a human's uncertainty as an engine's error inflates the error."""
    return None if t is None else n1(t).strip(STRIP)


def wilson(k, n, z=1.96):
    """A proportion without an interval is not a measurement. n is 56 here, so the
    interval is wide and saying so is the point."""
    if not n:
        return (0.0, 0.0)
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * ((p * (1 - p) / n + z * z / (4 * n * n)) ** 0.5) / d
    return (max(0.0, c - h), min(1.0, c + h))


def main():
    if not GOLD.exists():
        raise SystemExit("no gold set at %s" % GOLD)
    recs = json.loads(GOLD.read_text(encoding="utf-8"))
    bad = [r for r in recs if r["truth"] == "BAD_BOX"]
    good = [r for r in recs if r["truth"] != "BAD_BOX"]
    print("crops: %d  |  frame unusable (BAD_BOX): %d  |  scored: %d\n"
          % (len(recs), len(bad), len(good)))
    fails = []

    # ---- 1. calibrate the instrument before using it ------------------------
    print("PART 1 -- reference-standard self-check")
    print("  rule: if every engine agrees and the human disagrees, suspect the human")
    suspect = []
    for r in good:
        vals = [r[k] for k in ("pdf_layer", "multi", "en") if r.get(k) is not None]
        if len(vals) == 3 and len({n2(v) for v in vals}) == 1 and n2(vals[0]) != n2(r["truth"]):
            suspect.append((r["n"], r["truth"], vals[0]))
    if suspect:
        print("  %d crop(s) to re-read:" % len(suspect))
        for n, tr, v in suspect:
            print("    #%-3d human=%-18r all three=%-18r" % (n, tr, v))
        fails.append("%d gold labels contradict a unanimous ensemble" % len(suspect))
    else:
        print("  none. No label contradicts a unanimous reading of the pixels.")

    # ---- 2. every layer against the pixels ----------------------------------
    print("\nPART 2 -- each voter, and the ensemble, against what a human read at 900 dpi")
    LAYERS = [("pdf_layer", "PDF text layer"), ("multi", "rapidocr_multi"),
              ("en", "rapidocr_en"), ("chosen", "THE ENSEMBLE")]
    print("  %-18s %7s %7s %9s  %s" % ("voter", "strict", "core", "n", "core 95% interval"))
    scores = {}
    for key, label in LAYERS:
        st = ct = n = 0
        for r in good:
            v = r.get(key)
            if v is None:
                continue
            n += 1
            st += (n1(v) == n1(r["truth"]))
            ct += (n2(v) == n2(r["truth"]))
        lo, hi = wilson(ct, n)
        scores[key] = (ct, n)
        print("  %-18s %6.1f%% %6.1f%% %9d  [%.1f%%, %.1f%%]"
              % (label, 100.0 * st / max(n, 1), 100.0 * ct / max(n, 1), n, 100 * lo, 100 * hi))

    # The claim that matters is comparative, and it must survive its own interval.
    ens_k, ens_n = scores["chosen"]
    best_single = max((scores[k][0] / max(scores[k][1], 1), k) for k in ("pdf_layer", "multi", "en"))
    print("\n  ensemble %d/%d; best single voter is %r at %.1f%%"
          % (ens_k, ens_n, best_single[1], 100 * best_single[0]))
    if ens_k / max(ens_n, 1) < best_single[0]:
        fails.append("the ensemble scores BELOW the best single voter on this sample")

    # ---- 3. per rule, so the weak rules are visible -------------------------
    print("\nPART 3 -- the ensemble, per decision rule")
    print("  a rule that fires often and is wrong often is the one to fix first")
    byrule = collections.defaultdict(lambda: [0, 0])
    for r in good:
        base = r["rule"].split("|")[0]
        base = "SEP" if base.startswith("SEP") else base
        if r.get("chosen") is None:
            continue
        byrule[base][1] += 1
        byrule[base][0] += (n2(r["chosen"]) == n2(r["truth"]))
    print("  %-16s %6s %6s   %s" % ("rule", "right", "n", "95% interval (wide by design)"))
    for rule in sorted(byrule, key=lambda k: -byrule[k][1]):
        k, n = byrule[rule]
        lo, hi = wilson(k, n)
        print("  %-16s %6d %6d   [%.0f%%, %.0f%%]" % (rule, k, n, 100 * lo, 100 * hi))

    # ---- 4. the segmentation failures agreement cannot see -------------------
    print("\nPART 4 -- the %d crops where the frame itself is wrong" % len(bad))
    print("  Every engine reads inside the same bad box and agrees. Unanimity here is")
    print("  not evidence; it is the failure. This is why the headline accuracy is an")
    print("  UPPER BOUND and not an estimate.")
    for r in bad:
        print("    #%-3d page %-3s all engines: %r" % (r["n"], r.get("page"), r.get("chosen")))
    if len(bad) / max(len(recs), 1) > 0.15:
        fails.append("more than 15%% of the gold set is BAD_BOX; the sample is unusable")

    print()
    if fails:
        print("FAILED (%d):" % len(fails))
        for f in fails:
            print("  - %s" % f)
        return 1
    print("GOLD SET OK.")
    print("  The reference standard does not contradict itself, the ensemble beats every")
    print("  single voter on this sample, and the intervals are printed next to the point")
    print("  estimates so nobody quotes 99 %% from n=56 without seeing what that costs.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
