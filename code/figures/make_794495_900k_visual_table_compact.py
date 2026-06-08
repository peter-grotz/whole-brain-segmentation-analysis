from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib import font_manager, rcParams

from make_794495_900k_visual_table import (
    RUN_DIR,
    VOXEL_SCALE_XY,
    add_segments,
    bright_color,
    load_swc_xyz,
    swc_length_mm,
)


from figure_config import OUT_DIR

OUT_PATH = OUT_DIR / "794495_900k_visual_table_compact.png"
CSV_PATH = OUT_DIR / "794495_900k_visual_table_compact_order.csv"
GT_COLOR = "#6660e5"
VIOLIN_COLOR = "#16a8a4"
MERGE_COLOR = "#d81168"
HEAD_FONT_PATH = Path("/Library/Fonts/Managed/AllenInstitutePlusHead-Rg_357723850.otf")
PREDICTED_PALETTE = [
    "#8b46d8",  # purple
    "#16a8a4",  # teal
    "#ea06ff",  # magenta
    "#ff7a14",  # orange
    "#9a9a9a",  # lighter gray
]

if HEAD_FONT_PATH.exists():
    font_manager.fontManager.addfont(str(HEAD_FONT_PATH))
    rcParams["font.family"] = font_manager.FontProperties(fname=str(HEAD_FONT_PATH)).get_name()


def format_neuron_header(neuron: str) -> str:
    return neuron.split("-")[0]


def palette_color(key: str) -> str:
    return PREDICTED_PALETTE[abs(hash(key)) % len(PREDICTED_PALETTE)]


