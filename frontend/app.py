"""Premium Streamlit frontend for FruitVision AI."""

from __future__ import annotations

import base64
import html
import io
import sys
from pathlib import Path
from typing import Any

import streamlit as st
from PIL import Image, UnidentifiedImageError

# Ensure the project root is importable when this file is launched from /frontend.
ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

try:
    import backend.predict as prediction_service
    import backend.recommendation as recommendation_service
except Exception as exc:  # Keep the UI alive and show a readable error state.
    prediction_service = None
    recommendation_service = None
    BACKEND_IMPORT_ERROR = exc
else:
    BACKEND_IMPORT_ERROR = None


st.set_page_config(
    page_title="FruitVision AI",
    page_icon="🍎",
    layout="wide",
    initial_sidebar_state="expanded",
)


ALLOWED_TYPES = ["jpg", "jpeg", "png"]
APP_TAGLINE = "AI-Based Fruit Quality Inspection & Smart Storage Recommendation"


def inject_css() -> None:
    """Inject the custom visual system for the Streamlit application."""
    st.markdown(
        """
        <style>
            :root {
                --fv-bg: #f8fafc;
                --fv-surface: #ffffff;
                --fv-surface-soft: #f1f5f9;
                --fv-border: #e2e8f0;
                --fv-ink: #0f172a;
                --fv-muted: #64748b;
                --fv-muted-2: #94a3b8;
                --fv-fresh: #16a34a;
                --fv-fresh-soft: #ecfdf3;
                --fv-fresh-border: #bbf7d0;
                --fv-rotten: #dc2626;
                --fv-rotten-soft: #fef2f2;
                --fv-rotten-border: #fecaca;
                --fv-shadow: 0 18px 55px rgba(15, 23, 42, 0.08);
                --fv-shadow-soft: 0 10px 30px rgba(15, 23, 42, 0.06);
            }

            .stApp {
                background: linear-gradient(180deg, #ffffff 0%, #f8fafc 46%, #ffffff 100%);
                color: var(--fv-ink);
            }

            .block-container {
                max-width: 1100px;
                padding: 3.25rem 2rem 4rem;
            }

            html, body, [class*="css"] {
                font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
                letter-spacing: 0;
            }

            #MainMenu, footer, [data-testid="stToolbar"], [data-testid="stDecoration"], [data-testid="stStatusWidget"] {
                visibility: hidden;
                height: 0;
            }

            [data-testid="stSidebar"] {
                background: linear-gradient(180deg, #ffffff 0%, #f8fafc 100%);
                border-right: 1px solid var(--fv-border);
            }

            [data-testid="stSidebar"] > div:first-child {
                padding: 2rem 1.15rem;
            }

            .sidebar-brand {
                padding: 1rem 0.95rem 1.15rem;
                margin-bottom: 1rem;
            }

            .sidebar-brand-title {
                color: var(--fv-ink);
                font-size: 1.05rem;
                font-weight: 750;
                line-height: 1.25;
                margin: 0 0 0.25rem;
            }

            .sidebar-brand-subtitle {
                color: var(--fv-muted);
                font-size: 0.84rem;
                line-height: 1.5;
                margin: 0;
            }

            .sidebar-card {
                background: rgba(255, 255, 255, 0.92);
                border: 1px solid var(--fv-border);
                border-radius: 8px;
                box-shadow: var(--fv-shadow-soft);
                padding: 1rem;
                margin-bottom: 1rem;
            }

            .sidebar-title {
                color: var(--fv-ink);
                display: flex;
                align-items: center;
                gap: 0.45rem;
                font-size: 0.9rem;
                font-weight: 750;
                margin-bottom: 0.85rem;
            }

            .sidebar-row {
                display: flex;
                align-items: center;
                justify-content: space-between;
                gap: 1rem;
                border-top: 1px solid #eef2f7;
                padding: 0.7rem 0;
            }

            .sidebar-row:first-of-type {
                border-top: 0;
                padding-top: 0;
            }

            .sidebar-label {
                color: var(--fv-muted);
                font-size: 0.78rem;
                font-weight: 650;
            }

            .sidebar-value {
                color: var(--fv-ink);
                font-size: 0.82rem;
                font-weight: 750;
                text-align: right;
            }

            .sidebar-about {
                color: var(--fv-muted);
                font-size: 0.86rem;
                line-height: 1.55;
                margin: 0;
            }

            .fv-animate {
                animation: fadeUp 360ms ease-out both;
            }

            .hero-panel {
                text-align: center;
                padding: 1.2rem 0 2.35rem;
            }

            .hero-title {
                color: var(--fv-ink);
                font-size: 3.45rem;
                font-weight: 780;
                line-height: 1.05;
                letter-spacing: 0;
                margin: 0;
            }

            .hero-subtitle {
                color: var(--fv-muted);
                font-size: 1.08rem;
                line-height: 1.65;
                max-width: 680px;
                margin: 1rem auto 1.45rem;
            }

            .gradient-divider {
                width: min(520px, 72%);
                height: 3px;
                border-radius: 999px;
                margin: 0 auto;
                background: linear-gradient(90deg, rgba(22, 163, 74, 0), rgba(22, 163, 74, 0.9), rgba(249, 115, 22, 0.72), rgba(14, 165, 233, 0));
            }

            .section-heading {
                margin: 1rem 0 1.1rem;
                text-align: center;
            }

            .section-kicker {
                color: var(--fv-muted-2);
                font-size: 0.75rem;
                font-weight: 800;
                text-transform: uppercase;
                letter-spacing: 0.08em;
                margin: 0 0 0.35rem;
            }

            .section-title {
                color: var(--fv-ink);
                font-size: 1.45rem;
                font-weight: 760;
                line-height: 1.25;
                margin: 0;
            }

            .upload-helper {
                background: rgba(255, 255, 255, 0.9);
                border: 1px solid var(--fv-border);
                border-radius: 8px;
                box-shadow: var(--fv-shadow-soft);
                padding: 1.1rem 1.15rem;
                margin-bottom: 0.9rem;
            }

            .upload-helper-title {
                color: var(--fv-ink);
                font-size: 1rem;
                font-weight: 760;
                margin: 0 0 0.35rem;
            }

            .upload-helper-copy {
                color: var(--fv-muted);
                font-size: 0.9rem;
                line-height: 1.55;
                margin: 0;
            }

            [data-testid="stFileUploader"] {
                min-height: 230px;
                border: 1px dashed #cbd5e1;
                border-radius: 8px;
                background: linear-gradient(180deg, #ffffff 0%, #f8fafc 100%);
                box-shadow: var(--fv-shadow-soft);
                padding: 1.15rem;
                display: flex;
                align-items: center;
            }

            [data-testid="stFileUploader"] section {
                background: transparent;
                border: 0;
                padding: 1.25rem;
                width: 100%;
            }

            [data-testid="stFileUploader"] button {
                border-radius: 8px;
                border: 1px solid var(--fv-border);
                background: #ffffff;
                color: var(--fv-ink);
                font-weight: 700;
            }

            .image-card, .empty-preview-card, .prediction-card, .recommendation-panel {
                border: 1px solid var(--fv-border);
                border-radius: 8px;
                background: rgba(255, 255, 255, 0.94);
                box-shadow: var(--fv-shadow);
            }

            .image-card {
                padding: 0.85rem;
            }

            .preview-image {
                width: 100%;
                max-height: 420px;
                object-fit: contain;
                border-radius: 8px;
                background: #f8fafc;
                display: block;
            }

            .image-meta {
                display: flex;
                justify-content: space-between;
                gap: 1rem;
                color: var(--fv-muted);
                font-size: 0.82rem;
                font-weight: 650;
                line-height: 1.4;
                padding: 0.85rem 0.2rem 0.1rem;
            }

            .empty-preview-card {
                min-height: 350px;
                display: grid;
                place-items: center;
                padding: 1.4rem;
            }

            .scanner-frame {
                width: min(260px, 78%);
                aspect-ratio: 1.15;
                border: 1px solid #dbe4ee;
                border-radius: 8px;
                background: linear-gradient(180deg, #ffffff, #f8fafc);
                position: relative;
                overflow: hidden;
            }

            .scanner-frame::before,
            .scanner-frame::after {
                content: "";
                position: absolute;
                inset: 18px;
                border: 1px solid #e2e8f0;
                border-radius: 8px;
            }

            .scan-line {
                position: absolute;
                left: 14%;
                right: 14%;
                top: 44%;
                height: 2px;
                background: linear-gradient(90deg, transparent, #16a34a, transparent);
                animation: scanLine 2.4s ease-in-out infinite;
            }

            .empty-preview-label {
                color: var(--fv-muted);
                font-size: 0.9rem;
                font-weight: 700;
                margin-top: 1rem;
                text-align: center;
            }

            .button-row-spacer {
                height: 2rem;
            }

            .button-row-bottom {
                height: 1.6rem;
            }

            .stButton {
                display: flex;
                justify-content: center;
            }

            .stButton > button {
                min-height: 56px;
                border: 0;
                border-radius: 8px;
                background: linear-gradient(135deg, #0f172a 0%, #1f2937 58%, #14532d 100%);
                box-shadow: 0 16px 36px rgba(15, 23, 42, 0.18);
                color: #ffffff;
                font-size: 1rem;
                font-weight: 800;
                padding: 0 2.1rem;
                transition: transform 180ms ease, box-shadow 180ms ease, opacity 180ms ease;
            }

            .stButton > button:hover {
                transform: translateY(-1px);
                box-shadow: 0 20px 46px rgba(15, 23, 42, 0.22);
                color: #ffffff;
            }

            .stButton > button:active {
                transform: translateY(0);
            }

            .stButton > button:disabled {
                background: #e2e8f0;
                color: #94a3b8;
                box-shadow: none;
                opacity: 1;
            }

            .prediction-card {
                padding: 1.35rem;
                animation: fadeUp 360ms ease-out both;
            }

            .prediction-card.fresh {
                border-color: var(--fv-fresh-border);
                background: linear-gradient(180deg, #ffffff 0%, var(--fv-fresh-soft) 100%);
            }

            .prediction-card.rotten {
                border-color: var(--fv-rotten-border);
                background: linear-gradient(180deg, #ffffff 0%, var(--fv-rotten-soft) 100%);
            }

            .card-topline {
                display: flex;
                align-items: flex-start;
                justify-content: space-between;
                gap: 1rem;
                margin-bottom: 1.2rem;
            }

            .eyebrow {
                color: var(--fv-muted-2);
                font-size: 0.73rem;
                font-weight: 850;
                text-transform: uppercase;
                letter-spacing: 0.08em;
                margin: 0 0 0.35rem;
            }

            .fruit-name {
                color: var(--fv-ink);
                font-size: 2rem;
                line-height: 1.15;
                font-weight: 790;
                margin: 0;
            }

            .status-badge {
                border-radius: 999px;
                display: inline-flex;
                align-items: center;
                gap: 0.45rem;
                min-height: 34px;
                padding: 0.3rem 0.8rem;
                font-size: 0.82rem;
                font-weight: 850;
                white-space: nowrap;
            }

            .status-badge.fresh {
                color: #166534;
                background: #dcfce7;
                border: 1px solid #bbf7d0;
            }

            .status-badge.rotten {
                color: #991b1b;
                background: #fee2e2;
                border: 1px solid #fecaca;
            }

            .confidence-label {
                color: var(--fv-muted);
                font-size: 0.9rem;
                font-weight: 700;
                margin: 0;
            }

            .confidence-number {
                color: var(--fv-ink);
                font-variant-numeric: tabular-nums;
                font-size: 3.15rem;
                line-height: 1;
                font-weight: 820;
                margin: 0.15rem 0 1rem;
            }

            .progress-track {
                width: 100%;
                height: 13px;
                border-radius: 999px;
                background: #e2e8f0;
                overflow: hidden;
            }

            .progress-fill {
                height: 100%;
                border-radius: 999px;
                transform-origin: left center;
                animation: fillProgress 820ms cubic-bezier(0.16, 1, 0.3, 1) both;
            }

            .progress-fill.fresh {
                background: linear-gradient(90deg, #15803d, #22c55e);
            }

            .progress-fill.rotten {
                background: linear-gradient(90deg, #b91c1c, #ef4444);
            }

            .recommendation-panel {
                padding: 1.35rem;
                animation: fadeUp 420ms ease-out both;
            }

            .recommendation-header {
                display: flex;
                align-items: flex-start;
                justify-content: space-between;
                gap: 1rem;
                margin-bottom: 1rem;
            }

            .recommendation-title {
                color: var(--fv-ink);
                font-size: 1.35rem;
                line-height: 1.25;
                font-weight: 780;
                margin: 0;
            }

            .recommendation-grid {
                display: grid;
                grid-template-columns: repeat(2, minmax(0, 1fr));
                gap: 0.85rem;
            }

            .metric-tile {
                border: 1px solid #e5e7eb;
                border-radius: 8px;
                background: #f8fafc;
                padding: 1rem;
            }

            .metric-icon {
                color: var(--fv-muted);
                font-size: 1.05rem;
                line-height: 1;
                margin-bottom: 0.75rem;
            }

            .metric-label {
                color: var(--fv-muted);
                font-size: 0.76rem;
                font-weight: 800;
                text-transform: uppercase;
                letter-spacing: 0.06em;
                margin: 0 0 0.35rem;
            }

            .metric-value {
                color: var(--fv-ink);
                font-size: 1.02rem;
                font-weight: 780;
                line-height: 1.35;
                margin: 0;
                overflow-wrap: anywhere;
            }

            .advice-tile {
                grid-column: 1 / -1;
                display: grid;
                grid-template-columns: auto 1fr;
                gap: 0.85rem;
                align-items: start;
                border-radius: 8px;
                padding: 1rem;
            }

            .advice-tile.fresh {
                background: var(--fv-fresh-soft);
                border: 1px solid var(--fv-fresh-border);
            }

            .advice-tile.rotten {
                background: var(--fv-rotten-soft);
                border: 1px solid var(--fv-rotten-border);
            }

            .advice-icon {
                font-size: 1.15rem;
                line-height: 1;
                margin-top: 0.15rem;
            }

            .advice-copy {
                color: var(--fv-ink);
                font-size: 0.98rem;
                font-weight: 650;
                line-height: 1.55;
                margin: 0;
            }

            [data-testid="stAlert"] {
                border-radius: 8px;
                border: 1px solid var(--fv-border);
            }

            @keyframes fadeUp {
                from {
                    opacity: 0;
                    transform: translateY(10px);
                }
                to {
                    opacity: 1;
                    transform: translateY(0);
                }
            }

            @keyframes fillProgress {
                from {
                    opacity: 0.58;
                    transform: scaleX(0);
                }
                to {
                    opacity: 1;
                    transform: scaleX(1);
                }
            }

            @keyframes scanLine {
                0%, 100% { transform: translateY(-52px); opacity: 0.25; }
                50% { transform: translateY(52px); opacity: 1; }
            }

            @media (max-width: 900px) {
                .block-container {
                    padding: 2.4rem 1rem 3rem;
                }

                .hero-title {
                    font-size: 2.55rem;
                }

                .hero-subtitle {
                    font-size: 1rem;
                }

                .recommendation-grid {
                    grid-template-columns: 1fr;
                }

                .confidence-number {
                    font-size: 2.55rem;
                }
            }

            @media (prefers-reduced-motion: reduce) {
                *, *::before, *::after {
                    animation-duration: 0.01ms !important;
                    animation-iteration-count: 1 !important;
                    scroll-behavior: auto !important;
                    transition-duration: 0.01ms !important;
                }
            }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_sidebar() -> None:
    """Render the premium project sidebar."""
    st.sidebar.markdown(
        f"""
        <div class="sidebar-brand">
            <p class="sidebar-brand-title">🍎 FruitVision AI</p>
            <p class="sidebar-brand-subtitle">{html.escape(APP_TAGLINE)}</p>
        </div>
        <div class="sidebar-card">
            <div class="sidebar-title">▣ Project Information</div>
            <div class="sidebar-row">
                <span class="sidebar-label">Model</span>
                <span class="sidebar-value">MobileNetV2</span>
            </div>
            <div class="sidebar-row">
                <span class="sidebar-label">Framework</span>
                <span class="sidebar-value">TensorFlow</span>
            </div>
            <div class="sidebar-row">
                <span class="sidebar-label">Classes</span>
                <span class="sidebar-value">6</span>
            </div>
            <div class="sidebar-row">
                <span class="sidebar-label">Input Size</span>
                <span class="sidebar-value">224×224</span>
            </div>
        </div>
        <div class="sidebar-card">
            <div class="sidebar-title">◎ About</div>
            <p class="sidebar-about">
                FruitVision AI pairs image-based fruit quality inspection with practical storage guidance for everyday produce decisions.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_header() -> None:
    """Render the centered application header."""
    st.markdown(
        f"""
        <div class="hero-panel fv-animate">
            <h1 class="hero-title">🍎 FruitVision AI</h1>
            <p class="hero-subtitle">{html.escape(APP_TAGLINE)}</p>
            <div class="gradient-divider"></div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def load_uploaded_image(uploaded_file: Any) -> Image.Image:
    """Load an uploaded Streamlit file as a detached PIL image."""
    try:
        uploaded_file.seek(0)
        image = Image.open(uploaded_file)
        return image.copy()
    except UnidentifiedImageError as exc:
        raise ValueError("The uploaded file is not a valid image.") from exc
    except Exception as exc:
        raise ValueError(f"Unable to read the uploaded image: {exc}") from exc


def image_to_base64(image: Image.Image) -> str:
    """Convert a PIL image to a compact base64 PNG for styled HTML preview."""
    preview = image.copy().convert("RGB")
    preview.thumbnail((900, 900))

    buffer = io.BytesIO()
    preview.save(buffer, format="PNG", optimize=True)
    return base64.b64encode(buffer.getvalue()).decode("ascii")


def get_upload_signature(uploaded_file: Any | None) -> str | None:
    """Build a lightweight signature so stale results reset when the image changes."""
    if uploaded_file is None:
        return None
    return f"{uploaded_file.name}:{getattr(uploaded_file, 'size', 0)}"


def split_prediction_label(predicted_class: str) -> tuple[str, str]:
    """Split labels such as 'Fresh Apple' into fruit name and status."""
    parts = predicted_class.split(" ", 1)
    if len(parts) == 2 and parts[0] in {"Fresh", "Rotten"}:
        return parts[1], parts[0]
    return predicted_class, "Unknown"


def status_theme(status: str) -> str:
    """Return the CSS theme key for a freshness status."""
    return "fresh" if status.lower() == "fresh" else "rotten"


def render_upload_intro() -> None:
    """Render the image upload section heading."""
    st.markdown(
        """
        <div class="section-heading fv-animate">
            <p class="section-kicker">Image Upload</p>
            <h2 class="section-title">Inspect a fruit sample</h2>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_upload_helper() -> None:
    """Render a small premium panel beside the native uploader."""
    st.markdown(
        """
        <div class="upload-helper">
            <p class="upload-helper-title">Upload image</p>
            <p class="upload-helper-copy">Accepted formats: JPG, JPEG, PNG. The backend handles model preprocessing and inference.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_image_preview(image: Image.Image, filename: str) -> None:
    """Render the uploaded image inside a rounded preview card."""
    image_data = image_to_base64(image)
    safe_filename = html.escape(filename)

    st.markdown(
        f"""
        <div class="image-card fv-animate">
            <img class="preview-image" src="data:image/png;base64,{image_data}" alt="Uploaded fruit sample preview" />
            <div class="image-meta">
                <span>Image Preview</span>
                <span>{safe_filename}</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_empty_preview() -> None:
    """Render a calm placeholder preview before an image is uploaded."""
    st.markdown(
        """
        <div class="empty-preview-card fv-animate">
            <div>
                <div class="scanner-frame">
                    <div class="scan-line"></div>
                </div>
                <div class="empty-preview-label">Awaiting image</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_predict_button(disabled: bool) -> bool:
    """Render the centered prediction button and return its clicked state."""
    st.markdown('<div class="button-row-spacer"></div>', unsafe_allow_html=True)
    left, center, right = st.columns([1.45, 1, 1.45])
    with center:
        clicked = st.button(
            "Run AI Inspection",
            use_container_width=True,
            disabled=disabled,
        )
    st.markdown('<div class="button-row-bottom"></div>', unsafe_allow_html=True)
    return clicked


def render_prediction_card(result: dict[str, Any]) -> None:
    """Render the model prediction card with semantic confidence styling."""
    predicted_class = str(result["predicted_class"])
    recommendation = result["recommendation"]
    fruit_name, label_status = split_prediction_label(predicted_class)
    status = str(recommendation.get("status", label_status))
    theme = status_theme(status)
    confidence = max(0.0, min(100.0, float(result["confidence"])))

    st.markdown(
        f"""
        <div class="prediction-card {theme}">
            <div class="card-topline">
                <div>
                    <p class="eyebrow">Fruit Name</p>
                    <h2 class="fruit-name">{html.escape(fruit_name)}</h2>
                </div>
                <span class="status-badge {theme}">{html.escape(status)}</span>
            </div>
            <p class="confidence-label">Confidence</p>
            <p class="confidence-number">{confidence:.2f}%</p>
            <div class="progress-track" aria-label="Prediction confidence">
                <div class="progress-fill {theme}" style="width: {confidence:.2f}%;"></div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def metric_tile(icon: str, label: str, value: str) -> str:
    """Return HTML for a recommendation metric tile."""
    return f"""
        <div class="metric-tile">
            <div class="metric-icon">{html.escape(icon)}</div>
            <p class="metric-label">{html.escape(label)}</p>
            <p class="metric-value">{html.escape(value)}</p>
        </div>
    """


def render_recommendation_panel(recommendation: dict[str, str]) -> None:
    """Render smart storage recommendations as compact metric tiles."""
    theme = status_theme(recommendation.get("status", ""))
    tiles = "".join(
        [
            metric_tile("🌡️", "Temperature", recommendation["temperature"]),
            metric_tile("💧", "Humidity", recommendation["humidity"]),
            metric_tile("⏳", "Shelf Life", recommendation["shelf_life"]),
            metric_tile("📦", "Storage", recommendation["storage"]),
        ]
    )

    st.markdown(
        f"""
        <div class="recommendation-panel">
            <div class="recommendation-header">
                <div>
                    <p class="eyebrow">Smart Storage</p>
                    <h3 class="recommendation-title">Recommendation</h3>
                </div>
            </div>
            <div class="recommendation-grid">
                {tiles}
                <div class="advice-tile {theme}">
                    <div class="advice-icon">✦</div>
                    <p class="advice-copy">{html.escape(recommendation["advice"])}</p>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_results(result: dict[str, Any] | None) -> None:
    """Render prediction and recommendation cards after inference."""
    if not result:
        return

    result_col, recommendation_col = st.columns([0.92, 1.08], gap="large")
    with result_col:
        render_prediction_card(result)
    with recommendation_col:
        render_recommendation_panel(result["recommendation"])


def run_prediction(image: Image.Image) -> dict[str, Any]:
    """Call the existing backend services without modifying prediction logic."""
    if prediction_service is None or recommendation_service is None:
        raise RuntimeError(f"Backend modules could not be loaded: {BACKEND_IMPORT_ERROR}")

    predicted_class, confidence, raw_vector = prediction_service.predict_image(image)
    recommendation = recommendation_service.get_recommendation(predicted_class)

    return {
        "predicted_class": predicted_class,
        "confidence": confidence,
        "raw_vector": raw_vector,
        "recommendation": recommendation,
    }


def main() -> None:
    """Run the FruitVision AI Streamlit frontend."""
    inject_css()
    render_sidebar()
    render_header()

    if "prediction_result" not in st.session_state:
        st.session_state.prediction_result = None
    if "upload_signature" not in st.session_state:
        st.session_state.upload_signature = None

    render_upload_intro()
    upload_col, preview_col = st.columns([0.95, 1.05], gap="large")

    with upload_col:
        render_upload_helper()
        uploaded_file = st.file_uploader(
            "Upload fruit image",
            type=ALLOWED_TYPES,
            label_visibility="collapsed",
        )

    current_signature = get_upload_signature(uploaded_file)
    if current_signature != st.session_state.upload_signature:
        st.session_state.prediction_result = None
        st.session_state.upload_signature = current_signature

    image = None
    if uploaded_file is not None:
        try:
            image = load_uploaded_image(uploaded_file)
        except ValueError as exc:
            st.error(str(exc))

    with preview_col:
        if image is not None and uploaded_file is not None:
            render_image_preview(image, uploaded_file.name)
        else:
            render_empty_preview()

    if BACKEND_IMPORT_ERROR is not None:
        st.error(f"Backend modules could not be loaded: {BACKEND_IMPORT_ERROR}")

    clicked = render_predict_button(
        disabled=image is None or BACKEND_IMPORT_ERROR is not None,
    )

    if clicked and image is not None:
        try:
            with st.spinner("Inspecting fruit quality..."):
                st.session_state.prediction_result = run_prediction(image)
            st.success("Inspection complete.")
            try:
                st.toast("Inspection complete", icon="✅")
            except Exception:
                pass
        except Exception as exc:
            st.session_state.prediction_result = None
            st.error(f"Prediction failed: {exc}")

    render_results(st.session_state.prediction_result)


if __name__ == "__main__":
    main()

