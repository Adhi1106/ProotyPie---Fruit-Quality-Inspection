"""Gemini Vision service for FruitVision AI.

Responsibilities:
- Validate whether an uploaded image contains a fruit.
- Identify the fruit and determine if it is supported by the TensorFlow model.
- Generate AI-powered storage analysis and recommendations as structured JSON.

The Gemini client is created once and reused for all calls.
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path

from dotenv import load_dotenv
from google import genai
from google.genai import types

# ---------------------------------------------------------------------------
# Env / client setup
# ---------------------------------------------------------------------------

_ENV_PATH = Path(__file__).resolve().parents[1] / ".env"
_GEMINI_API_KEY: str | None = None
_client: genai.Client | None = None
_client_key: str | None = None

SUPPORTED_FRUITS = {"apple", "banana", "orange"}
_DEFAULT_MODEL = "gemini-3.1-flash-lite"
_DEFAULT_FALLBACK_MODELS = (
    "gemini-3.1-flash-lite",
    "gemini-3.5-flash",
    "gemini-2.5-flash-lite",
    "gemini-2.5-flash",
)
_MAX_CHAT_HISTORY_MESSAGES = 10
_VISION_IMAGE_MAX_SIDE = 768


def _load_api_key() -> str | None:
    """Load the Gemini API key from .env each time a client may be created."""
    load_dotenv(dotenv_path=_ENV_PATH, override=True)
    key = os.getenv("GEMINI_API_KEY")
    return key.strip() if key else None


def _get_model() -> str:
    """Return the configured Gemini model, falling back to a working default."""
    load_dotenv(dotenv_path=_ENV_PATH, override=True)
    model = os.getenv("GEMINI_MODEL", _DEFAULT_MODEL)
    return model.strip() or _DEFAULT_MODEL


def _get_model_candidates() -> list[str]:
    """Return the primary model followed by temporary-failure fallbacks."""
    load_dotenv(dotenv_path=_ENV_PATH, override=True)
    configured_fallbacks = os.getenv("GEMINI_FALLBACK_MODELS", "")
    fallback_models = [
        model.strip()
        for model in configured_fallbacks.split(",")
        if model.strip()
    ] or list(_DEFAULT_FALLBACK_MODELS)

    candidates: list[str] = []
    for model in [_get_model(), *fallback_models]:
        if model and model not in candidates:
            candidates.append(model)
    return candidates


def _get_client() -> genai.Client:
    """Return the shared Gemini client, initialising it on first call."""
    global _client, _client_key, _GEMINI_API_KEY
    key = _load_api_key()
    _GEMINI_API_KEY = key
    if not key:
        raise RuntimeError(
            "GEMINI_API_KEY is not set. Add it to your .env file and restart the API server."
        )
    if _client is None or _client_key != key:
        _client = genai.Client(api_key=key)
        _client_key = key
    return _client


def _is_temporary_model_error(exc: Exception) -> bool:
    """Return True for model overload/network errors worth trying on a fallback."""
    err_lower = str(exc).lower()
    temporary_markers = (
        "503",
        "unavailable",
        "high demand",
        "overloaded",
        "temporarily",
        "timeout",
        "deadline",
        "connection reset",
        "connection aborted",
        "connection refused",
    )
    permanent_markers = (
        "api key",
        "api_key_invalid",
        "permission_denied",
        "quota",
        "resource_exhausted",
        "429",
    )
    return any(marker in err_lower for marker in temporary_markers) and not any(
        marker in err_lower for marker in permanent_markers
    )


def _is_model_unavailable_error(exc: Exception) -> bool:
    """Return True when a model candidate itself is unavailable for this key."""
    err_lower = str(exc).lower()
    return (
        "not_found" in err_lower
        or "no longer available" in err_lower
        or ("model" in err_lower and "not found" in err_lower)
    )


def _fast_config(
    *,
    max_output_tokens: int,
    response_json: bool = False,
    system_instruction: str | None = None,
) -> types.GenerateContentConfig:
    """Return a low-latency config for concise app-facing Gemini responses."""
    kwargs = {
        "temperature": 0,
        "max_output_tokens": max_output_tokens,
        "thinking_config": types.ThinkingConfig(thinking_budget=0),
    }
    if response_json:
        kwargs["response_mime_type"] = "application/json"
    if system_instruction is not None:
        kwargs["system_instruction"] = system_instruction
    return types.GenerateContentConfig(**kwargs)


def _generate_content(prefix: str, *, contents, config=None):
    """Call Gemini with a primary model and fallbacks for temporary 503 spikes."""
    client = _get_client()
    attempted: list[str] = []
    last_exc: Exception | None = None

    for model in _get_model_candidates():
        attempted.append(model)
        try:
            kwargs = {"model": model, "contents": contents}
            if config is not None:
                kwargs["config"] = config
            return client.models.generate_content(**kwargs)
        except Exception as exc:
            last_exc = exc
            if not (_is_temporary_model_error(exc) or _is_model_unavailable_error(exc)):
                raise _runtime_error(prefix, exc) from exc

    tried = ", ".join(attempted)
    raise RuntimeError(
        f"{prefix}: Gemini is temporarily busy or unavailable across the configured "
        f"models ({tried}). Please try again shortly."
    )


def _runtime_error(prefix: str, exc: Exception) -> RuntimeError:
    """Convert Gemini SDK exceptions into actionable app-facing errors."""
    err_str = str(exc)
    err_lower = err_str.lower()

    if "429" in err_str or "resource_exhausted" in err_lower or "quota" in err_lower:
        retry_match = re.search(r"retry in (\d+)", err_str, re.IGNORECASE)
        retry_hint = (
            f" Retry in {retry_match.group(1)} seconds."
            if retry_match
            else " Try again in a minute."
        )
        return RuntimeError(
            f"Gemini API quota reached for today's free tier.{retry_hint}"
        )

    if (
        "api key not valid" in err_lower
        or "api_key_invalid" in err_lower
        or "invalid api key" in err_lower
        or "permission_denied" in err_lower
    ):
        return RuntimeError(
            "Gemini API key was rejected by Google. Check GEMINI_API_KEY in .env, "
            "then restart the API server."
        )

    if (
        "not_found" in err_lower
        or "no longer available" in err_lower
        or ("model" in err_lower and "not found" in err_lower)
    ):
        return RuntimeError(
            f"{prefix}: configured Gemini model '{_get_model()}' is unavailable. "
            f"Set GEMINI_MODEL={_DEFAULT_MODEL} in .env, then restart the API server."
        )

    if _is_temporary_model_error(exc):
        return RuntimeError(
            f"{prefix}: Gemini is temporarily busy. Please try again shortly."
        )

    return RuntimeError(f"{prefix}: {exc}")


def _chat_error_message(exc: Exception) -> str:
    """Return a concise chat-visible error without swallowing config issues."""
    message = str(_runtime_error("Gemini chat failed", exc))
    if "quota reached" in message.lower():
        return message
    if "api key" in message.lower() or "configured gemini model" in message.lower():
        return message
    if "temporarily busy" in message.lower():
        return "Gemini is temporarily busy right now. Please try again shortly."
    return "I'm having trouble connecting right now. Please try again in a moment."


def _image_to_part(image) -> types.Part:
    """Convert a PIL Image to a compact Gemini image part."""
    import io

    prepared = image.convert("RGB")
    prepared.thumbnail((_VISION_IMAGE_MAX_SIDE, _VISION_IMAGE_MAX_SIDE))
    buf = io.BytesIO()
    prepared.save(buf, format="JPEG", quality=82, optimize=True)
    return types.Part.from_bytes(data=buf.getvalue(), mime_type="image/jpeg")


def _response_text(response) -> str:
    """Return non-empty text from a Gemini response."""
    text = getattr(response, "text", None)
    if not text:
        raise RuntimeError("Gemini returned an empty response.")
    return text.strip()


def _parse_json_response(raw: str, context: str) -> dict:
    """Parse JSON from Gemini, tolerating code fences or brief surrounding prose."""
    cleaned = raw.strip()
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*```$", "", cleaned)

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        json_match = re.search(r"\{.*\}", cleaned, flags=re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(0))
            except json.JSONDecodeError:
                pass

    snippet = cleaned[:220].replace("\n", " ")
    raise RuntimeError(f"Gemini returned invalid JSON for {context}: {snippet}")


def _coerce_bool(value, default: bool = False) -> bool:
    """Convert Gemini JSON booleans safely, including string values."""
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


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def validate_image(image) -> dict:
    """Analyse an image with Gemini Vision and return a structured result.

    Returns a dict with the following keys:
        is_fruit      (bool)   – True if a fruit is detected in the image.
        fruit_name    (str)    – Identified fruit name, or detected object label.
        is_supported  (bool)   – True only when the fruit is Apple/Banana/Orange.
        fun_message   (str)    – Playful message for non-fruit images.
        object_label  (str)    – Short label of the primary detected object.

    Raises RuntimeError on unrecoverable Gemini API failures.
    """
    prompt = """Analyse this image carefully and respond ONLY with a valid JSON object.