def main() -> None:
    results = pd.read_csv(RUN_DIR / "partitioned-swcs/results.csv")
    merged = pd.read_csv(RUN_DIR / "merged-length.csv").rename(columns={"Neuron": "name"})
    table = results.merge(merged[["name", "GT Length (mm)", "Merged Length (mm)"]], on="name", how="left")
    table = table.sort_values(["omit_proportion", "correct_proportion"], ascending=[False, False]).reset_index(drop=True)

    neurons = table["name"].tolist()
    pred_root = RUN_DIR / "predicted-components"
    gt_root = RUN_DIR / "input-swcs-flattened"

    table["fragment_count"] = 0
    table["mean_fragment_length_mm"] = 0.0
    column_axes = []

    fig = plt.figure(figsize=(2.75 * len(neurons), 15.8), constrained_layout=False, facecolor="white")
    gs = fig.add_gridspec(
        4,
        len(neurons),
        height_ratios=[1.0, 1.85, 1.85, 1.0],
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
            pred_xy_flat = np.empty((0, 2), dtype=float)
        gt_xy_flat = gt_pts[:, :2] if gt_pts.size else np.empty((0, 2), dtype=float)
        if pred_xy_flat.size and gt_xy_flat.size:
            all_xy = np.vstack([pred_xy_flat, gt_xy_flat])
        elif pred_xy_flat.size:
            all_xy = pred_xy_flat
        else:
            all_xy = gt_xy_flat
        mins = all_xy.min(axis=0)
        maxs = all_xy.max(axis=0)
        span = np.maximum(maxs - mins, 1.0)
        pad = 0.05 * span
        xlim = (mins[0] - pad[0], maxs[0] + pad[0])
        ylim = (mins[1] - pad[1], maxs[1] + pad[1])

        top_gs = gs[0, col].subgridspec(1, 2, width_ratios=[0.9, 1.25], wspace=0.28)

        ax = fig.add_subplot(top_gs[0, 0])
        ax.bar([0.0], [row["correct_proportion"]], color="#9bd400", edgecolor="none", linewidth=0.0, width=0.42)
        ax.bar([0.0], [row["omit_proportion"]], bottom=[row["correct_proportion"]], color="#d62728", edgecolor="none", linewidth=0.0, width=0.42)
        ax.set_ylim(0, 1.0)
        ax.set_xlim(-0.5, 0.5)
        ax.set_xticks([0.0], ["Recall"])
        ax.tick_params(axis="x", labelrotation=0, labelsize=14, pad=2)
        ax.set_yticks([])
        for spine in ("top", "right", "left"):
            ax.spines[spine].set_visible(False)
        ax.grid(axis="y", alpha=0.12, linewidth=0.35)

        gt_len = float(row["GT Length (mm)"])
        merge_len = float(row["Merged Length (mm)"])
        ax_len = fig.add_subplot(top_gs[0, 1])
        ax_len.bar([0.0], [gt_len], color=GT_COLOR, width=0.28)
        ax_len.bar([0.42], [merge_len], color=(MERGE_COLOR if merge_len >= 0 else "#999999"), width=0.28)
        ax_len.axhline(0, color="#555555", linewidth=0.5)
        ymax = max(1.0, gt_len * 1.08)
        ymin = min(-15.0, merge_len * 1.2 if merge_len < 0 else -15.0)
        ax_len.set_ylim(ymin, ymax)
        ax_len.set_xlim(-0.3, 0.72)
        ax_len.set_xticks([0.0, 0.42], ["GT", "Merge"])
        ax_len.tick_params(axis="x", labelrotation=0, labelsize=14, pad=2)
        ax_len.set_yticks([])
        ax_len.text(0.0, gt_len, f"{gt_len:.0f}", ha="center", va="bottom", fontsize=13, color=GT_COLOR)
        ax_len.text(0.42, merge_len, f"{merge_len:.1f}", ha="center", va="bottom" if merge_len >= 0 else "top", fontsize=6.5, color=MERGE_COLOR if merge_len >= 0 else "#666666")
        for spine in ("top", "right", "left"):
            ax_len.spines[spine].set_visible(False)
        ax_len.grid(axis="y", alpha=0.12, linewidth=0.35)

        ax = fig.add_subplot(gs[1, col])
        column_axes.append(ax)
        for p in pred_paths:
            _, segs = load_swc_xyz(p)
            if segs.size:
                add_segments(ax, segs[:, :, :2], palette_color(p.stem), linewidth=0.75, alpha=0.95)
        ax.set_xlim(*xlim)
        ax.set_ylim(*ylim)
        ax.set_aspect("equal", adjustable="box")
        ax.set_facecolor("white")
        ax.set_xticks([])
        ax.set_yticks([])
        if col == 0:
            ax.set_ylabel("Predicted XY", fontsize=20)
        for spine in ax.spines.values():
            spine.set_edgecolor("#dddddd")
            spine.set_linewidth(0.8)

        ax = fig.add_subplot(gs[2, col])
        if gt_segs.size:
            add_segments(ax, gt_segs[:, :, :2], GT_COLOR, linewidth=0.95, alpha=0.95)
        ax.set_xlim(*xlim)
        ax.set_ylim(*ylim)
        ax.set_aspect("equal", adjustable="box")
        ax.set_facecolor("white")
        ax.set_xticks([])
        ax.set_yticks([])
        if col == 0:
            ax.set_ylabel("GT XY", fontsize=20)
        for spine in ax.spines.values():
            spine.set_edgecolor("#dddddd")
            spine.set_linewidth(0.8)

        ax = fig.add_subplot(gs[3, col])
        if frag_lengths:
            vp = ax.violinplot([frag_lengths], positions=[1], showmeans=False, showextrema=False, showmedians=True, widths=0.55)
            vp["bodies"][0].set_facecolor(VIOLIN_COLOR)
            vp["bodies"][0].set_edgecolor(VIOLIN_COLOR)
            vp["bodies"][0].set_alpha(0.5)
            vp["cmedians"].set_color("#333333")
            ymax = max(frag_lengths)
            ax.set_ylim(0, ymax * 1.15 if ymax > 0 else 1.0)
            ax.text(1.0, ymax * 1.05 if ymax > 0 else 0.9, f"n={len(frag_lengths)}", ha="center", va="bottom", fontsize=16)
        else:
            ax.text(0.5, 0.9, "n=0", ha="center", va="top", fontsize=16, transform=ax.transAxes)
        ax.set_xlim(0.4, 1.6)
        ax.set_xticks([])
        ax.set_yticks([] if col else ax.get_yticks())
        if col == 0:
            ax.set_ylabel("Frag mm", fontsize=18)
        for spine in ("top", "right"):
            ax.spines[spine].set_visible(False)
        ax.grid(axis="y", alpha=0.15, linewidth=0.4)

    fig.subplots_adjust(left=0.025, right=0.995, bottom=0.035, top=0.925, wspace=0.035, hspace=0.12)
    fig.canvas.draw()
    for ax, neuron in zip(column_axes, neurons):
        pos = ax.get_position()
        xc = 0.5 * (pos.x0 + pos.x1)
        fig.text(xc, 0.992, format_neuron_header(neuron), ha="center", va="top", fontsize=27, fontweight="bold")

    for left_ax, right_ax in zip(column_axes[:-1], column_axes[1:]):
        x = 0.5 * (left_ax.get_position().x1 + right_ax.get_position().x0)
        fig.add_artist(
            plt.Line2D(
                [x, x],
                [0.055, 0.955],
                transform=fig.transFigure,
                color="#cfcfcf",
                linewidth=0.8,
                alpha=0.9,
                zorder=0,
            )
        )

    fig.savefig(OUT_PATH, dpi=100, facecolor="white")
    plt.close(fig)

    table[[
        "name",
        "correct_proportion",
        "omit_proportion",
        "fragment_count",
        "mean_fragment_length_mm",
        "GT Length (mm)",
        "Merged Length (mm)",
    ]].to_csv(CSV_PATH, index=False)
    print(OUT_PATH)
    print(CSV_PATH)


if __name__ == "__main__":
    main()
