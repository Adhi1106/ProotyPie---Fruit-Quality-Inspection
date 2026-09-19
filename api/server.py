"""Thin HTTP adapter for the ProotyPie Next.js frontend.

This file intentionally imports the existing backend modules unchanged. It
does not alter prediction, Gemini validation, storage recommendation, or chat
logic; it only exposes those capabilities over local HTTP for the browser UI.
"""

from __future__ import annotations

import cgi
import json
import os
import re
import sys
import threading
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from io import BytesIO
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from PIL import Image, UnidentifiedImageError

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

EXPERIMENT_DIR = ROOT_DIR / "artifacts" / "experiment"


def runtime_status():
    from backend.classification_service import runtime_status as status
    return status()


def experiment_summary():
    from backend.classification_service import experiment_summary as summary
    return summary(EXPERIMENT_DIR)


def classify_fruit_type(image):
    from backend.classification_service import classify_fruit_type as classify
    return classify(image, EXPERIMENT_DIR)


HOST = "127.0.0.1"
PORT = 8000
MAX_UPLOAD_BYTES = 12 * 1024 * 1024
MAX_IMAGE_PIXELS = 25_000_000
SUPPORTED_MODEL_FRUITS = {"apple", "banana", "orange"}
FAST_SUPPORTED_CONFIDENCE = float(os.getenv("PROOTYPIE_FAST_SUPPORTED_CONFIDENCE", "70"))
_gemini_service = None
_prediction_service = None

_LOCAL_RECOMMENDATIONS = {
    ("apple", "fresh"): {
        "temperature": "32F - 36F",
        "humidity": "90% - 95%",
        "shelf_life": "3-4 weeks refrigerated",
        "storage": "Crisper drawer",
        "advice": "Keep apples cold and away from ethylene-sensitive produce to slow softening.",
        "ripening_advice": "Leave at room temperature briefly only if you want it to soften faster.",
        "nutrition_highlights": "Fiber, vitamin C, polyphenols",
        "market_recommendation": "Best marketed within 7 days for peak quality.",
    },
    ("apple", "rotten"): {
        "temperature": "32F - 36F",
        "humidity": "90% - 95%",
        "shelf_life": "Expired - discard immediately",
        "storage": "Store future apples cold in a ventilated crisper drawer",
        "advice": "Do not consume rotten apple tissue. Remove spoiled fruit from nearby produce to slow spread.",
        "ripening_advice": "",
        "nutrition_highlights": "Not safe to consume when rotten",
        "market_recommendation": "Sell at least 5 days before full spoilage to maximise value.",
    },
    ("banana", "fresh"): {
        "temperature": "56F - 60F",
        "humidity": "85% - 90%",
        "shelf_life": "2-5 days at room temperature",
        "storage": "Countertop, away from direct heat",
        "advice": "Keep bananas separated from other fruit if you want slower ripening.",
        "ripening_advice": "Place in a paper bag to ripen faster.",
        "nutrition_highlights": "Potassium, vitamin B6, quick carbohydrates",
        "market_recommendation": "Best marketed within 2-3 days for peak quality.",
    },
    ("banana", "rotten"): {
        "temperature": "56F - 60F",
        "humidity": "85% - 90%",
        "shelf_life": "Expired - discard immediately",
        "storage": "Store future bananas cool, dry, and away from ethylene-heavy produce",
        "advice": "Discard rotten bananas and clean the storage surface before placing fresh produce there.",
        "ripening_advice": "",
        "nutrition_highlights": "Not safe to consume when rotten",
        "market_recommendation": "Sell at least 2 days before full spoilage to maximise value.",
    },
    ("orange", "fresh"): {
        "temperature": "38F - 48F",
        "humidity": "85% - 90%",
        "shelf_life": "1-2 weeks refrigerated",
        "storage": "Ventilated fridge drawer",
        "advice": "Keep oranges dry and ventilated; trapped moisture encourages mold.",
        "ripening_advice": "",
        "nutrition_highlights": "Vitamin C, folate, citrus flavonoids",
        "market_recommendation": "Best marketed within 5-7 days for peak quality.",
    },
    ("orange", "rotten"): {
        "temperature": "38F - 48F",
        "humidity": "85% - 90%",
        "shelf_life": "Expired - discard immediately",
        "storage": "Store future oranges in a dry, ventilated fridge drawer",
        "advice": "Discard moldy or rotten oranges and separate nearby citrus immediately.",
        "ripening_advice": "",
        "nutrition_highlights": "Not safe to consume when rotten",
        "market_recommendation": "Sell at least 4 days before full spoilage to maximise value.",
    },
}


