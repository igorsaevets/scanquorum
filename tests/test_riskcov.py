# tests/test_riskcov.py  v1.0
#
# THE RISK-COVERAGE CURVE AND THE SINGLE-ENGINE BASELINE, RECOMPUTABLE BY A STRANGER.
#
# Every external reviewer of the paper asked for the same two measurements, in almost
# the same words: (1) vary the acceptance rule and plot accepted-token accuracy against
# coverage instead of reporting one operating point; (2) threshold a single engine on
# its own confidence to the same coverage, because -- as one reviewer put it -- if the
# ensemble does not beat that curve, the premise collapses.
#
# Both were measured on 2026-08-09 (testing/TESTED.md, round 4). This test recomputes
# every published point from `tests/fixtures/index_census.json`, which carries only
# aggregate cross-tabulations of the 41-page EOIR index evidence plus the 56 scored
# gold crops -- no lab files, no OCR engine, no network.
#
# WHAT THE ESTIMATOR IS, in one paragraph, so nobody has to reverse-engineer it:
# coverage is EXACT (a census of which tokens each policy accepts); accuracy among
# accepted tokens is a Hájek ratio -- Horvitz-Thompson totals for "correct and
# accepted" over "accepted", both estimated from the same stratified gold crops with
# post-stratification weights N_h/n_h by the three-voice rule stratum each crop's
# token belongs to. The first version of the measuring script divided the estimated
# numerator by the EXACT accepted count instead, and printed 143 % accuracy: the
# dominant stratum has 23,585 tokens behind 8 crops, and which of those crops land
# inside a policy is sampling noise that only cancels if numerator and denominator
# come from the same sample. The ratio form cannot leave [0, 1]. That defect is kept
# in the lab script's header the same way every other rejected instrument is kept.
#
# Run:  python tests/test_riskcov.py     Exit: 0 pass, 1 fail.
import sys
import json
import pathlib

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = pathlib.Path(__file__).resolve().parent.parent
FX = ROOT / "tests" / "fixtures" / "index_census.json"

TOTAL = 29853

# Published points (testing/riskcov_results.json, riskcov.py v1.1, seed 20260809).
# coverage is exact and must match EXACTLY; accuracy is a deterministic ratio and
# must match to 1e-6.
E1_EXPECT = {
    "VOTE4/4 only": (0.773289, 1.000000),
    "VOTE4/4 only +SEP/NUM": (0.879744, 1.000000),
    "VOTE4/4 only +LEX/PATTERN": (0.777074, 1.000000),
    "VOTE4/4 only +SEP/NUM +LEX/PATTERN": (0.883529, 1.000000),
    "VOTE>=3": (0.846414, 0.993013),
    "VOTE>=3 +SEP/NUM": (0.952869, 0.993788),
    "VOTE>=3 +LEX/PATTERN": (0.850199, 0.993040),
    "VOTE>=3 +SEP/NUM +LEX/PATTERN": (0.956654, 0.993809),
    "VOTE>=2": (0.865776, 0.993129),
    "VOTE>=2 +SEP/NUM": (0.972231, 0.993879),
    "VOTE>=2 +LEX/PATTERN": (0.869561, 0.993155),
    "VOTE>=2 +SEP/NUM +LEX/PATTERN": (0.976016, 0.993900),
    "all present agree (VOTEk/k)": (0.775500, 1.000000),
    "everything emitted (+flags)": (0.989314, 0.992664),
}
E2_EXPECT = [  # (tau, coverage, accuracy)
    (0.0, 0.989884, 0.958992), (0.5, 0.989884, 0.958992), (0.7, 0.989247, 0.960177),
    (0.8, 0.988879, 0.960177), (0.85, 0.988778, 0.960177), (0.9, 0.987740, 0.960177),
    (0.925, 0.983620, 0.970804), (0.95, 0.968780, 0.970114), (0.96, 0.951998, 0.969940),
    (0.97, 0.912471, 0.970124), (0.975, 0.869695, 0.972912), (0.98, 0.808160, 0.972211),
    (0.985, 0.710180, 0.971375), (0.99, 0.564700, 0.972897), (0.9925, 0.467960, 0.978377),
    (0.995, 0.370482, 0.986882), (0.9975, 0.275651, 0.982429), (0.999, 0.189696, 0.974148),
    (0.9995, 0.143001, 0.973995),
]

S_RULES = {"SEP", "SEP=", "NUM"}
R_RULES = {"LEX", "PATTERN"}
FLAG_RULES = {"ONLY_ONE", "MEDOID_FLAG"}


def votes_k(rule):
    return int(rule[4:].split("/")[0]) if rule.startswith("VOTE") else None


def unanimous(rule):
    if not rule.startswith("VOTE"):
        return False
    k, m = rule[4:].split("/")
    return k == m


def accepted(rule, kmin, s, rr, flags=False, unan=False):
    k = votes_k(rule)
    if k is not None:
        return unanimous(rule) if unan else k >= kmin
    return (s and rule in S_RULES) or (rr and rule in R_RULES) or (flags and rule in FLAG_RULES)


POLICIES = []
for kmin, kl in ((4, "VOTE4/4 only"), (3, "VOTE>=3"), (2, "VOTE>=2")):
    for s, rr, sl in ((0, 0, ""), (1, 0, " +SEP/NUM"), (0, 1, " +LEX/PATTERN"),
                      (1, 1, " +SEP/NUM +LEX/PATTERN")):
        POLICIES.append((kl + sl, dict(kmin=kmin, s=s, rr=rr)))
