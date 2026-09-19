"""Serve the real, separately trained Fruits-360 subset classifier.

This module never substitutes fruit type for freshness or food safety.
"""
from __future__ import annotations
import json
import os
import threading
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
EXPERIMENT_DIR = ROOT / 'artifacts' / 'experiment'
_model = None
_model_signature = None
_lock = threading.Lock()


def experiment_summary(directory: Path | None = None) -> dict:
    directory = directory or EXPERIMENT_DIR
    path = directory / 'summary.json'
    if not path.is_file():
        return {'available': False, 'message': 'Experiment artifacts have not been generated yet.'}
    return {**json.loads(path.read_text(encoding='utf-8')), 'available': True}


def runtime_status() -> dict:
    from dotenv import dotenv_values
    local = dotenv_values(ROOT / '.env')
    key = os.environ.get('GEMINI_API_KEY') or local.get('GEMINI_API_KEY') or ''
    model_present = (ROOT / 'models' / 'mobilenet_fruit_model.keras').is_file()
    classification_ready = all((EXPERIMENT_DIR / f).is_file() for f in ['best_model.keras', 'class_names.json'])
    return {
        'ok': True,
        'model_present': model_present,
        'gemini_configured': bool(key.strip()) and key not in {'YOUR_API_KEY', 'replace-me'},
        'inspection_ready': model_present and bool(key.strip()) and key not in {'YOUR_API_KEY', 'replace-me'},
        'classification_ready': classification_ready,
        'model_loaded': _model is not None,
        'classification_scope': 'Fruits-360 subset fruit-type classification; not freshness or food safety.',
        'freshness_scope': 'Original six-class model missing' if not model_present else 'Apple, Banana and Orange fresh/rotten classification; requires Gemini validation',
    }


def classify_fruit_type(image: Image.Image, directory: Path | None = None) -> dict:
    global _model, _model_signature
    directory = directory or EXPERIMENT_DIR
    model_path, mapping_path = directory / 'best_model.keras', directory / 'class_names.json'
    if not model_path.is_file() or not mapping_path.is_file():
        raise RuntimeError('Fruit-type classification model is not available yet. Run the experiment pipeline first.')
    import numpy as np
    import tensorflow as tf
    signature = (str(model_path.resolve()), model_path.stat().st_mtime_ns)
    with _lock:
        if signature != _model_signature:
            _model = tf.keras.models.load_model(model_path, compile=False)
            _model_signature = signature
        names = json.loads(mapping_path.read_text(encoding='utf-8'))
        if not isinstance(names, list) or not names or any(not isinstance(n, str) for n in names):
            raise RuntimeError('Invalid class mapping; refusing inference.')
        shape = _model.input_shape
        prepared = image.convert('RGB').resize((int(shape[2]), int(shape[1])), Image.Resampling.BILINEAR)
        values = np.asarray(prepared, dtype=np.float32) / 255.0
        scores = np.asarray(_model(np.expand_dims(values, 0), training=False))[0]
        if len(scores) != len(names) or not np.all(np.isfinite(scores)):
            raise RuntimeError('Classifier output does not match its class mapping.')
        best = int(np.argmax(scores))
    return {
        'kind': 'classification', 'fruit_name': names[best], 'predicted_class': names[best],
        'confidence': float(scores[best] * 100), 'raw_vector': scores.astype(float).tolist(),
        'classes': names, 'source': 'local_cnn',
        'model_scope': 'Fruits-360 subset fruit-type classification. Closed-set model: it cannot reject unknown objects or assess freshness/food safety.',
    }
