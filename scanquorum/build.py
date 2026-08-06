# scanquorum/build.py  v1.0
#
# THE PIPELINE. One PDF in; a quorum-checked text layer, a Markdown sidecar and an
# index of everything that could not be confirmed, out.
#
#   python -m scanquorum build document.pdf
#
# What happens, in order:
#   1. read the text layer already in the PDF, with each word's box
#   2. run the OCR engines that are installed on this machine
#   3. for every word, ask vote.decide() what the engines collectively read
#   4. write:  <name>.md          clean text, provenance header, page markers
#              <name>.unconfirmed.json   every place a person should look at
#              <name>.evidence.json      every candidate from every engine
#
# DESIGN RULE THROUGHOUT: the tool reports what it could not do. A missing engine is
# printed, counted, and recorded in the sidecar header -- never silently skipped. A
# three-engine run and a four-engine run produce different confidence and the output
# has to say which one it was.
import os
import sys
import json
import time
import hashlib
import pathlib
import argparse
import collections

from . import vote
from . import layout

VERSION = "1.0"

# Which engine's line boxes define the page's layout, in order of preference.
# STATED, not alphabetical -- see the note at the frame selection below. The
# first name in this list that produced boxes on a page frames that page, and
# which one it was is written into the sidecar header.
FRAME_PREFERENCE = ("rapidocr_en", "rapidocr_multi", "tesseract")