class NotFruitError(Exception):
    """Raised when Gemini says the uploaded image is not a fruit."""


def get_gemini_service():
    """Import and cache the existing Gemini service lazily."""
    global _gemini_service
    if _gemini_service is None:
        import backend.gemini_service as gemini_service

        _gemini_service = gemini_service
    return _gemini_service


def get_prediction_service():
    """Import and cache the existing TensorFlow prediction service lazily."""
    global _prediction_service
    if _prediction_service is None:
        import backend.predict as prediction_service

        _prediction_service = prediction_service
    return _prediction_service


def clean_text(value) -> str:
    """Return compact plain text."""
    text = str(value or "")
    text = re.sub(r"\*{1,2}([^*]+)\*{1,2}", r"\1", text)
    text = re.sub(r"<[^>]+>", "", text)
    return re.sub(r"\s{2,}", " ", text).strip()


def coerce_bool(value, default: bool = False) -> bool:
    """Convert booleans safely when model JSON returns strings."""
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"true", "yes", "y", "1"}:
            return True
        if normalized in {"false", "no", "n", "0", ""}:
            return False
    return default


def split_prediction_label(predicted_class: str) -> tuple[str, str]:
    """Split labels such as 'Fresh Apple' into status and fruit."""
    parts = predicted_class.split(" ", 1)
    if len(parts) == 2 and parts[0] in {"Fresh", "Rotten"}:
        return parts[0], parts[1]
    return "Unknown", predicted_class


def is_temporary_gemini_error(exc: Exception) -> bool:
    """Return True when Gemini is busy/networking rather than the app being broken."""
    text = str(exc).lower()
    return any(
        marker in text
        for marker in (
            "temporarily busy",
            "temporary",
            "503",
            "unavailable",
            "high demand",
            "overloaded",
            "timeout",
        )
    )


def local_recommendation(fruit_name: str, freshness_status: str | None) -> dict:
    """Return a deterministic recommendation when Gemini storage is unavailable."""
    fruit_key = clean_text(fruit_name).lower()
    status_key = clean_text(freshness_status or "fresh").lower()
    recommendation = _LOCAL_RECOMMENDATIONS.get((fruit_key, status_key))
    if recommendation is None:
        recommendation = {
            "temperature": "Cool, dry conditions",
            "humidity": "Moderate humidity",
            "shelf_life": "Varies by ripeness and handling",
            "storage": "Keep ventilated and away from direct sunlight",
            "advice": f"Gemini storage guidance is temporarily unavailable. Keep {fruit_name} cool, dry, and separate from spoiled produce.",
            "ripening_advice": "",
            "nutrition_highlights": "Fruit-specific nutrition varies by variety",
            "market_recommendation": "Market soon after harvest for best quality.",
        }
    status = freshness_status or "Unknown"
    if freshness_status is None:
        recommendation = {
            **recommendation,
            "shelf_life": "Freshness not assessed; storage duration is only a general reference.",
            "advice": "Fruit type alone cannot determine freshness or food safety. Inspect smell, texture, damage, and mold before use.",
        }
    if status_key == "rotten":
        return {
            **recommendation,
            "status": "Rotten",
            "spoilage_signs": "Possible soft spots, leaking, discoloration, mold growth, or sour fermented smell.",
            "possible_causes": "Likely caused by age, bruising, trapped moisture, heat exposure, or mold transfer from nearby produce.",
            "safe_use": "Do not eat rotten fruit. If rot is widespread, there is no safe use left.",
            "disposal": "Seal it in a small bag and place it in compost or trash, then clean the storage surface.",
            "prevention": recommendation.get("advice") or "Store future fruit cool, dry, ventilated, and separate from spoiled produce.",
            "shelf_life": "Expired - discard immediately",
        }

    return {
        **recommendation,
        "status": status,
        "storage_temperature": recommendation.get("temperature", "N/A"),
        "storage_space": recommendation.get("storage", "N/A"),
        "market_sale": recommendation.get("market_recommendation", "N/A"),
        "longevity_tip": recommendation.get("advice", ""),
        "nutrition": recommendation.get("nutrition_highlights", ""),
    }


