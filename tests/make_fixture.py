# tests/make_fixture.py  v1.0
#
# Build the parity fixture by running the ORIGINAL, MEASURED decision engine over
# every candidate set in the real evidence file, and recording what it returned.
#
# WHY IT IS BUILT THIS WAY. The published engine (scanquorum/vote.py) was written
# out by hand in English from the original. A hand transcription is exactly the
# kind of step that silently changes behaviour -- one flipped comparison, one
# dropped `.strip()`, and the accuracy numbers in README.md would describe code
# that no longer exists. So the fixture is not written by hand: it is generated
# by importing the original module and calling it. The published engine then has
# to reproduce all of it, or the test suite goes red.
#
# This script is only runnable on the machine that has the original lab tree. The
# fixture it produces is committed, so everyone else can run the test.
#
#   python tests/make_fixture.py --lab "D:/Claude Cowork/_docbench2"
import sys
import json
import pathlib
import argparse
import hashlib
import itertools
import collections

sys.stdout.reconfigure(encoding="utf-8")

# The original Russian rule names, and their published English equivalents.
# Any name the original emits that is NOT in this map is a hard error: an
# unmapped rule would otherwise be silently recorded as a mismatch-free pass.
RULE_MAP = {
    "ПУСТО": "EMPTY",
    "ЕДИНСТВЕННЫЙ": "ONLY_ONE",
    "SEP": "SEP",
    "SEP=": "SEP=",
    "NUM": "NUM",
    "LEX": "LEX",
    "PATTERN": "PATTERN",
    "МЕДОИД-ФЛАГ": "MEDOID_FLAG",
    "СПОР": "DISPUTED",
}


def map_rule(r):
    if r.startswith("VOTE"):
        return r
    if r not in RULE_MAP:
        raise SystemExit("UNMAPPED RULE %r -- add it to RULE_MAP, do not guess" % r)
    return RULE_MAP[r]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--lab", required=True, help="directory holding the original ensemble.py")
    ap.add_argument("--out", default=str(pathlib.Path(__file__).parent / "fixtures" / "decisions.jsonl"))
    a = ap.parse_args()

    lab = pathlib.Path(a.lab)
    sys.path.insert(0, str(lab))
    import ensemble as original            # noqa: E402  -- the measured implementation

    print("original ensemble.py v%s from %s" % (original.VERSION, lab))

    ev = json.loads((lab / "merged_evidence.json").read_text(encoding="utf-8"))
    lex = json.loads((lab / "lexicon.json").read_text(encoding="utf-8"))
    print("evidence records: %d | lexicon words: %d" % (len(ev), len(lex)))

    out, seen, stats = [], set(), collections.Counter()
    for r in ev:
        cands = {}
        for src in ("adobe", "multi", "en", "tess"):
            if src in r:
                cands[src] = r[src]
        # Deduplicate identical candidate sets: 29,853 tokens contain a lot of
        # repetition, and the test should exercise distinct inputs, not the same
        # four words ten thousand times. Every DISTINCT input is kept.
        sig = json.dumps(cands, sort_keys=True, ensure_ascii=False)
        if sig in seen:
            continue
        seen.add(sig)
        chosen, rule, who = original.decide(cands, lex)

        # Is the ORIGINAL's answer stable under reordering of the engines?
        # Several of its tie-breaks reduce to Counter.most_common / max, which
        # resolve ties by insertion order -- so the answer depends on the order
        # the engines happen to sit in a dict. Permuting them exposes exactly
        # which inputs are decided by luck. Those, and only those, are allowed
        # to differ from the published engine.
        outs = {original.decide(dict(p), lex)
                for p in itertools.permutations(cands.items())}
        order_dependent = len(outs) > 1

        stats[map_rule(rule)] += 1
        if order_dependent:
            stats["~order-dependent"] += 1
        out.append({"cands": cands, "chosen": chosen, "rule": map_rule(rule), "who": who,
                    "order_dependent": order_dependent})

    dst = pathlib.Path(a.out)
    dst.parent.mkdir(parents=True, exist_ok=True)
    with dst.open("w", encoding="utf-8", newline="\n") as f:
        for rec in out:
            f.write(json.dumps(rec, ensure_ascii=False, sort_keys=True) + "\n")

    body = dst.read_bytes()
    print("\ndistinct candidate sets recorded: %d" % len(out))
    print("sha256(%s) = %s" % (dst.name, hashlib.sha256(body).hexdigest()))
    print("\n--- which rule decided, over DISTINCT inputs ---")
    for k, v in stats.most_common():
        print("  %-14s %6d  (%.2f%%)" % (k, v, 100 * v / len(out)))

    # The lexicon is needed to replay LEX decisions, so it ships with the fixture.
    lexdst = dst.parent / "lexicon.json"
    lexdst.write_text(json.dumps(lex, ensure_ascii=False, sort_keys=True, indent=0),
                      encoding="utf-8", newline="\n")
    print("\nlexicon copied -> %s (%d words)" % (lexdst.name, len(lex)))


if __name__ == "__main__":
    main()
