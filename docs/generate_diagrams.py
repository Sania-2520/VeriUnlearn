"""Publication-quality architecture diagrams for VeriUnlearn."""

from __future__ import annotations

import math
import os
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import networkx as nx

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
OUTPUT_DIR = Path(__file__).resolve().parent / "figures"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

COLORS = [
    "#4C72B0", "#DD8452", "#55A868", "#C44E52", "#8172B3",
    "#937860", "#DA8BC3", "#8C8C8C", "#CCB974", "#64B5CD",
]

# Extended palette for diagrams
PALETTE = {
    "frontend": "#4C72B0",
    "backend": "#DD8452",
    "ml_engine": "#55A868",
    "database": "#C44E52",
    "cache": "#8172B3",
    "queue": "#937860",
    "storage": "#DA8BC3",
    "vector": "#64B5CD",
    "monitoring": "#8C8C8C",
    "proxy": "#CCB974",
    "crypto": "#C44E52",
    "governance": "#8172B3",
    "training": "#55A868",
    "verification": "#4C72B0",
    "audit": "#DD8452",
    "unlearning": "#DA8BC3",
    "certificate": "#8172B3",
    "compliance": "#937860",
}

FIG_WIDTH = 12
FIG_HEIGHT = 8
DPI = 300


def _setup_style():
    plt.rcParams.update({
        "font.family": "sans-serif",
        "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans"],
        "font.size": 10,
        "axes.titlesize": 13,
        "axes.labelsize": 11,
        "xtick.labelsize": 9,
        "ytick.labelsize": 9,
        "legend.fontsize": 9,
        "figure.dpi": DPI,
        "savefig.dpi": DPI,
        "savefig.bbox": "tight",
        "savefig.pad_inches": 0.05,
        "axes.grid": False,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.spines.left": False,
        "axes.spines.bottom": False,
        "lines.linewidth": 1.5,
    })


def _save(name: str):
    base = OUTPUT_DIR / name
    for ext in ("pdf", "png", "svg"):
        plt.savefig(str(base.with_suffix(f".{ext}")), format=ext, dpi=DPI)
    print(f"  Saved {name}.{{pdf,png,svg}}")


def _draw_box(ax, x, y, w, h, text, color="#4C72B0", text_color="white",
              fontsize=9, alpha=0.9, linewidth=1.5, subtext=None, subtext_color="#cccccc"):
    box = FancyBboxPatch((x - w / 2, y - h / 2), w, h,
                         boxstyle="round,rounding_size=3",
                         facecolor=color, edgecolor="white", linewidth=linewidth,
                         alpha=alpha)
    ax.add_patch(box)
    ax.text(x, y, text, ha="center", va="center", fontsize=fontsize,
            fontweight="bold", color=text_color)
    if subtext:
        ax.text(x, y - h * 0.25, subtext, ha="center", va="top", fontsize=fontsize - 2,
                color=subtext_color, style="italic")


def _draw_arrow(ax, x1, y1, x2, y2, color="#888888", lw=1.5, style="-",
                connectionstyle="arc3,rad=0.0", alpha=0.7):
    arrow = FancyArrowPatch((x1, y1), (x2, y2),
                            arrowstyle="-|>,head_width=4,head_length=6",
                            color=color, linewidth=lw, linestyle=style,
                            connectionstyle=connectionstyle,
                            alpha=alpha,
                            shrinkA=5, shrinkB=5)
    ax.add_patch(arrow)


def _draw_label(ax, x, y, text, fontsize=8, color="#666666", ha="center",
                va="bottom", rotation=0, fontweight="normal"):
    ax.text(x, y, text, fontsize=fontsize, color=color, ha=ha, va=va,
            rotation=rotation, fontweight=fontweight)


def _draw_database(ax, x, y, label, color="#C44E52", sublabel=None):
    r = 0.25
    cx, cy = x, y + r
    _draw_box(ax, cx, cy, r * 2.5, r * 0.6, label, color=color, fontsize=8)
    for i in range(3):
        layer_y = cy - r * 0.3 - i * r * 0.28
        rect = FancyBboxPatch((cx - r * 1.25, layer_y - r * 0.12),
                              r * 2.5, r * 0.24,
                              boxstyle="round,rounding_size=2",
                              facecolor=color, edgecolor="white",
                              linewidth=0.8, alpha=0.7 - i * 0.15)
        ax.add_patch(rect)
    if sublabel:
        _draw_label(ax, x, y - r * 1.1, sublabel, fontsize=7)