No markdown, no explanation, just raw JSON.

Use this exact schema:
{
  "is_fruit": <true or false>,
  "fruit_name": "<name of the fruit, or name of the detected object if not a fruit>",
  "is_supported": <true if the fruit is Apple, Banana or Orange; false otherwise>,
  "object_label": "<a short 1-3 word label for what you see in the image>",
  "fun_message": "<only fill this if is_fruit is false: a short, playful, friendly 1-sentence message referencing what you see, with a relevant emoji. Never insult the user. Leave empty string if is_fruit is true.>"
}

Rules:
- Supported fruits are ONLY: Apple, Banana, Orange.
- If the image contains a fruit that is NOT Apple/Banana/Orange, set is_supported to false and still set is_fruit to true.
- If the image is not a fruit at all, set is_fruit to false and write a fun_message.
- fun_message examples for non-fruit images:
    dog -> "Cute dog 🐶... anyway, where's the fruit?"
    cat -> "That cat looks adorable 😺... but I'm still waiting for a fruit."
    laptop -> "Nice laptop 💻... unfortunately I only inspect fruits."
    car -> "Cool car 🚗... but it won't fit in my fruit basket."
    game screenshot -> "Interesting screenshot 🎮... but I can't judge game graphics for freshness."
  Make it unique to what you actually see.