def unsupported_produce_message(produce_name: str) -> str:
    """Return app copy for produce outside the demo model classes."""
    name = clean_text(produce_name) or "this produce"
    return (
        f"Gemini sees this as {name}. ProotyPie can identify it, but the freshness "
        "model is trained for Apple, Banana, and Orange right now. Upload one of "
        "those three for a real freshness score."
    )


def non_produce_message(object_label: str, gemini_message: str | None = None) -> str:
    """Return a playful non-produce message without breaking the API shape."""
    message = clean_text(gemini_message)
    if message:
        return message

    label = clean_text(object_label)
    if label and label.lower() not in {"unknown", "object", "image"}:
        return (
            f"Bold choice: that looks like {label}, not produce. Please upload a "
            "fruit image before ProotyPie starts judging your shopping list."
        )
    return (
        "Bold choice, but that is not giving fruit. Please upload Apple, Banana, "
        "or Orange so ProotyPie can do its actual job."
    )


def is_supported_model_prediction(predicted_class: str, confidence: float) -> bool:
    """Return True when the local model result is demo-safe to show immediately."""
    freshness_status, fruit_name = split_prediction_label(predicted_class)
    return (
        freshness_status in {"Fresh", "Rotten"}
        and fruit_name.lower() in SUPPORTED_MODEL_FRUITS
        and confidence >= FAST_SUPPORTED_CONFIDENCE
    )


def supported_result_from_prediction(
    predicted_class: str,
    confidence: float,
    raw_vector: list,
    detected_fruit: str | None = None,
) -> dict:
    """Build the supported-fruit API response from TensorFlow output."""
    freshness_status, predicted_fruit = split_prediction_label(predicted_class)
    return {
        "kind": "supported",
        "fruit_name": predicted_fruit,
        "detected_fruit": detected_fruit or predicted_fruit,
        "freshness_status": freshness_status,
        "predicted_class": predicted_class,
        "confidence": float(confidence),
        "raw_vector": raw_vector,
        "recommendation": local_recommendation(predicted_fruit, freshness_status),
        "recommendation_source": "local",
        "storage_pending": True,
    }