# ---------------------------------------------------------------------------
# 1. architecture_overview
# ---------------------------------------------------------------------------
def architecture_overview():
    fig, ax = plt.subplots(figsize=(FIG_WIDTH, FIG_HEIGHT))
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 8)
    ax.set_aspect("equal")
    ax.set_title("VeriUnlearn — System Architecture Overview", fontweight="bold", fontsize=15, pad=15)

    # ---- Row 5 (top): External / Users ----
    _draw_box(ax, 2.0, 7.5, 2.0, 0.5, "Users / Browsers", PALETTE["frontend"], fontsize=8)
    _draw_box(ax, 5.5, 7.5, 2.0, 0.5, "API Clients", PALETTE["frontend"], fontsize=8)
    _draw_box(ax, 9.0, 7.5, 1.8, 0.5, "External Systems", PALETTE["frontend"], fontsize=8)

    # ---- Row 4: Frontend + Nginx ----
    _draw_box(ax, 2.0, 6.3, 2.5, 0.6, "Frontend (Next.js 15 / React 19)", PALETTE["frontend"], fontsize=8)
    _draw_box(ax, 6.0, 6.3, 2.0, 0.6, "Nginx Reverse Proxy", PALETTE["proxy"], fontsize=8)

    _draw_arrow(ax, 2.0, 7.25, 2.0, 6.6, "#888888")
    _draw_arrow(ax, 5.5, 7.25, 5.5, 6.9, "#888888")
    _draw_arrow(ax, 9.0, 7.25, 9.0, 6.9, "#888888")
    _draw_arrow(ax, 9.0, 6.9, 6.0, 6.9, "#888888", style="--")

    # ---- Row 3: Backend + ML Engine ----
    _draw_box(ax, 2.0, 5.0, 3.5, 0.8, "Backend API (FastAPI + Uvicorn)", PALETTE["backend"], fontsize=9,
              subtext="SQLAlchemy 2.0 | Pydantic v2 | Celery | 55 per-request services",
              subtext_color="#dddddd")
    _draw_box(ax, 7.0, 5.0, 3.0, 0.8, "ML Engine (PyTorch, LoRA, Transformers)", PALETTE["ml_engine"], fontsize=9,
              subtext="5 unlearning algorithms | 5 verification strategies",
              subtext_color="#dddddd")
    _draw_box(ax, 10.5, 5.0, 2.0, 0.8, "Celery Workers", PALETTE["queue"], fontsize=8,
              subtext="Async task execution", subtext_color="#dddddd")

    _draw_arrow(ax, 6.0, 6.0, 2.0, 5.4, "#888888")
    _draw_arrow(ax, 2.0, 4.2, 2.0, 3.0, "#888888")

    _draw_arrow(ax, 6.0, 6.0, 7.0, 5.4, "#888888")
    _draw_arrow(ax, 7.0, 4.2, 7.0, 3.0, "#888888")

    _draw_arrow(ax, 8.5, 5.0, 10.5, 5.0, "#888888")

    # Row 3.5: Monitoring
    _draw_box(ax, 10.5, 6.3, 2.5, 0.5, "Prometheus / Grafana / Loki / Alertmanager", PALETTE["monitoring"], fontsize=7)

    _draw_arrow(ax, 10.5, 5.8, 10.5, 6.05, "#888888", style="--")
    _draw_arrow(ax, 6.0, 6.3, 10.5, 6.3, "#888888", style="--")

    # ---- Row 2: Data layer ----
    _draw_database(ax, 2.0, 2.5, "PostgreSQL", PALETTE["database"], "Primary DB")
    _draw_database(ax, 4.5, 2.5, "Redis", PALETTE["cache"], "Cache / Queue")
    _draw_database(ax, 7.0, 2.5, "Qdrant", PALETTE["vector"], "Vector Store")
    _draw_database(ax, 9.5, 2.5, "MinIO", PALETTE["storage"], "Object Storage")

    _draw_arrow(ax, 2.0, 3.0, 2.0, 3.8, "#888888")
    _draw_arrow(ax, 4.5, 3.0, 3.5, 4.2, "#888888")
    _draw_arrow(ax, 4.5, 2.5, 10.5, 2.5, "#888888", style="--")
    _draw_arrow(ax, 7.0, 3.0, 6.0, 4.2, "#888888")
    _draw_arrow(ax, 9.5, 3.0, 9.5, 4.2, "#888888")

    # ---- Row 1: RabbitMQ ----
    _draw_box(ax, 2.0, 1.0, 2.5, 0.5, "RabbitMQ (Message Broker)", PALETTE["queue"], fontsize=8)
    _draw_arrow(ax, 2.0, 2.0, 2.0, 1.3, "#888888")

    legend_elements = [
        mpatches.Patch(color=c, label=l) for c, l in [
            (PALETTE["frontend"], "Frontend"),
            (PALETTE["backend"], "Backend API"),
            (PALETTE["ml_engine"], "ML Engine"),
            (PALETTE["database"], "Database"),
            (PALETTE["cache"], "Cache"),
            (PALETTE["queue"], "Queue / Broker"),
            (PALETTE["monitoring"], "Monitoring"),
            (PALETTE["proxy"], "Proxy"),
        ]
    ]
    ax.legend(handles=legend_elements, loc="lower right", fontsize=7,
              framealpha=0.9, edgecolor="#cccccc", ncol=2)
    ax.axis("off")
    _save("architecture_overview")
    plt.close(fig)