"""
    prompt = """Classify the image for a fruit-inspection app.
Return only JSON with this exact schema:
{"is_fruit":true,"fruit_name":"Apple","is_supported":true,"object_label":"apple","fun_message":""}

Rules:
- Treat edible fruit or vegetable produce as is_fruit true. This includes mango, strawberry, tomato, carrot, potato, cucumber, and similar produce.
- Supported freshness fruits are only Apple, Banana, and Orange.
- If it is Apple, Banana, or Orange, set is_supported true.
- If it is any other fruit or vegetable, set is_supported false and keep is_fruit true.
- If it is not fruit or vegetable produce, set is_fruit false, set object_label to what you see, and write one short sarcastic but friendly fun_message telling the user to upload fruit instead.
- Do not add markdown or explanation outside the JSON."""

    try:
        response = _generate_content(
            "Gemini Vision validation failed",
            contents=[
                _image_to_part(image),
                prompt,
            ],
            config=_fast_config(max_output_tokens=180, response_json=True),
        )

        data = _parse_json_response(_response_text(response), "image validation")
        return {
            "is_fruit": _coerce_bool(data.get("is_fruit"), False),
            "fruit_name": str(data.get("fruit_name", "Unknown")),
            "is_supported": _coerce_bool(data.get("is_supported"), False),
            "object_label": str(data.get("object_label", "Unknown")),
            "fun_message": str(data.get("fun_message", "")),
        }

    except json.JSONDecodeError as exc:
        raise RuntimeError(
            f"Gemini returned an unexpected response format: {exc}"
        ) from exc
    except Exception as exc:
        raise _runtime_error("Gemini Vision validation failed", exc) from exc


def get_storage_analysis(fruit_name: str, freshness_status: str | None = None) -> dict:
    """Ask Gemini to generate structured storage, market, and nutrition data for a fruit.

    Args:
        fruit_name: The name of the fruit (e.g. "Apple", "Mango").
        freshness_status: Optional – "Fresh" or "Rotten" when known from TensorFlow.

    Returns a dict with keys matching the recommendation panel:
        temperature, humidity, shelf_life, storage, advice,
        ripening_advice, nutrition_highlights, market_recommendation, status
    """
    is_rotten = (freshness_status or "").strip().lower() == "rotten"

    if is_rotten:
        specific_instructions = (
            "The fruit is ROTTEN. Follow these rules strictly:\n"
            "- 'temperature': ideal temperature to store THIS type of fruit to PREVENT spoilage.\n"
            "- 'humidity': ideal humidity to PREVENT spoilage for this fruit type.\n"
            "- 'shelf_life': write exactly 'Expired — discard immediately'.\n"
            "- 'storage': recommended storage method TO PREVENT spoilage in future (e.g. 'Keep refrigerated in a breathable bag').\n"
            "- 'advice': 1-2 sentences framed as 'To prevent spoilage, store it like this: ...' — practical prevention guidance.\n"
            "- 'ripening_advice': empty string (not relevant for rotten fruit).\n"
            "- 'market_recommendation': How many days before full spoilage the fruit should ideally be sold. "
            "Frame it as: 'Sell at least X days before full spoilage to maximise value.' "
            "Give a realistic number based on the fruit type. Do NOT say 'discard'.\n"
            "- Do NOT suggest consuming the rotten fruit."
        )
    else:
        specific_instructions = (
            "The fruit is FRESH. Follow these rules strictly:\n"
            "- 'temperature': ideal storage temperature range for this fresh fruit.\n"
            "- 'humidity': ideal relative humidity for storage.\n"
            "- 'shelf_life': realistic shelf life from today (e.g. '5-7 days at room temperature, up to 3 weeks refrigerated').\n"
            "- 'storage': best storage location or method to keep it fresh longest.\n"
            "- 'advice': 1-2 sentence practical tip on keeping this fruit fresh as long as possible.\n"
            "- 'ripening_advice': 1 sentence ripening tip if applicable, otherwise empty string.\n"
            "- 'market_recommendation': Realistic number of days within which this fresh fruit should be marketed/sold "
            "to reach buyers while still at peak quality. Frame it as: 'Best marketed within X days for peak quality.'"
        )

    freshness_label = freshness_status if freshness_status else "Unknown"

    prompt = f"""You are an expert in produce storage, freshness, and market timing.

