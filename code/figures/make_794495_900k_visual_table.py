from __future__ import annotations

import colorsys
import hashlib
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.collections import LineCollection

from figure_config import RUN_DIR, OUT_DIR


OUT_PATH = OUT_DIR / "794495_900k_visual_table.png"
CSV_PATH = OUT_DIR / "794495_900k_visual_table_order.csv"
VOXEL_SCALE_XY = 0.748


def load_swc_xyz(path: Path) -> tuple[np.ndarray, np.ndarray]:
    coords: dict[int, tuple[float, float, float]] = {}
    parents: dict[int, int] = {}
    for raw_line in path.read_text(errors="ignore").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        if len(parts) < 7:
            continue
        nid = int(float(parts[0]))
        coords[nid] = (float(parts[2]), float(parts[3]), float(parts[4]))
        parents[nid] = int(float(parts[6]))
    if not coords:
        return np.empty((0, 3), dtype=float), np.empty((0, 2, 3), dtype=float)
    node_ids = sorted(coords)
    pts = np.asarray([coords[n] for n in node_ids], dtype=float)
    segs = []
    for nid, parent in parents.items():
        if parent == -1 or parent not in coords or nid not in coords:
            continue
        segs.append([coords[nid], coords[parent]])
    return pts, np.asarray(segs, dtype=float) if segs else np.empty((0, 2, 3), dtype=float)


def swc_length_mm(path: Path) -> float:
    _, segs = load_swc_xyz(path)
    if segs.size == 0:
        return 0.0
    lengths = np.linalg.norm(segs[:, 0, :] - segs[:, 1, :], axis=1)
    return float(lengths.sum() / 1000.0)


def bright_color(key: str) -> tuple[float, float, float]:
    digest = hashlib.md5(key.encode("utf-8")).digest()
    hue = digest[0] / 255.0
    sat = 0.72 + 0.18 * (digest[1] / 255.0)
    val = 0.90 + 0.08 * (digest[2] / 255.0)
    return colorsys.hsv_to_rgb(hue, sat, min(val, 1.0))


def add_segments(ax: plt.Axes, segs_xy: np.ndarray, color, linewidth: float, alpha: float = 1.0) -> None:
    if segs_xy.size == 0:
        return
    lc = LineCollection(segs_xy, colors=[color], linewidths=linewidth, alpha=alpha)
    ax.add_collection(lc)


