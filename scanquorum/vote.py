# scanquorum/vote.py  v1.0
#
# THE DECISION ENGINE. Given what several independent OCR engines read at the same
# place on the page, decide what to accept -- or refuse to decide and say so.
#
# ONE INVARIANT GOVERNS EVERY RULE BELOW:
#
#     No rule may return a string that no engine proposed.
#
# Every branch returns either a candidate verbatim, or a normalised form of a
# candidate, or None. Nothing here composes characters, "corrects spelling",
# or asks a language model. That is the entire reason this file can be trusted
# with a legal quotation: the worst it can do is pick the wrong engine's answer,
# which is a visible error, not an invented one.
#
# The cascade is ordered by how much evidence each rule requires, most first.
# A rule only runs when every rule above it has declined.
#
# PARITY: tests/test_vote_parity.py replays 29,853 real decisions recorded from
# the measured run and asserts this file reproduces every one of them. If you
# change anything here and that test still passes, you changed nothing that
# matters; if it fails, you changed the measured behaviour and the numbers in
# README.md no longer describe this code.
import re
import difflib
import unicodedata
import collections

VERSION = "1.0"

# Characters that different engines emit for "a dash". A citation printed as
# 12-855 comes back as 12‑855, 12–855 or 12—855 depending on the engine, and
# three spellings of the same dash look like three disagreeing engines.
DASHES = "‐‑‒–—―−­⁃·•‧・－"
TBL = {ord(c): "-" for c in DASHES}
STRIP = ".,;:()[]{}'\"`«»"

# Letter/digit confusions that every OCR engine makes, because the glyphs are
# genuinely ambiguous at 300 dpi in a 1970s typewriter face.
CONF = {"l": "1", "I": "1", "|": "1", "i": "1", "O": "0", "o": "0", "D": "0",
        "S": "5", "s": "5", "B": "8", "Z": "2", "z": "2", "G": "6", "T": "7",
        "q": "9", "g": "9", "A": "4", "J": "1", "b": "6"}

CIT = re.compile(r"^\d{1,2}-\d{2,4}$")          # 12-855   volume-page citation
STAT = re.compile(r"^\d{2,3}(\([a-zA-Z0-9]{1,3}\))+$")   # 245(a)(1)  statute subsection


def norm(t):
    return unicodedata.normalize("NFKC", str(t)).translate(TBL)


def collapse(t):
    """Squeeze runs of the same non-alphanumeric: '3--172' and '3—172' are one token."""
    return re.sub(r"([^A-Za-z0-9])\1+", r"\1", norm(t))


def key(tok):
    return collapse(tok).strip(STRIP).lower()


def skel(tok):
    """Only the letters and digits -- '11-911' and '11911' share a skeleton."""
    return re.sub(r"[^A-Za-z0-9]", "", norm(tok)).lower()


def digitish(t):
    return "".join(CONF.get(c, c) for c in collapse(t))


def ndig(t):
    return sum(c.isdigit() for c in str(t))


def noise(tok):
    return len(re.findall(r"[^A-Za-z0-9]", norm(tok)))


def has_sep(tok):
    return bool(re.search(r"[A-Za-z0-9][^A-Za-z0-9]+[A-Za-z0-9]", norm(tok)))


def lev(a, b):
    """Levenshtein distance. Used only to pick the most central candidate."""
    if a == b:
        return 0
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def pick_form(forms):
    """Choose among surface forms that are ALREADY KNOWN to be the same word.

    🔴 TIE-BREAK, SITE 1 of 3. This replaces `Counter(forms).most_common(1)`,
    which breaks a tie by INSERTION ORDER -- that is, by the order the engines
    happen to sit in a Python dict. Measured on 11,780 real candidate sets:
    165 of them (1.40 %) changed their answer when the engines were reordered,
    and 29 of those changed a DIGIT -- '12-869' against '12369', '1910' against
    '1940'. In a citation index that is a different citation.

    The same defect had already been found and fixed one branch below, for the
    2:2 vote split, with the note that insertion order decides "silently, and by
    an accident of dict ordering". It was fixed in one place out of four.

    Here the tie is NOT substantive: every form has the same `key()`, so they
    differ only in punctuation that `key()` strips. Flagging 'sec' against
    'sec.' would bury the reader in noise. So this one is settled by a stated,
    deterministic rule instead of by luck: fewest stray marks, then shortest,
    then lexicographic. The other two sites hold genuinely different digits and
    are sent to the reader instead.

    🔴 THE FIRST VERSION OF THIS FUNCTION WAS WRONG, and the parity test caught
    it on its first run. It applied the tie-break to ALL the forms and ignored
    how many engines backed each one -- so with 'children;' from three engines
    and 'children:' from one it returned the SINGLE engine's reading, because
    ':' sorts before ';'. Three engines agreeing is not a tie. Count first;
    break only the tie that is actually there.
    """
    c = collections.Counter(forms)
    best = max(c.values())
    tied = [f for f in c if c[f] == best]
    return min(tied, key=lambda f: (noise(f), len(f), f))


