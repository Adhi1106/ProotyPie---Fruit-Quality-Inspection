# ProotyPie

Submission-ready fruit inspection coursework project with two clearly separated capabilities:

1. **Original freshness inspection flow** for Apple, Banana, and Orange only.
   - This path depends on the missing original trained model `models/mobilenet_fruit_model.keras` and an optional Gemini key.
   - In the current verified state, this path is **honestly reported as unavailable**.
2. **Fruits-360 CNN experiment submission flow** for fruit-type classification.
   - This path is fully implemented, trained, tested, documented, and exposed in the UI as **Fruit classification lab**.
   - It is explicitly labelled **fruit-type classification, not freshness or food-safety assessment**.

This repository now complies with the assignment by providing a reproducible CNN experiment that compares:
- activation functions: **ReLU, Sigmoid, Tanh, Leaky ReLU**
- learning rates: **0.001, 0.01, 0.1**
- optimizer: **SGD**
- evaluation: **accuracy, precision, recall, F1-score, training/validation curves, confusion matrix**

## Verified final state

- Python API tests: `6 passed`
- Frontend behavioral contract: passed
- Frontend production build: passed
- CNN experiment runs completed: **12/12**
- Best validation configuration: **Tanh + SGD lr=0.1**
- Held-out test metrics on the documented Fruits-360 subset:
  - accuracy: **1.0**
  - precision_macro: **1.0**
  - recall_macro: **1.0**
  - f1_macro: **1.0**
- API verification:
  - `GET /api/health` returns honest readiness state
  - `GET /api/experiments` returns experiment summary
  - `POST /api/classify` returns working local CNN predictions

## What changed

### Frontend
- Premium single-page dashboard rebuilt in `frontend/app/page.tsx`
- Accessible image upload and preview
- Honest runtime readiness banner using `/api/health`
- Separate **Fruit classification lab** mode using `/api/classify`
- JSON export and print-report affordances
- Same-origin API by default through Next rewrite
- Frontend contract test in `frontend/tests/frontend-behavior.mjs`

### Backend/API
- Added `backend/classification_service.py`
- Added `/api/classify` for the trained Fruits-360 subset classifier
- Added `/api/experiments` for report data exposure
- Upgraded `/api/health` to expose real readiness instead of a fake always-ok stub
- Storage advice now avoids implying freshness was assessed when it was not
- Image loading now rejects excessive pixel dimensions

### CNN experiment submission assets
- Reproducible training script: `experiments/run_fruits360_experiment.py`
- Experiment tests: `experiments/test_cnn_experiments.py`
- Notebook wrapper: `notebooks/Fruits360_CNN_Experiments.ipynb`
- Trained winner: `artifacts/experiment/best_model.keras`
- Class map: `artifacts/experiment/class_names.json`
- Full result summary: `artifacts/experiment/summary.json`
- Curves and confusion matrix under `artifacts/experiment/`

## Assignment alignment

The assignment asks for a CNN mini-project using a public dataset, comparing activations and learning rates, and evaluating convergence and classification quality.

This repo now satisfies that by using a **documented Fruits-360 subset**:
- Classes: `Apple Braeburn`, `Banana`, `Orange`, `Strawberry`
- Image size: `48 x 48 x 3`
- Samples used:
  - training: `320`
  - validation: `80`
  - held-out official test: `160`
- Source repository: `https://github.com/Horea94/Fruit-Images-Dataset`
- License reference: repository MIT license

## Important scope note

The submitted experiment is a **fruit-type classifier**. It does **not** detect freshness, spoilage, or food safety.

The original ProotyPie freshness workflow cannot be honestly claimed as working in this repository snapshot because the required trained file `models/mobilenet_fruit_model.keras` is not present. The UI and API now report that truthfully.

## Quick start

### 1) Python environment
```bash
python -m venv .venv
source .venv/bin/activate
pip install pillow numpy python-dotenv google-genai pytest tensorflow-cpu matplotlib scikit-learn
```

### 2) Frontend
```bash
cd frontend
npm install
npm run dev
```

### 3) Backend API
```bash
cd /path/to/ProotyPie
source .venv/bin/activate
python api/server.py
```

Backend default: `http://127.0.0.1:8000`

### 4) Re-run the experiment
```bash
source .venv/bin/activate
python experiments/run_fruits360_experiment.py --run
```

## Key files

```text
api/server.py
backend/classification_service.py
experiments/run_fruits360_experiment.py
experiments/test_cnn_experiments.py
notebooks/Fruits360_CNN_Experiments.ipynb
frontend/app/page.tsx
frontend/app/globals.css
frontend/lib/api.ts
frontend/tests/frontend-behavior.mjs
artifacts/experiment/summary.json
artifacts/experiment/validation_comparison.png
artifacts/experiment/test_confusion_matrix.png
reports/ProotyPie_Project_Report.md
reports/ProotyPie_Project_Report.docx
reports/ProotyPie_Project_Report.pdf
```

## Commands used for verification

```bash
.venv/bin/python -m pytest tests -q
node frontend/tests/frontend-behavior.mjs
cd frontend && npm run build
python experiments/run_fruits360_experiment.py --run
```

## Current limitations

- The experiment uses a **small documented subset**, not the full Fruits-360 dataset.
- The held-out test results are perfect on that subset, but that does not prove equal performance on broader real-world images.
- The original freshness model file is missing, so the freshness workflow is unavailable in this snapshot.
- Gemini-backed enhancement features require a valid `GEMINI_API_KEY`.

## Authoring notes for submission

If you present this project, describe it as:
- a **CNN activation-function comparison mini-project** using Fruits-360
- a **web interface that visualizes and serves the trained classifier**
- a project with **clear scope boundaries**, where fruit-type classification is kept separate from freshness claims