# ---------------------------------------------------------------------------
# 2. training_pipeline
# ---------------------------------------------------------------------------
def training_pipeline():
    fig, ax = plt.subplots(figsize=(FIG_WIDTH, 4))
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 4)
    ax.set_title("VeriUnlearn — Training Pipeline", fontweight="bold", fontsize=14, pad=10)

    stages = [
        (1.0, "Data\nIngestion", PALETTE["database"]),
        (3.0, "Pre-\nprocessing", PALETTE["backend"]),
        (5.0, "Feature\nExtraction", PALETTE["ml_engine"]),
        (7.0, "LoRA\nTraining", PALETTE["training"]),
        (9.0, "Model\nEvaluation", PALETTE["verification"]),
        (11.0, "Model\nRegistry", PALETTE["certificate"]),
    ]

    for i, (x, label, color) in enumerate(stages):
        _draw_box(ax, x, 2.0, 1.6, 1.2, label, color=color, fontsize=9)
        if i < len(stages) - 1:
            _draw_arrow(ax, x + 0.8, 2.0, stages[i + 1][0] - 0.8, 2.0, "#888888")

    labels = [
        "Datasets from\nPostgreSQL / MinIO",
        "Tokenization,\nnormalization,\nsplitting",
        "Embeddings via\nTransformer\nencoders",
        "PEFT with\n4-bit QLoRA\nadapter layers",
        "Accuracy, F1,\nloss, privacy\nmetrics",
        "Versioned,\nhashed, stored\nin PostgreSQL",
    ]
    for i, (x, _, _) in enumerate(stages):
        _draw_label(ax, x, 0.7, labels[i], fontsize=7, color="#666666")

    ax.axis("off")
    _save("training_pipeline")
    plt.close(fig)


# ---------------------------------------------------------------------------
# 3. unlearning_pipeline
# ---------------------------------------------------------------------------
def unlearning_pipeline():
    fig, ax = plt.subplots(figsize=(FIG_WIDTH, 5))
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 5)
    ax.set_title("VeriUnlearn — Machine Unlearning Pipeline", fontweight="bold", fontsize=14, pad=10)

    stages = [
        (1.0, "Deletion\nRequest", PALETTE["audit"]),
        (2.8, "Validation\nEngine", PALETTE["backend"]),
        (4.6, "Checkpoint\nSnapshot", PALETTE["storage"]),
        (6.4, "Algorithm\nSelection", PALETTE["unlearning"]),
        (8.2, "Unlearning\nExecution", PALETTE["ml_engine"]),
        (10.0, "Verification\nSuite", PALETTE["verification"]),
    ]

    for i, (x, label, color) in enumerate(stages):
        _draw_box(ax, x, 2.5, 1.4, 1.2, label, color=color, fontsize=8)
        if i < len(stages) - 1:
            _draw_arrow(ax, x + 0.7, 2.5, stages[i + 1][0] - 0.7, 2.5, "#888888")

    # side branches
    _draw_box(ax, 5.5, 4.2, 2.5, 0.5, "Adaptive Controller: SISA / Influence / Fine-Tune / SCRUB / Retrain",
              PALETTE["unlearning"], fontsize=7, subtext_color="#dddddd")
    _draw_arrow(ax, 6.4, 3.1, 6.4, 3.95, "#888888", style="-")

    _draw_box(ax, 10.0, 0.6, 2.8, 0.5,
              "Hash | Merkle | Influence | MIA | Forget Quality",
              PALETTE["verification"], fontsize=7, subtext_color="#dddddd")
    _draw_arrow(ax, 10.0, 1.9, 10.0, 0.85, "#888888")

    details = [
        "User/API\ninitiates",
        "Integrity &\nformat check",
        "Pre-unlearning\nmodel snapshot",
        "Automatic or\nmanual selection",
        "Algorithm\nruns on ML\nEngine",
        "5 strategies\ncryptographic\nproofs",
    ]
    for i, (x, _, _) in enumerate(stages):
        _draw_label(ax, x, 0.2, details[i], fontsize=7, color="#666666")

    ax.axis("off")
    _save("unlearning_pipeline")
    plt.close(fig)