Fruit: {fruit_name}
Freshness status: {freshness_label}

{specific_instructions}

Respond ONLY with a valid JSON object. No markdown, no code fences, no explanation — raw JSON only.

Schema:
{{
  "temperature": "<storage temperature range>",
  "humidity": "<ideal relative humidity>",
  "shelf_life": "<shelf life as instructed>",
  "storage": "<storage location or method>",
  "advice": "<1-2 sentence advice as instructed>",
  "ripening_advice": "<ripening tip or empty string>",
  "nutrition_highlights": "<2-3 key nutrition facts as a short plain-text phrase>",
  "market_recommendation": "<market timing recommendation as instructed>",
  "status": "{freshness_label}"
}}
"""

    try:
        response = _generate_content(
            "Gemini storage analysis failed",
            contents=prompt,
            config=_fast_config(max_output_tokens=520, response_json=True),
        )

        data = _parse_json_response(_response_text(response), "storage analysis")

        # Normalise keys to what the UI expects
        return {
            "temperature": str(data.get("temperature", "N/A")),
            "humidity": str(data.get("humidity", "N/A")),
            "shelf_life": str(data.get("shelf_life", "N/A")),
            "storage": str(data.get("storage", "N/A")),
            "advice": str(data.get("advice", "")),
            "ripening_advice": str(data.get("ripening_advice", "")),
            "nutrition_highlights": str(data.get("nutrition_highlights", "")),
            "market_recommendation": str(data.get("market_recommendation", "")),
            "status": str(data.get("status", freshness_status or "Unknown")),
        }

    except json.JSONDecodeError as exc:
        raise RuntimeError(
            f"Gemini returned an unexpected response format for storage analysis: {exc}"
        ) from exc

    except Exception as exc:
        raise _runtime_error("Gemini storage analysis failed", exc) from exc


def get_storage_analysis(fruit_name: str, freshness_status: str | None = None) -> dict:
    """Return the recommendation JSON shape used by the ProotyPie result cards."""
    freshness_label = (freshness_status or "Fresh").strip() or "Fresh"
    is_rotten = freshness_label.lower() == "rotten"

    if is_rotten:
        prompt = f"""You are a produce safety expert.
Fruit: {fruit_name}
TensorFlow freshness result: Rotten

Explain what the user needs to know for a rotten fruit image.
Return ONLY valid JSON with this exact schema:
{{
  "status": "Rotten",
  "spoilage_signs": "<possible visible spoilage signs in 1 sentence>",
  "possible_causes": "<likely causes such as bruising, moisture, age, heat, mold transfer>",
  "safe_use": "<whether any safe use remains; be conservative and food-safe>",
  "disposal": "<safe disposal method>",
  "prevention": "<how to prevent this in future>"
}}
Do not suggest eating rotten fruit. Keep each value concise and practical."""
    else:
        prompt = f"""You are a produce storage expert.
Fruit: {fruit_name}
TensorFlow freshness result: {freshness_label}

