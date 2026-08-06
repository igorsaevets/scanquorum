# What actually goes wrong in a scanned document

This is the defect catalogue this tool was built against. Every class below was
observed in the five documents in [`../samples/`](../samples/), with counts from the
41-page EOIR Cumulative Index (29,853 words, four engines).

The last section is the important one: **the defects this tool does not catch.**

---

## A. Defects a quorum fixes

### A1. The separator disappears — `12-855` becomes `12855`
The most common failure in this corpus and the most expensive. A volume–page citation
loses its hyphen and becomes an unsearchable seven-digit number. Engines disagree about
which of `‐ ‑ ‒ – — ― −` they saw, or whether they saw one at all.

**Why it costs so much:** searching the document for `12-855` returns nothing, and
returns it with no indication that anything is wrong. Measured: the existing text layer
of the index contained **2,583** citations of this shape; the quorum recovered **3,182**,
and **1,825 distinct** citations against **1,629**.

**Fixed by:** the `SEP` rule — when the digits agree and only the separator differs, take
the cleanest form.

### A2. Two citations weld together — `8409;11-224;`
Adjacent citations run into one token, so both become unsearchable at once. Detected by
comparing digit runs across engines.

### A3. Letters read as digits and back — `l`/`1`, `O`/`0`, `S`/`5`, `B`/`8`, `i`/`1`
`lOl(b)(l)(B)` for `101(b)(1)(B)`. In a statute subsection this is not cosmetic.
**Fixed by:** the `NUM` rule — fold the confusable pairs, and if agreement appears, keep
the candidate that needed the fewest substitutions.

### A4. Stray punctuation — `May 1, .1974`
Harmless to a reader, fatal to an exact-match quotation check, which is what a citation
verifier does. **Fixed by:** the vote, on the normalised form.

### A5. Hyphenation debris — `los` where the page reads `loss`
A word broken across a line break leaves a fragment that looks like a real short word.
**Fixed by:** the `LEX` rule, weighted by how often the document itself uses each form —
and deliberately never applied to a capitalised token, because that is where surnames and
case names live and a dictionary would "correct" them into different people.

---

## B. Defects a quorum does **not** fix — read this part

### B1. 🔴 Truncation. All engines agree, and all are wrong.
**This is the one that matters.**

The engines are given the same region of the page to read. If that region is cut short —
a box ending mid-word — then every engine reads inside the same wrong box, and they agree
unanimously on a fragment. Four voices, perfect consensus, wrong answer.

Measured on this corpus: **289 truncations in 91,879 tokens (0.31 %)** across the working
set, found by an independent fifth engine reading with its own layout analysis and
checking whether our token was a proper substring of what it read at overlapping
coordinates.

The number that should worry you is this one: of 24 disagreements checked by eye,
ScanQuorum was right on 17 and **wrong on 7 — and all 7 were truncations.** So this class
is not merely uncaught by the vote; it is *the majority of what is left*.

🔴 **And the accuracy measurement cannot see it, by construction.** The reference standard
was built by rendering each token's box at 900 dpi and reading it. If the box is wrong,
the reference is wrong in exactly the same way. A crop-relative gold standard can never
find a truncation. This is a hole in the measurement, not just in the tool, and no amount
of additional sampling closes it.

**Partial defence, shipped:** `--detect-truncation` runs a second engine with independent
layout analysis and flags any token that is a proper substring of what that engine read at
overlapping coordinates. It is a detector, not a fix.

### B2. Words no OCR engine ever sees
**340 words** in the index were present in the original text layer and read by none of the
neural engines — most of them in the running heads, margins and column gutters that layout
analysis discards. They are kept, credited to the single engine that saw them, and marked
as unconfirmed rather than dropped.

The inverse also happens: text the old layer never had, which the new engines find. Both
directions matter, and a tool that only ever *replaces* a layer silently loses the first
kind.

### B3. Correlated engines
Two of the four default engines share a text detector: **2,921 of 3,006 boxes are
byte-identical**. When those two agree, that is close to one opinion, not two. A "3 of 4"
majority containing both of them is weaker than a "2 of 4" majority that does not.

This is why the fourth engine was added. It is the weakest of the four and it still helped
— because it is the only one that draws its own boxes. **Independence beats accuracy in an
ensemble**, and adding a fifth engine from the same family would add nothing.

### B4. The right word in the wrong place
Nothing here checks reading order. A word correctly recognised but placed in the wrong
column produces a quotation that is verbatim and meaningless. Two-column detection is
heuristic (a whitespace gutter); it is right on this corpus and is not guaranteed anywhere
else.

---

## C. Defects in the tool itself, found and fixed

Kept here because a catalogue of other people's failures and none of your own is marketing.

### C1. Token duplication — 1.29× inflation
Overlapping OCR line boxes each claimed the same word, so a word appeared in the output
once per box that covered it. In assembled text this read `On On On November November
November`. On full-width pages it inflated the text by **1.29×**; on the narrow-column
index it was almost invisible (7 cases in 29,858), which is why it survived two rounds of
code review.

It died the first time someone *used* the tool to pull a quotation. **Reading code did not
find it; applying the artefact did.**

### C2. 🔴 Ties broken by dict ordering — found while publishing this repository
Four separate places in the decision cascade resolved a tie with
`Counter.most_common()` or `max()`, both of which return whichever item the dictionary
happened to yield first. **165 of 11,780 distinct decisions (1.40 %) changed their answer
when the engines were reordered. 29 of those changed a digit:**

```
12-869  vs  12369      a different citation
1910    vs  1940       a year, thirty years apart
11-335  vs  11-336     adjacent citations, both plausible
```

The defect had already been found once, for the 2:2 vote split, and fixed there with the
note that insertion order decides *"silently, and by an accident of dict ordering."* It
was fixed in one place out of four. Three of the remaining sites were found by a parity
test written for a completely different purpose; the fourth was only exposed after the
first three were fixed.

**Now:** ties that are merely about punctuation are settled by a stated rule (fewest stray
marks, then shortest, then lexicographic); ties that hold different digits are sent to the
reader as disputes. 33 decisions moved from "guessed" to "shown to you". No gold-set crop
changed, so the published accuracy still describes the current code.

### C3. A tie-break fix that was itself wrong
The first version of that fix ignored how many engines backed each form, so with
`children;` from three engines and `children:` from one it returned the single engine's
reading, because `:` sorts before `;`. The parity test caught it on its first run.

**Three engines agreeing is not a tie.** Count first; break only the tie that is there.
