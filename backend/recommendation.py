"""Recommendation data for FruitVision AI prediction classes."""


# Storage and safety guidance keyed by the exact model prediction labels.
RECOMMENDATIONS = {
    "Fresh Apple": {
        "temperature": "0–4°C",
        "humidity": "90–95%",
        "shelf_life": "2–4 weeks",
        "storage": "Refrigerator",
        "status": "Fresh",
        "advice": "Keep away from bananas to slow ripening.",
    },
    "Fresh Banana": {
        "temperature": "12–15°C",
        "humidity": "90–95%",
        "shelf_life": "2–7 days",
        "storage": "Room temperature until ripe",
        "status": "Fresh",
        "advice": "Refrigerate only after ripening.",
    },
    "Fresh Orange": {
        "temperature": "4–8°C",
        "humidity": "85–90%",
        "shelf_life": "2–3 weeks",
        "storage": "Refrigerator",
        "status": "Fresh",
        "advice": "Store in a ventilated container.",
    },
    "Rotten Apple": {
        "temperature": "N/A",
        "humidity": "N/A",
        "shelf_life": "Expired",
        "storage": "Do not store",
        "status": "Rotten",
        "advice": "Unsafe to consume. Dispose safely and keep away from healthy fruits.",
    },
    "Rotten Banana": {
        "temperature": "N/A",
        "humidity": "N/A",
        "shelf_life": "Expired",
        "storage": "Do not store",
        "status": "Rotten",
        "advice": "Unsafe to consume. Dispose safely and keep away from healthy fruits.",
    },
    "Rotten Orange": {
        "temperature": "N/A",
        "humidity": "N/A",
        "shelf_life": "Expired",
        "storage": "Do not store",
        "status": "Rotten",
        "advice": "Unsafe to consume. Dispose safely and keep away from healthy fruits.",
    },
}


def get_recommendation(predicted_class):
    """Return storage and safety recommendations for a predicted fruit class.

    Args:
        predicted_class: Exact class name returned by the prediction model.

    Returns:
        dict: Recommendation details for the class.

    Raises:
        ValueError: If the class name is not one of the supported predictions.
    """
    if not isinstance(predicted_class, str) or predicted_class not in RECOMMENDATIONS:
        valid_classes = ", ".join(RECOMMENDATIONS)
        raise ValueError(
            f"Invalid predicted class: {predicted_class!r}. "
            f"Expected one of: {valid_classes}."
        )

    return RECOMMENDATIONS[predicted_class]
