# scanquorum/verify_ai.py  v1.0
#
# THE AI STANDING IN FOR THE HUMAN AT THE ONE STEP THAT NEEDS EYES.
#
# When the engines cannot agree, someone has to look at the pixels. `verify_ui.py`
# opens a window and asks a person. This module asks a vision model instead, and
# it is deliberately built so that the model CANNOT do the thing that would ruin
# the document.
#
# ================= THE ONE RULE THIS FILE EXISTS TO ENFORCE ==================
#
#     THE MODEL NEVER TRANSCRIBES. IT ONLY CHOOSES, OR ABSTAINS.
#
# It is shown the crop and the candidate readings the OCR engines produced, and
# it must answer with an INDEX into that list, or with "none of these". Free text
# coming back from the model is discarded, not parsed. This is enforced in code
# (`_parse_choice`), not requested in a prompt -- a prompt is a wish, and the
# whole point of this project is that a language model asked to read a scan will
# produce fluent, confident, wrong text and no downstream check will notice.
#
# So the worst case here is that the model picks the wrong engine's reading --
# a visible error of the same kind a tired person makes. It cannot invent a
# citation that no engine ever saw, because there is no code path for that.
#
# ============================ AND IT IS AUDITED =============================
#
# A model that says "yes, looks right" to everything is worse than no model, and
# it is indistinguishable from a good one unless you test for it. So every run
# includes NEGATIVE CONTROLS: a fraction of the questions are asked with the
# correct candidate REMOVED from the list. The only defensible answer is "none of
# these". The abstention rate on those controls is printed and stored.
#
# This is not hypothetical. Measured on this project's own queue, on the same
# task, with the same prompt: one model abstained on 95 % of negative controls,
# another on 46 %. The second model was confidently choosing a wrong reading half
# the time it was given no right answer. Same task, same prompt -- so the safety
# property belongs to the MODEL, not to the harness, and it has to be re-measured
# for every model you point this at. `--control-rate 0` disables it, and the run
# then reports its own verdicts as unaudited.
#
# Usage:
#   python -m scanquorum.verify_ai --pending pending.json --model <id> --pages 2
#
# Secrets: the API key is read from the environment and is never printed, logged
# or written to any output file. Only its presence and length are ever reported.
import os
import re
import io
import sys
import json
import base64
import random
import pathlib
import argparse
import datetime
import urllib.request

VERSION = "1.0"
ENDPOINT = "https://openrouter.ai/api/v1/chat/completions"

SYSTEM = (
    "You compare printed text on a scanned page against a short list of readings "
    "produced by OCR engines. You are NOT transcribing and you must never write out "
    "text of your own.\n\n"
    "Answer with a single line, exactly one of:\n"
    "  CHOICE: <n>     where <n> is the number of the reading that matches the paper\n"
    "  NONE            if none of the listed readings matches what is printed\n\n"
    "A wrong choice is worse than NONE. If the crop is unclear, if the region is cut "
    "off, or if the correct reading is simply not in the list, answer NONE. You will "
    "sometimes be given a list from which the correct reading has been deliberately "
    "removed; NONE is the only correct answer in that case."
)


def _parse_choice(text, n_candidates):
    """Accept ONLY an index or an abstention. Everything else is an abstention.

    This is the safety boundary. It is a function, not a prompt instruction,
    because the model does not get a vote on whether it obeys."""
    if not text or not text.strip():
        return None                       # a blank reply used to crash this
    head = text.strip().splitlines()[0][:80]
    # The number must be the WHOLE value, not the start of one. Without the
    # trailing guard, 'CHOICE: 12-855' -- a model putting the TEXT where the
    # index goes -- parses as index 12, and with twelve or more candidates that
    # silently selects one. The range check hid this while the lists were short.
    m = re.match(r"\s*CHOICE\s*:?\s*(\d{1,3})\s*[.)]?\s*$", head, re.I)
    if m:
        i = int(m.group(1))
        return i if 1 <= i <= n_candidates else None
    return None


def _png(pdf_path, page, bbox, dpi, pad):
    import pymupdf
    doc = pymupdf.open(pdf_path)
    pg = doc[page]
    x0, y0, x1, y1 = bbox
    clip = pymupdf.Rect(max(0, x0 - pad), max(0, y0 - pad * 0.4),
                        min(pg.rect.width, x1 + pad), min(pg.rect.height, y1 + pad * 0.4))
    pix = pg.get_pixmap(dpi=dpi, clip=clip)
    out = pix.tobytes("png")
    doc.close()
    return out


def _page_text(pdf_path, page, radius):
    """Context the model is allowed to see: the plain text of this page and up to
    `radius` pages either side. It is context for judging plausibility, never a
    source to copy from -- the answer format makes copying impossible."""
    import pymupdf
    doc = pymupdf.open(pdf_path)
    lo, hi = max(0, page - radius), min(doc.page_count - 1, page + radius)
    parts = []
    for p in range(lo, hi + 1):
        parts.append("--- page %d ---\n%s" % (p + 1, doc[p].get_text()[:6000]))
    doc.close()
    return "\n".join(parts)


