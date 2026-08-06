# tests/test_vote_parity.py  v1.1
#
# THE TEST THAT MAKES THE PUBLISHED NUMBERS MEAN SOMETHING.
#
# README.md states accuracy figures. Those were measured against one specific
# implementation of the decision cascade. This test replays every distinct
# candidate set from that measured run through the code in this repository.
#
# It asserts two different things, and the split is the whole point:
#
#   1. STABLE inputs -- where the original's answer does not depend on the order
#      the engines sit in a dict -- must be reproduced EXACTLY, all three
#      outputs. This is what proves the published engine is the measured engine
#      and not a lookalike rewritten from memory.
#
#   2. ORDER-DEPENDENT inputs -- 1.40 % of the corpus, where the original
#      returned a different answer depending on dict ordering -- are ALLOWED to
#      differ, because this repository deliberately fixed that. For those, the
#      test instead requires that the new answer is itself STABLE under every
#      permutation of the engines. Replacing one arbitrary answer with a
#      different arbitrary answer would be no improvement, and this is what
#      detects it.
#
# Run:  python tests/test_vote_parity.py
# Exit: 0 = pass, 1 = fail. No network, no key, no OCR engine needed.
import sys
import json
import pathlib
import itertools

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from scanquorum import vote                                    # noqa: E402

HERE = pathlib.Path(__file__).resolve().parent
FIX = HERE / "fixtures" / "decisions.jsonl"
LEXP = HERE / "fixtures" / "lexicon.json"


def main():
    if not FIX.exists():
        raise SystemExit("no fixture at %s -- run tests/make_fixture.py first" % FIX)

    lexicon = json.loads(LEXP.read_text(encoding="utf-8"))
    recs = [json.loads(l) for l in FIX.read_text(encoding="utf-8").splitlines() if l.strip()]
    print("scanquorum.vote v%s" % vote.VERSION)
    print("replaying %d recorded decisions (lexicon %d words)\n" % (len(recs), len(lexicon)))

    stable = [r for r in recs if not r["order_dependent"]]
    flaky = [r for r in recs if r["order_dependent"]]

    # ---- part 1: exact parity on everything the original decided stably ------
    bad, byrule = [], {}
    for i, r in enumerate(stable):
        chosen, rule, who = vote.decide(dict(r["cands"]), lexicon)
        byrule.setdefault(r["rule"], [0, 0])
        byrule[r["rule"]][0] += 1
        if (chosen, rule, who) == (r["chosen"], r["rule"], r["who"]):
            byrule[r["rule"]][1] += 1
        else:
            bad.append((i, r, (chosen, rule, who)))

    print("PART 1 -- exact parity on order-independent inputs")
    print("%-14s %8s %8s" % ("rule", "recorded", "matched"))
    for k in sorted(byrule):
        tot, good = byrule[k]
        print("%-14s %8d %8d%s" % (k, tot, good, "" if tot == good else "   <-- MISMATCH"))
    print("  %d of %d reproduced exactly\n" % (len(stable) - len(bad), len(stable)))

    if bad:
        print("--- first 15 differences (these are BUGS, not intended changes) ---")
        for i, r, got in bad[:15]:
            print("  cands=%s" % json.dumps(r["cands"], ensure_ascii=False))
            print("      expected: %r  %s  [%s]" % (r["chosen"], r["rule"], r["who"]))
            print("      got:      %r  %s  [%s]" % got)
        return 1

    # ---- part 2: the deliberately-changed ones must now be deterministic -----
    print("PART 2 -- the %d inputs the original decided by dict order" % len(flaky))
    unstable, moved, kept = [], 0, 0
    for r in flaky:
        outs = {vote.decide(dict(p), lexicon)
                for p in itertools.permutations(r["cands"].items())}
        if len(outs) > 1:
            unstable.append((r, sorted(outs)))
            continue
        got = outs.pop()
        if got[1] != r["rule"]:
            moved += 1
        else:
            kept += 1

    print("  now stable under every engine ordering: %d of %d" % (len(flaky) - len(unstable), len(flaky)))
    print("  sent to the reader as a dispute instead of guessed: %d" % moved)
    print("  same rule, now with a stated tie-break:             %d" % kept)
    if unstable:
        print("\n  STILL ORDER-DEPENDENT -- the fix is incomplete:")
        for r, outs in unstable[:10]:
            print("    %s" % json.dumps(r["cands"], ensure_ascii=False))
            print("       -> %s" % " | ".join(repr(o[0]) for o in outs))
        return 1

    # A test that only ever exercises one branch passes for the wrong reason.
    must = {"ONLY_ONE", "SEP", "NUM", "LEX", "MEDOID_FLAG", "DISPUTED", "PATTERN"}
    missing = must - {r["rule"] for r in recs}
    if missing:
        print("\nFIXTURE TOO NARROW: no recorded case exercises %s" % sorted(missing))
        return 1

    print("\nPARITY OK.")
    print("  Every decision the measured engine made stably is reproduced here exactly,")
    print("  and every decision it made by accident is now made by a stated rule.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
