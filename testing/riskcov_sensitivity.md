# Sensitivity analyses behind TESTED.md round 4

Console output of riskcov_sens.py v1.1 (lab tree), 2026-08-09. The script imports
riskcov.py, so the main measurement re-runs deterministically first; only the
sections S1-S5 below are additive. Referenced from testing/TESTED.md T12/T13.

```
================ riskcov_sens.py v1.1 ================

S1 -- lexicon ablation: every decision re-made with an EMPTY lexicon
  rule-census delta (no-lex minus with-lex): {"LEX": -109, "MEDOID_FLAG": 20, "DISPUTED": 89}
  gold crops whose correctness changed without the lexicon: [(11, 1, 0), (22, 1, 0), (34, 1, 0), (40, 1, 0)]
  policy                              coverage  accepted  acc      note
  VOTE4/4 only                          77.33%     23085  100.00%  gold 7/7
  VOTE>=3 +SEP/NUM                      95.29%     28446   99.38%  gold 38/39
  VOTE>=2 +SEP/NUM +LEX/PATTERN         97.24%     29028   99.39%  gold 47/48
  everything emitted (+flags)           98.63%     29445   99.26%  gold 48/50

S2 -- Tesseract WORD-level confidence baseline (the fair granularity)
  tokens with a tesseract reading+confidence: 29373 of 29853 (98.4%)
  tau       coverage  accepted  acc      gold
  0           98.39%     29373   84.56%  42/56
  0.5         91.87%     27426   86.01%  33/42
  0.7         86.50%     25822   86.73%  27/33
  0.8         82.98%     24773   98.38%  22/25
  0.85        80.63%     24069   99.21%  20/21
  0.9         76.80%     22928   99.20%  16/17
  0.93        69.83%     20846   99.19%  14/15
  0.95        58.68%     17518   98.85%  8/9
  0.97         0.25%        75    0.00%  0/0
  0.99         0.00%         0    0.00%  0/0

S2b -- PAIRED difference: ensemble policy minus tesseract@word-conf, same resamples
  VOTE4/4 only                   vs tess@0.85 (cov  80.6%): diff CI [+0.00, +2.68]
  VOTE4/4 only                   vs tess@0.90 (cov  76.8%): diff CI [+0.00, +2.72]
  VOTE4/4 only                   vs tess@0.95 (cov  58.7%): diff CI [+0.00, +4.48]
  VOTE>=3 +SEP/NUM               vs tess@0.85 (cov  80.6%): diff CI [+0.00, +0.84]
  VOTE>=3 +SEP/NUM               vs tess@0.90 (cov  76.8%): diff CI [+0.00, +0.87]
  VOTE>=3 +SEP/NUM               vs tess@0.95 (cov  58.7%): diff CI [+0.00, +2.60]
  VOTE>=2 +SEP/NUM +LEX/PATTERN  vs tess@0.85 (cov  80.6%): diff CI [+0.00, +0.87]
  VOTE>=2 +SEP/NUM +LEX/PATTERN  vs tess@0.90 (cov  76.8%): diff CI [+0.00, +0.90]
  VOTE>=2 +SEP/NUM +LEX/PATTERN  vs tess@0.95 (cov  58.7%): diff CI [+0.00, +2.63]
  everything emitted (+flags)    vs tess@0.85 (cov  80.6%): diff CI [-0.34, +0.69]
  everything emitted (+flags)    vs tess@0.90 (cov  76.8%): diff CI [-0.33, +0.71]
  everything emitted (+flags)    vs tess@0.95 (cov  58.7%): diff CI [-0.25, +2.55]

S3 -- the 4 BAD_BOX crops counted as ERRORS in their strata
  strata gain: [('СПОР', 2), ('VOTE2/3', 1), ('LEX', 1)]
  policy                              coverage  accepted  acc      note
  VOTE4/4 only                          77.33%     23085  100.00%  gold 7/7
  VOTE>=3 +SEP/NUM                      95.29%     28446   99.42%  gold 38/39
  VOTE>=2 +SEP/NUM +LEX/PATTERN         97.60%     29137   98.82%  gold 52/55
  everything emitted (+flags)           98.93%     29534   98.73%  gold 52/56

S4 -- correct-token YIELD (coverage x accuracy): what a policy actually delivers
  VOTE4/4 only                       coverage   77.33%  acc  100.00%  -> yield   77.33%
  VOTE4/4 only +SEP/NUM              coverage   87.97%  acc  100.00%  -> yield   87.97%
  VOTE4/4 only +LEX/PATTERN          coverage   77.71%  acc  100.00%  -> yield   77.71%
  VOTE4/4 only +SEP/NUM +LEX/PATTERN coverage   88.35%  acc  100.00%  -> yield   88.35%
  VOTE>=3                            coverage   84.64%  acc   99.30%  -> yield   84.05%
  VOTE>=3 +SEP/NUM                   coverage   95.29%  acc   99.38%  -> yield   94.69%
  VOTE>=3 +LEX/PATTERN               coverage   85.02%  acc   99.30%  -> yield   84.43%
  VOTE>=3 +SEP/NUM +LEX/PATTERN      coverage   95.67%  acc   99.38%  -> yield   95.07%
  VOTE>=2                            coverage   86.58%  acc   99.31%  -> yield   85.98%
  VOTE>=2 +SEP/NUM                   coverage   97.22%  acc   99.39%  -> yield   96.63%
  VOTE>=2 +LEX/PATTERN               coverage   86.96%  acc   99.32%  -> yield   86.36%
  VOTE>=2 +SEP/NUM +LEX/PATTERN      coverage   97.60%  acc   99.39%  -> yield   97.01%
  all present agree (VOTEk/k)        coverage   77.55%  acc  100.00%  -> yield   77.55%
  everything emitted (+flags)        coverage   98.93%  acc   99.27%  -> yield   98.21%

S5 -- crops per page (for the clustering caveat)
  56 scored crops on 30 distinct pages; crops-per-page histogram: {1: 12, 2: 12, 3: 4, 4: 2}

riskcov_sens.py v1.1 done.
```
