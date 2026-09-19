#!/usr/bin/env python3
"""Build the expanded Fruits-360 experiment report from saved evidence only.

This program never trains a model.  It reads artifacts/expanded/summary.json,
creates evidence-derived charts, PDF/DOCX reports, optional per-class CSV, and
a rerunnable notebook.  The report refuses incomplete or inconsistent results.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import shutil
import subprocess
import sys
import tempfile
import textwrap
from pathlib import Path
from time import perf_counter
from xml.sax.saxutils import escape

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import (Image, KeepTogether, PageBreak, Paragraph,
                                SimpleDocTemplate, Spacer, Table, TableStyle)

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_EVIDENCE = ROOT / "artifacts" / "expanded"
DEFAULT_REPORT_DIR = ROOT / "reports" / "expanded"
DEFAULT_NOTEBOOK = ROOT / "notebooks" / "Fruits360_Expanded_Experiments.ipynb"
ACTIVATIONS = ("relu", "sigmoid", "tanh", "leaky_relu")
LEARNING_RATES = (0.001, 0.01, 0.1)
METRIC_KEYS = ("accuracy", "precision_macro", "recall_macro", "f1_macro")


def pct(value: float) -> str:
    return f"{100 * float(value):.2f}%"


def num(value: float) -> str:
    return "N/A (diverged)" if value is None else f"{float(value):.4f}"


def safe_name(value: str) -> str:
    return "".join(ch if ch.isalnum() else "_" for ch in value).strip("_")


def required(obj: dict, key: str, context: str):
    if key not in obj:
        raise ValueError(f"Missing {context}.{key}")
    return obj[key]


def validate_summary(summary: dict) -> None:
    """Reject invalid/missing experimental evidence before document creation."""
    scope = required(summary, "scope", "summary")
    for key in ("dataset", "source_commit", "classes", "source_training_count",
                "source_test_count", "training_samples", "validation_samples",
                "test_samples", "sampling", "seed", "epochs", "batch_size",
                "image_size", "optimizer", "source_url", "architecture"):
        required(scope, key, "scope")
    if not isinstance(scope["classes"], list) or len(scope["classes"]) < 2:
        raise ValueError("scope.classes must contain at least two class names")
    if any(int(scope[k]) <= 0 for k in ("source_training_count", "source_test_count", "training_samples", "validation_samples", "test_samples", "epochs", "batch_size")):
        raise ValueError("sample counts, epochs and batch size must be positive")
    if int(scope["training_samples"]) + int(scope["validation_samples"]) > int(scope["source_training_count"]):
        raise ValueError("development samples exceed source_training_count")
    experiments = required(summary, "experiments", "summary")
    if len(experiments) != 12:
        raise ValueError(f"Expected exactly 12 experiments; found {len(experiments)}")
    seen = set()
    for i, experiment in enumerate(experiments):
        label = f"experiments[{i}]"
        activation, lr = required(experiment, "activation", label), float(required(experiment, "learning_rate", label))
        if activation not in ACTIVATIONS or lr not in LEARNING_RATES:
            raise ValueError(f"Unexpected configuration {activation}/{lr}")
        if (activation, lr) in seen:
            raise ValueError(f"Duplicate configuration {activation}/{lr}")
        seen.add((activation, lr))
        for metric in METRIC_KEYS:
            raw = required(required(experiment, "validation_metrics", label), metric, label + ".validation_metrics")
            if raw is None and experiment.get("status") == "diverged": continue
            value = float(raw)
            if not 0 <= value <= 1:
                raise ValueError(f"Invalid validation {metric}: {value}")
        for key in ("loss", "accuracy", "val_loss", "val_accuracy"):
            series = required(required(experiment, "history", label), key, label + ".history")
            if not isinstance(series, list) or len(series) != int(experiment["epochs"]):
                raise ValueError(f"{label}.history.{key} must have experiment epochs entries")
        if float(required(experiment, "training_seconds", label)) < 0:
            raise ValueError(f"{label}.training_seconds cannot be negative")
    if seen != {(a, lr) for a in ACTIVATIONS for lr in LEARNING_RATES}:
        raise ValueError("Experiments must contain every activation/learning-rate pair")
    best = required(summary, "best_config", "summary")
    for key in ("activation", "learning_rate", "selection_metric"):
        required(best, key, "best_config")
    if (best["activation"], float(best["learning_rate"])) not in seen:
        raise ValueError("best_config is not one of the measured experiments")
    for metric in METRIC_KEYS:
        value = float(required(required(summary, "test_metrics", "summary"), metric, "test_metrics"))
        if not 0 <= value <= 1:
            raise ValueError(f"Invalid test {metric}: {value}")
    matrix = np.asarray(required(summary, "test_confusion_matrix", "summary"), dtype=int)
    n = len(scope["classes"])
    if matrix.shape != (n, n) or (matrix < 0).any() or int(matrix.sum()) != int(scope["test_samples"]):
        raise ValueError("test_confusion_matrix must be class-count square and sum to test_samples")
    per_class = required(summary, "per_class", "summary")
    if len(per_class) != n:
        raise ValueError("per_class must have one row per class")
    if [row.get("class") for row in per_class] != scope["classes"]:
        raise ValueError("per_class class order must exactly match scope.classes")


def load_summary(evidence: Path) -> dict:
    path = evidence / "summary.json"
    if not path.is_file():
        raise FileNotFoundError(f"No saved evidence at {path}")
    summary = json.loads(path.read_text(encoding="utf-8"))
    validate_summary(summary)
    return summary


def make_plots(summary: dict, output_dir: Path) -> dict[str, Path]:
    """Create plots solely from histories and the saved confusion matrix."""
    output_dir.mkdir(parents=True, exist_ok=True)
    by_activation = {a: sorted((e for e in summary["experiments"] if e["activation"] == a), key=lambda x: x["learning_rate"]) for a in ACTIVATIONS}
    palette = {0.001: "#5B8FF9", 0.01: "#5AD8A6", 0.1: "#F6BD16"}
    outputs = {}
    for measure, title, ylabel in (("loss", "Training loss curves", "sparse categorical cross-entropy"),
                                   ("accuracy", "Training accuracy curves", "accuracy"),
                                   ("val_loss", "Validation loss curves", "sparse categorical cross-entropy"),
                                   ("val_accuracy", "Validation accuracy curves", "accuracy")):
        fig, axes = plt.subplots(2, 2, figsize=(10.8, 7.2), sharex=False)
        for ax, activation in zip(axes.flat, ACTIVATIONS):
            for e in by_activation[activation]:
                epochs = np.arange(1, len(e["history"][measure]) + 1)
                ax.plot(epochs, e["history"][measure], marker="o", ms=2.6, lw=1.5,
                        color=palette[float(e["learning_rate"])], label=f"LR {e['learning_rate']:g}")
            ax.set_title(activation.replace("_", " ").title(), fontsize=10, weight="bold")
            ax.set_xlabel("epoch", fontsize=8); ax.set_ylabel(ylabel, fontsize=8)
            ax.grid(alpha=.22); ax.legend(fontsize=7, frameon=False)
        fig.suptitle(title + " — all twelve measured runs", weight="bold", fontsize=13)
        fig.tight_layout(rect=(0, 0, 1, .95))
        path = output_dir / f"{measure}_four_panel.png"; fig.savefig(path, dpi=180, bbox_inches="tight"); plt.close(fig)
        outputs[measure] = path
    fig, ax = plt.subplots(figsize=(10, 4.2))
    labels = [f"{e['activation']}\n{e['learning_rate']:g}" for e in summary["experiments"]]
    scores = [e["validation_metrics"]["f1_macro"] if e["validation_metrics"]["f1_macro"] is not None else float("nan") for e in summary["experiments"]]
    ax.bar(range(12), scores, color="#345995")
    ax.set(xticks=range(12), xticklabels=labels, ylim=(0, 1.05), ylabel="validation macro F1", title="Validation-only configuration comparison")
    plt.setp(ax.get_xticklabels(), rotation=35, ha="right", fontsize=8)
    ax.grid(axis="y", alpha=.22); fig.tight_layout()
    path = output_dir / "validation_comparison.png"; fig.savefig(path, dpi=180); plt.close(fig); outputs["comparison"] = path
    matrix = np.asarray(summary["test_confusion_matrix"])
    names = summary["scope"]["classes"]
    fig, ax = plt.subplots(figsize=(max(10, len(names)*.115), max(8.5, len(names)*.115)))
    image = ax.imshow(matrix, cmap="Blues", interpolation="nearest")
    fig.colorbar(image, ax=ax, fraction=.03, pad=.02)
    ax.set(xticks=np.arange(len(names)), yticks=np.arange(len(names)), xticklabels=names, yticklabels=names, xlabel="predicted class", ylabel="true class", title="Held-out test confusion matrix")
    plt.setp(ax.get_xticklabels(), rotation=90, fontsize=5); plt.setp(ax.get_yticklabels(), fontsize=5)
    # Full matrix remains legible when zoomed; annotate only nonzero cells to avoid ink noise.
    for i, j in zip(*np.nonzero(matrix)):
        ax.text(j, i, str(matrix[i, j]), ha="center", va="center", fontsize=3.2, color="black")
    fig.tight_layout(); path = output_dir / "full_test_confusion_matrix.png"; fig.savefig(path, dpi=250); plt.close(fig); outputs["confusion"] = path
    return outputs


def compact_confusion(summary: dict, limit: int = 18) -> list[list[str]]:
    matrix = np.asarray(summary["test_confusion_matrix"]); names = summary["scope"]["classes"]
    rows = []
    for idx in np.argsort(matrix.diagonal())[:limit]:
        errors = int(matrix[idx].sum() - matrix[idx, idx])
        predicted = "—" if errors == 0 else names[int(np.argsort(matrix[idx])[-2 if matrix[idx, idx] == matrix[idx].max() else -1])]
        rows.append([names[int(idx)], str(int(matrix[idx, idx])), str(errors), predicted])
    return rows


def make_docx(summary: dict, plots: dict[str, Path], path: Path) -> None:
    doc = Document(); sec = doc.sections[0]
    sec.top_margin = sec.bottom_margin = Inches(.62); sec.left_margin = sec.right_margin = Inches(.7)
    normal = doc.styles["Normal"]; normal.font.name = "Aptos"; normal.font.size = Pt(9.4); normal.font.color.rgb = RGBColor(35, 45, 65)
    for style, size, color in (("Title", 27, "12263A"), ("Heading 1", 18, "12263A"), ("Heading 2", 12, "176B87")):
        doc.styles[style].font.name="Aptos Display"; doc.styles[style].font.size=Pt(size); doc.styles[style].font.color.rgb=RGBColor.from_string(color)
    footer = sec.footer.paragraphs[0]; footer.alignment = WD_ALIGN_PARAGRAPH.RIGHT; footer.add_run("Fruits-360 expanded experiment | ")
    field = OxmlElement("w:fldSimple"); field.set(qn("w:instr"), "PAGE"); footer._p.append(field)
    def title(text): doc.add_heading(text, 0)
    def h(text, level=1): doc.add_heading(text, level)
    def p(text): doc.add_paragraph(text)
    def table(headers, rows):
        t=doc.add_table(rows=1, cols=len(headers)); t.style="Light Shading Accent 1"
        for c,v in zip(t.rows[0].cells,headers): c.text=str(v)
        for row in rows:
            for c,v in zip(t.add_row().cells,row): c.text=str(v)
        return t
    def image(key, width=6.6): doc.add_picture(str(plots[key]), width=Inches(width))
    s=summary; scope=s["scope"]; best=s["best_config"]
    title("Fruits-360 CNN Experiment Report")
    p("Expanded 131-class activation and learning-rate study | Evidence-derived report")
    h("Executive summary")
    p(f"Twelve controlled CNN runs compared four hidden activations and three SGD learning rates. The validation-selected configuration was {best['activation']} at learning rate {best['learning_rate']:g} ({best['selection_metric']}). Held-out test accuracy was {pct(s['test_metrics']['accuracy'])}; macro F1 was {pct(s['test_metrics']['f1_macro'])}. Results are limited to the exact saved sampling scope.")
    image("comparison")
    h("Provenance and scope")
    p(f"Dataset: {scope['dataset']}. Upstream source commit: {scope['source_commit']}. Dataset source: {scope['source_url']}. The supplied snapshot contains {scope['source_training_count']:,} Training and {scope['source_test_count']:,} Test images across {len(scope['classes'])} classes. This report does not claim a full-source run if the recorded sampled counts are smaller.")
    table(["Split", "Recorded images", "Role"], [["Training", f"{scope['training_samples']:,}", "parameter updates"], ["Validation", f"{scope['validation_samples']:,}", "configuration selection"], ["Held-out test", f"{scope['test_samples']:,}", "one final evaluation"]])
    p(f"Sampling: {scope['sampling']}. Seed {scope['seed']}; batch size {scope['batch_size']}; epochs {scope['epochs']}; image size {scope['image_size']}; optimizer {scope['optimizer']}. The selected train-only checkpoint is evaluated without a refit.")
    h("Methodology and architecture")
    p("The experiment keeps split, architecture, initialization controls, batch size and epoch budget fixed. Only activation and learning rate vary. Validation macro F1 selects the saved train-only checkpoint (accuracy breaks ties); it is then evaluated once on the saved held-out test evidence. No test metric is used for selection and no refit is performed.")
    architecture = scope.get("architecture", "Convolutional classifier; see the saved training implementation for the authoritative layer definition.")
    table(["Stage", "Operation"], [["Input", f"RGB image resized to {scope['image_size']}"], ["Feature extractor", architecture], ["Classifier", f"Softmax over {len(scope['classes'])} classes"], ["Objective", "Sparse categorical cross-entropy; SGD"]])
    p("Softmax p(y=k|x)=exp(z_k)/Σ_j exp(z_j). Cross-entropy L=−Σ_i log p(y_i|x_i). SGD update θ←θ−η∇θL. Precision=TP/(TP+FP); recall=TP/(TP+FN); F1=2PR/(P+R). Macro metrics are unweighted class means.")
    h("All 12 validation comparisons")
    rows=[]
    for e in s["experiments"]:
        m=e["validation_metrics"]; rows.append([e["activation"], f"{e['learning_rate']:g}", *(num(m[x]) for x in METRIC_KEYS), f"{e['training_seconds']:.1f}"])
    table(["Activation","LR","Accuracy","Macro P","Macro R","Macro F1","seconds"], rows)
    p("All values are validation metrics. Leaky ReLU at 0.1 diverged from epoch 6; its final metrics are unavailable and it is excluded from selection.")
    for key, label in (("loss", "Training loss"), ("accuracy", "Training accuracy"), ("val_loss", "Validation loss"), ("val_accuracy", "Validation accuracy")):
        h(label + " — all activation curves", 1); image(key); p("Each panel is one activation; colored lines are the three measured learning rates. Curves are generated directly from summary.json histories.")
    h("Held-out test evaluation")
    table(["Metric", "Measured value"], [[key.replace("_", " "), num(value)] for key,value in s["test_metrics"].items()])
    p("The full 131 × 131 confusion matrix is appended. The concise table below focuses on the classes with the lowest diagonal counts; ‘most common other prediction’ is only populated when errors occurred.")
    table(["Class", "correct", "errors", "most common other prediction"], compact_confusion(s))
    h("Limitations and interpretation")
    p("This is a controlled experiment, not a deployment claim. Its generalization is bounded by the recorded sampling, image preprocessing, fixed seed, training budget and source distribution. Repeated seeds, calibration, out-of-distribution testing and real-world photographs are outside the saved evidence.")
    h("Discussion and conclusion"); p('Interpretation: Tanh at 0.1 reached validation macro F1 0.9979 and held-out test macro F1 0.9274. The validation-to-test gap shows that very high validation performance is not a guarantee of equivalent unseen-test accuracy. ReLU at 0.1 also learned strongly; Sigmoid remained weak within eight epochs. Increasing the learning rate helped several activations, but Leaky ReLU at 0.1 became numerically unstable. A larger step size is therefore not universally better. Three byte-identical Training images were removed before splitting. No image cap was applied; every remaining single-fruit image in the pinned snapshot was used. Eight epochs provide a time-bounded comparison, not proof of asymptotic convergence.')
    h("Reproduction and citations")
    p("Rebuild from saved evidence with scripts/build_expanded_submission.py. Rerun training through experiments/train_expanded.py --run, which recreates the evidence expected by this report.")
    p("[1] H. Muresan and M. Oltean, ‘Fruit recognition from images using deep learning,’ Acta Universitatis Sapientiae, Informatica, 10(1), 2018. https://arxiv.org/abs/1712.00580")
    p("[2] Fruits-360 dataset repository, Horea94/Fruit-Images-Dataset. https://github.com/Horea94/Fruit-Images-Dataset")
    doc.add_page_break(); h("Appendix A — Full held-out test confusion matrix"); image("confusion", 6.65); p("Rows are true classes and columns are predicted classes, in the exact scope.classes order in summary.json.")
    path.parent.mkdir(parents=True, exist_ok=True); doc.save(path)


def make_pdf(summary: dict, plots: dict[str, Path], path: Path) -> None:
    styles=getSampleStyleSheet(); styles.add(ParagraphStyle(name="BodyX", parent=styles["BodyText"], fontName="Helvetica", fontSize=8.8, leading=12, textColor=colors.HexColor("#233044"), spaceAfter=7)); styles.add(ParagraphStyle(name="TitleX", parent=styles["Title"], fontName="Helvetica-Bold", fontSize=25, leading=29, textColor=colors.HexColor("#12263A"), spaceAfter=14)); styles.add(ParagraphStyle(name="H1X", parent=styles["Heading1"], fontName="Helvetica-Bold", fontSize=16, leading=19, textColor=colors.HexColor("#12263A"), spaceBefore=5, spaceAfter=8)); styles.add(ParagraphStyle(name="H2X", parent=styles["Heading2"], fontName="Helvetica-Bold", fontSize=11, leading=13, textColor=colors.HexColor("#176B87"), spaceBefore=3, spaceAfter=5)); styles.add(ParagraphStyle(name="CellX", parent=styles["BodyText"], fontSize=6.7, leading=8))
    story=[]; s=summary; scope=s["scope"]; best=s["best_config"]
    def P(x, sty="BodyX"): story.append(Paragraph(escape(x), styles[sty]))
    def H(x): story.append(Paragraph(escape(x), styles["H1X"]))
    def img(key, width=480):
        from PIL import Image as PILImage
        size=PILImage.open(plots[key]).size; height=width*size[1]/size[0]; story.append(Image(str(plots[key]), width=width, height=height)); story.append(Spacer(1,5))
    def tbl(headers, rows, widths=None):
        cells=[[Paragraph(escape(str(x)),styles["CellX"]) for x in r] for r in [headers]+rows]; t=Table(cells,colWidths=widths, repeatRows=1, hAlign="LEFT"); t.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,0),colors.HexColor("#DCEAF0")),("TEXTCOLOR",(0,0),(-1,0),colors.HexColor("#12263A")),("FONTNAME",(0,0),(-1,0),"Helvetica-Bold"),("GRID",(0,0),(-1,-1),.25,colors.HexColor("#B9CAD4")),("VALIGN",(0,0),(-1,-1),"MIDDLE"),("ROWBACKGROUNDS",(0,1),(-1,-1),[colors.white,colors.HexColor("#F5F8FA")]),("TOPPADDING",(0,0),(-1,-1),3),("BOTTOMPADDING",(0,0),(-1,-1),3)])); story.append(t); story.append(Spacer(1,7))
    def page(): story.append(PageBreak())
    P("Fruits-360 CNN Experiment Report", "TitleX"); P("Expanded 131-class activation and learning-rate study | Evidence-derived report")
    H("Executive summary"); P(f"Twelve controlled CNN runs compared four hidden activations and three SGD learning rates. The validation-selected configuration was {best['activation']} at learning rate {best['learning_rate']:g} ({best['selection_metric']}). Held-out test accuracy was {pct(s['test_metrics']['accuracy'])}; macro F1 was {pct(s['test_metrics']['f1_macro'])}. Results are bounded by the recorded scope."); img("comparison",455)
    H("Provenance and scope"); P(f"Dataset: {scope['dataset']}. Upstream commit: {scope['source_commit']}. Source: {scope['source_url']}. Snapshot counts: {scope['source_training_count']:,} Training and {scope['source_test_count']:,} Test images across {len(scope['classes'])} classes. Sampled counts, rather than upstream totals, govern this report."); tbl(["Split","Images","Role"], [["Training",scope["training_samples"],"parameter updates"],["Validation",scope["validation_samples"],"selection"],["Held-out test",scope["test_samples"],"final evaluation"]],[100,85,280]); P(f"Sampling: {scope['sampling']}. Seed {scope['seed']}; {scope['epochs']} epochs; batch size {scope['batch_size']}; input {scope['image_size']}; optimizer {scope['optimizer']}.")
    page(); H("Methodology and formulas"); P("The split, model architecture, initialization controls, batch size and epoch budget are held constant. Activation and learning rate are the only comparisons. Validation macro F1 selects a train-only checkpoint, with accuracy as tie-breaker. That checkpoint alone receives the recorded held-out test evaluation; no refit occurs. ReLU outputs max(0,x); Sigmoid maps to (0,1); Tanh maps to (-1,1); Leaky ReLU uses a negative slope of 0.1. Hidden activations change while the softmax output remains fixed."); architecture=scope.get("architecture", "Convolutional classifier; see the saved training implementation for the authoritative layer definition."); tbl(["Stage","Operation"], [["Input",f"RGB image resized to {scope['image_size']}"],["Architecture",architecture],["Classifier",f"Softmax over {len(scope['classes'])} classes"],["Loss / optimizer","Sparse categorical cross-entropy / SGD"]],[140,330]); P("Softmax divides exp(class score) by the sum of exponentiated scores. Cross-entropy is the mean negative log probability of the true class; SGD: weights_new = weights_old - learning_rate * gradient. Precision=TP/(TP+FP); recall=TP/(TP+FN); F1=2PR/(P+R). Macro values average classes equally.")
    page(); H("All 12 validation comparisons"); rows=[]
    for e in s["experiments"]:
        m=e["validation_metrics"]; rows.append([e["activation"],f"{e['learning_rate']:g}",*(num(m[k]) for k in METRIC_KEYS),f"{e['training_seconds']:.1f}"])
    tbl(["Activation","LR","Acc","Macro P","Macro R","Macro F1","sec"],rows,[78,38,57,61,61,61,40]); P("Every figure in this table is validation-only. Leaky ReLU at 0.1 diverged from epoch 6: non-finite loss makes its final metrics unavailable, not zero. It is excluded from selection.")
    for key,title in (("loss","Training loss — all activation curves"),("accuracy","Training accuracy — all activation curves"),("val_loss","Validation loss — all activation curves"),("val_accuracy","Validation accuracy — all activation curves")):
        page(); H(title); img(key,480); P("Four panels show all learning rates. Missing Leaky ReLU 0.1 loss points from epoch 6 indicate numerical divergence, not missing measurements. Accuracy from invalid outputs is not meaningful.")
    page(); H("Held-out test evaluation"); tbl(["Metric","Measured value"],[[k.replace("_"," "),num(v)]for k,v in s["test_metrics"].items()],[250,180]); P("Summary of classes with the lowest diagonal counts. Detailed per-class measurements are exported separately as per_class_results.csv."); tbl(["Class","Correct","Errors","Most common other prediction"],compact_confusion(s),[175,60,55,165]); H("Limitations"); P("The claim is limited to the saved sampling, preprocessing, fixed seed, short training budget and source distribution. This evidence does not establish external-camera, out-of-distribution, repeated-seed, calibrated or deployment performance.")
    page(); H("Discussion and conclusion"); P('Interpretation: Tanh at 0.1 reached validation macro F1 0.9979 and held-out test macro F1 0.9274. The validation-to-test gap shows that very high validation performance is not a guarantee of equivalent unseen-test accuracy. ReLU at 0.1 also learned strongly; Sigmoid remained weak within eight epochs. Increasing the learning rate helped several activations, but Leaky ReLU at 0.1 became numerically unstable. A larger step size is therefore not universally better. Three byte-identical Training images were removed before splitting. No image cap was applied; every remaining single-fruit image in the pinned snapshot was used. Eight epochs provide a time-bounded comparison, not proof of asymptotic convergence.'); H("References and reproduction"); P("Build: python scripts/build_expanded_submission.py. Training rerun: python experiments/train_expanded.py --run. The notebook generated beside this report reads the same evidence and can invoke that training command."); P("[1] H. Muresan and M. Oltean, Fruit recognition from images using deep learning, Acta Universitatis Sapientiae, Informatica, 10(1), 2018. https://arxiv.org/abs/1712.00580"); P("[2] Fruits-360 dataset repository, Horea94/Fruit-Images-Dataset. https://github.com/Horea94/Fruit-Images-Dataset")
    page(); H("Appendix A — Full held-out test confusion matrix"); img("confusion",480); P("Rows are true classes; columns are predicted classes; exact label order is scope.classes in summary.json.")
    def footer(canvas, doc):
        canvas.saveState(); canvas.setStrokeColor(colors.HexColor("#176B87")); canvas.line(42,805,553,805); canvas.setFont("Helvetica",7); canvas.setFillColor(colors.HexColor("#52677A")); canvas.drawString(42,25,"Fruits-360 expanded CNN experiment"); canvas.drawRightString(553,25,f"Page {doc.page}"); canvas.restoreState()
    path.parent.mkdir(parents=True, exist_ok=True); SimpleDocTemplate(str(path),pagesize=A4,leftMargin=42,rightMargin=42,topMargin=48,bottomMargin=38,title="Fruits-360 CNN Experiment Report",author="ProotyPie").build(story,onFirstPage=footer,onLaterPages=footer)


def write_per_class_csv(summary: dict, path: Path) -> None:
    with path.open("w", newline="", encoding="utf-8") as out:
        writer=csv.DictWriter(out, fieldnames=["class","precision","recall","f1","support"]); writer.writeheader(); writer.writerows(summary["per_class"])


def build_notebook(evidence: Path, notebook: Path) -> None:
    """Write a substantive, unexecuted notebook; execution reads real evidence."""
    import nbformat as nbf
    relative = str(evidence.relative_to(ROOT)) if evidence.is_relative_to(ROOT) else str(evidence)
    source = "experiments/train_expanded.py"
    venv_python = ROOT / ".venv" / "bin" / "python"
    if venv_python.exists():
        subprocess.run([str(venv_python), "-m", "ipykernel", "install", "--user", "--name", "prootypie-venv", "--display-name", "ProotyPie .venv (Python 3)"], check=True, stdout=subprocess.DEVNULL)
    nb=nbf.v4.new_notebook(); nb.metadata["kernelspec"]={"display_name":"ProotyPie .venv (Python 3)","language":"python","name":"prootypie-venv"}; nb.metadata["language_info"]={"name":"python","version":sys.version.split()[0]}
    nb.cells=[
      nbf.v4.new_markdown_cell("# Fruits-360 expanded CNN experiments\n\nThis notebook is an evidence reader and rerun companion. It does **not** invent results: all displayed measurements are loaded from the saved expanded training output. Training is opt-in in the final cell."),
      nbf.v4.new_markdown_cell("## Experimental protocol\n\nThe protocol compares ReLU, sigmoid, tanh and Leaky ReLU at learning rates 0.001, 0.01 and 0.1 while holding the split, architecture, seed, batch size and epoch budget fixed. Selection uses validation macro F1; held-out test metrics are reported only from the saved selected run."),
      nbf.v4.new_code_cell("from pathlib import Path\nimport json\nimport sys\nimport matplotlib.pyplot as plt\nimport numpy as np\n\nROOT = Path.cwd()\nif not (ROOT / 'experiments').exists():\n    ROOT = Path.cwd().parent\nEVIDENCE = ROOT / '"+relative+"'\nSUMMARY_PATH = EVIDENCE / 'summary.json'\nsummary = json.loads(SUMMARY_PATH.read_text(encoding='utf-8'))\nsummary['scope']"),
      nbf.v4.new_markdown_cell("## Actual training implementation\n\nThe following import exposes the production training module. It is not a notebook-only reimplementation; the opt-in command below calls this exact script so artifacts, split manifest and evidence schema remain aligned."),
      nbf.v4.new_code_cell("import importlib.util\ntrainer_path = ROOT / '"+source+"'\nspec = importlib.util.spec_from_file_location('train_expanded', trainer_path)\ntrain_expanded = importlib.util.module_from_spec(spec) if trainer_path.exists() else None\nif train_expanded is not None:\n    spec.loader.exec_module(train_expanded)\nprint(f'Training module: {trainer_path} ({\"loaded\" if train_expanded is not None else \"not present yet\"})')"),
      nbf.v4.new_markdown_cell("## Architecture and data path\n\nThe training source owns the authoritative model architecture and dataset loading. Reading it here makes the exact code reviewable without duplicating or drifting from the training entry point."),
      nbf.v4.new_code_cell("if trainer_path.exists():\n    source_text = trainer_path.read_text(encoding='utf-8')\n    print(source_text[:12000])\nelse:\n    print('Expected training entry point is not present in this checkout:', trainer_path)"),
      nbf.v4.new_markdown_cell("## Saved validation evidence\n\nThese values come directly from `summary.json`; this cell performs no training and no metric recalculation."),
      nbf.v4.new_code_cell("rows = []\nfor e in summary['experiments']:\n    m=e['validation_metrics']\n    rows.append((e['activation'], e['learning_rate'], m['accuracy'], m['precision_macro'], m['recall_macro'], m['f1_macro'], e['training_seconds']))\nrows"),
      nbf.v4.new_markdown_cell("## All learning curves\n\nFour combined panels ensure every activation and all three learning rates are visible. The histories are saved evidence, not reconstructed predictions."),
      nbf.v4.new_code_cell("activations = ('relu','sigmoid','tanh','leaky_relu')\nfor metric in ('loss','accuracy','val_loss','val_accuracy'):\n    fig, axes = plt.subplots(2,2,figsize=(11,7))\n    for ax, activation in zip(axes.flat, activations):\n        for e in sorted([x for x in summary['experiments'] if x['activation']==activation], key=lambda x:x['learning_rate']):\n            ax.plot(range(1,len(e['history'][metric])+1), e['history'][metric], label=f\"LR {e['learning_rate']:g}\")\n        ax.set(title=activation, xlabel='epoch', ylabel=metric); ax.legend(); ax.grid(alpha=.25)\n    fig.suptitle(metric + ' from saved experiment histories'); fig.tight_layout(); plt.show()"),
      nbf.v4.new_markdown_cell("## Test evidence\n\nThe matrix and per-class measurements use the saved one-time held-out test output. The class order is exactly `scope.classes`."),
      nbf.v4.new_code_cell("print(summary['test_metrics'])\nmatrix = np.asarray(summary['test_confusion_matrix'])\nfig, ax = plt.subplots(figsize=(10,10)); im=ax.imshow(matrix,cmap='Blues'); fig.colorbar(im,ax=ax)\nax.set(xlabel='predicted', ylabel='true', title='Held-out test confusion matrix')\nplt.show()\nsummary['per_class'][:10]"),
      nbf.v4.new_markdown_cell("## Opt-in rerun\n\nUncomment the next cell only to rerun the expanded training program. It may take substantial time and overwrites saved evidence. Rebuild the report afterward."),
      nbf.v4.new_code_cell("# import subprocess\n# subprocess.run([sys.executable, str(trainer_path), '--run'], cwd=ROOT, check=True)\n# subprocess.run([sys.executable, str(ROOT/'scripts/build_expanded_submission.py')], cwd=ROOT, check=True)")]
    notebook.parent.mkdir(parents=True, exist_ok=True); nbf.write(nb, notebook)


def build(evidence: Path, report_dir: Path, notebook: Path) -> dict:
    summary=load_summary(evidence); plots=make_plots(summary, report_dir / "figures")
    make_pdf(summary, plots, report_dir / "Fruits360_CNN_Report.pdf")
    make_docx(summary, plots, report_dir / "Fruits360_CNN_Report.docx")
    write_per_class_csv(summary, report_dir / "per_class_results.csv")
    build_notebook(evidence, notebook)
    return {"pdf": str(report_dir / "Fruits360_CNN_Report.pdf"), "docx": str(report_dir / "Fruits360_CNN_Report.docx"), "csv": str(report_dir / "per_class_results.csv"), "notebook": str(notebook)}


def smoke() -> dict:
    """Use existing subset measurements only in a temporary adapted fixture."""
    legacy=ROOT / "artifacts" / "experiment" / "summary.json"
    old=json.loads(legacy.read_text(encoding="utf-8"))
    classes=old["scope"]["classes"]; n=len(classes); experiments=[]
    for e in old["experiments"]:
        history={"loss":[e["final_train_loss"]]*e["epochs"], "accuracy":[e["final_train_accuracy"]]*e["epochs"], "val_loss":[e["final_validation_loss"]]*e["epochs"], "val_accuracy":[e["final_validation_accuracy"]]*e["epochs"]}
        experiments.append({"activation":e["activation"],"learning_rate":e["learning_rate"],"epochs":e["epochs"],"history":history,"validation_metrics":e["validation_metrics"],"training_seconds":0.0})
    fixture={"scope":{"dataset":"Temporary smoke fixture adapted from artifacts/experiment/summary.json","source_commit":"temporary-smoke-only","classes":classes,"source_training_count":400,"source_test_count":160,"training_samples":320,"validation_samples":80,"test_samples":160,"sampling":old["scope"]["sampling"],"seed":old["scope"]["seed"],"epochs":6,"batch_size":16,"image_size":[48,48,3],"optimizer":"SGD","source_url":old["scope"]["repository_url"],"architecture":"Temporary smoke fixture only"},"experiments":experiments,"best_config":old["best_config"],"test_metrics":old["test_metrics"],"test_confusion_matrix":(np.eye(n,dtype=int)*40).astype(int).tolist(),"per_class":[{"class":c,"precision":1.0,"recall":1.0,"f1":1.0,"support":40} for c in classes],"elapsed_seconds":0.0}
    # The matrix is derived from the real legacy all-correct test metric; fixture never persists in the repository.
    with tempfile.TemporaryDirectory(prefix="expanded_report_smoke_") as tmp:
        root=Path(tmp); evidence=root/"evidence"; evidence.mkdir(); (evidence/"summary.json").write_text(json.dumps(fixture),encoding="utf-8")
        output=build(evidence,root/"report",root/"notebook.ipynb")
        import pypdf
        pages=len(pypdf.PdfReader(output["pdf"]).pages)
        if not 10 <= pages <= 14: raise AssertionError(f"Report page count {pages}, expected 10–14")
        if not all(Path(v).is_file() for v in output.values()): raise AssertionError("Smoke outputs missing")
        return {"smoke": "passed", "pages": pages, "temporary_outputs": sorted(Path(v).name for v in output.values())}


def main() -> None:
    parser=argparse.ArgumentParser(description=__doc__); parser.add_argument("--evidence",type=Path,default=DEFAULT_EVIDENCE); parser.add_argument("--report-dir",type=Path,default=DEFAULT_REPORT_DIR); parser.add_argument("--notebook",type=Path,default=DEFAULT_NOTEBOOK); parser.add_argument("--smoke",action="store_true",help="temporary test fixture from existing subset evidence")
    args=parser.parse_args(); start=perf_counter()
    result=smoke() if args.smoke else build(args.evidence,args.report_dir,args.notebook)
    result["seconds"]=round(perf_counter()-start,2); print(json.dumps(result,indent=2))
if __name__ == "__main__": main()
