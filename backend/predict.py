from pathlib import Path

import numpy as np
import tensorflow as tf
from PIL import Image
from tensorflow.keras.applications.mobilenet_v2 import preprocess_input


# The model was trained to predict these classes in this exact order.
CLASS_NAMES = [
    "Fresh Apple",
    "Fresh Banana",
    "Fresh Orange",
    "Rotten Apple",
    "Rotten Banana",
    "Rotten Orange",
]

IMAGE_SIZE = (224, 224)
MODEL_PATH = Path(__file__).resolve().parent.parent / "models" / "mobilenet_fruit_model.keras"

# Cached model instance. This keeps TensorFlow from reloading the model on every prediction.
_prediction_model = None


def load_prediction_model():
    """Load and cache the trained Keras model for inference."""
    global _prediction_model

    if _prediction_model is not None:
        return _prediction_model

    try:
        if not MODEL_PATH.exists():
            raise FileNotFoundError(f"Model file not found: {MODEL_PATH}")

        _prediction_model = tf.keras.models.load_model(MODEL_PATH)
        return _prediction_model
    except Exception as exc:
        raise RuntimeError(f"Failed to load prediction model: {exc}") from exc


def preprocess_image(image):
    """Convert a PIL image into a MobileNetV2-ready input tensor."""
    try:
        if not isinstance(image, Image.Image):
            raise TypeError("preprocess_image expects a PIL.Image.Image instance.")

        # MobileNetV2 expects RGB images sized to 224x224.
        image = image.convert("RGB")
        image = image.resize(IMAGE_SIZE)

        # Convert to float32 and apply MobileNetV2 preprocessing.
        image_array = np.asarray(image, dtype=np.float32)
        image_array = preprocess_input(image_array)

        # Add the batch dimension: (1, 224, 224, 3).
        return np.expand_dims(image_array, axis=0)
    except Exception as exc:
        raise ValueError(f"Failed to preprocess image: {exc}") from exc


def predict_image(image):
    """Predict fruit quality from a PIL image.

    Returns:
        tuple: (predicted_class, confidence_percentage, raw_prediction_vector)
    """
    try:
        model = load_prediction_model()
        processed_image = preprocess_image(image)

        predictions = model.predict(processed_image, verbose=0)
        raw_prediction_vector = predictions[0].astype(float).tolist()

        if len(raw_prediction_vector) != len(CLASS_NAMES):
            raise ValueError(
                "Model output size does not match the configured class list. "
                f"Expected {len(CLASS_NAMES)}, got {len(raw_prediction_vector)}."
            )

        predicted_index = int(np.argmax(raw_prediction_vector))
        predicted_class = CLASS_NAMES[predicted_index]
        confidence_percentage = float(raw_prediction_vector[predicted_index] * 100.0)

        return predicted_class, confidence_percentage, raw_prediction_vector
    except Exception as exc:
        raise RuntimeError(f"Failed to predict image: {exc}") from exc