def ask(model, key, img_png, prompt, timeout=120):
    body = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {
                    "url": "data:image/png;base64," + base64.b64encode(img_png).decode()}},
            ]},
        ],
        "max_tokens": 24,          # an index and nothing else needs no more room
        "temperature": 0,
    }
    req = urllib.request.Request(
        ENDPOINT, data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json", "Authorization": "Bearer " + key})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        j = json.loads(r.read().decode())
    return j["choices"][0]["message"]["content"]


def main(argv=None):
    ap = argparse.ArgumentParser(prog="scanquorum verify-ai")
    ap.add_argument("--pending", required=True, help="questions written by `scanquorum check --ui`")
    ap.add_argument("--pdf", help="override the source PDF path")
    ap.add_argument("--model", default="qwen/qwen3.8-vl-max")
    ap.add_argument("--out", default="ai_verdicts.json")
    ap.add_argument("--pages", type=int, default=1,
                    help="pages of surrounding text to show as context (0-2)")
    ap.add_argument("--dpi", type=int, default=700)
    ap.add_argument("--control-rate", type=float, default=0.2,
                    help="fraction of questions asked with the right answer removed")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--seed", type=int, default=17)
    a = ap.parse_args(argv)

    key = os.environ.get("OPENROUTER_API_KEY") or ""
    if not key:
        raise SystemExit("OPENROUTER_API_KEY is not set. Nothing was sent.")
    print("scanquorum verify_ai v%s | model %s | key present (%d chars, never printed)"
          % (VERSION, a.model, len(key)))

    items = json.loads(pathlib.Path(a.pending).read_text(encoding="utf-8"))
    if a.limit:
        items = items[:a.limit]
    rng = random.Random(a.seed)
    out, ctrl_total, ctrl_abstain, decided, abstained = {}, 0, 0, 0, 0

    for n, it in enumerate(items, 1):
        pdf = a.pdf or it.get("pdf")
        cands = list(it["candidates"])
        truth = it.get("current")
        is_ctrl = (rng.random() < a.control_rate and truth in cands and len(cands) > 1)
        if is_ctrl:
            cands = [c for c in cands if c != truth]
            ctrl_total += 1

        img = _png(pdf, it["page"], it["bbox"], a.dpi, 150)
        ctx = _page_text(pdf, it["page"], a.pages) if a.pages else ""
        lines = "\n".join("  %d. %s" % (i, c) for i, c in enumerate(cands, 1))
        prompt = (
            "Document: %s\nPage: %d\n\n"
            "The region inside the red box on the image is a single token.\n"
            "Readings proposed by the OCR engines:\n%s\n\n"
            "%sWhich numbered reading matches what is printed? Answer CHOICE: <n> or NONE."
            % (it.get("doc", "?"), it["page"] + 1, lines,
               ("Surrounding text for context only -- do not copy from it:\n%s\n\n" % ctx[:9000]) if ctx else "")
        )
        try:
            raw = ask(a.model, key, img, prompt)
        except Exception as e:
            print("  #%-4d request failed: %r" % (n, e))
            continue
        pick = _parse_choice(raw, len(cands))

        if is_ctrl:
            if pick is None:
                ctrl_abstain += 1
            print("  #%-4d [CONTROL] %s" % (n, "abstained (correct)" if pick is None
                                            else "CHOSE %r WITH NO RIGHT ANSWER PRESENT" % cands[pick - 1]))
            continue

        if pick is None:
            abstained += 1
            print("  #%-4d abstained -> stays for a human" % n)
            continue
        decided += 1
        out[it["key"]] = {
            "answer": cands[pick - 1],
            "when": datetime.datetime.now().isoformat(timespec="seconds"),
            "source": "vision model %s, chose among engine readings" % a.model,
            "doc": it.get("doc"), "page": it["page"], "bbox": it["bbox"],
            "candidates": cands,
        }
        print("  #%-4d -> %r" % (n, cands[pick - 1]))

    # 🔴 THE FILE MUST CARRY ITS OWN AUDIT RESULT. Found by an outside reviewer:
    # this file used to have an identical shape whether the negative controls ran or
    # not, so an operator who passed --control-rate 0 "to save tokens" produced
    # something downstream code would treat exactly like an audited result. The audit
    # belongs INSIDE the artefact, not only in terminal scrollback nobody keeps.
    rate = (100.0 * ctrl_abstain / ctrl_total) if ctrl_total else None
    audited = bool(ctrl_total) and rate >= 90
    doc = {
        "_audit": {
            "model": a.model,
            "controls_run": ctrl_total,
            "controls_abstained": ctrl_abstain,
            "abstention_rate_percent": None if rate is None else round(rate, 1),
            "audited": audited,
            "verdict": ("controls passed -- the model abstained when given no right answer"
                        if audited else
                        "NOT AUDITED -- no negative controls were run in this run"
                        if not ctrl_total else
                        "FAILED THE CONTROLS -- this model chose a reading when none was "
                        "correct; treat every verdict below as a suggestion for a human, "
                        "not as an answer"),
        },
        "verdicts": out,
    }
    pathlib.Path(a.out).write_text(json.dumps(doc, ensure_ascii=False, indent=1),
                                   encoding="utf-8", newline="\n")

    print("\n=== RESULT ===")
    print("  decided by the model : %d" % decided)
    print("  abstained            : %d  (these still need a human)" % abstained)
    if ctrl_total:
        rate = 100.0 * ctrl_abstain / ctrl_total
        print("  negative controls    : %d asked, %d abstained (%.0f %%)" % (ctrl_total, ctrl_abstain, rate))
        print("    ^ this is the number that decides whether to trust the run above.")
        if rate < 90:
            print("  🔴 THIS MODEL FAILS THE CONTROL. It picked a reading when none was correct")
            print("     in %.0f %% of controls. Its verdicts above are not safe to accept" % (100 - rate))
            print("     unattended -- treat them as suggestions for a human, not as answers.")
    else:
        print("  negative controls    : NONE RUN -- these verdicts are unaudited.")
    print("\n  written to %s" % a.out)
    print("  NOTE: this file is deliberately NOT the human verdict file. A person's")
    print("  answer outranks a model's, and the two must never be merged silently.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