_FRUIT_CHAT_KNOWLEDGE = {
    "mango": {
        "benefits": "Mango is good for vitamin C, vitamin A, antioxidants, and quick natural energy. It also supports immune health and can be great in smoothies, yogurt bowls, or salads.",
        "storage": "Keep unripe mangoes at room temperature. Once ripe, refrigerate them and use within about 3-5 days.",
        "ripeness": "A ripe mango gives slightly when pressed and smells sweet near the stem. Color alone is not a reliable ripeness signal.",
    },
    "apple": {
        "benefits": "Apples are good for fiber, hydration, vitamin C, and steady snacking. The peel has many of the useful polyphenols, so keep it on when possible.",
        "recipes": "Try apple cinnamon oats, apple peanut-butter toast, apple walnut salad, or baked apple slices with yogurt.",
        "calories": "A medium apple has about 95 calories, mostly from natural carbohydrates plus useful fiber.",
        "desserts": "Apple crumble, baked cinnamon apples, apple tart, and apple yogurt parfaits are easy dessert options.",
        "storage": "Store apples in the fridge crisper drawer for best shelf life. Keep them away from ethylene-sensitive produce.",
        "ripeness": "A good apple should feel firm and smell fresh. Soft spots, wrinkling, or fermented odor are warning signs.",
    },
    "banana": {
        "benefits": "Bananas are good for potassium, vitamin B6, quick energy, and gentle digestion. They are especially useful before workouts or in smoothies.",
        "recipes": "Use banana in smoothies, banana oats, peanut-butter banana toast, pancakes, or a yogurt bowl.",
        "calories": "A medium banana has about 105 calories and gives quick energy with potassium and vitamin B6.",
        "desserts": "Banana bread, frozen banana bites, banana pudding, and caramelized banana with yogurt work beautifully.",
        "storage": "Keep bananas at room temperature until ripe. Refrigeration darkens the peel but slows the fruit inside from over-ripening.",
        "ripeness": "Green bananas are firmer and less sweet. Yellow bananas with small brown speckles are usually sweet and ready to eat.",
    },
    "orange": {
        "benefits": "Oranges are good for vitamin C, hydration, folate, and citrus flavonoids. They are a strong everyday immune-support fruit.",
        "recipes": "Try orange segments in salads, orange mint yogurt bowls, citrus salsa, or orange juice blended into smoothies.",
        "calories": "A medium orange has about 60 to 65 calories and is rich in vitamin C and hydration.",
        "desserts": "Orange sorbet, chocolate-dipped orange slices, orange cake, and citrus parfaits are good dessert picks.",
        "storage": "Store oranges in a cool ventilated place, or refrigerate them for longer shelf life. Keep them dry to reduce mold.",
        "ripeness": "A good orange feels heavy for its size and has a clean citrus smell. Soft wet patches or mold mean discard it.",
    },
    "strawberry": {
        "benefits": "Strawberries are good for vitamin C, antioxidants, and light hydration. They are best eaten soon after purchase.",
        "storage": "Refrigerate strawberries unwashed in a breathable container. Wash only right before eating.",
        "ripeness": "Ripe strawberries are bright, fragrant, and firm. Mushy texture or fuzzy patches mean they should be discarded.",
    },
    "blueberry": {
        "benefits": "Blueberries are good for anthocyanin antioxidants, fiber, and vitamin C. They are a great low-mess snack fruit.",
        "storage": "Refrigerate blueberries dry and wash them right before eating. Remove any spoiled berries quickly.",
        "ripeness": "Good blueberries look plump and deep blue with a light natural bloom. Shriveled or leaking berries are past peak.",
    },
    "pomegranate": {
        "benefits": "Pomegranate is good for antioxidants, polyphenols, potassium, and a bright tart-sweet flavor. The arils are great over yogurt or salads.",
        "storage": "Whole pomegranates keep well in the fridge. Store opened arils in an airtight container and use within a few days.",
        "ripeness": "A ripe pomegranate feels heavy for its size and has firm, angular skin. Avoid fruit with soft sunken patches.",
    },
}


def quick_chat_reply(messages: list) -> str:
    """Return a fast fruit-only assistant reply without using Gemini."""
    user_text = ""
    for message in reversed(messages):
        if message.get("role") == "user":
            user_text = clean_text(message.get("content", ""))
            break

    if not user_text:
        return "Ask me about a fruit, storage, ripeness, freshness, or nutrition and I will help."

    text = user_text.lower()
    outside_markers = ("code", "python", "politics", "movie", "cricket", "football", "stock", "crypto")
    fruit_markers = tuple(_FRUIT_CHAT_KNOWLEDGE.keys()) + (
        "fruit",
        "storage",
        "fresh",
        "rotten",
        "ripe",
        "ripen",
        "nutrition",
        "shelf",
        "safe",
        "eat",
        "smoothie",
    )
    if any(marker in text for marker in outside_markers) and not any(marker in text for marker in fruit_markers):
        return "That is outside my fruit lane. Ask me about storage, ripeness, nutrition, freshness, or fruit safety."

    fruit_name = next((fruit for fruit in _FRUIT_CHAT_KNOWLEDGE if fruit in text), "")
    topic = "benefits"
    if any(word in text for word in ("recipe", "recipes", "healthy recipe", "meal", "cook", "ideas")):
        topic = "recipes"
    elif any(word in text for word in ("calorie", "calories", "kcal", "energy")):
        topic = "calories"
    elif any(word in text for word in ("dessert", "desserts", "sweet", "treat")):
        topic = "desserts"
    elif any(word in text for word in ("store", "storage", "fridge", "keep", "shelf")):
        topic = "storage"
    elif any(word in text for word in ("ripe", "ripen", "ready", "good to eat", "fresh", "rotten")):
        topic = "ripeness"

    if fruit_name:
        return _FRUIT_CHAT_KNOWLEDGE[fruit_name].get(topic) or _FRUIT_CHAT_KNOWLEDGE[fruit_name]["benefits"]

    if topic == "storage":
        return "For most fruit, keep it cool, dry, and ventilated. Refrigerate ripe fruit, keep moisture low, and remove spoiled pieces quickly so they do not affect the rest."
    if topic == "ripeness":
        return "Check firmness, smell, and surface condition. Fresh fruit should smell clean, feel appropriate for its type, and have no wet moldy patches or fermented odor."
    if topic == "recipes":
        return "For healthy fruit recipes, try smoothies, yogurt bowls, salads, overnight oats, or toast toppings. Tell me the fruit name and I can make it more specific."
    if topic == "calories":
        return "Calories vary by fruit and size. Tell me the fruit name and portion size, and I can give a cleaner estimate."
    if topic == "desserts":
        return "For fruit desserts, think baked fruit, parfaits, sorbets, crumbles, or chocolate-dipped slices. Tell me the fruit name for better ideas."
    return "Fruit is best judged by firmness, smell, color consistency, and surface condition. Tell me the fruit name and I can give a more specific answer."