POLICIES.append(("all present agree (VOTEk/k)", dict(kmin=99, unan=True)))
POLICIES.append(("everything emitted (+flags)", dict(kmin=2, s=1, rr=1, flags=True)))


def main():
    fx = json.loads(FX.read_text(encoding="utf-8"))
    fails = []

    # ---- 0. the fixture must account for every token, twice over ------------
    census = fx["shipped_rule_census"]
    old = fx["old_stratum_census"]
    assert sum(census.values()) == TOTAL and sum(old.values()) == TOTAL
    from collections import Counter
    m_rule = Counter()
    m_old = Counter()
    for h, rl, c in fx["cross_old_by_shipped_rule"]:
        m_rule[rl] += c
        m_old[h] += c
    assert dict(m_rule) == census, "cross table does not marginalise to the rule census"
    assert dict(m_old) == old, "cross table does not marginalise to the stratum census"
    rows = fx["gold_rows"]
    assert len(rows) == 56, "expected 56 scored gold crops"
    H = set(fx["covered_strata"])
    nh = Counter(r["h"] for r in rows)
    assert set(nh) == H
    print("fixture accounts for every one of %d tokens, both ways; 56 gold crops in %d strata"
          % (TOTAL, len(H)))

    def hajek(y_num_key, acc_fn):
        tn = td = 0.0
        for h in H:
            w = old[h] / nh[h]
            for r in rows:
                if r["h"] != h or not acc_fn(r):
                    continue
                tn += w * r[y_num_key]
                td += w
        return tn / td if td else 0.0

    # ---- 1. the risk-coverage curve -----------------------------------------
    print("\nPART 1 -- accepted-token accuracy vs coverage, every published point recomputed")
    for label, kw in POLICIES:
        cov = sum(c for rl, c in census.items()
                  if accepted(rl, kw.get("kmin", 2), kw.get("s", 0), kw.get("rr", 0),
                              kw.get("flags", False), kw.get("unan", False))) / TOTAL
        acc = hajek("ens_ok", lambda r: accepted(
            r["rule"], kw.get("kmin", 2), kw.get("s", 0), kw.get("rr", 0),
            kw.get("flags", False), kw.get("unan", False)))
        ecov, eacc = E1_EXPECT[label]
        ok = abs(cov - ecov) < 5e-7 and abs(acc - eacc) < 1e-6
        print("  %-36s cov %7.2f%%  acc %7.2f%%  %s"
              % (label, 100 * cov, 100 * acc, "ok" if ok else "MISMATCH"))
        if not ok:
            fails.append("E1 %r: got (%.6f, %.6f), published (%.6f, %.6f)"
                         % (label, cov, acc, ecov, eacc))

    # ---- 2. the single-engine confidence baseline ---------------------------
    print("\nPART 2 -- rapidocr_multi alone, thresholded on its own line confidence")
    grid = fx["conf_grid"]
    bins = Counter()
    for h, b, c in fx["cross_old_by_conf_bin"]:
        bins[b] += c
    for tau, ecov, eacc in E2_EXPECT:
        cov = sum(c for b, c in bins.items()
                  if b != "none" and float(b) >= tau - 1e-12) / TOTAL
        acc = hajek("multi_ok", lambda r: r["conf_mu"] is not None and r["conf_mu"] >= tau)
        ok = abs(cov - ecov) < 5e-7 and abs(acc - eacc) < 1e-6
        print("  tau %-7s cov %7.2f%%  acc %7.2f%%  %s"
              % (("%.4f" % tau).rstrip("0").rstrip("."), 100 * cov, 100 * acc,
                 "ok" if ok else "MISMATCH"))
        if not ok:
            fails.append("E2 tau=%s: got (%.6f, %.6f), published (%.6f, %.6f)"
                         % (tau, cov, acc, ecov, eacc))
    assert grid == sorted(grid)

    # ---- 3. the comparative claim, which is the one that matters ------------
    print("\nPART 3 -- at every policy's coverage, the ensemble vs the single engine")
    e2pts = sorted(((c, a) for _, c, a in E2_EXPECT))
    below = 0
    for label, _ in POLICIES:
        cov, acc = E1_EXPECT[label]
        cand = [(c, a) for c, a in e2pts if c >= cov - 1e-9]
        mcov, macc = min(cand) if cand else max(e2pts)
        if acc <= macc:
            below += 1
            print("  %-36s ensemble %6.2f%% <= single %6.2f%%" % (label, 100 * acc, 100 * macc))
    if below:
        fails.append("the ensemble fails to beat the single-engine baseline at %d point(s)" % below)
    else:
        print("  the ensemble is above the single-engine curve at all %d matched points."
              % len(POLICIES))
        print("  (point estimates; most per-point intervals overlap -- see TESTED.md before")
        print("   quoting this as significant)")

    print()
    if fails:
        print("FAILED (%d):" % len(fails))
        for f in fails:
            print("  - %s" % f)
        return 1
    print("RISK-COVERAGE OK.")
    print("  Every published point on both curves is recomputed from the shipped fixture,")
    print("  and the comparative claim holds at every matched coverage.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
