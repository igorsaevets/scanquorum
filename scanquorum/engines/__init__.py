"""Engine adapters. Each exposes run(pdf, dpi, progress) -> {page_str: {"boxes": [...]}}
where a box is {"t": text, "b": (x0,y0,x1,y1) in PDF points, "s": confidence or None}.

An adapter for an engine that is not installed must raise ImportError at import
time. It must never return empty results that look like a successful run -- a
silently absent voter turns a four-engine quorum into a three-engine one without
saying so, and the output would claim a confidence it does not have.
"""