def align(pivot, other):
    """Line up one engine's tokens against another's, so the same word on the page
    is compared with the same word, not with its neighbour. Where the alignment is
    ambiguous the candidate is dropped rather than guessed -- a mis-aligned
    comparison manufactures disagreement, and disagreement costs a human's time."""
    kp, ko = [key(t) for t in pivot], [key(t) for t in other]
    sm = difflib.SequenceMatcher(None, kp, ko, autojunk=False)
    m = {}
    for op, i1, i2, j1, j2 in sm.get_opcodes():
        if op == "equal" or (op == "replace" and (i2 - i1) == (j2 - j1)):
            for d in range(i2 - i1):
                m[i1 + d] = [other[j1 + d]]
        elif op == "replace":
            for d in range(i1, i2):
                m[d] = other[j1:j2]
        elif op == "delete":
            for d in range(i1, i2):
                m.setdefault(d, [])
    return m


def decide(cands, lexicon):
    """Return (chosen, rule, who).

    `cands` maps engine name -> what that engine read here, or None if it read
    nothing. `chosen` is None only when the engines cannot be reconciled, and
    that is a result, not a failure: it is the tool telling you which words a
    person still has to look at.
    """
    have = [(s, v) for s, v in cands.items() if v is not None and str(v).strip()]
    if not have:
        return None, "EMPTY", ""
    if len(have) == 1:
        return norm(have[0][1]), "ONLY_ONE", have[0][0]

    # ---- 2. SEP: same digits, disagreement is only about the separator --------
    # '11-911' vs '11911' vs '11-9\l'. Decided on the majority SKELETON, not on
    # full equality: requiring full equality meant one damaged candidate stopped
    # the rule firing even though the other two agreed.
    #
    # TIE-BREAK, SITE 2 of 3 -- see the note above `pick_form` below. If two
    # skeleton groups are the same size, `max()` returns whichever the dict
    # happened to yield first. Those groups hold DIFFERENT DIGITS, so that is a
    # substantive disagreement decided by nothing. It falls through instead.
    by_sk = collections.defaultdict(list)
    for s, v in have:
        by_sk[skel(v)].append((s, v))
    sizes = sorted((len(g) for g in by_sk.values()), reverse=True)
    sep_tied = len(sizes) > 1 and sizes[0] == sizes[1]
    grp = max(by_sk.values(), key=len)
    sk0 = skel(grp[0][1])
    if not sep_tied and (len(grp) >= 2 or len(by_sk) == 1):
        if sk0 and sk0.isdigit():
            withs = [(s, v) for s, v in grp if has_sep(v)]
            if withs:
                # TIE-BREAK, SITE 4 of 4 -- found by the parity test only AFTER
                # the first three were fixed, which is the argument for having
                # the test at all. '9-50,' and '9.50,' both collapse to two
                # stray marks and five characters, so `min` returned whichever
                # the dict yielded first. The primary key stays exactly as
                # measured; what follows it is how many engines wrote that form,
                # then the form itself, so the result cannot depend on ordering.
                cnt = collections.Counter(collapse(v) for _, v in withs)
                s, v = min(withs, key=lambda t: (noise(collapse(t[1])), len(collapse(t[1])),
                                                 -cnt[collapse(t[1])], collapse(t[1])))
                tag = "SEP" if len(withs) < len(grp) else "SEP="
                return collapse(v), tag, ",".join(sorted(x for x, _ in withs))

    # ---- 3. VOTE: a plain majority of engines read the same thing ------------
    # A 2:2 split is NOT a majority. Counter.most_common would break that tie by
    # insertion order -- silently, and by an accident of dict ordering. A split
    # down the middle is a dispute and must fall through to the rules below.
    #
    # It also matters on the merits: two of the four engines share a text
    # detector, so "2 against 2" is often one correlated voice against two
    # independent ones rather than an even contest.
    votes = collections.Counter(key(v) for _, v in have)
    ranked = votes.most_common()
    top, n = ranked[0]
    if len(ranked) > 1 and ranked[1][1] == n:
        n = 0
    if n >= 2:
        who = sorted(s for s, v in have if key(v) == top)
        forms = [collapse(v) for s, v in have if key(v) == top]
        return pick_form(forms), "VOTE%d/%d" % (n, len(have)), ",".join(who)

    # ---- 4. NUM: agreement appears once l/1, O/0, S/5, B/8 are folded --------
    # Among the candidates that agree after folding, keep the one that needed the
    # fewest substitutions -- i.e. the engine that already read digits as digits.
    #
    # TIE-BREAK, SITE 3 of 3. Two digit-forms backed by the same number of
    # engines is '351,' against '851,' -- a real disagreement about a real
    # number. `most_common(1)` would have picked one by dict order. It falls
    # through to the reader instead.
    if sum(ndig(v) for _, v in have) >= 2:
        dv = collections.Counter(digitish(v).strip(STRIP).lower() for _, v in have)
        dranked = dv.most_common()
        dtop, dn = dranked[0]
        if len(dranked) > 1 and dranked[1][1] == dn:
            dn = 0
        if dn >= 2:
            grp2 = [(s, v) for s, v in have if digitish(v).strip(STRIP).lower() == dtop]
            # Same two primary keys as measured -- most digits, then fewest stray
            # marks -- expressed as a `min` so that deterministic tie-breakers can
            # follow them. '212(a)(28)(I)(ii);' and '212(a)(28)(I)(il);' match on
            # both primary keys, and `max` was returning whichever came first.
            c2 = collections.Counter(collapse(v) for _, v in grp2)
            s, v = min(grp2, key=lambda t: (-ndig(t[1]), noise(t[1]),
                                            -c2[collapse(t[1])], collapse(t[1])))
            return collapse(v), "NUM", ",".join(sorted(x for x, _ in grp2))

    # ---- 5. LEX: one candidate is a word this document actually uses ---------
    # The lexicon is built from the document's own confident text, not from a
    # dictionary, so it carries the case names and terms of art this document
    # uses and nothing else.
    #
    # A FABRICATION PATH CLOSED HERE, named by an outside reviewer: a real
    # surname absent from the lexicon ('Smythe') could be replaced by a frequent
    # lexicon word ('Smith'). So LEX never touches a capitalised token -- which
    # is exactly where surnames and case names live. Measured cost of the
    # restriction: zero. Every LEX firing in the gold set was lower-case.
    #
    # Weighted by frequency, because the lexicon contains hyphenation debris
    # ('los' from 'loss'), and an unweighted rule preferred the debris.
    if not any(str(v)[:1].isupper() for _, v in have):
        hits = sorted(((lexicon.get(key(v), 0), s, v) for s, v in have if key(v) in lexicon),
                      reverse=True)
        if hits:
            w1 = hits[0][0]
            w2 = hits[1][0] if len(hits) > 1 else 0
            if w1 >= 5 and w1 >= 2 * max(w2, 1) or (len(hits) == 1 and w1 >= 2):
                return collapse(hits[0][2]), "LEX", hits[0][1]

    # ---- 6. PATTERN: exactly one candidate has the shape of a citation ------
    # A SECOND FABRICATION PATH CLOSED HERE: the SHAPE of a citation is not the
    # TRUTH of a citation. '12-856' matches the pattern exactly as well as
    # '12-855' does, and picking on shape alone would mint a citation to a
    # decision that may not exist. So the DIGITS must additionally match at least
    # one other engine: shape from one, digits from two.
    pat = []
    for s, v in have:
        if not ((CIT.match(key(v)) or STAT.match(key(v))) and noise(norm(v)) <= 1):
            continue
        dv = re.sub(r"\D", "", norm(v))
        if any(re.sub(r"\D", "", norm(v2)) == dv for s2, v2 in have if s2 != s):
            pat.append((s, v))
    if len(pat) == 1:
        return collapse(pat[0][1]), "PATTERN", pat[0][0]

    # ---- 7. MEDOID: propose the most central candidate, do NOT accept it -----
    # A THIRD FABRICATION PATH CLOSED HERE. This rule used to decide. An outside
    # reviewer pointed out that it was accepting tokens no two engines had ever
    # agreed on -- unverified text entering a quotation through the back door.
    # It now FLAGS instead: the token is shown to the reader, marked unconfirmed.
    # The cost is a slightly longer review queue. That is the right trade for a
    # quotation of law: places to look at are cheap, a wrong citation is not.
    if len(have) >= 3:
        vals = [collapse(v) for _, v in have]
        tot = [sum(lev(vals[i], vals[j]) for j in range(len(vals)) if j != i)
               for i in range(len(vals))]
        mn = min(tot)
        if tot.count(mn) == 1:
            i = tot.index(mn)
            return vals[i], "MEDOID_FLAG", have[i][0]

    # ---- Nothing reconciled them. Say so. -----------------------------------
    return None, "DISPUTED", ""
