"""Run a reproducible Fruits-360 fruit-type CNN activation experiment.

This is intentionally a *fruit-type* classifier (Apple Braeburn, Banana,
Orange, Strawberry), not a fresh/rotten classifier.  Official Fruits-360
Training images are stratified into train/validation; official Test images
remain held out until the validation-selected winner is evaluated once.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import random
import shutil
import urllib.parse
import urllib.request
from collections import Counter
from pathlib import Path
from typing import Iterable

# Bound threads before TensorFlow import: shared/CI CPU environments otherwise
# can fail to allocate tf.data thread pools.
os.environ.setdefault("TF_NUM_INTRAOP_THREADS", "2")
os.environ.setdefault("TF_NUM_INTEROP_THREADS", "2")
os.environ.setdefault("OMP_NUM_THREADS", "2")
os.environ.setdefault("TF_DATA_PRIVATE_THREADPOOL_SIZE", "2")

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import tensorflow as tf
from PIL import Image
from sklearn.metrics import accuracy_score, confusion_matrix, precision_recall_fscore_support

ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = ROOT / "artifacts" / "experiment"
CACHE = ARTIFACTS / "data"
CLASSES = ["Apple Braeburn", "Banana", "Orange", "Strawberry"]
ACTIVATIONS = ["relu", "sigmoid", "tanh", "leaky_relu"]
LEARNING_RATES = [0.001, 0.01, 0.1]
SEED = 20260919
IMAGE_SIZE = 48
TRAIN_PER_CLASS = 100
TEST_PER_CLASS = 40
EPOCHS = 6
BATCH_SIZE = 16
REPO_API = "https://api.github.com/repos/Horea94/Fruit-Images-Dataset/contents"
RAW = "https://raw.githubusercontent.com/Horea94/Fruit-Images-Dataset/master"


def set_seed(seed: int = SEED) -> None:
    os.environ["PYTHONHASHSEED"] = str(seed)
    random.seed(seed)
    np.random.seed(seed)
    tf.keras.utils.set_random_seed(seed)
    try:
        tf.config.experimental.enable_op_determinism()
    except Exception:
        pass
    tf.config.threading.set_intra_op_parallelism_threads(2)
    tf.config.threading.set_inter_op_parallelism_threads(2)


def activation_layer(name: str) -> tf.keras.layers.Layer:
    if name == "relu":
        return tf.keras.layers.Activation("relu")
    if name == "sigmoid":
        return tf.keras.layers.Activation("sigmoid")
    if name == "tanh":
        return tf.keras.layers.Activation("tanh")
    if name == "leaky_relu":
        return tf.keras.layers.LeakyReLU(negative_slope=0.1)
    raise ValueError(f"Unsupported activation: {name}")


def split_train_validation(records: list[tuple[Path, str, str]], validation_fraction: float, seed: int) -> tuple[list[tuple[Path, str, str]], list[tuple[Path, str, str]]]:
    rng = random.Random(seed)
    grouped: dict[str, list[tuple[Path, str, str]]] = {}
    for record in records:
        grouped.setdefault(record[1], []).append(record)
    train, validation = [], []
    for label in sorted(grouped):
        items = grouped[label].copy()
        rng.shuffle(items)
        count = max(1, round(len(items) * validation_fraction))
        validation.extend(items[:count])
        train.extend(items[count:])
    return train, validation


def fetch_json(url: str):
    request = urllib.request.Request(url, headers={"User-Agent": "ProotyPie-coursework"})
    with urllib.request.urlopen(request, timeout=45) as response:
        return json.load(response)


def ensure_images(split: str, label: str, limit: int) -> list[Path]:
    destination = CACHE / split / label
    destination.mkdir(parents=True, exist_ok=True)
    present = sorted(destination.glob("*.jpg"))
    if len(present) >= limit:
        return present[:limit]
    api_path = f"{REPO_API}/{urllib.parse.quote(split)}/{urllib.parse.quote(label)}?ref=master"
    entries = fetch_json(api_path)
    files = sorted((entry for entry in entries if entry["name"].lower().endswith(".jpg")), key=lambda x: x["name"])[:limit]
    for entry in files:
        target = destination / entry["name"]
        if not target.exists():
            urllib.request.urlretrieve(entry["download_url"], target)
    return sorted(destination.glob("*.jpg"))[:limit]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 16), b""):
            digest.update(block)
    return digest.hexdigest()


def prepare_records() -> tuple[list[tuple[Path, str, str]], list[tuple[Path, str, str]]]:
    train_records, test_records = [], []
    for label in CLASSES:
        for path in ensure_images("Training", label, TRAIN_PER_CLASS):
            train_records.append((path, label, sha256(path)))
        for path in ensure_images("Test", label, TEST_PER_CLASS):
            test_records.append((path, label, sha256(path)))
    hashes = [x[2] for x in train_records + test_records]
    if len(hashes) != len(set(hashes)):
        raise RuntimeError("Identical SHA-256 image hashes found across or within splits; aborting.")
    return train_records, test_records


def load_arrays(records: Iterable[tuple[Path, str, str]], class_names: list[str]) -> tuple[np.ndarray, np.ndarray]:
    images, labels = [], []
    lookup = {name: idx for idx, name in enumerate(class_names)}
    for path, label, _ in records:
        with Image.open(path) as image:
            image = image.convert("RGB").resize((IMAGE_SIZE, IMAGE_SIZE))
            images.append(np.asarray(image, dtype=np.float32) / 255.0)
        labels.append(lookup[label])
    return np.asarray(images), np.asarray(labels, dtype=np.int64)


def make_model(activation: str, learning_rate: float) -> tf.keras.Model:
    inputs = tf.keras.Input(shape=(IMAGE_SIZE, IMAGE_SIZE, 3), name="image")
    x = tf.keras.layers.Conv2D(8, 3, padding="same")(inputs)
    x = activation_layer(activation)(x)
    x = tf.keras.layers.MaxPooling2D()(x)
    x = tf.keras.layers.Conv2D(16, 3, padding="same")(x)
    x = activation_layer(activation)(x)
    x = tf.keras.layers.GlobalAveragePooling2D()(x)
    outputs = tf.keras.layers.Dense(len(CLASSES), activation="softmax", name="fruit_type")(x)
    model = tf.keras.Model(inputs, outputs, name=f"fruits360_{activation}")
    model.compile(optimizer=tf.keras.optimizers.SGD(learning_rate=learning_rate), loss="sparse_categorical_crossentropy", metrics=["accuracy"])
    return model


def metric_dict(y_true: np.ndarray, probabilities: np.ndarray) -> dict[str, float]:
    predicted = probabilities.argmax(axis=1)
    precision, recall, f1, _ = precision_recall_fscore_support(y_true, predicted, average="macro", zero_division=0)
    return {"accuracy": float(accuracy_score(y_true, predicted)), "precision_macro": float(precision), "recall_macro": float(recall), "f1_macro": float(f1)}


def plot_history(history: dict, tag: str) -> dict[str, str]:
    paths = {}
    for metric, label in [("loss", "Loss"), ("accuracy", "Accuracy")]:
        plt.figure(figsize=(6, 4))
        plt.plot(history[metric], label="train")
        plt.plot(history[f"val_{metric}"], label="validation")
        plt.title(f"{tag}: {label}")
        plt.xlabel("epoch")
        plt.ylabel(label.lower())
        plt.legend()
        plt.tight_layout()
        path = ARTIFACTS / f"{tag}_{metric}.png"
        plt.savefig(path, dpi=160)
        plt.close()
        paths[metric] = path.name
    return paths


def plot_comparison(results: list[dict]) -> str:
    labels = [f"{r['activation']}\n{r['learning_rate']}" for r in results]
    scores = [r["validation_metrics"]["f1_macro"] for r in results]
    plt.figure(figsize=(12, 5))
    plt.bar(range(len(scores)), scores)
    plt.xticks(range(len(scores)), labels, rotation=45, ha="right")
    plt.ylabel("validation macro F1")
    plt.title("Validation-only activation / learning-rate comparison")
    plt.tight_layout()
    path = ARTIFACTS / "validation_comparison.png"
    plt.savefig(path, dpi=160)
    plt.close()
    return path.name


def plot_confusion(y_true: np.ndarray, probabilities: np.ndarray) -> str:
    matrix = confusion_matrix(y_true, probabilities.argmax(axis=1), labels=range(len(CLASSES)))
    fig, ax = plt.subplots(figsize=(6, 5))
    im = ax.imshow(matrix, cmap="Blues")
    fig.colorbar(im, ax=ax)
    ax.set(xticks=range(len(CLASSES)), yticks=range(len(CLASSES)), xticklabels=CLASSES, yticklabels=CLASSES, xlabel="Predicted fruit type", ylabel="True fruit type", title="Held-out official Test confusion matrix")
    plt.setp(ax.get_xticklabels(), rotation=35, ha="right")
    for i in range(len(CLASSES)):
        for j in range(len(CLASSES)):
            ax.text(j, i, matrix[i, j], ha="center", va="center")
    plt.tight_layout()
    path = ARTIFACTS / "test_confusion_matrix.png"
    plt.savefig(path, dpi=160)
    plt.close()
    return path.name


def run() -> dict:
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    set_seed()
    train_all, test_records = prepare_records()
    train_records, val_records = split_train_validation(train_all, 0.2, SEED)
    train_hashes, val_hashes, test_hashes = ({x[2] for x in z} for z in (train_records, val_records, test_records))
    if train_hashes & val_hashes or train_hashes & test_hashes or val_hashes & test_hashes:
        raise RuntimeError("Split hash overlap detected; aborting.")
    x_train, y_train = load_arrays(train_records, CLASSES)
    x_val, y_val = load_arrays(val_records, CLASSES)
    x_test, y_test = load_arrays(test_records, CLASSES)
    results = []
    for activation in ACTIVATIONS:
        for learning_rate in LEARNING_RATES:
            tf.keras.backend.clear_session()
            set_seed()  # Exact initial weights/configuration per experimental run.
            model = make_model(activation, learning_rate)
            history = model.fit(x_train, y_train, validation_data=(x_val, y_val), epochs=EPOCHS, batch_size=BATCH_SIZE, verbose=0).history
            validation = metric_dict(y_val, model.predict(x_val, verbose=0))
            tag = f"{activation}_lr{learning_rate:g}".replace(".", "p")
            result = {"activation": activation, "learning_rate": learning_rate, "epochs": EPOCHS, "validation_metrics": validation, "final_train_loss": float(history["loss"][-1]), "final_validation_loss": float(history["val_loss"][-1]), "final_train_accuracy": float(history["accuracy"][-1]), "final_validation_accuracy": float(history["val_accuracy"][-1]), "plots": plot_history(history, tag)}
            results.append(result)
            print(f"{activation:10s} lr={learning_rate:<5g} val_f1={validation['f1_macro']:.4f} val_acc={validation['accuracy']:.4f}", flush=True)
    best = max(results, key=lambda r: (r["validation_metrics"]["f1_macro"], r["validation_metrics"]["accuracy"]))
    # Refit only the selected configuration with train+validation. Test has not
    # influenced any selection and is evaluated exactly once afterwards.
    tf.keras.backend.clear_session()
    set_seed()
    winner = make_model(best["activation"], best["learning_rate"])
    winner.fit(np.concatenate([x_train, x_val]), np.concatenate([y_train, y_val]), epochs=EPOCHS, batch_size=BATCH_SIZE, verbose=0)
    test_probabilities = winner.predict(x_test, verbose=0)
    test_metrics = metric_dict(y_test, test_probabilities)
    winner.save(ARTIFACTS / "best_model.keras")
    (ARTIFACTS / "class_names.json").write_text(json.dumps(CLASSES, indent=2) + "\n")
    summary = {"scope": {"experiment_type": "fruit-type classification, not freshness/rottenness classification", "dataset_identity": "Fruits-360 official GitHub repository Horea94/Fruit-Images-Dataset (master)", "repository_url": "https://github.com/Horea94/Fruit-Images-Dataset", "license_url": "https://raw.githubusercontent.com/Horea94/Fruit-Images-Dataset/master/LICENSE", "license": "MIT License (repository LICENSE)", "classes": CLASSES, "image_shape": [IMAGE_SIZE, IMAGE_SIZE, 3], "training_samples": len(train_records), "validation_samples": len(val_records), "held_out_official_test_samples": len(test_records), "sampling": "first lexicographically ordered official JPGs: 100 Training and 40 Test per class", "deduplication": "SHA-256 checked across train/validation/official Test; no overlap", "seed": SEED, "optimizer": "SGD", "epochs": EPOCHS}, "best_config": {"activation": best["activation"], "learning_rate": best["learning_rate"], "selection_metric": "validation macro F1", "model_path": "best_model.keras", "class_names_path": "class_names.json", "input_shape": [None, IMAGE_SIZE, IMAGE_SIZE, 3]}, "test_metrics": test_metrics, "experiments": results, "plots": {"validation_comparison": plot_comparison(results), "test_confusion_matrix": plot_confusion(y_test, test_probabilities)}}
    (ARTIFACTS / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", action="store_true", help="download subset and execute all 12 training runs")
    args = parser.parse_args()
    if args.run:
        print(json.dumps(run()["best_config"], indent=2))
    else:
        parser.print_help()