# ---------------------------------------------------------------------------
# 4. verification_pipeline
# ---------------------------------------------------------------------------
def verification_pipeline():
    G = nx.DiGraph()
    plt.figure(figsize=(FIG_WIDTH, 6))

    stages = [
        ("Artifact\nHash", "SHA-256\nfingerprint\nof model\nweights"),
        ("Hash\nChain", "Cryptographic\nlinking of\nhashes"),
        ("Merkle\nTree", "Binary tree\nroot = combined\nhash"),
        ("Ed25519\nSignature", "Libsodium\nsign root\nwith private key"),
        ("Verification\nCertificate", "X.509-style\ncertificate\nwith proof"),
        ("Trust\nScore", "Weighted\naggregate\n(0-100)"),
    ]

    pos = {}
    y_center = 0.0
    for i, (label, desc) in enumerate(stages):
        x = i * 2.0
        y_center = 0.0 if i % 2 == 0 else -1.5
        pos[label] = (x, y_center if i < 3 else y_center)
        G.add_node(label)

    for i in range(len(stages) - 1):
        G.add_edge(stages[i][0], stages[i + 1][0])

    nx.draw_networkx_nodes(G, pos, node_size=3500, node_color=[PALETTE["crypto"]] * 3 + [PALETTE["verification"]] * 3,
                           node_shape="o", edgecolors="white", linewidths=2)
    nx.draw_networkx_labels(G, pos, font_size=8, font_weight="bold", font_color="white")

    descriptions = {label: desc for label, desc in stages}
    for label, (x, y) in pos.items():
        plt.text(x, y - 0.7, descriptions[label], ha="center", va="top",
                 fontsize=7, color="#666666")

    nx.draw_networkx_edges(G, pos, edge_color="#888888", width=2.0, arrows=True,
                           arrowsize=20, arrowstyle="-|>,head_width=6,head_length=8",
                           connectionstyle="arc3,rad=0.1")

    plt.xlim(-0.5, 10.5)
    plt.ylim(-3.0, 1.5)
    plt.axis("off")
    plt.title("VeriUnlearn — Cryptographic Verification Pipeline", fontweight="bold", fontsize=14, pad=15)
    _save("verification_pipeline")
    plt.close()


# ---------------------------------------------------------------------------
# 5. benchmark_pipeline
# ---------------------------------------------------------------------------
def benchmark_pipeline():
    fig, ax = plt.subplots(figsize=(FIG_WIDTH, 4.5))
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 4.5)
    ax.set_title("VeriUnlearn — Evaluation Benchmark Pipeline", fontweight="bold", fontsize=14, pad=10)

    stages = [
        (1.0, "Dataset\nLoading", PALETTE["database"]),
        (3.2, "Algorithm\nSelection", PALETTE["ml_engine"]),
        (5.4, "Unlearning\nExecution", PALETTE["unlearning"]),
        (7.6, "Metric\nComputation", PALETTE["verification"]),
        (9.8, "Report\nGeneration", PALETTE["certificate"]),
    ]

    for i, (x, label, color) in enumerate(stages):
        _draw_box(ax, x, 2.5, 1.8, 1.2, label, color=color, fontsize=9)
        if i < len(stages) - 1:
            _draw_arrow(ax, x + 0.9, 2.5, stages[i + 1][0] - 0.9, 2.5, "#888888")

    _draw_box(ax, 5.5, 0.8, 4.0, 0.5,
              "Datasets: CIFAR-10 / CIFAR-100 / MNIST / Fashion-MNIST / SVHN",
              PALETTE["database"], fontsize=7)
    _draw_arrow(ax, 2.8, 1.9, 4.0, 1.05, "#888888", style="--")

    sub_labels = [
        "PostgreSQL\nMinIO\nQdrant",
        "Retrain\nSISA\nSCRUB\nInfluence\nFine-Tune",
        "Forget ratio\nconfig\nMulti-run\nrepeat",
        "Accuracy\nF1\nMIA\nTrust score\nEfficiency",
        "PDF/PNG\nJSON/CSV\nLeaderboard\nPublication",
    ]
    for i, (x, _, _) in enumerate(stages):
        _draw_label(ax, x, 4.0, sub_labels[i], fontsize=7, color="#666666")

    ax.axis("off")
    _save("benchmark_pipeline")
    plt.close(fig)


