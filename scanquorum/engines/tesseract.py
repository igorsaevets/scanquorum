# scanquorum/engines/tesseract.py
"""Tesseract 5 through its own binary, in hOCR mode.

THE WEAKEST OF THE FOUR ENGINES AND THE MOST VALUABLE ADDITION -- because it is
the only one that draws its own text boxes. The two RapidOCR voters share a
detector (2,921 of 3,006 boxes byte-identical), so they are nearer one voice than
two. Independence beats accuracy in an ensemble: adding this engine moved the gold
set from 49/56 to 53/56, helping 4 times and hurting 0, and in one of those the
correct reading had been proposed by no other engine at all.

Needs the `tesseract` binary. Set TESSERACT_EXE, or have it on PATH. A portable
unpacked copy is fine -- nothing needs to be installed system-wide or touch the
registry. Language data is a separate download (`eng.traineddata`); if
TESSDATA_PREFIX is not set, the directory next to the binary is tried.

The page goes in on stdin and hOCR comes back on stdout: no temporary files, so
two runs in parallel cannot collide over the same scratch path.
"""
import os
import re
import html
import shutil
import subprocess
import pymupdf

EXE = os.environ.get("TESSERACT_EXE") or shutil.which("tesseract")
if not EXE or not os.path.exists(EXE):
    raise ImportError("tesseract binary not found; set TESSERACT_EXE or put it on PATH")

# Taken from real hOCR output, not from documentation. Note `x_wconf` for the word
# confidence -- an adapter written from memory used `x_conf` and matched nothing,
# while looking exactly like a parser that worked.
RE_WORD = re.compile(
    r"<span class='ocrx_word'[^>]*title='bbox (\d+) (\d+) (\d+) (\d+); x_wconf (\d+)'[^>]*>(.*?)</span>",
    re.S)
RE_TAG = re.compile(r"<[^>]+>")


# This engine returns word-level boxes. See build.py for why it matters.
GRANULARITY = "word"


def run(pdf, dpi=300, progress=None):
    env = dict(os.environ)
    env.setdefault("TESSDATA_PREFIX", os.path.join(os.path.dirname(EXE), "tessdata"))
    doc = pymupdf.open(pdf)
    k = 72.0 / dpi
    out = {}
    for pi in range(doc.page_count):
        png = doc[pi].get_pixmap(dpi=dpi).tobytes("png")
        p = subprocess.run([EXE, "stdin", "stdout", "--dpi", str(dpi), "-l", "eng",
                            "--psm", "3", "hocr"],
                           input=png, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env)
        if p.returncode != 0:
            raise RuntimeError("tesseract failed on page %d: %s"
                               % (pi, p.stderr.decode("utf-8", "replace")[-300:]))
        doc_h = p.stdout.decode("utf-8", "replace")
        boxes = []
        for m in RE_WORD.finditer(doc_h):
            x0, y0, x1, y1, conf = (int(g) for g in m.groups()[:5])
            t = html.unescape(RE_TAG.sub("", m.group(6))).strip()
            if t:
                boxes.append({"t": t, "s": conf / 100.0,
                              "b": [round(x0 * k, 2), round(y0 * k, 2),
                                    round(x1 * k, 2), round(y1 * k, 2)]})
        out[str(pi)] = {"boxes": boxes}
        if progress:
            progress(pi + 1, doc.page_count, "tesseract")
    doc.close()
    return out
