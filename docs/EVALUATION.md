# Evaluation results (updated September 2026 review)

> Synthetic/hand-written numbers are NOT a real-world accuracy claim. The real-report section is a single hand-verified PDF, not a statistical sample either -- treat it as "the known real-world bugs are fixed and verifiably don't regress", not as a population accuracy figure.

## A. Text input, synthetic `sample_data/` (25 reports)

```
Reports: 25   Expected values: 375   (SYNTHETIC data unless you passed real labelled reports)
Extraction recall (value found):        375/375 = 100.0%
Value correct (within 1%, std units):   375/375 = 100.0%
Status correct (low/normal/high):       375/375 = 100.0%
Abnormal recall  (flagged / truly abn): 42/42 = 100.0%
Abnormal precision (correct / flagged): 42/42 = 100.0%
Spurious / unmatched parameters:        0 of 375 extracted rows
Avg pipeline time (rule-based):         8 ms/report
Status confusions (truth -> predicted): none

Per layout   (expected / found / value-ok / status-ok)
  layout 0 (colon list): 90 / 90 / 90 / 90   -> status acc 100.0%
  layout 1 (spaced table): 105 / 105 / 105 / 105   -> status acc 100.0%
  layout 2 (pipe table + flags): 90 / 90 / 90 / 90   -> status acc 100.0%
  layout 3 (Indian-lab style): 90 / 90 / 90 / 90   -> status acc 100.0%
```

## B. Text input, hand-written realistic formats `tests_realistic/` (5 reports)

```
Reports: 5   Expected values: 54   (SYNTHETIC data unless you passed real labelled reports)
Extraction recall (value found):        54/54 = 100.0%
Value correct (within 1%, std units):   54/54 = 100.0%
Status correct (low/normal/high):       54/54 = 100.0%
Abnormal recall  (flagged / truly abn): 26/26 = 100.0%
Abnormal precision (correct / flagged): 26/26 = 100.0%
Spurious / unmatched parameters:        0 of 54 extracted rows
Avg pipeline time (rule-based):         11 ms/report
Status confusions (truth -> predicted): none

Per layout   (expected / found / value-ok / status-ok)
  layout 10 (?): 12 / 12 / 12 / 12   -> status acc 100.0%
  layout 11 (?): 13 / 13 / 13 / 13   -> status acc 100.0%
  layout 12 (?): 11 / 11 / 11 / 11   -> status acc 100.0%
  layout 13 (?): 11 / 11 / 11 / 11   -> status acc 100.0%
  layout 14 (?): 7 / 7 / 7 / 7   -> status acc 100.0%
```

## C. Real de-identified lab report `tests_real_reports/` (Sterling Accuris, 1 report, 60 values)

```
Reports: 1   Expected values: 60   (SYNTHETIC data unless you passed real labelled reports)
Extraction recall (value found):        60/60 = 100.0%
Value correct (within 1%, std units):   60/60 = 100.0%
Status correct (low/normal/high):       60/60 = 100.0%
Abnormal recall  (flagged / truly abn): 14/14 = 100.0%
Abnormal precision (correct / flagged): 14/14 = 100.0%
Spurious / unmatched parameters:        0 of 60 extracted rows
Avg pipeline time (rule-based):         220 ms/report
Status confusions (truth -> predicted): none

Per layout   (expected / found / value-ok / status-ok)
  layout 20 (?): 60 / 60 / 60 / 60   -> status acc 100.0%
```

## D. Image/OCR input (Tesseract, best-of-2 PSM race), poor blurry photo, sample_data

```
Extraction recall (value found):        301/375 = 80.3%
Value correct (within 1%, std units):   262/301 = 87.0%
Status correct (low/normal/high):       265/301 = 88.0%
```

## E. Image/OCR input (Tesseract, best-of-2 PSM race), good scan, sample_data

```
Extraction recall (value found):        359/375 = 95.7%
Value correct (within 1%, std units):   357/359 = 99.4%
Status correct (low/normal/high):       357/359 = 99.4%
```

Blurry-photo OCR now tries two Tesseract page-segmentation modes per image
and keeps whichever produces more parseable parameter rows (see
`app/ocr_extraction.py::extract_text_from_image` and `_score_ocr_text`),
instead of trusting one fixed config. A third mode is commented in that file
for anyone with CPU/time budget to spend on a further improvement.