Explain how to store and sell this fresh fruit.
Return ONLY valid JSON with this exact schema:
{{
  "status": "{freshness_label}",
  "storage_temperature": "<ideal temperature range>",
  "storage_space": "<best storage place or container>",
  "shelf_life": "<realistic remaining shelf life>",
  "market_sale": "<best market/sale timing>",
  "longevity_tip": "<one tip to make it last longer>",
  "nutrition": "<2-3 nutrition highlights>"
}}
Keep each value concise and practical."""

    try:
        response = _generate_content(
            "Gemini storage analysis failed",
            contents=prompt,
            config=_fast_config(max_output_tokens=420, response_json=True),
        )
        data = _parse_json_response(_response_text(response), "storage analysis")

        if is_rotten:
            return {
                "status": "Rotten",
                "spoilage_signs": str(data.get("spoilage_signs", "Possible soft spots, mold, leaking, discoloration, or sour smell.")),
                "possible_causes": str(data.get("possible_causes", "Age, bruising, excess moisture, heat exposure, or mold transfer from nearby produce.")),
                "safe_use": str(data.get("safe_use", "Do not eat rotten fruit. Discard it safely.")),
                "disposal": str(data.get("disposal", "Seal in a bag and place in compost or trash; clean the storage surface.")),
                "prevention": str(data.get("prevention", "Store future fruit cool, dry, ventilated, and away from spoiled produce.")),
                "shelf_life": "Expired - discard immediately",
            }

        storage_temperature = str(data.get("storage_temperature", data.get("temperature", "N/A")))
        storage_space = str(data.get("storage_space", data.get("storage", "N/A")))
        market_sale = str(data.get("market_sale", data.get("market_recommendation", "N/A")))
        longevity_tip = str(data.get("longevity_tip", data.get("advice", "")))
        nutrition = str(data.get("nutrition", data.get("nutrition_highlights", "")))
        return {
            "status": str(data.get("status", freshness_label)),
            "storage_temperature": storage_temperature,
            "storage_space": storage_space,
            "shelf_life": str(data.get("shelf_life", "N/A")),
            "market_sale": market_sale,
            "longevity_tip": longevity_tip,
            "nutrition": nutrition,
            "temperature": storage_temperature,
            "storage": storage_space,
            "market_recommendation": market_sale,
            "advice": longevity_tip,
            "nutrition_highlights": nutrition,
        }
    except Exception as exc:
        raise _runtime_error("Gemini storage analysis failed", exc) from exc


# ---------------------------------------------------------------------------
# Curated fruit facts — multiple per fruit so every rotation feels fresh.
# All facts are unambiguous: strictly about the edible fruit.
# ---------------------------------------------------------------------------
_FRUIT_FACTS: dict[str, list[str]] = {
    "Dragonfruit": [
        "Dragonfruit is actually the fruit of a cactus, and its flowers only bloom for a single night.",
        "The red flesh variety of dragonfruit gets its colour from betacyanins, the same pigments found in beetroot.",
        "Dragonfruit plants are pollinated exclusively by moths and bats because they only flower after dark.",
        "Despite its dramatic appearance, dragonfruit has almost no scent at all.",
        "Vietnam is the world's largest exporter of dragonfruit, shipping more than any other country.",
        "Dragonfruit cactus vines can grow up to 10 metres long when left unpruned.",
    ],
    "Passion Fruit": [
        "Passion fruit gets its name from Spanish missionaries who saw the flower as a symbol of the Passion of Christ.",
        "The wrinkled, shrivelled skin of a passion fruit is actually a sign that it is ripe, not rotting.",
        "Passion fruit pulp contains a natural sedative called passiflorine, which can promote relaxation.",
        "There are over 500 species of passiflora, but only a handful produce edible fruit.",
        "Passion fruit vines can produce fruit within the first year of planting under warm conditions.",
        "The seeds of passion fruit are fully edible and provide a satisfying crunch when eaten.",
    ],
    "Lychee": [
        "Lychee trees can live for over 1,000 years — there are trees in China still bearing fruit today.",
        "Unripe lychees contain a toxin called hypoglycin A that has been linked to mysterious illness outbreaks in India.",
        "China has cultivated lychees for over 2,000 years, and they were a favourite fruit of Tang Dynasty emperors.",
        "Lychee wood is prized in China for smoking meat and fish due to its distinctive aromatic smoke.",
        "A single lychee tree can produce up to 200 kg of fruit in a good harvest year.",
        "Lychees must be harvested by hand because the thin skin bruises extremely easily.",
    ],
    "Papaya": [
        "Papaya contains papain, an enzyme so powerful it is used industrially to tenderise leather.",
        "The papaya plant can produce fruit within 9 to 11 months of planting, one of the fastest of any fruit tree.",
        "Unripe green papaya is eaten as a vegetable across Southeast Asia and is a key ingredient in Thai salads.",
        "Papaya seeds are edible and have a peppery taste — they are sometimes dried and used as a black pepper substitute.",
        "Papaya leaves are traditionally used in some cultures to treat dengue fever symptoms.",
        "Columbus called papaya the 'fruit of the angels' when he encountered it in the Caribbean in 1492.",
    ],
    "Jackfruit": [
        "Jackfruit is the largest tree-borne fruit on Earth, with single fruits regularly exceeding 35 kg.",
        "The flesh of unripe jackfruit has a texture so similar to pulled pork that it is widely used as a meat substitute.",
        "A single jackfruit tree can produce up to 200 fruits per year.",
        "Jackfruit seeds are edible when boiled or roasted and taste similar to chestnuts.",
        "The wood of the jackfruit tree is used to make Sri Lankan drums called 'raban'.",
        "Jackfruit is the national fruit of Bangladesh and Sri Lanka.",
    ],
    "Durian": [
        "Durian is banned on public transport in Singapore, Thailand, and Japan because of its powerful odour.",
        "The smell of durian comes from a cocktail of 44 volatile chemical compounds identified by researchers.",
        "Despite its reputation, durian is called the 'king of fruits' across Southeast Asia and is intensely sweet.",
        "Durian flowers are pollinated by cave-dwelling bats, which are attracted to the fermented-smelling nectar.",
        "A single durian fruit can weigh up to 8 kg and falls from trees with enough force to cause serious injury.",
        "Durian contains more calories per 100g than almost any other fruit because of its high fat content.",
    ],
    "Guava": [
        "Guava has more vitamin C per 100g than an orange — the skin alone contains up to 5 times as much.",
        "Guava leaves are used in traditional medicine across Asia and Latin America as a treatment for diarrhoea.",
        "The guava tree can withstand brief freezing temperatures, making it one of the hardiest tropical fruit trees.",
        "India is the world's largest producer of guava, growing about 45% of the global supply.",
        "Guava seeds are so hard they were historically used in pre-Columbian cultures as a source of oil.",
        "A guava tree bears fruit within two to three years and can remain productive for 40 years.",
    ],
    "Tamarind": [
        "Tamarind is the key souring ingredient in Worcestershire sauce, a fact most people are unaware of.",
        "The tamarind tree is so slow-growing that it takes between 10 and 15 years to bear fruit for the first time.",
        "Tamarind paste is used to clean copper and brass in Indian households because its acid removes tarnish.",
        "The word tamarind comes from the Arabic 'tamar hindi', meaning 'Indian date'.",
        "Tamarind seeds can be roasted and ground into a flour used for thickening sauces.",
        "A mature tamarind tree can live for more than 200 years and produce fruit throughout.",
    ],
    "Star Fruit": [
        "Star fruit contains caramboxin, a neurotoxin that can be dangerous for people with kidney disease.",
        "The cross-section of a star fruit forms a perfect five-pointed star, which gave the fruit its name.",
        "Star fruit is 91% water, making it one of the most hydrating fruits you can eat.",
        "The entire star fruit is edible — skin, flesh, and seeds — without any preparation.",
        "Star fruit changes from green to yellow as it ripens and becomes sweeter as the colour deepens.",
        "Malaysia, Taiwan, and Guyana are the primary commercial producers of star fruit globally.",
    ],
    "Fig": [
        "Figs are not a fruit in the traditional sense — they are an inverted flower cluster called a syconium.",
        "Each fig variety can only be pollinated by one specific species of fig wasp that lives inside it.",
        "Figs were likely one of the first plants cultivated by humans — fig remains have been found from 9,400 BC.",
        "The fig tree is mentioned more times in the Bible than any other fruit plant.",
        "Dried figs were used as currency and athletic fuel during the ancient Olympic Games.",
        "A single fig tree can produce two harvests per year — an early crop and a main crop.",
    ],
    "Pomegranate": [
        "Pomegranate trees can live for over 200 years and continue producing fruit throughout their lives.",
        "The pomegranate has exactly 613 seeds according to Jewish tradition, symbolising the 613 commandments.",
        "Pomegranate juice stains are nearly impossible to remove because the pigments bond chemically to fabric.",
        "The pomegranate is native to modern-day Iran and has been cultivated for at least 4,000 years.",
        "Pomegranate peel extract is being studied as a natural preservative for food packaging.",
        "The name 'grenade' comes from the French word for pomegranate — the fruit's shape inspired the weapon.",
    ],
    "Persimmon": [
        "Unripe persimmons are so astringent they will make your mouth go numb due to soluble tannins.",
        "Japan has over 1,000 named persimmon varieties, more than any other country.",
        "Persimmon wood is so hard it is used to make golf club heads and billiard cues.",
        "The hachiya persimmon must be completely soft before eating — eating it firm is extremely unpleasant.",
        "Dried persimmons called 'hoshigaki' are considered a luxury confection in Japan.",
        "Persimmon leaves are brewed into a tea in Korea and Japan and contain more vitamin C than the fruit itself.",
    ],
    "Rambutan": [
        "The word rambutan comes from the Malay word 'rambut', meaning hair, referring to its spiky red exterior.",
        "Rambutan and lychee are closely related and have nearly identical flesh despite looking completely different.",
        "Rambutan seeds contain a waxy fat called rambutan tallow, which is used in candle and soap making.",
        "A rambutan tree must be at least five years old before it starts producing fruit.",
        "Rambutan is one of the few fruits where male, female, and hermaphrodite trees all exist separately.",
        "Southeast Asian traditional medicine uses rambutan roots, bark, and leaves to treat fever.",
    ],
    "Mangosteen": [
        "The mangosteen is so perishable that it was illegal to import fresh mangosteens into the US until 2007.",
        "Queen Victoria reportedly offered a reward of 100 pounds to anyone who could bring her a fresh mangosteen.",
        "The purple outer shell of the mangosteen contains xanthones, compounds being studied for anti-inflammatory properties.",
        "A mangosteen tree takes 10 to 15 years to bear its first fruit and cannot be grown from cuttings.",
        "The number of segments inside a mangosteen perfectly matches the number of petals on the base of the fruit.",
        "Mangosteen trees will die if the temperature drops below 4 degrees Celsius even briefly.",
    ],
    "Breadfruit": [
        "Breadfruit gets its name because when roasted, its starchy flesh tastes remarkably like freshly baked bread.",
        "A single breadfruit tree can produce up to 200 fruits per year for decades with almost no maintenance.",
        "Breadfruit was at the centre of the famous mutiny on the Bounty in 1789 — the ship was transporting it.",
        "Breadfruit is seedless and propagates only through root shoots, meaning all trees are essentially clones.",
        "Breadfruit flour is gluten-free and has a lower glycaemic index than wheat flour.",
        "Pacific Island communities have used breadfruit as a staple carbohydrate for over 3,000 years.",
    ],
    "Soursop": [
        "Soursop contains acetogenins, compounds being researched for their potential to target specific cancer cells.",
        "The soursop tree is unusual because its flowers can bloom and fruit can grow directly from the trunk.",
        "Soursop leaves brewed as a tea are used across the Caribbean as a traditional sleep aid.",
        "A single soursop fruit can weigh up to 7 kg and contains hundreds of seeds embedded in fibrous pulp.",
        "Soursop is closely related to the custard apple and the cherimoya — all belong to the Annonaceae family.",
        "The soursop tree is one of the few tropical fruit trees that produces year-round without a clear season.",
    ],
    "Feijoa": [
        "Feijoa is almost completely unknown outside South America, New Zealand, and parts of the Caucasus.",
        "The feijoa flower petals are edible and sweet — they are eaten directly off the tree in New Zealand.",
        "Feijoa contains a unique flavour compound called methyl benzoate that no other fruit produces.",
        "Despite being a subtropical fruit, feijoa plants can survive frost down to minus 10 degrees Celsius.",
        "Feijoa is the national fruit of the Republic of Georgia, where it grows wild in the mountains.",
        "The feijoa has no widely recognised English name in most of the world — it is simply called feijoa everywhere.",
    ],
    "Banana": [
        "Bananas are botanically classified as berries, but strawberries and raspberries are not.",
        "Banana plants are not trees — they are the world's largest herbaceous plants.",
        "Bananas are slightly radioactive due to their naturally high potassium-40 content.",
        "The Cavendish banana, which dominates global trade, nearly went extinct in the 1950s due to Panama disease.",
        "A cluster of bananas is called a hand, and a single banana is called a finger.",
        "Banana peels have been used in water purification research to remove heavy metals from contaminated water.",
    ],
    "Pineapple": [
        "Pineapple contains bromelain, an enzyme that actively digests the proteins in your mouth as you eat it.",
        "Pineapples were so rare in 18th-century Europe that people rented them by the day as status symbols.",
        "It takes two to three years for a pineapple plant to produce a single fruit.",
        "Pineapple is not a single fruit but a mass of individual fruitlets fused around a central core.",
        "Bromelain in pineapple prevents gelatin from setting, which is why fresh pineapple ruins jellies.",
        "The pineapple plant only produces one fruit per growing cycle before it must be regrown.",
    ],
    "Watermelon": [
        "Watermelon is 92% water and was historically carried on long desert journeys as a portable water source.",
        "The first recorded watermelon harvest was depicted in Egyptian hieroglyphics nearly 5,000 years ago.",
        "Japan produces cube-shaped watermelons by growing them inside square glass moulds.",
        "Every part of a watermelon is edible, including the rind, which is pickled across many cultures.",
        "Seedless watermelons are triploid hybrids — they are sterile and cannot reproduce without seeded parent plants.",
        "The heaviest watermelon ever recorded weighed 159 kg, grown in the United States in 2013.",
    ],
    "Strawberry": [
        "Strawberries are the only fruit with seeds on the outside — a single berry carries around 200 of them.",
        "Strawberries are members of the rose family, which also includes apples, cherries, and plums.",
        "Strawberries are not true berries in botanical terms, while bananas and avocados actually are.",
        "The garden strawberry was first bred in Brittany, France in the 1740s by crossing two wild species.",
        "Some Japanese white strawberry varieties are deliberately bred to be pale and taste like pineapple.",
        "Ancient Romans used strawberry leaves and roots in medicinal preparations centuries before eating the fruit.",
    ],
    "Blueberry": [
        "Wild blueberries have been eaten by humans for over 13,000 years, well before agriculture existed.",
        "Blueberries are one of the only naturally blue foods — the colour comes from anthocyanin pigments.",
        "Blueberry plants can live for 50 years or more and actually become more productive as they age.",
        "Blueberries were used by Native Americans as a dye for baskets and clothing.",
        "North America produces about 90% of the world's commercially grown blueberries.",
        "A single blueberry bush can produce up to 6,000 blueberries in one growing season.",
    ],
    "Orange": [
        "The colour orange was named after the fruit — English had no word for the colour until oranges arrived.",
        "Navel oranges are all clones — every single one descends from a single mutant tree found in Brazil in 1820.",
        "Sweet oranges do not exist naturally in the wild — they are an ancient hybrid of pomelo and mandarin.",
        "Orange blossom honey is one of the most commercially produced mono-floral honeys in the world.",
        "Brazil produces about one third of the world's oranges but exports most of it as concentrated juice.",
        "The white pith beneath an orange peel contains nearly as much vitamin C as the flesh itself.",
    ],
    "Apple": [
        "There are over 7,500 known varieties of the apple fruit grown around the world.",
        "The apple fruit genome contains about 57,000 genes — more than the human genome.",
        "Apple fruit trees can live for more than 100 years and still produce a full harvest.",
        "Apple fruits ripen up to ten times faster at room temperature than when refrigerated.",
        "Apple seeds must experience cold temperatures to germinate, a dormancy process called stratification.",
        "A single apple tree can produce enough fruit to fill 20 boxes per year at peak maturity.",
    ],
}

_FACT_COUNTERS: dict[str, int] = {}


def get_spotlight_fact(fruit_name: str) -> str:
    """Return the next curated fact for the given fruit, cycling through the list.

    Purely local — no network call, no ambiguity, always fruit-specific.
    """
    facts = _FRUIT_FACTS.get(
        fruit_name,
        [f"The {fruit_name} fruit has been cultivated and enjoyed across many cultures for centuries."],
    )
    idx = _FACT_COUNTERS.get(fruit_name, 0)
    _FACT_COUNTERS[fruit_name] = (idx + 1) % len(facts)
    return facts[idx]


# ---------------------------------------------------------------------------
# AI Fruit Assistant — topic-restricted conversational chat
# ---------------------------------------------------------------------------

_ASSISTANT_SYSTEM_PROMPT = """You are FruitVision AI Assistant, a friendly and knowledgeable expert \
strictly focused on fruit-related topics.

