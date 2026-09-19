# Expanded Fruits-360 experiment report

`../Fruits360_CNN_Report.pdf` and `../Fruits360_CNN_Report.docx` are generated **only** from `artifacts/expanded/summary.json`. The generator rejects partial, duplicate, malformed, or inconsistent experiment evidence; it never trains a model and it never fills absent values.

## Build after expanded training

From the repository root:

```bash
.venv/bin/python scripts/build_expanded_submission.py
```

Expected evidence location and required companion inputs:

- `artifacts/expanded/summary.json` — the supplied expanded result schema.
- `artifacts/expanded/best_model.keras` and `artifacts/expanded/split_manifest.csv` — training provenance artifacts retained by the training run (the report uses the JSON evidence rather than loading model weights).
- `experiments/train_expanded.py` — referenced by the generated rerunnable notebook.

Outputs:

- `reports/expanded/Fruits360_CNN_Report.pdf` — 10–14 page experimental report.
- `reports/expanded/Fruits360_CNN_Report.docx` — editable equivalent.
- `reports/expanded/per_class_results.csv` — all per-class precision, recall, F1 and support.
- `reports/expanded/figures/` — evidence-derived validation, learning-curve and 131-class confusion-matrix figures.
- `notebooks/Fruits360_Expanded_Experiments.ipynb` — substantive evidence-reader notebook with opt-in rerun command.

Use alternate locations without changing source:

```bash
.venv/bin/python scripts/build_expanded_submission.py \
  --evidence /path/to/artifacts/expanded \
  --report-dir /path/to/reports/expanded \
  --notebook /path/to/Fruits360_Expanded_Experiments.ipynb
```

## Dependencies

The project virtual environment needs:

```bash
.venv/bin/pip install reportlab python-docx matplotlib numpy nbformat pypdf
```

`nbclient` and `ipykernel` are optional if you want to execute the generated notebook:

```bash
.venv/bin/pip install nbclient ipykernel
.venv/bin/jupyter nbconvert --to notebook --execute \
  --ExecutePreprocessor.timeout=600 \
  --output Fruits360_Expanded_Experiments.executed.ipynb \
  notebooks/Fruits360_Expanded_Experiments.ipynb
```

The executed notebook only loads saved results until its final, commented opt-in rerun cell is enabled. The report sources its only external background citations from the Fruits-360 repository and Muresan & Oltean (2018, arXiv:1712.00580); all metrics, curves, per-class values and matrix entries come from saved expanded evidence.

## Temporary smoke test

```bash
.venv/bin/python scripts/build_expanded_submission.py --smoke
```

This adapts the existing real four-class subset result **in a temporary directory only** to exercise the full generator. It does not create, overwrite, or label any expanded-training result in the repository.
