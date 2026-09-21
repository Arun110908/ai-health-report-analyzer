# Accuracy update - what changed

## Bugs fixed (found by running the pipeline against ground truth)
1. `HbA1c` was never extracted (regex cut the name at "Hb", it was then de-duplicated as Hemoglobin).
2. `Vitamin B12` was read as value **12** (name cut at "Vitamin B") -> every report flagged B12 low.
3. Substring alias matching ("k" -> Potassium, "na" -> Sodium, "Mean Corpuscular Hemoglobin" -> Hemoglobin). Now exact / alias / token-safe fuzzy only, unknown names stay unknown.
4. Classification used a hard-coded table (male haemoglobin 13-17, cholesterol low=0) and ignored the range PRINTED on the report. Now printed range first, table only as fallback.
5. No unit handling: `6,500 cells/cumm`, `2.5 lakhs/cumm`, mmol/L, umol/L, g/L are now converted.
6. Pipe / spaced tables, H/L flag columns, "technology" columns, one-sided ranges (<200, >40), multi-band and sex-specific ranges are handled.
7. Non-result lines (Age, dates, page numbers, interpretation text) no longer become parameters.
8. OCR: grayscale + autocontrast + upscale + `--psm 6`; OCR confidence now reaches the report (warning when < 85%).
9. Generator produced negative lab values (-193 pg/mL) and its "4 formats" were one layout.
10. Docs said critical = 1.5x band, code used 0.5x. Docs now match the code.

## Files
Modified: backend/app/{reference_ranges,ocr_extraction,models,main}.py, backend/app/agents/agent1_report_processing.py,
          backend/scripts/generate_sample_reports.py, docs/ARCHITECTURE.md (md only - update the .docx yourself)
New:      backend/scripts/{evaluate,evaluate_ocr}.py, backend/tests_realistic/, backend/sample_data/ground_truth.json,
          docs/EVALUATION.md
Regenerated: backend/sample_data/*.txt, sample_io/*

## Measure your own accuracy
    cd backend
    python scripts/evaluate.py                          # synthetic
    python scripts/evaluate.py --dir tests_realistic    # hand-written realistic
    python scripts/evaluate_ocr.py --quality good|poor  # image + Tesseract
    python scripts/evaluate.py --dir my_real --truth my_real/ground_truth.json   # REAL reports you label