# ---------------------------------------------------------------------------
# 6. deployment_architecture
# ---------------------------------------------------------------------------
def deployment_architecture():
    fig, ax = plt.subplots(figsize=(FIG_WIDTH, FIG_HEIGHT))
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 8)
    ax.set_title("VeriUnlearn — Kubernetes Deployment Architecture", fontweight="bold", fontsize=14, pad=15)

    # Namespace boxes
    ns_y = 6.5

    # Ingress at top
    _draw_box(ax, 6.0, 7.5, 4.0, 0.6, "Ingress Controller (NGINX / Traefik)", PALETTE["proxy"], fontsize=9,
              subtext="TLS termination | Rate limiting | JWT validation",
              subtext_color="#dddddd")

    # App namespace
    ax.add_patch(FancyBboxPatch((0.3, 3.0), 3.8, 3.2,
                                boxstyle="round,rounding_size=4",
                                facecolor="none", edgecolor=PALETTE["frontend"],
                                linewidth=1.5, linestyle="--"))
    _draw_label(ax, 2.2, 6.15, "Namespace: veriunlearn-app", fontsize=9, color=PALETTE["frontend"], fontweight="bold")

    app_svcs = [
        (0.8, 5.2, "Frontend\nNext.js"),
        (2.6, 5.2, "Backend API\nFastAPI"),
        (0.8, 4.0, "Auth Service\nJWT + RBAC"),
        (2.6, 4.0, "Governance\nEngine"),
        (1.7, 3.5, "Webhook\nDispatcher"),
    ]
    for x, y, label in app_svcs:
        _draw_box(ax, x, y, 1.4, 0.55, label, PALETTE["frontend"], fontsize=7)

    # ML namespace
    ax.add_patch(FancyBboxPatch((4.3, 3.0), 3.6, 3.2,
                                boxstyle="round,rounding_size=4",
                                facecolor="none", edgecolor=PALETTE["ml_engine"],
                                linewidth=1.5, linestyle="--"))
    _draw_label(ax, 6.1, 6.15, "Namespace: veriunlearn-ml", fontsize=9, color=PALETTE["ml_engine"], fontweight="bold")

    ml_svcs = [
        (4.8, 5.2, "ML Engine\nPyTorch"),
        (6.6, 5.2, "Verification\nEngine"),
        (4.8, 4.0, "Unlearning\nWorkers"),
        (6.6, 4.0, "Inference\nService"),
        (5.7, 3.5, "Benchmark\nRunner"),
    ]
    for x, y, label in ml_svcs:
        _draw_box(ax, x, y, 1.4, 0.55, label, PALETTE["ml_engine"], fontsize=7)

    # Infra namespace
    ax.add_patch(FancyBboxPatch((8.1, 3.0), 3.6, 3.2,
                                boxstyle="round,rounding_size=4",
                                facecolor="none", edgecolor=PALETTE["database"],
                                linewidth=1.5, linestyle="--"))
    _draw_label(ax, 9.9, 6.15, "Namespace: veriunlearn-infra", fontsize=9, color=PALETTE["database"], fontweight="bold")

    infra_svcs = [
        (8.6, 5.2, "PostgreSQL"),
        (10.4, 5.2, "Redis"),
        (8.6, 4.0, "Qdrant"),
        (10.4, 4.0, "MinIO"),
        (9.5, 3.5, "RabbitMQ"),
    ]
    for x, y, label in infra_svcs:
        _draw_box(ax, x, y, 1.2, 0.55, label, PALETTE["database"], fontsize=7)

    # Monitoring namespace
    ax.add_patch(FancyBboxPatch((0.3, 0.3), 3.8, 2.2,
                                boxstyle="round,rounding_size=4",
                                facecolor="none", edgecolor=PALETTE["monitoring"],
                                linewidth=1.5, linestyle="--"))
    _draw_label(ax, 2.2, 2.4, "Namespace: veriunlearn-monitoring", fontsize=8, color=PALETTE["monitoring"], fontweight="bold")

    mon_svcs = [
        (0.8, 1.5, "Prometheus"),
        (2.4, 1.5, "Grafana"),
        (4.0, 1.5, "Loki"),
        (2.4, 0.7, "Alertmanager"),
    ]
    for x, y, label in mon_svcs:
        _draw_box(ax, x, y, 1.3, 0.4, label, PALETTE["monitoring"], fontsize=7)

    # Arrows between namespaces
    _draw_arrow(ax, 6.0, 7.2, 2.2, 5.5, "#888888")
    _draw_arrow(ax, 6.0, 7.2, 6.1, 5.5, "#888888")
    _draw_arrow(ax, 4.1, 4.5, 4.5, 4.5, "#888888")
    _draw_arrow(ax, 7.9, 4.5, 8.3, 4.5, "#888888")
    _draw_arrow(ax, 2.2, 4.5, 2.2, 2.5, "#888888", style="--")

    # Legend
    legend = [
        mpatches.Patch(color=PALETTE["frontend"], label="App Services"),
        mpatches.Patch(color=PALETTE["ml_engine"], label="ML Services"),
        mpatches.Patch(color=PALETTE["database"], label="Infrastructure"),
        mpatches.Patch(color=PALETTE["monitoring"], label="Monitoring"),
        mpatches.Patch(color="none", label="HPA | Cert-Manager | External Secrets"),
    ]
    ax.legend(handles=legend, loc="lower right", fontsize=7, framealpha=0.9,
              edgecolor="#cccccc", ncol=2)
    ax.axis("off")
    _save("deployment_architecture")
    plt.close(fig)