def _sha256(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_engines(names, pdf, dpi, progress):
    """Return {engine_name: {page: {"boxes": [{"t":text,"b":bbox,"s":conf}]}}}.

    An engine that is not installed is reported and omitted. It is never faked and
    never silently replaced by another engine's output."""
    out, missing = {}, []
    for n in names:
        try:
            mod = __import__("scanquorum.engines." + n, fromlist=["run"])
        except ImportError as e:
            missing.append((n, "no adapter: %r" % e))
            continue
        try:
            out[n] = mod.run(pdf, dpi=dpi, progress=progress)
        except Exception as e:
            missing.append((n, repr(e)[:120]))
    return out, missing


def build(pdf, engines=("rapidocr_multi", "rapidocr_en", "tesseract"),
          dpi=300, out_dir=None, lexicon=None, heartbeat=900):
    import pymupdf
    pdf = pathlib.Path(pdf)
    out_dir = pathlib.Path(out_dir or pdf.parent)
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = pdf.stem
    t0 = time.time()
    last_beat = [t0]

    def progress(done, total, what=""):
        """Long runs must leave a trace on disk, not only on a terminal nobody is
        watching. Without this, a stalled run and a slow run look identical."""
        now = time.time()
        if now - last_beat[0] < heartbeat and done < total:
            return
        last_beat[0] = now
        pct = 100.0 * done / max(total, 1)
        eta = (now - t0) / max(done, 1) * (total - done) / 60.0
        rec = {"stage": what, "done": done, "total": total, "percent": round(pct, 1),
               "minutes_left": round(eta, 1), "finished": done >= total,
               "stale_if_older_than_seconds": heartbeat * 2,
               "updated": time.strftime("%Y-%m-%dT%H:%M:%S")}
        (out_dir / (stem + ".progress.json")).write_text(
            json.dumps(rec, indent=1), encoding="utf-8", newline="\n")
        print("  [%5.1f%%] %s  %d/%d  ~%.0f min left" % (pct, what, done, total, eta))

    doc = pymupdf.open(pdf)
    meta = doc.metadata or {}
    print("scanquorum build v%s" % VERSION)
    print("  document : %s (%d pages)" % (pdf.name, doc.page_count))
    print("  existing text layer produced by: %s / %s"
          % (meta.get("producer") or "-", meta.get("creator") or "-"))

    ocr, missing = load_engines(engines, pdf, dpi, progress)
    # Each adapter declares whether it returns line boxes or word boxes.
    # Defaulting to "line" is the safe side: a word engine mistaken for a line
    # engine still aligns correctly, the reverse silently mutes the voter.
    granularity = {}
    for n in ocr:
        mod = __import__("scanquorum.engines." + n, fromlist=["GRANULARITY"])
        granularity[n] = getattr(mod, "GRANULARITY", "line")

    for n, why in missing:
        print("  🔴 engine NOT available: %-16s %s" % (n, why))
    used = ["pdf_layer"] + sorted(ocr)
    print("  engines voting: %d  (%s)" % (len(used), ", ".join(used)))
    # 🔴 THIS WARNING WAS OFF BY ONE, AND AN OUTSIDE REVIEWER FOUND IT.
    # `used` includes "pdf_layer", so on the commonest configuration -- Tesseract
    # not installed, two RapidOCR voters present -- len(used) is exactly 3 and the
    # warning never fired. That is the install most people will have, and it is
    # precisely the one that needed warning: the two RapidOCR voters SHARE A
    # DETECTOR, so "three engines" there is the PDF layer plus roughly one and a
    # bit opinions. Counting voters is not the same as counting independence.
    CORRELATED = [{"rapidocr_multi", "rapidocr_en"}]
    independent = len(ocr)
    for group in CORRELATED:
        overlap = group & set(ocr)
        if len(overlap) > 1:
            independent -= len(overlap) - 1
    print("  independent OCR opinions: %d (voters that do not share a detector)" % independent)
    if len(ocr) < 2:
        print("  ⚠  fewer than two OCR engines besides the PDF's own text layer.")
        print("     There is no quorum here at all -- treat every word as unconfirmed.")
    elif independent < 3:
        print("  ⚠  only %d INDEPENDENT OCR opinions." % independent)
        for group in CORRELATED:
            if len(group & set(ocr)) > 1:
                print("     %s share a text detector, so they are nearer one voter than two;"
                      % " and ".join(sorted(group & set(ocr))))
                print("     their agreement is weaker evidence than the count suggests.")
        print("     Install Tesseract for a voter that draws its own boxes.")

    lex = lexicon if lexicon is not None else {}
    ev, unconf, stats = [], [], collections.Counter()
    frames_used = {}
    pages_md = []

    for pi in range(doc.page_count):
        pg = doc[pi]
        words = pg.get_text("words")
        # 🔴 A FIFTH ORDERING DEPENDENCE, found by a third outside reviewer -- and
        # this one lives OUTSIDE the voter, where the parity test cannot see it.
        # This used to be `for n in sorted(ocr)`, i.e. the frame was whichever
        # engine sorted first ALPHABETICALLY. The frame decides the line boxes, and
        # the line boxes decide which words are compared with which, before
        # decide() is ever called. So installing or removing an engine could change
        # the answer for reasons that have nothing to do with what it read.
        #
        # Now the preference is stated, in this constant, and the engine that was
        # actually used is recorded in the sidecar header -- so two runs that
        # disagree can be told apart without rerunning them.
        frame, frame_engine = None, None
        for n in list(FRAME_PREFERENCE) + sorted(ocr):
            b = ocr.get(n, {}).get(str(pi), {}).get("boxes")
            if b:
                frame, frame_engine = b, n
                break
        frames_used[frame_engine] = frames_used.get(frame_engine, 0) + 1
        if frame is None:
            # No OCR saw this page. Keep the existing layer, mark it unconfirmed.
            for w in words:
                rec = {"page": pi, "bbox": [round(x, 1) for x in w[:4]],
                       "pdf_layer": w[4], "chosen": vote.collapse(w[4]),
                       "rule": "ONLY_ONE|NO_OCR", "who": "pdf_layer"}
                ev.append(rec)
                unconf.append(rec)
                stats["ONLY_ONE|NO_OCR"] += 1
            pages_md.append((pi, " ".join(w[4] for w in words)))
            progress(pi + 1, doc.page_count, "voting")
            continue

        cut = layout.gutter([b["b"] for b in frame], pg.rect.width)
        colf = (lambda bb: 0) if cut is None else (lambda bb: 0 if (bb[0] + bb[2]) / 2 < cut else 1)
        owner = layout.assign(frame, words)
        idx = {n: layout.BoxIndex(ocr[n].get(str(pi), {}).get("boxes", [])) for n in ocr}
        order = sorted(range(len(frame)),
                       key=lambda i: (colf(frame[i]["b"]), round(frame[i]["b"][1], 1), frame[i]["b"][0]))
        rows, used_w = [], set()

        for bi in order:
            wis = sorted(owner.get(bi, []))
            used_w.update(wis)
            a_tok = [words[wi][4] for wi in wis]

            # 🔴 GRANULARITY. Neural OCR returns LINE boxes; Tesseract returns WORD
            # boxes. Looking a single word's box up in a line index gives an IoU of
            # roughly word-area over line-area -- almost always under threshold --
            # so the engine returns None for nearly every word and silently stops
            # voting. Measured when this was wrong: VOTE4/4 collapsed from 77 % to
            # 0.3 %, and VOTE2/2 rose to 76 %, i.e. two of four voters had quietly
            # left the room while the output still looked healthy.
            #
            # So line engines are matched line-to-line and their token SEQUENCE is
            # aligned against the word sequence; word engines are looked up
            # directly by box.
            seqs = {}
            for n in sorted(ocr):
                if granularity.get(n) == "word":
                    continue
                best, bt = 0.0, None
                for ob in ocr[n].get(str(pi), {}).get("boxes", []):
                    v = layout.iou(frame[bi]["b"], ob["b"])
                    if v > best:
                        best, bt = v, ob
                toks = bt["t"].split() if (bt and best > 0.3) else []
                seqs[n] = vote.align(a_tok, toks) if toks else {}

            for i, wi in enumerate(wis):
                w = words[wi]
                box = (w[0], w[1], w[2], w[3])
                cands = {"pdf_layer": w[4]}
                for n in sorted(ocr):
                    if granularity.get(n) == "word":
                        cands[n] = idx[n].at(box)[0]
                    else:
                        m = seqs.get(n, {}).get(i, [])
                        # Exactly one aligned token, or nothing. An ambiguous
                        # alignment is dropped rather than guessed: comparing a
                        # word against its neighbour manufactures disagreement,
                        # and disagreement costs a person's time.
                        cands[n] = m[0] if len(m) == 1 else None
                chosen, rule, who = vote.decide(cands, lex)
                rec = {"page": pi, "bbox": [round(x, 1) for x in box], "col": colf(box),
                       "y": box[1], "x": box[0], "chosen": chosen, "rule": rule, "who": who}
                rec.update(cands)
                # 🔴 EVERY word not carried by a quorum belongs in the unconfirmed
                # index -- not only the contested ones. An outside reviewer caught
                # the header claiming that anything absent from this index had been
                # read identically by two engines, which was false for every
                # ONLY_ONE word (~340 per document: running heads, margins, gutters
                # that layout analysis discards). A machine-readable warning that is
                # false is worse than no warning, because it is believed.
                if rule in ("DISPUTED", "MEDOID_FLAG") or rule.startswith("ONLY_ONE"):
                    if chosen is None:
                        rec["chosen"] = vote.collapse(w[4])
                    unconf.append(rec)
                rows.append(rec)
                stats[rule] += 1

        for wi, w in enumerate(words):
            if wi in used_w:
                continue
            box = (w[0], w[1], w[2], w[3])
            rec = {"page": pi, "bbox": [round(x, 1) for x in box], "col": colf(box),
                   "y": box[1], "x": box[0], "pdf_layer": w[4],
                   "chosen": vote.collapse(w[4]), "rule": "ONLY_ONE|OCR_BLIND",
                   "who": "pdf_layer"}
            rows.append(rec)
            unconf.append(rec)
            stats["ONLY_ONE|OCR_BLIND"] += 1

        rows.sort(key=lambda r: (r["col"], round(r["y"], 1), r["x"]))
        ev.extend(rows)
        pages_md.append((pi, " ".join(r["chosen"] for r in rows if r["chosen"])))
        progress(pi + 1, doc.page_count, "voting")

    # ---------------- outputs ------------------------------------------------
    # 🔴 A QUORUM OF CORRELATED VOTERS IS NOT A QUORUM. Found by a fourth outside
    # reviewer, and it is sharper than the console warning fixed earlier: that one
    # was about what the run PRINTS, this one is about the NUMBER itself. A 2-of-3
    # majority carried by rapidocr_multi + rapidocr_en is one shared text detector
    # agreeing with itself, and counting it as two independent confirmations is the
    # same overstatement the tool exists to catch elsewhere.
    QUORUM_RULES = ("NUM", "LEX", "PATTERN")
    quorum = weak = 0
    for r in ev:
        rule = r.get("rule", "")
        if not (rule.startswith("VOTE") or rule.startswith("SEP") or rule in QUORUM_RULES):
            continue
        backers = set((r.get("who") or "").split(","))
        quorum += 1
        # Weak when every engine that backed it comes from one correlated group and
        # nothing outside that group agreed.
        for group in CORRELATED:
            if backers and backers <= group:
                weak += 1
                break
    hdr = {
        "source_pdf": pdf.name,
        "source_sha256": _sha256(pdf),
        "pages": doc.page_count,
        "engines": used,
        "engines_unavailable": [n for n, _ in missing],
        "frame_engine": max(frames_used, key=frames_used.get) if frames_used else None,
        "frame_engine_pages": frames_used,
        "words": len(ev),
        "accepted_by_quorum": quorum,
        "quorum_from_correlated_voters_only": weak,
        "unconfirmed": len(unconf),
        "unconfirmed_index": stem + ".unconfirmed.json",
        "existing_layer_producer": meta.get("producer") or "",
        "generated_by": "scanquorum " + VERSION,
    }
    warn = (
        "%d of the %d words in this file were read identically by at least two independent "
        "OCR engines. The other %d were NOT, and every one of them is listed in %s with its "
        "page and coordinates -- they include words that only a single engine saw as well as "
        "words the engines could not reconcile. THE BODY TEXT BELOW DOES NOT MARK THEM "
        "INLINE, so before quoting any passage, check it against that index; if a word from "
        "it appears in what you are about to quote, say that the word is unverified rather "
        "than presenting it as the text of the document. No language model wrote or corrected "
        "any character in this file."
        % (quorum, len(ev), len(ev) - quorum, stem + ".unconfirmed.json")
    )
    if len(used) < 3:
        warn = ("THIS RUN HAD ONLY %d ENGINES. Nothing here is confirmed by a quorum. "
                "Treat the whole file as unverified. " % len(used)) + warn

    md = ["---"]
    for k, v in hdr.items():
        md.append("%s: %s" % (k, json.dumps(v, ensure_ascii=False) if isinstance(v, (list, dict)) else v))
    md.append("warning: >")
    md.append("  " + warn)
    md.append("---")
    md.append("")
    for pi, text in pages_md:
        md.append("<!-- page %d -->" % (pi + 1))
        md.append(text)
        md.append("")

    (out_dir / (stem + ".md")).write_text("\n".join(md), encoding="utf-8", newline="\n")
    (out_dir / (stem + ".unconfirmed.json")).write_text(
        json.dumps(unconf, ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")
    (out_dir / (stem + ".evidence.json")).write_text(
        json.dumps(ev, ensure_ascii=False), encoding="utf-8", newline="\n")

    print("\n=== HOW EACH WORD WAS DECIDED ===")
    for r, n in sorted(stats.items(), key=lambda t: -t[1]):
        print("  %-22s %7d  (%.2f%%)" % (r, n, 100.0 * n / max(len(ev), 1)))
    print("\n  words                : %d" % len(ev))
    print("  accepted by quorum   : %d  (%.2f%%)" % (quorum, 100.0 * quorum / max(len(ev), 1)))
    if weak:
        print("    of which carried ONLY by voters that share a detector: %d (%.2f%%)"
              % (weak, 100.0 * weak / max(quorum, 1)))
        print("    those are one opinion agreeing with itself -- weaker than the count.")
    print("  shown to you         : %d  (%.2f%%)" % (len(unconf), 100.0 * len(unconf) / max(len(ev), 1)))
    print("\n  -> %s.md" % stem)
    print("  -> %s.unconfirmed.json" % stem)
    print("  -> %s.evidence.json" % stem)
    doc.close()
    return hdr


def main(argv=None):
    ap = argparse.ArgumentParser(prog="scanquorum build")
    ap.add_argument("pdf")
    ap.add_argument("--engines", default="rapidocr_multi,rapidocr_en,tesseract")
    ap.add_argument("--dpi", type=int, default=300)
    ap.add_argument("--out-dir")
    ap.add_argument("--lexicon", help="JSON word->count, built from the document's own text")
    ap.add_argument("--heartbeat", type=int, default=900,
                    help="seconds between progress files (default 900 = 15 min)")
    a = ap.parse_args(argv)
    lex = json.loads(pathlib.Path(a.lexicon).read_text(encoding="utf-8")) if a.lexicon else {}
    build(a.pdf, engines=tuple(x for x in a.engines.split(",") if x), dpi=a.dpi,
          out_dir=a.out_dir, lexicon=lex, heartbeat=a.heartbeat)
    return 0


if __name__ == "__main__":
    sys.exit(main())
