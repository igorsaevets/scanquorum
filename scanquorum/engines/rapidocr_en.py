# scanquorum/engines/rapidocr_en.py
"""RapidOCR (PP-OCR family) -- English-specialised v5 mobile recogniser. Faster, and wrong in different places, which is what a second voter is for.

    pip install rapidocr onnxruntime

CONFIGURATION IS NOT GUESSED. These parameter names and enum values are the ones
that actually ran in the measurement behind README.md. An earlier version of this
adapter invented plausible keys ("Global.lang_det") and every page failed with
`ValueError: ... is not a valid key` -- which the pipeline correctly reported as
an ABSENT ENGINE rather than as empty results, so the run degraded to one voter
and said so instead of quietly claiming a quorum.

Measured note kept from that work: PP-OCRv6 in this build has NO mobile tier at
all -- neither detector nor recogniser. Asking for one raises. When one branch of
a config turns out not to exist, check every branch of that family, not just the
one that broke.
"""
import numpy as np
import pymupdf
from rapidocr import RapidOCR, ModelType, OCRVersion, LangRec   # noqa: F401

_DET = {"Det.ocr_version": OCRVersion.PPOCRV6, "Det.model_type": ModelType.MEDIUM}
PARAMS = dict(_DET, **{"Rec.ocr_version": OCRVersion.PPOCRV5, "Rec.model_type": ModelType.MOBILE, "Rec.lang_type": LangRec.EN})

_ENGINE = None


def _engine():
    global _ENGINE
    if _ENGINE is None:
        _ENGINE = RapidOCR(params=dict(PARAMS))
    return _ENGINE


# This engine returns line-level boxes. See build.py for why it matters.
GRANULARITY = "line"


def run(pdf, dpi=300, progress=None):
    doc = pymupdf.open(pdf)
    eng = _engine()
    k = 72.0 / dpi
    out = {}
    for pi in range(doc.page_count):
        pm = doc[pi].get_pixmap(dpi=dpi)
        arr = np.frombuffer(pm.samples, dtype=np.uint8).reshape(pm.height, pm.width, pm.n)
        if pm.n >= 3:
            # RGB(A) -> BGR, to match what cv2 hands the model. Getting this
            # backwards does not crash; it quietly costs accuracy.
            arr = np.ascontiguousarray(arr[:, :, 2::-1])
        boxes = []
        res = eng(arr)
        if getattr(res, "txts", None):
            for box, txt, sc in zip(res.boxes, res.txts, res.scores):
                xs = [float(p[0]) for p in box]
                ys = [float(p[1]) for p in box]
                boxes.append({"t": str(txt), "s": round(float(sc), 4),
                              "b": [round(min(xs) * k, 2), round(min(ys) * k, 2),
                                    round(max(xs) * k, 2), round(max(ys) * k, 2)]})
        out[str(pi)] = {"boxes": boxes}
        if progress:
            progress(pi + 1, doc.page_count, "rapidocr_en")
    doc.close()
    return out