# ---------------------------------------------------------------------------
# 7. component_diagram
# ---------------------------------------------------------------------------
def component_diagram():
    fig, ax = plt.subplots(figsize=(FIG_WIDTH, FIG_HEIGHT))
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 8)
    ax.set_title("VeriUnlearn — System Component Diagram", fontweight="bold", fontsize=14, pad=15)

    layers = [
        (6.0, 7.2, "Presentation Layer", 10.5, 0.5),
        (6.0, 5.5, "Application Layer", 10.5, 1.2),
        (6.0, 3.5, "Domain Layer", 10.5, 1.5),
        (6.0, 1.0, "Infrastructure Layer", 10.5, 2.0),
    ]
    colors = ["#4C72B0", "#DD8452", "#55A868", "#8172B3"]

    for i, (cx, cy, label, w, h) in enumerate(layers):
        alpha = 0.08
        ax.add_patch(FancyBboxPatch((cx - w / 2, cy - h / 2), w, h,
                                     boxstyle="round,rounding_size=6",
                                     facecolor=colors[i], edgecolor=colors[i],
                                     linewidth=1.5, alpha=alpha))
        _draw_label(ax, cx, cy + h / 2 - 0.2, label, fontsize=10, fontweight="bold",
                    color=colors[i])

    # Presentation layer components
    comps_pres = [
        (2.0, 7.2, "Next.js 15\nReact 19 UI"),
        (5.0, 7.2, "TailwindCSS\nShadcn UI"),
        (8.0, 7.2, "Zustand\nReact Query"),
        (10.5, 7.2, "SSE / WebSocket\nStreaming"),
    ]
    for x, y, label in comps_pres:
        _draw_box(ax, x, y, 1.8, 0.5, label, colors[0], fontsize=7, alpha=0.7)

    # Application layer
    comps_app = [
        (1.0, 5.8, "Auth Service\nJWT / OAuth"),
        (3.0, 5.8, "Unlearning\nService"),
        (5.0, 5.8, "Verification\nService"),
        (7.0, 5.8, "Governance\nService"),
        (9.0, 5.8, "Compliance\nService"),
        (11.0, 5.8, "Benchmark\nService"),
        (2.0, 4.8, "Celery\nWorkers"),
        (5.0, 4.8, "Event Bus\n44 events"),
        (8.0, 4.8, "Plugin\nManager"),
        (10.5, 4.8, "Audit\nService"),
    ]
    for x, y, label in comps_app:
        _draw_box(ax, x, y, 1.6, 0.45, label, colors[1], fontsize=7, alpha=0.7)

    # Domain layer
    comps_domain = [
        (1.5, 3.7, "User / Tenant\nModels"),
        (3.5, 3.7, "Unlearning\nModels"),
        (5.5, 3.7, "Verification\nModels"),
        (7.5, 3.7, "Governance\nModels"),
        (9.5, 3.7, "Research\nModels"),
        (11.0, 3.7, "Audit\nModels"),
        (2.5, 2.7, "ML Algorithms\nSISA / Influence / etc."),
        (5.5, 2.7, "Verification\nStrategies (5)"),
        (8.5, 2.7, "Crypto\nEd25519 / SHA-256"),
        (10.5, 2.7, "RBAC\n8 roles / 24 perms"),
    ]
    for x, y, label in comps_domain:
        _draw_box(ax, x, y, 1.6, 0.45, label, colors[2], fontsize=7, alpha=0.7)

    # Infrastructure layer
    comps_infra = [
        (1.0, 1.3, "PostgreSQL"),
        (3.0, 1.3, "Redis"),
        (5.0, 1.3, "Qdrant"),
        (7.0, 1.3, "MinIO"),
        (9.0, 1.3, "RabbitMQ"),
        (11.0, 1.3, "Nginx"),
        (2.5, 0.5, "Docker /\nDocker Compose"),
        (5.5, 0.5, "Kubernetes\n(3 namespaces)"),
        (8.5, 0.5, "Prometheus /\nGrafana"),
    ]
    for x, y, label in comps_infra:
        _draw_box(ax, x, y, 1.6, 0.4, label, colors[3], fontsize=7, alpha=0.7)

    # layer connectors
    for x in [2.0, 5.0, 8.0, 10.5]:
        _draw_arrow(ax, x, 7.0, x, 6.1, "#cccccc", style="--", lw=0.8)
        _draw_arrow(ax, x, 5.0, x, 4.3, "#cccccc", style="--", lw=0.8)
        _draw_arrow(ax, x, 3.0, x, 2.2, "#cccccc", style="--", lw=0.8)

    ax.axis("off")
    _save("component_diagram")
    plt.close(fig)