def get_storage_safely(fruit_name: str, freshness_status: str | None) -> dict:
    """Use Gemini storage guidance, falling back locally if Gemini is busy."""
    try:
        return get_gemini_service().get_storage_analysis(
            fruit_name,
            freshness_status=freshness_status,
        )
    except Exception as exc:
        if not is_temporary_gemini_error(exc):
            raise
        return local_recommendation(fruit_name, freshness_status)


def load_image(raw: bytes) -> Image.Image:
    """Decode uploaded image bytes as a detached PIL image."""
    try:
        image = Image.open(BytesIO(raw))
        if image.width * image.height > MAX_IMAGE_PIXELS:
            raise ValueError("Image dimensions are too large. Please use an image under 25 megapixels.")
        image.load()
        return image.copy()
    except UnidentifiedImageError as exc:
        raise ValueError("The uploaded file is not a valid image.") from exc


def run_inspection(image: Image.Image) -> dict:
    """Run the existing Gemini + TensorFlow inspection flow."""
    gemini_service = get_gemini_service()
    prediction_error: Exception | None = None
    predicted_class = ""
    confidence = 0.0
    raw_vector = []

    try:
        predicted_class, confidence, raw_vector = get_prediction_service().predict_image(image)
    except Exception as exc:
        prediction_error = exc

    try:
        vision = gemini_service.validate_image(image)
    except Exception as exc:
        if is_temporary_gemini_error(exc):
            raise RuntimeError(
                "Gemini validation is temporarily unavailable. Try again in a moment; "
                "I won't guess unsupported produce as Apple, Banana, or Orange."
            ) from exc
        raise

    is_produce = coerce_bool(vision.get("is_fruit"), False)
    is_supported = coerce_bool(vision.get("is_supported"), False)

    if not is_produce:
        message = non_produce_message(
            vision.get("object_label") or vision.get("fruit_name") or "",
            vision.get("fun_message"),
        )
        raise NotFruitError(message)

    fruit_name = clean_text(vision.get("fruit_name") or "Unknown fruit")

    if not is_supported:
        return {
            "kind": "unsupported",
            "fruit_name": fruit_name,
            "message": unsupported_produce_message(fruit_name),
        }

    if not predicted_class:
        if prediction_error is not None:
            raise prediction_error
    return supported_result_from_prediction(
        predicted_class,
        confidence,
        raw_vector,
        detected_fruit=fruit_name,
    )


