# scanquorum/layout.py  v1.0
#
# Where things are on the page. Three jobs, all geometric, none of them about
# characters: find the column gutter, decide which OCR line owns each word, and
# look a word up by its box quickly.
import collections


def iou(a, b):
    x0, y0 = max(a[0], b[0]), max(a[1], b[1])
    x1, y1 = min(a[2], b[2]), min(a[3], b[3])
    if x1 <= x0 or y1 <= y0:
        return 0.0
    i = (x1 - x0) * (y1 - y0)
    ua = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - i
    return i / ua if ua > 0 else 0.0


def gutter(boxes, page_w):
    """Find the vertical whitespace channel of a two-column page, or None.

    🔴 HEURISTIC, and the tool's weakest part. It looks for a band between 30 %
    and 70 % of the width that almost no box crosses. It is right on the corpus
    this was measured on and is guaranteed nowhere else. Reading order is not
    otherwise checked, so a wrong answer here produces text that is perfectly
    recognised and in the wrong order -- a quotation that is verbatim and
    meaningless. See testing/TO-TEST.md#g6."""
    if len(boxes) < 10:
        return None
    occ = [0] * 100
    for b in boxes:
        for i in range(max(0, int(b[0] / page_w * 100)), min(99, int(b[2] / page_w * 100)) + 1):
            occ[i] += 1
    thr = max(1, int(0.02 * len(boxes)))
    best, i = None, 30
    while i <= 70:
        if occ[i] <= thr:
            j = i
            while j <= 70 and occ[j] <= thr:
                j += 1
            if best is None or (j - i) > (best[1] - best[0]):
                best = (i, j)
            i = j
        else:
            i += 1
    return (best[0] + best[1]) / 2 / 100 * page_w if best and (best[1] - best[0]) >= 3 else None


def assign(ocr_lines, words):
    """Map each word of the existing text layer to EXACTLY ONE OCR line.

    🔴 THE DEFECT THIS FUNCTION EXISTS TO CLOSE. The obvious loop -- for each OCR
    line, take every word whose centre falls inside it -- emits a word once per
    line that covers it. OCR line boxes overlap constantly on full-width pages, so
    the assembled text came out as 'On On On November November November', inflating
    one document by 1.29x and 4,801 surplus tokens.

    It was nearly invisible on narrow-column pages (7 cases in 29,858), which is
    why it survived two rounds of code review and died the first time anyone used
    the output to pull a real quotation.

    Resolution: the word belongs to the line whose vertical centre is nearest; ties
    go to the tighter box. Stable under nested and slightly shifted detections."""
    owner = collections.defaultdict(list)
    for wi, w in enumerate(words):
        cx, cy = (w[0] + w[2]) / 2, (w[1] + w[3]) / 2
        best, bi = None, -1
        for i, eb in enumerate(ocr_lines):
            r = eb["b"]
            if not (r[0] - 2 <= cx <= r[2] + 2 and r[1] - 2 <= cy <= r[3] + 2):
                continue
            sc = (abs(cy - (r[1] + r[3]) / 2), (r[2] - r[0]) * (r[3] - r[1]))
            if best is None or sc < best:
                best, bi = sc, i
        if bi >= 0:
            owner[bi].append(wi)
    return owner


class BoxIndex:
    """Look up an engine's reading by box. Bucketed vertically because the naive
    scan is ~730 words x ~750 boxes x 200 pages = 100 million overlap tests."""

    def __init__(self, boxes, bucket=6.0):
        self.bucket = bucket
        self.idx = collections.defaultdict(list)
        for bx in boxes or ():
            for k in range(int(bx["b"][1] // bucket), int(bx["b"][3] // bucket) + 1):
                self.idx[k].append(bx)

    def at(self, bbox, thr=0.25):
        seen, best, bt = set(), 0.0, None
        for k in range(int(bbox[1] // self.bucket), int(bbox[3] // self.bucket) + 1):
            for bx in self.idx.get(k, ()):
                if id(bx) in seen:
                    continue
                seen.add(id(bx))
                v = iou(bbox, bx["b"])
                if v > best:
                    best, bt = v, bx
        if bt is None or best <= thr:
            return None, None
        t = bt.get("t")
        # A line box holds several words; a single-word query wants the word, and
        # returning the whole line would manufacture disagreement at every token.
        return (t.split()[0] if t and len(t.split()) == 1 else t), bt.get("s")