# ---------------------------------------------------------------------------
# 8. governance_pipeline
# ---------------------------------------------------------------------------
def governance_pipeline():
    fig, ax = plt.subplots(figsize=(FIG_WIDTH, 5))
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 5)
    ax.set_title("VeriUnlearn — Governance & Compliance Workflow", fontweight="bold", fontsize=14, pad=10)

    stages = [
        (1.0, "Consent\nManagement", PALETTE["governance"]),
        (3.0, "Policy\nEvaluation", PALETTE["compliance"]),
        (5.0, "Compliance\nWorkflow", PALETTE["governance"]),
        (7.0, "Approval\nEngine", PALETTE["audit"]),
        (9.0, "Deletion\nExecution", PALETTE["unlearning"]),
        (11.0, "Audit\nLogging", PALETTE["audit"]),
    ]

    for i, (x, label, color) in enumerate(stages):
        _draw_box(ax, x, 2.5, 1.6, 1.0, label, color=color, fontsize=8)
        if i < len(stages) - 1:
            _draw_arrow(ax, x + 0.8, 2.5, stages[i + 1][0] - 0.8, 2.5, "#888888")

    # Sidebar branches
    _draw_box(ax, 1.0, 4.2, 2.5, 0.4,
              "Consent Lifecycle: Granted / Withdrawn / Expired / Updated",
              PALETTE["governance"], fontsize=7)
    _draw_arrow(ax, 1.0, 3.5, 1.0, 4.0, "#888888", style="--")

    _draw_box(ax, 5.0, 0.7, 4.0, 0.4,
              "Approval Levels: Standard → Escalated → Multi-party",
              PALETTE["audit"], fontsize=7)
    _draw_arrow(ax, 7.0, 1.5, 7.0, 1.0, "#888888", style="--")

    sub_labels = [
        "Data subject\nconsent records\nimmutable history",
        "Configured rules\nviolation detection\nrisk scoring",
        "Workflow steps\ntimeline\nnotifications",
        "Multi-level\napproval with\nescalation",
        "Unlinking data\nfrom model\ncrypto proof",
        "Hash-chain\nimmutable log\nblockchain anchor",
    ]
    for i, (x, _, _) in enumerate(stages):
        _draw_label(ax, x, 0.1, sub_labels[i], fontsize=7, color="#666666")

    ax.axis("off")
    _save("governance_pipeline")
    plt.close(fig)


# ---------------------------------------------------------------------------
# 9. compliance_workflow
# ---------------------------------------------------------------------------
def compliance_workflow():
    fig, ax = plt.subplots(figsize=(FIG_WIDTH, 6))
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 6)
    ax.set_title("VeriUnlearn — GDPR Compliance Workflow", fontweight="bold", fontsize=14, pad=10)

    # Main flow
    steps = [
        (1.0, 3.0, "Right to\nbe Forgotten", PALETTE["compliance"]),
        (3.5, 3.0, "Identity\nVerification", PALETTE["backend"]),
        (6.0, 3.0, "Deletion\nRequest", PALETTE["audit"]),
        (8.5, 3.0, "Unlearning\nPipeline", PALETTE["unlearning"]),
        (11.0, 3.0, "Deletion\nCertificate", PALETTE["certificate"]),
    ]

    for i, (x, y, label, color) in enumerate(steps):
        _draw_box(ax, x, y, 2.0, 1.0, label, color=color, fontsize=8)
        if i < len(steps) - 1:
            _draw_arrow(ax, x + 1.0, y, steps[i + 1][0] - 1.0, y, "#888888")

    # Compliance branches
    _draw_box(ax, 6.0, 5.0, 5.0, 0.5,
              "GDPR Article 17 | Article 16 | Article 32 Compliance",
              PALETTE["compliance"], fontsize=7)
    _draw_arrow(ax, 6.0, 4.0, 6.0, 4.7, "#888888", style="--")

    _draw_box(ax, 6.0, 1.0, 5.0, 0.5,
              "Audit Trail: SHA-256 hash chain → Immutable log → Blockchain anchor",
              PALETTE["audit"], fontsize=7)
    _draw_arrow(ax, 8.5, 2.5, 8.5, 1.3, "#888888", style="--")

    details = [
        "Data subject\nsubmits request",
        "Verify identity\nvia JWT or\nOAuth",
        "Track request\nstatus and\ntimeline",
        "Run algorithm\nwith crypto\nverification",
        "Ed25519-signed\ncertificate\nwith QR code",
    ]
    for i, (x, y, _, _) in enumerate(steps):
        _draw_label(ax, x, y - 0.9, details[i], fontsize=7, color="#666666")

    # 72h SLA box
    _draw_box(ax, 6.0, 5.5, 3.0, 0.35, "GDPR 72-hour SLA Enforcement", PALETTE["compliance"], fontsize=7)

    ax.axis("off")
    _save("compliance_workflow")
    plt.close(fig)