def main() -> None:
    results = pd.read_csv(RUN_DIR / "partitioned-swcs/results.csv")
    merged = pd.read_csv(RUN_DIR / "merged-length.csv")
    merged = merged.rename(columns={"Neuron": "name"})
    table = results.merge(merged[["name", "GT Length (mm)", "Merged Length (mm)"]], on="name", how="left")
    table = table.sort_values(["omit_proportion", "correct_proportion"], ascending=[False, False]).reset_index(drop=True)

    neurons = table["name"].tolist()
    pred_root = RUN_DIR / "predicted-components"
    gt_root = RUN_DIR / "input-swcs-flattened"
    intensity_root = RUN_DIR / "intensity-npys"

    table["fragment_count"] = 0
    table["mean_fragment_length_mm"] = 0.0

    fig = plt.figure(figsize=(2.5 * len(neurons), 20), constrained_layout=True, facecolor="white")
    gs = fig.add_gridspec(
        6,
        len(neurons),
        height_ratios=[0.7, 1.75, 1.75, 1.05, 0.8, 0.9],
        wspace=0.04,
        hspace=0.08,
    )

    for col, neuron in enumerate(neurons):
        row = table.iloc[col]

        pred_paths = sorted((pred_root / neuron).glob("*.swc"))
        frag_lengths = [swc_length_mm(p) for p in pred_paths]
        table.loc[table["name"] == neuron, "fragment_count"] = len(pred_paths)
        table.loc[table["name"] == neuron, "mean_fragment_length_mm"] = float(np.mean(frag_lengths)) if frag_lengths else 0.0

        gt_pts, gt_segs = load_swc_xyz(gt_root / f"{neuron}.swc")
        if gt_pts.size:
            gt_pts[:, 0] *= VOXEL_SCALE_XY
            gt_pts[:, 1] *= VOXEL_SCALE_XY
        if gt_segs.size:
            gt_segs[:, :, 0] *= VOXEL_SCALE_XY
            gt_segs[:, :, 1] *= VOXEL_SCALE_XY

        pred_segs_all = []
        for p in pred_paths:
            _, segs = load_swc_xyz(p)
            if segs.size:
                pred_segs_all.append(segs[:, :, :2])
        if pred_segs_all:
            pred_xy_all = np.concatenate(pred_segs_all, axis=0)
            pred_xy_flat = pred_xy_all.reshape(-1, 2)
        else:
            pred_xy_all = np.empty((0, 2, 2), dtype=float)
            pred_xy_flat = np.empty((0, 2), dtype=float)

        gt_xy_flat = gt_pts[:, :2] if gt_pts.size else np.empty((0, 2), dtype=float)
        if pred_xy_flat.size and gt_xy_flat.size:
            all_xy = np.vstack([pred_xy_flat, gt_xy_flat])
        elif pred_xy_flat.size:
            all_xy = pred_xy_flat
        else:
            all_xy = gt_xy_flat
        if all_xy.size:
            mins = all_xy.min(axis=0)
            maxs = all_xy.max(axis=0)
            span = np.maximum(maxs - mins, 1.0)
            pad = 0.05 * span
            xlim = (mins[0] - pad[0], maxs[0] + pad[0])
            ylim = (mins[1] - pad[1], maxs[1] + pad[1])
        else:
            xlim = (0.0, 1.0)
            ylim = (0.0, 1.0)

        ax = fig.add_subplot(gs[0, col])
        ax.bar([0], [row["correct_proportion"]], color="#2ca02c", width=0.72)
        ax.bar([0], [row["omit_proportion"]], bottom=[row["correct_proportion"]], color="#d62728", width=0.72)
        ax.set_ylim(0, 1.0)
        ax.set_xlim(-0.6, 0.6)
        ax.set_xticks([])
        ax.set_yticks([0, 0.5, 1.0] if col == 0 else [])
        if col == 0:
            ax.set_ylabel("Prop.")
        ax.set_title(neuron.replace("-794495-", "\n"), fontsize=9)
        ax.text(0, max(row["correct_proportion"] - 0.045, 0.02), f"{row['correct_proportion']:.2f}", ha="center", va="top", color="white", fontsize=8, fontweight="bold")
        ax.text(0, row["correct_proportion"] + row["omit_proportion"] + 0.015, f"{row['omit_proportion']:.2f}", ha="center", va="bottom", color="#b22222", fontsize=8, fontweight="bold")
        for spine in ("top", "right", "bottom"):
            ax.spines[spine].set_visible(False)
        ax.grid(axis="y", alpha=0.15, linewidth=0.4)

        ax = fig.add_subplot(gs[1, col])
        for p in pred_paths:
            _, segs = load_swc_xyz(p)
            add_segments(ax, segs[:, :, :2], bright_color(p.stem), linewidth=0.9, alpha=0.95)
        ax.set_xlim(*xlim)
        ax.set_ylim(*ylim)
        ax.set_aspect("equal", adjustable="box")
        ax.set_facecolor("white")
        ax.set_xticks([])
        ax.set_yticks([])
        if col == 0:
            ax.set_ylabel("Predicted XY", fontsize=10)
        for spine in ax.spines.values():
            spine.set_edgecolor("#dddddd")
            spine.set_linewidth(0.8)

        ax = fig.add_subplot(gs[2, col])
        add_segments(ax, gt_segs[:, :, :2], "steelblue", linewidth=0.9, alpha=0.95)
        ax.set_xlim(*xlim)
        ax.set_ylim(*ylim)
        ax.set_aspect("equal", adjustable="box")
        ax.set_facecolor("white")
        ax.set_xticks([])
        ax.set_yticks([])
        if col == 0:
            ax.set_ylabel("GT XY", fontsize=10)
        for spine in ax.spines.values():
            spine.set_edgecolor("#dddddd")
            spine.set_linewidth(0.8)

        ax = fig.add_subplot(gs[3, col])
        correct = np.load(intensity_root / f"{neuron}_correct.npy", allow_pickle=False)
        omit = np.load(intensity_root / f"{neuron}_omit.npy", allow_pickle=False)
        pooled = np.concatenate([correct, omit]) if correct.size and omit.size else (correct if correct.size else omit)
        xmax = float(np.quantile(pooled, 0.995)) if pooled.size else 1.0
        bins = np.linspace(0.0, xmax if xmax > 0 else 1.0, 60)
        if correct.size:
            ax.hist(correct, bins=bins, density=True, color="#2ca02c", alpha=0.55)
        if omit.size:
            ax.hist(omit, bins=bins, density=True, color="#d62728", alpha=0.55)
        ax.set_xticks([])
        ax.set_yticks([] if col else ax.get_yticks())
        if col == 0:
            ax.set_ylabel("Intensity\nDensity", fontsize=9)
        for spine in ("top", "right"):
            ax.spines[spine].set_visible(False)
        ax.grid(axis="y", alpha=0.15, linewidth=0.4)

        ax = fig.add_subplot(gs[4, col])
        if frag_lengths:
            bp = ax.boxplot([frag_lengths], vert=True, patch_artist=True, showfliers=False, widths=0.45)
            bp["boxes"][0].set_facecolor("#7fbf7f")
            bp["boxes"][0].set_alpha(0.75)
            for key in ("whiskers", "caps", "medians"):
                for item in bp[key]:
                    item.set_color("#2f5d2f")
                    item.set_linewidth(1.0)
            ymax = max(float(max(frag_lengths)), float(np.percentile(frag_lengths, 75)))
            ax.set_ylim(0, ymax * 1.18 if ymax > 0 else 1.0)
            ax.text(1.0, ymax * 1.08 if ymax > 0 else 0.9, f"n={len(frag_lengths)}", ha="center", va="bottom", fontsize=8)
        else:
            ax.text(1.0, 0.9, "n=0", ha="center", va="top", fontsize=8, transform=ax.transAxes)
        ax.set_xticks([])
        ax.set_yticks([] if col else ax.get_yticks())
        if col == 0:
            ax.set_ylabel("Frag\nmm", fontsize=9)
        for spine in ("top", "right", "bottom"):
            ax.spines[spine].set_visible(False)
        ax.grid(axis="y", alpha=0.15, linewidth=0.4)

        ax = fig.add_subplot(gs[5, col])
        gt_len = float(row["GT Length (mm)"])
        merge_len = float(row["Merged Length (mm)"])
        ax.bar([0], [gt_len], color="steelblue", width=0.34)
        ax.bar([0.42], [merge_len], color=("#ff8c00" if merge_len >= 0 else "#999999"), width=0.34)
        ax.axhline(0, color="#555555", linewidth=0.6)
        ax.set_xticks([0, 0.42], ["GT", "Merge"], rotation=90, fontsize=7)
        ax.set_yticks([] if col else ax.get_yticks())
        if col == 0:
            ax.set_ylabel("mm", fontsize=9)
        ax.text(0, gt_len, f"{gt_len:.0f}", ha="center", va="bottom", fontsize=7, color="steelblue")
        ax.text(0.42, merge_len, f"{merge_len:.0f}", ha="center", va="bottom" if merge_len >= 0 else "top", fontsize=7, color="#8a4f00" if merge_len >= 0 else "#666666")
        for spine in ("top", "right"):
            ax.spines[spine].set_visible(False)
        ax.grid(axis="y", alpha=0.15, linewidth=0.4)

    fig.suptitle("794495 900k checkpoint: per-neuron omit/recall, geometry, intensities, fragment lengths, and merge-length proxy", fontsize=18)
    fig.savefig(OUT_PATH, dpi=220, bbox_inches="tight", facecolor="white")
    plt.close(fig)

    table[[
        "name",
        "correct_proportion",
        "omit_proportion",
        "split_proportion",
        "fragment_count",
        "mean_fragment_length_mm",
        "GT Length (mm)",
        "Merged Length (mm)",
    ]].to_csv(CSV_PATH, index=False)
    print(OUT_PATH)
    print(CSV_PATH)


if __name__ == "__main__":
    main()
