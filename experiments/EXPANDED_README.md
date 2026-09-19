# Expanded experiment run

The expanded study uses the pinned 131-class Fruits-360 snapshot at `ffda2d14eada57a0c5537700190b309cfea2e120`.

## Execute

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
# Download the pinned upstream ZIP to the cache's source.zip first.
export FRUITS360_CACHE=/absolute/path/to/fruits360-131
python experiments/train_expanded.py --run --epochs 8
```

Source archive: https://codeload.github.com/Horea94/Fruit-Images-Dataset/zip/ffda2d14eada57a0c5537700190b309cfea2e120

The default cache location is `../../datasets/fruits360-131` relative to the project root. It is kept outside Git. Only Training, Test, readme.md and LICENSE are extracted. Exact-file duplicates are excluded and logged. The multiple-fruit detection folder is not part of single-label classification.

## Evidence

- `scope.json`: actual image counts and run settings.
- `split_manifest.csv`: source-relative file, label, SHA-256 and split.
- `run_*.json`: per-epoch histories and validation metrics, saved after each configuration.
- `model_*.keras`: configuration checkpoints.
- `partial_results.json`: completed configurations only.
- `summary.json`: produced only after all configurations and final test evaluation finish.
- `test_predictions.npz`: actual labels, predicted labels and class probability vectors.
- `progress.json`: current state, configuration and completed epoch.

The best configuration is selected by validation macro F1, with validation accuracy as tie-breaker. The saved training-only model is evaluated on the official Test set after selection. No test-based tuning or refitting is performed. The original four-class pilot and application model remain unchanged.

To resume, use the same scope, seed and epoch configuration. Do not change the epoch count or sample cap in an existing output directory. Delete/move the expanded output directory to conduct a new protocol instead.