class ProotyPieHandler(BaseHTTPRequestHandler):
    """Local API handler for the Next.js app."""

    server_version = "ProotyPieAPI/1.0"

    def _set_headers(self, status: HTTPStatus = HTTPStatus.OK) -> None:
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def _json(self, payload: dict, status: HTTPStatus = HTTPStatus.OK) -> None:
        self._set_headers(status)
        self.wfile.write(json.dumps(payload).encode("utf-8"))

    def do_OPTIONS(self) -> None:  # noqa: N802 - stdlib hook name
        self._set_headers()

    def do_GET(self) -> None:  # noqa: N802 - stdlib hook name
        parsed = urlparse(self.path)
        if parsed.path == "/api/health":
            self._json(runtime_status())
            return

        if parsed.path == "/api/experiments":
            self._json(experiment_summary())
            return

        if parsed.path == "/api/spotlight":
            query = parse_qs(parsed.query)
            fruit = clean_text(query.get("fruit", ["Pomegranate"])[0]) or "Pomegranate"
            fact = get_gemini_service().get_spotlight_fact(fruit)
            self._json({"fruit": fruit, "fact": fact})
            return

        self._json({"error": "Not found"}, HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:  # noqa: N802 - stdlib hook name
        parsed = urlparse(self.path)
        try:
            if parsed.path in {"/api/inspect", "/api/classify"}:
                self._handle_inspect(classification=parsed.path == "/api/classify")
                return
            if parsed.path == "/api/chat":
                self._handle_chat()
                return
            if parsed.path == "/api/storage":
                self._handle_storage()
                return
            self._json({"error": "Not found"}, HTTPStatus.NOT_FOUND)
        except NotFruitError as exc:
            self._json({"kind": "non_fruit", "message": str(exc)})
        except ValueError as exc:
            self._json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)
        except Exception as exc:
            self._json({"error": str(exc)}, HTTPStatus.INTERNAL_SERVER_ERROR)

    def _handle_inspect(self, classification: bool = False) -> None:
        content_length = int(self.headers.get("Content-Length", "0"))
        if content_length <= 0:
            raise ValueError("No upload received.")
        if content_length > MAX_UPLOAD_BYTES:
            raise ValueError("Image upload is too large. Please use an image under 12 MB.")

        form = cgi.FieldStorage(
            fp=self.rfile,
            headers=self.headers,
            environ={
                "REQUEST_METHOD": "POST",
                "CONTENT_TYPE": self.headers.get("Content-Type", ""),
                "CONTENT_LENGTH": str(content_length),
            },
        )
        field = form["image"] if "image" in form else None
        if field is None or not getattr(field, "file", None):
            raise ValueError("Upload field 'image' is required.")

        raw = field.file.read()
        image = load_image(raw)
        self._json(classify_fruit_type(image) if classification else run_inspection(image))

    def _handle_chat(self) -> None:
        content_length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(content_length)
        data = json.loads(raw.decode("utf-8") or "{}")
        messages = data.get("messages", [])
        if not isinstance(messages, list):
            raise ValueError("'messages' must be a list.")

        mode = clean_text(data.get("mode") or os.getenv("PROOTYPIE_CHAT_MODE", "fast")).lower()
        if mode in {"fast", "local", "demo"}:
            self._json({"reply": quick_chat_reply(messages), "source": "local"})
            return

        reply = get_gemini_service().chat_with_assistant(messages)
        self._json({"reply": reply, "source": "gemini"})

    def _handle_storage(self) -> None:
        content_length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(content_length)
        data = json.loads(raw.decode("utf-8") or "{}")
        fruit_name = clean_text(data.get("fruit_name") or "")
        freshness_status = clean_text(data.get("freshness_status") or "") or None
        if not fruit_name:
            raise ValueError("'fruit_name' is required.")
        recommendation = get_storage_safely(fruit_name, freshness_status)
        self._json({"recommendation": recommendation})

    def log_message(self, format: str, *args) -> None:
        """Keep local API logs compact."""
        sys.stderr.write("[api] " + (format % args) + "\n")


def warm_prediction_model() -> None:
    """Load the TensorFlow model in the background for faster first inspection."""
    try:
        get_prediction_service().load_prediction_model()
        sys.stderr.write("[api] TensorFlow model warmed.\n")
    except Exception as exc:
        sys.stderr.write(f"[api] TensorFlow warm-up skipped: {exc}\n")


def main() -> None:
    """Start the local API server."""
    port = int(os.getenv("PORT", str(PORT)))
    server = ThreadingHTTPServer((HOST, port), ProotyPieHandler)
    print(f"ProotyPie API listening on http://{HOST}:{port}")
    threading.Thread(target=warm_prediction_model, daemon=True).start()
    server.serve_forever()


if __name__ == "__main__":
    main()
