# Submission files

Submit Fruits360_CNN_Report.pdf and notebooks/Fruits360_Expanded_Experiments.ipynb. Word version is editable; the notebook contains executed saved-evidence displays, not a fabricated training transcript.

This final run covers all 131 classes in the pinned 2020 Fruits-360 snapshot: 54,163 train / 13,526 validation / 22,688 Test images. Three exact Training duplicates were removed. Eight epochs per configuration; all 12 attempted. Leaky ReLU / 0.1 diverged from epoch 6, is labelled N/A and is excluded from selection. The winner is Tanh / SGD 0.1. Test accuracy 93.23%; macro precision 94.06%; macro recall 92.81%; macro F1 92.74%.

The earlier four-class report and notebook are superseded for submission, but preserved as pilot artifacts. No app content is needed for this assignment.

The source dataset is downloaded separately as described in experiments/EXPANDED_README.md. Evidence includes actual per-epoch histories, validation metrics, labels and predictions, split hashes, trained models and provenance. Full confusion matrix figure and per-class CSV accompany the report.
