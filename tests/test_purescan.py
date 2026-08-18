# tests/test_purescan.py  v1.0
#
# THE FAILURE THIS FILE EXISTS TO PREVENT. On a PDF with NO existing text
# layer, the pipeline in build.py used to iterate the voting loop over
# `pg.get_text("words") == []` and emit an .md with a valid YAML header and an
# empty body. Every OCR engine had already produced boxes for the page; nothing
# in the header said the emission was empty. Found on Igor's I-485 exhibit
# corpus on 2026-08-17: five of five SCAN documents in the pilot were affected,
# three of them still emitted 10-19 rows -- but only because a stamp had been
# added to the PDF layer by the packaging tool, so the "OCR output" was the
# stamp read three times, not the document read once.
#
# The fix is a separate emission path in build.py (`_emit_pure_scan_page`) that
# runs when `words == []` AND at least one engine produced boxes. This test
# builds a minimal pure-scan PDF from a PIL image (guaranteed no text layer),
# runs build(), and asserts:
#
#   1. the pipeline exits without raising
#   2. the .md exists and its BODY (past the YAML header) is non-empty
#   3. the header field `pure_scan_pages` is >= 1
#   4. at least two of the tokens rendered into the image appear in the body
#
# The last assertion is deliberately weak. It is not a scoring test: OCR
# accuracy is measured against goldset.json, and both RapidOCR configurations
# happily read a PIL-rendered TrueType page at the DPI used here. The point is
# to catch a REGRESSION where the .md returns to being empty on a pure scan,
# not to demand every glyph.
#
# Skips if pillow / rapidocr / onnxruntime are not installed. That is
# deliberate too: the CI 'replay' matrix does not install OCR engines (its
# whole design is that replay tests must run without them), so this test is a
# no-op in the parity suites and a real run only when the doctor's engine
# dependencies are present.
import io
import sys
import tempfile
import unittest
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def _make_pure_scan_pdf(text, out_path):
    """Build a one-page PDF whose only content is a rasterised image.

    Uses PIL to render `text` onto a white canvas, embeds the raster into a
    fresh PyMuPDF document, and saves. The saved file has NO text layer, i.e.
    `pg.get_text("words")` returns `[]` and `pg.get_text()` returns the empty
    string. That is what a scanner produces from paper, and it is what defeats
    a pipeline anchored to the PDF layer."""
    from PIL import Image, ImageDraw, ImageFont
    import pymupdf
    W, H = 1400, 900
    img = Image.new("RGB", (W, H), "white")
    d = ImageDraw.Draw(img)
    font = None
    for candidate in ("arial.ttf", "DejaVuSans.ttf", "LiberationSans-Regular.ttf"):
        try:
            font = ImageFont.truetype(candidate, 60)
            break
        except Exception:
            continue
    if font is None:
        font = ImageFont.load_default()
    y = 150
    for line in text.splitlines():
        d.text((100, y), line, fill="black", font=font)
        y += 110
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    doc = pymupdf.open()
    page = doc.new_page(width=W * 72 / 150, height=H * 72 / 150)
    page.insert_image(page.rect, stream=buf.getvalue())
    doc.save(str(out_path))
    doc.close()


class PureScan(unittest.TestCase):
    def _require(self, *modules):
        for m in modules:
            try:
                __import__(m)
            except ImportError:
                self.skipTest("%s not installed" % m)

    def test_build_emits_non_empty_md_and_reports_pure_scan(self):
        self._require("PIL", "pymupdf", "rapidocr", "onnxruntime")

        with tempfile.TemporaryDirectory() as td:
            td = pathlib.Path(td)
            pdf_path = td / "purescan_fixture.pdf"
            _make_pure_scan_pdf("SCANQUORUM 12-855\nHELLO WORLD 42\nSAMPLE LINE\n", pdf_path)

            import pymupdf
            doc = pymupdf.open(str(pdf_path))
            self.assertEqual(doc[0].get_text("words"), [],
                             "fixture is not a pure scan: get_text('words') is non-empty")
            doc.close()

            # RapidOCR is enough on its own for a regression test; not
            # requiring Tesseract keeps this test runnable on more machines,
            # and doctor already exercises the missing-engine path.
            from scanquorum.build import build
            hdr = build(str(pdf_path),
                        engines=("rapidocr_multi", "rapidocr_en"),
                        dpi=200, out_dir=str(td))

            md_path = td / "purescan_fixture.md"
            self.assertTrue(md_path.exists(), ".md was not written")
            md_text = md_path.read_text(encoding="utf-8")

            # There are TWO "---" lines in the file: the YAML header opens with
            # one at line 0 and closes with another before the body. Split
            # gives us [head_meta, warning_block, body].
            parts = md_text.split("\n---\n")
            self.assertGreaterEqual(len(parts), 2, "no YAML header separator found")
            body = parts[-1].strip()
            self.assertNotEqual(body, "",
                                "body is empty -- the pure-scan bug regressed. "
                                "Header was: %r" % md_text[:400])

            self.assertGreaterEqual(hdr.get("pure_scan_pages", 0), 1,
                                    "hdr['pure_scan_pages'] did not increment; "
                                    "either the pure-scan path did not fire, or "
                                    "the counter was not wired into the header")

            expect = ["SCANQUORUM", "12-855", "HELLO", "WORLD", "SAMPLE"]
            found = [t for t in expect if t in body]
            self.assertGreaterEqual(len(found), 2,
                                    "expected >=2 of %r in body, got %r. "
                                    "OCR may have failed at the fixture DPI or "
                                    "PIL font choice; check the render before "
                                    "declaring a regression." % (expect, found))


if __name__ == "__main__":
    unittest.main(verbosity=2)
