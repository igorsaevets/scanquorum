# Queued: a full survey of how everyone else solves this

**Status: not yet run.** To be sent to the multi-model orchestration once the current
backlog in [PLANNED.md](PLANNED.md) and [TO-TEST.md](TO-TEST.md) is cleared.

Recorded here rather than in a chat message because a task that lives only in a
conversation does not survive the conversation.

## The brief to send

Give every channel the full inlined source of this repository (the same packet used for
the 0.1.0 review — build it mechanically, do not summarise the code by hand), plus the
measured results and the defect catalogue. Then ask:

1. **Prior art, exhaustively.** Every open-source and commercial system that combines OCR
   engines rather than picking one. ROVER (Fiscus 1997) and its descendants; OCR-D;
   ocropus; Kraken; anything in the digital-humanities and archival world, where this
   problem is older than it is in legal tech. URLs and dates for everything.
2. **Alternatives we have not considered.** Character-level lattice combination instead of
   token voting; weighted voting by per-engine confidence calibration; CTC lattice
   intersection; layout-aware alignment; sequence models over the disagreement stream.
   For each: what it would cost to test here, and what result would kill it.
3. **The academic literature since 2020**, not just the classics. What is the current best
   published accuracy for multi-engine OCR combination, on what benchmark, and is that
   benchmark comparable to ours?
4. **Attack our measurement.** Given that our reference standard cannot see truncation by
   construction (ARTIFACTS.md B1), what is the standard way that class is measured
   elsewhere, and what would it cost us?
5. **What would you build differently**, given the same constraint — no language model in
   the transcription path?

## Rules for that round

- Every channel gets the same packet. Report separately what was accepted, what was
  rejected with proof, and where the channels contradicted each other.
- Demand URLs with dates. A survey citing no sources has surveyed nothing.
- Output should be a ranked list of things to TEST, each with the measurement that would
  settle it — not a list of things that sound promising.

## Lesson to carry into it, learned on the 0.1.0 round

Two of four channels could not fetch a URL: one had tool calling disabled, one hit a
permission its headless mode could not prompt for. **Inline the source in the brief from
the start.** The channel with no tools refused to review rather than reconstruct the code
from the brief's prose — the correct answer, and it cost a full round to discover.