You may ONLY answer questions about:
- Fruits (any variety, exotic or common)
- Fruit storage and shelf life
- Fruit nutrition and health benefits
- Fruit freshness, ripeness, and quality assessment
- Food safety related to fruits
- Fruit ripening processes and tips
- Fruit farming, cultivation, and harvesting

If the user asks about ANYTHING outside these topics (politics, coding, sports, general science, \
celebrities, etc.), respond warmly but firmly redirect them. Example:
"That's outside my area of expertise! I'm here to help with anything fruit-related — \
storage, nutrition, ripeness, or farming. What would you like to know?"

Keep answers concise, practical, and friendly. Use plain text only — no markdown, no bullet symbols, \
no asterisks. Write in short paragraphs."""


def chat_with_assistant(history: list[dict]) -> str:
    """Send the full conversation history to Gemini and return the assistant reply.

    Args:
        history: List of dicts with keys 'role' ('user' or 'assistant') and 'content' (str).
                 The last entry must be the latest user message.

    Returns:
        Plain-text reply string. Never raises — returns a fallback on failure.
    """
    try:
        # Build the multi-turn contents list the Gemini SDK expects.
        # Roles must be "user" or "model" (Gemini's term for assistant).
        gemini_contents: list[types.Content] = []

        for msg in history[-_MAX_CHAT_HISTORY_MESSAGES:]:
            role = msg.get("role", "user")
            text = msg.get("content", "").strip()
            if not text:
                continue
            gemini_role = "model" if role == "assistant" else "user"
            gemini_contents.append(
                types.Content(
                    role=gemini_role,
                    parts=[types.Part.from_text(text=text)],
                )
            )

        if not gemini_contents:
            return "I didn't catch that. Could you ask me something about fruit?"

        response = _generate_content(
            "Gemini chat failed",
            contents=gemini_contents,
            config=_fast_config(
                max_output_tokens=260,
                system_instruction=_ASSISTANT_SYSTEM_PROMPT,
            ),
        )
        reply = response.text.strip() if response.text else ""
        return reply if reply else "I didn't quite catch that. Could you rephrase your question?"

    except Exception as exc:
        return _chat_error_message(exc)
