from __future__ import annotations

from pathlib import Path
import json
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from figure_config import RUN_DIR, OUT_DIR

# Merge-detection eval output (run_summary.json with n_merge_events /
# n_self_merge_events). This is produced by a SEPARATE merge-detection eval,
# not by the capsule's own metric stages, so it is optional: point
# FIGURE_MERGE_DIR at an "errors" dir to populate the merge-events panel,
# otherwise that panel is drawn with zeros and annotated "n/a".
_merge_dir_env = os.environ.get("FIGURE_MERGE_DIR")
MERGE_DIR = Path(_merge_dir_env) if _merge_dir_env else None
OUT_FIG = OUT_DIR / "794495_900k_summary_panels.png"
OUT_CSV = OUT_DIR / "794495_900k_summary_panels_stats.csv"


def _load_merge_summary() -> tuple[dict, bool]:
    """Return (summary, available). Falls back to zeros when absent."""
    if MERGE_DIR is not None:
        summary_path = MERGE_DIR / "run_summary.json"
        if summary_path.exists():
            return json.loads(summary_path.read_text()), True
    return {"n_merge_events": 0, "n_self_merge_events": 0}, False


def main() -> None:
    results = pd.read_csv(RUN_DIR / "partitioned-swcs/results.csv")
    merged = pd.read_csv(RUN_DIR / "merged-length.csv").rename(columns={"Neuron": "name"})
    df = results.merge(merged[["name", "GT Length (mm)", "Merged Length (mm)"]], on="name", how="left")
    df = df.sort_values(["omit_proportion", "correct_proportion"], ascending=[False, False]).reset_index(drop=True)
    merge_summary, merge_available = _load_merge_summary()
    fragment_counts = []
    mean_fragment_lengths = []
    pred_root = RUN_DIR / "predicted-components"
    for neuron in df["name"]:
        frag_paths = sorted((pred_root / neuron).glob("*.swc"))
        fragment_counts.append(len(frag_paths))
        frag_lengths = []
        for path in frag_paths:
            coords: dict[int, tuple[float, float, float]] = {}
            parents: dict[int, int] = {}
            for raw in path.read_text(errors="ignore").splitlines():
                line = raw.strip()
                if not line or line.startswith("#"):
                    continue
                parts = line.split()
                if len(parts) < 7:
                    continue
                nid = int(float(parts[0]))
                coords[nid] = (float(parts[2]), float(parts[3]), float(parts[4]))
                parents[nid] = int(float(parts[6]))
            total = 0.0
            for nid, parent in parents.items():
                if parent == -1 or nid not in coords or parent not in coords:
                    continue
                total += float(np.linalg.norm(np.asarray(coords[nid]) - np.asarray(coords[parent])))
            frag_lengths.append(total / 1000.0)
        mean_fragment_lengths.append(float(np.mean(frag_lengths)) if frag_lengths else 0.0)

    correct_arrays = []
    omit_arrays = []
    for neuron in df["name"]:
        correct_path = RUN_DIR / "intensity-npys" / f"{neuron}_correct.npy"
        omit_path = RUN_DIR / "intensity-npys" / f"{neuron}_omit.npy"
        if correct_path.exists():
            correct_arrays.append(np.load(correct_path, allow_pickle=False))
        if omit_path.exists():
            omit_arrays.append(np.load(omit_path, allow_pickle=False))
    pooled_correct = np.concatenate(correct_arrays) if correct_arrays else np.array([], dtype=float)
    pooled_omit = np.concatenate(omit_arrays) if omit_arrays else np.array([], dtype=float)

    mean_correct = float(df["correct_proportion"].mean())
    mean_omit = float(df["omit_proportion"].mean())
    estimated_merged_length = float(df.loc[df["Merged Length (mm)"] > 0, "Merged Length (mm)"].sum())

    stats = pd.DataFrame(
        [
            {
                "mean_correct_proportion": mean_correct,
                "mean_omit_proportion": mean_omit,
                "merge_events": int(merge_summary["n_merge_events"]),
                "self_merge_events": int(merge_summary["n_self_merge_events"]),
                "estimated_merged_length_mm": estimated_merged_length,
                "n_neurons": int(len(df)),
            }
        ]
    )
    stats.to_csv(OUT_CSV, index=False)

    labels = df["name"].tolist()
    x = np.arange(len(labels))

    fig = plt.figure(figsize=(24, 16), constrained_layout=True)
    gs = fig.add_gridspec(3, 3, height_ratios=[1.2, 1.0, 1.1])

    ax = fig.add_subplot(gs[0, :])
    ax.bar(x, df["correct_proportion"], color="#2ca02c", width=0.82, label="Correct")
    ax.bar(x, df["omit_proportion"], bottom=df["correct_proportion"], color="#d62728", width=0.82, label="Omit")
    ax.set_ylim(0, 1.0)
    ax.set_xticks(x, labels, rotation=45, ha="right")
    ax.set_ylabel("Proportion")
    ax.set_title("Per-neuron correct and omit proportions")
    ax.legend(frameon=False, ncol=2, loc="upper right")
    ax.grid(axis="y", alpha=0.2, linewidth=0.5)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    ax = fig.add_subplot(gs[1, 0])
    ax.bar([0], [mean_correct], color="#2ca02c", width=0.6, label="Correct")
    ax.bar([0], [mean_omit], bottom=[mean_correct], color="#d62728", width=0.6, label="Omit")
    ax.set_xlim(-0.8, 0.8)
    ax.set_ylim(0, 1.0)
    ax.set_xticks([0], ["900k"])
    ax.set_ylabel("Mean proportion")
    ax.set_title("Mean correct and omit")
    ax.text(0, max(mean_correct - 0.04, 0.02), f"{mean_correct:.3f}", ha="center", va="top", color="white", fontsize=10, fontweight="bold")
    ax.grid(axis="y", alpha=0.2, linewidth=0.5)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    ax = fig.add_subplot(gs[1, 1:3])
    pooled = np.concatenate([pooled_correct, pooled_omit]) if pooled_correct.size and pooled_omit.size else (pooled_correct if pooled_correct.size else pooled_omit)
    xmax = float(np.quantile(pooled, 0.995)) if pooled.size else 1.0
    bins = np.linspace(0.0, xmax if xmax > 0 else 1.0, 120)
    if pooled_correct.size:
        ax.hist(pooled_correct, bins=bins, density=True, color="#2ca02c", alpha=0.55, label="Correct")
    if pooled_omit.size:
        ax.hist(pooled_omit, bins=bins, density=True, color="#d62728", alpha=0.55, label="Omit")
    ax.set_xlabel("Intensity")
    ax.set_ylabel("Density")
    ax.set_title("Omit and correct intensity histogram")
    ax.legend(frameon=False)
    ax.grid(axis="y", alpha=0.2, linewidth=0.5)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    ax = fig.add_subplot(gs[2, 0])
    bp = ax.boxplot([fragment_counts], vert=True, patch_artist=True, showfliers=False, widths=0.5)
    bp["boxes"][0].set_facecolor("#4c78a8")
    bp["boxes"][0].set_alpha(0.55)
    ax.set_xlim(0.4, 1.6)
    ax.set_xticks([1], ["900k"])
    ax.set_ylabel("Predicted components per cell")
    ax.set_title("Fragments per cell")
    ax.grid(axis="y", alpha=0.2, linewidth=0.5)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    ax = fig.add_subplot(gs[2, 1])
    bp = ax.boxplot([mean_fragment_lengths], vert=True, patch_artist=True, showfliers=False, widths=0.5)
    bp["boxes"][0].set_facecolor("#59a14f")
    bp["boxes"][0].set_alpha(0.55)
    ax.set_xlim(0.4, 1.6)
    ax.set_xticks([1], ["900k"])
    ax.set_ylabel("Mean fragment length per cell (mm)")
    ax.set_title("Fragment length per cell")
    ax.grid(axis="y", alpha=0.2, linewidth=0.5)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    ax = fig.add_subplot(gs[2, 2])
    ax.bar([0], [int(merge_summary["n_merge_events"])], width=0.38, color="#ff8c00", label="Merge")
    ax.bar([0.5], [int(merge_summary["n_self_merge_events"])], width=0.38, color="#f3c38b", label="Self-merge")
    ax.set_xlim(-0.35, 0.85)
    ax.set_xticks([0, 0.5], ["Merge", "Self-merge"])
    ax.set_ylabel("Event count")
    ax.set_title("Merge-detection events")
    if not merge_available:
        ax.text(0.5, 0.5, "n/a\n(set FIGURE_MERGE_DIR)", ha="center", va="center",
                transform=ax.transAxes, color="#999999", fontsize=11)
    ax.legend(frameon=False)
    ax.grid(axis="y", alpha=0.2, linewidth=0.5)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    fig.suptitle("794495 900k checkpoint summary", fontsize=20)
    fig.savefig(OUT_FIG, dpi=220, bbox_inches="tight")
    plt.close(fig)
    print(OUT_FIG)
    print(OUT_CSV)


if __name__ == "__main__":
    main()