# ---------------------------------------------------------------------------
# 10. database_schema
# ---------------------------------------------------------------------------
def database_schema():
    G = nx.DiGraph()
    plt.figure(figsize=(FIG_WIDTH, 8))

    entities = {
        "Tenant": PALETTE["database"],
        "User": PALETTE["frontend"],
        "Deletion\nRequest": PALETTE["audit"],
        "Unlearning\nJob": PALETTE["unlearning"],
        "Verification\nCertificate": PALETTE["certificate"],
        "Audit\nLog": PALETTE["compliance"],
        "Model\nVersion": PALETTE["ml_engine"],
        "Proof\nRecord": PALETTE["verification"],
        "Compliance\nReport": PALETTE["governance"],
        "Consent\nRecord": PALETTE["compliance"],
    }

    G.add_nodes_from(entities.keys())

    edges = [
        ("Tenant", "User", "1:N"),
        ("Tenant", "Deletion\nRequest", "1:N"),
        ("Tenant", "Audit\nLog", "1:N"),
        ("Tenant", "Consent\nRecord", "1:N"),
        ("User", "Deletion\nRequest", "1:N"),
        ("Deletion\nRequest", "Unlearning\nJob", "1:1"),
        ("Unlearning\nJob", "Proof\nRecord", "1:1"),
        ("Proof\nRecord", "Verification\nCertificate", "1:1"),
        ("Unlearning\nJob", "Model\nVersion", "N:1"),
        ("Model\nVersion", "Model\nVersion", "1:N parent"),
        ("Consent\nRecord", "Audit\nLog", "1:N"),
        ("Deletion\nRequest", "Audit\nLog", "1:N"),
        ("User", "Consent\nRecord", "1:N"),
        ("Deletion\nRequest", "Verification\nCertificate", "1:1"),
        ("Tenant", "Compliance\nReport", "1:N"),
        ("Compliance\nReport", "Audit\nLog", "1:N"),
    ]

    for src, dst, label in edges:
        G.add_edge(src, dst, label=label)

    pos = nx.spring_layout(G, k=2.5, iterations=100, seed=42)

    nx.draw_networkx_nodes(G, pos, node_size=4500, node_color=[entities[n] for n in G.nodes()],
                           node_shape="s", edgecolors="white", linewidths=2)
    nx.draw_networkx_labels(G, pos, font_size=9, font_weight="bold", font_color="white")

    nx.draw_networkx_edges(G, pos, edge_color="#888888", width=1.5, arrows=True,
                           arrowsize=15, arrowstyle="-|>,head_width=4,head_length=6",
                           connectionstyle="arc3,rad=0.15",
                           node_size=4500)

    edge_labels = {(u, v): d["label"] for u, v, d in G.edges(data=True)}
    nx.draw_networkx_edge_labels(G, pos, edge_labels=edge_labels, font_size=7,
                                 font_color="#666666", label_pos=0.5)

    plt.axis("off")
    plt.title("VeriUnlearn — Database Entity-Relationship Diagram", fontweight="bold", fontsize=14, pad=15)
    _save("database_schema")
    plt.close()


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------
def main():
    print("=" * 60)
    print("VeriUnlearn — Publication-Quality Architecture Diagrams")
    print("=" * 60)
    _setup_style()

    generators = [
        ("Architecture Overview", architecture_overview),
        ("Training Pipeline", training_pipeline),
        ("Unlearning Pipeline", unlearning_pipeline),
        ("Verification Pipeline", verification_pipeline),
        ("Benchmark Pipeline", benchmark_pipeline),
        ("Deployment Architecture", deployment_architecture),
        ("Component Diagram", component_diagram),
        ("Governance Pipeline", governance_pipeline),
        ("Compliance Workflow", compliance_workflow),
        ("Database Schema", database_schema),
    ]

    for name, func in generators:
        print(f"\n[{name}]")
        func()

    print(f"\n{'=' * 60}")
    print(f"All diagrams saved to: {OUTPUT_DIR}")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
