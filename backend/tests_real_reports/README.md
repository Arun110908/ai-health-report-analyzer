Real Sterling Accuris pathology report (de-identified test patient, uploaded
during the September 2026 review). This is a hand-verified regression
snapshot, not an independently authored ground truth: every value below was
manually cross-checked against the source PDF's own printed Result column
during debugging (Hemoglobin 14.5, WBC 10570/cmm -> 10.57 x10^3/uL,
Triglyceride 168.0, HbA1c 7.10, Vitamin B12 <148, IgE 492.30, and more, all
confirmed). Its purpose is to catch future regressions on a real report
layout. Run: python scripts/evaluate.py --dir tests_real_reports
