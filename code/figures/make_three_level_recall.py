#!/usr/bin/env python3
"""Three-level recall summary: binary mask (stage 1) -> label mask / FFN
(stage 2) -> skeleton (stage 3).

Recall is reported at three successively stricter levels:

  stage 1  binary mask (detection)     -- GT length on nonzero foreground. The
           ceiling; anything dropped here is unrecoverable downstream. OPTIONAL:
           computed only when a binary-mask volume is provided via
           FIGURE_BINARY_MASK (and the GCS/S3 read succeeds). Otherwise this
           level is shown as "n/a" -- never a placeholder number.
  stage 2  label mask / FFN (segmentation) -- GT length whose nodes carry a
           nonzero FFN label. Taken from misalignment_metrics.csv as
           1 - pure_omit/total, so MISALIGNMENT COUNTS AS RECALLED (a continuous
           fragment runs through the gap; the GT merely drifted off it).
  stage 3  skeleton (predicted components) -- fraction of GT length within
           --skeleton-tol-um of a predicted-component skeleton, EXCLUDING merged
           excess. Computed locally from predicted-components/ + the GT.

Denominator for every level is GT length, so the three are directly comparable.

Panels: recall cascade (pooled); recalled/omitted per cell at label-mask and
skeleton levels; predicted vs traced length (skeleton level) with merged excess;
predicted-component length distribution; label-mask intensity at GT nodes;
per-cell table. Also writes three_level_per_cell.csv.

Reads FIGURE_RUN_DIR; writes FIGURE_OUT_DIR. Env:
  FIGURE_VOXEL_SIZE   x,y,z microns (default 0.748,0.748,1.0)
  FIGURE_BINARY_MASK  optional tensorstore path to the binary mask volume
  FIGURE_SKELETON_TOL_UM  match tolerance for stage 3 (default 5)
"""
from __future__ import annotations

import collections
import csv
import os
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.patches import Patch

from figure_config import (RUN_DIR, OUT_DIR, VOXEL_SIZE, SKELETON_TOL_UM,
                           BINARY_MASK, apply_house_style)

BIN, FFN, SKEL = "#6660e5", "#7cbf4d", "#16a8a4"
GT_C, MERGED, OMIT = "#9a94ff", "#d81168", "#cd0f55"
apply_house_style()
VOX = VOXEL_SIZE
TOL_UM = SKELETON_TOL_UM


def load_swc(path: Path):
    ids, xyz, par = [], [], []
    for ln in path.read_text(errors="ignore").splitlines():
        s = ln.strip()
        if not s or s.startswith("#"):
            continue
        p = s.split()
        if len(p) < 7:
            continue
        ids.append(int(float(p[0])))
        xyz.append((float(p[2]), float(p[3]), float(p[4])))
        par.append(int(float(p[6])))
    if not ids:
        return np.zeros((0, 3)), np.zeros((0, 2), int)
    xyz = np.array(xyz)
    row = {n: i for i, n in enumerate(ids)}
    e = np.array([(i, row[p_]) for i, p_ in enumerate(par) if p_ in row], int)
    return xyz, e


def swc_len_mm(path: Path):
    x, e = load_swc(path)
    if len(e) == 0:
        return 0.0
    return float(np.linalg.norm(x[e[:, 0]] - x[e[:, 1]], axis=1).sum()) / 1000.0


def skeleton_recall(cell: str, gx_phys, ge, L_mm):
    """Fraction of GT length within TOL_UM of any predicted-component skeleton.

    Local, no GCS: pools all predicted-component nodes for the cell into a KD-tree
    and marks GT nodes whose nearest predicted node is within tolerance. An edge
    counts as recovered when BOTH endpoints are within tolerance.
    """
    from scipy.spatial import cKDTree
    comp_dir = RUN_DIR / "predicted-components" / cell
    if not comp_dir.is_dir():
        return None
    pts = []
    for f in comp_dir.glob("*.swc"):
        x, _ = load_swc(f)
        if len(x):
            pts.append(x)
    if not pts:
        return 0.0
    tree = cKDTree(np.vstack(pts))
    d, _ = tree.query(gx_phys, k=1, workers=-1)
    near = d <= TOL_UM
    both = near[ge[:, 0]] & near[ge[:, 1]]
    return float(L_mm[both].sum() / L_mm.sum()) if L_mm.sum() else 0.0


def binary_recall(cell: str, gx_phys, ge, L_mm):
    """GT length on nonzero binary-mask voxels. None unless a mask is provided
    and readable -- never a fabricated number."""
    if not BINARY_MASK:
        return None
    try:
        import tensorstore as ts
        # opened once and cached on the function object
        arr = getattr(binary_recall, "_arr", None)
        if arr is None:
            arr = ts.open({"driver": "neuroglancer_precomputed",
                           "kvstore": BINARY_MASK, "scale_index": 0},
                          open=True, read=True).result()
            binary_recall._arr = arr
        # mask is 2x-downsampled in this pipeline; index by physical / mask res
        info = arr.spec().to_json()
        res = np.array(arr.dimension_units[:3])  # microns per voxel
        res = np.array([float(str(u).split()[0]) for u in res]) if res[0] else VOX * 2
        idx = np.floor(gx_phys / res).astype(int)
        shape = np.array(arr.shape[:3])
        idx = np.clip(idx, 0, shape - 1)
        vals = arr[idx[:, 0], idx[:, 1], idx[:, 2], 0].read().result()
        near = np.asarray(vals) != 0
        both = near[ge[:, 0]] & near[ge[:, 1]]
        return float(L_mm[both].sum() / L_mm.sum()) if L_mm.sum() else 0.0
    except Exception as e:  # pragma: no cover - depends on live volume
        print(f"    binary mask read failed for {cell}: {str(e)[:80]}", flush=True)
        return None


def main():
    mis = pd.read_csv(RUN_DIR / "misalignment_metrics.csv")
    mis = mis[mis["name"] != "ALL"].set_index("name")
    mgd = pd.read_csv(RUN_DIR / "merged-length.csv").set_index("Neuron")
    cells = sorted(mis.index)

    rec_bin, rec_ffn, rec_skel = {}, {}, {}
    gt_mm, pred_mm, merged_mm, ncomp, comp_lens = {}, {}, {}, {}, {}
    any_binary = False
    for c in cells:
        gx, ge = load_swc(RUN_DIR / "input-swcs-flattened" / f"{c}.swc")
        gx = gx * VOX
        L = np.linalg.norm(gx[ge[:, 0]] - gx[ge[:, 1]], axis=1) / 1000.0
        tot = float(mis.loc[c, "total_um"])
        pure = float(mis.loc[c, "pure_omit_um"])
        rec_ffn[c] = 100 * (1 - pure / tot)                 # misaligned = recalled
        rec_skel[c] = None
        sk = skeleton_recall(c, gx, ge, L)
        rec_skel[c] = None if sk is None else 100 * sk
        b = binary_recall(c, gx, ge, L)
        rec_bin[c] = None if b is None else 100 * b
        any_binary = any_binary or (b is not None)
        gt_mm[c] = float(mgd.loc[c, "GT Length (mm)"]) if c in mgd.index else L.sum()
        pred_mm[c] = float(mgd.loc[c, "Predicted Components Length (mm)"]) if c in mgd.index else 0.0
        merged_mm[c] = float(mgd.loc[c, "Merged Length (mm)"]) if c in mgd.index else 0.0
        cl = [swc_len_mm(f) for f in (RUN_DIR / "predicted-components" / c).glob("*.swc")]
        comp_lens[c] = cl; ncomp[c] = len(cl)
        print(f"  {c.split('-')[0]}: FFN {rec_ffn[c]:.1f}%  "
              f"skel {rec_skel[c] if rec_skel[c] is None else round(rec_skel[c],1)}  "
              f"bin {rec_bin[c] if rec_bin[c] is None else round(rec_bin[c],1)}", flush=True)

    short = [c.split("-")[0] for c in cells]
    order = sorted(range(len(cells)), key=lambda i: -gt_mm[cells[i]])
    cells = [cells[i] for i in order]; short = [short[i] for i in order]

    def pooled(d):
        num = sum((d[c] / 100) * gt_mm[c] for c in cells if d[c] is not None)
        den = sum(gt_mm[c] for c in cells if d[c] is not None)
        return 100 * num / den if den else None
    ffn_all = pooled(rec_ffn); skel_all = pooled(rec_skel); bin_all = pooled(rec_bin)

    # per-cell CSV
    with (OUT_DIR / "three_level_per_cell.csv").open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["cell", "gt_mm", "binary_recall_pct", "ffn_recall_pct",
                    "skeleton_recall_pct", "predicted_mm", "merged_mm", "n_components"])
        for c in cells:
            w.writerow([c.split("-")[0], f"{gt_mm[c]:.2f}",
                        "" if rec_bin[c] is None else f"{rec_bin[c]:.2f}",
                        f"{rec_ffn[c]:.2f}",
                        "" if rec_skel[c] is None else f"{rec_skel[c]:.2f}",
                        f"{pred_mm[c]:.2f}", f"{merged_mm[c]:.2f}", ncomp[c]])

    fig = plt.figure(figsize=(18.0, 13.5))
    gs = fig.add_gridspec(3, 3, height_ratios=[1.0, 0.95, 0.95],
                          hspace=0.5, wspace=0.28)
    x = np.arange(len(cells))

    # cascade
    ax = fig.add_subplot(gs[0, 0])
    stg = [("traced", 100.0, "#aaa39f"),
           ("binary\nmask", bin_all, BIN), ("label\nmask", ffn_all, FFN),
           ("skeleton", skel_all, SKEL)]
    vals = [v for _, v, _ in stg if v is not None]
    ymin = min(vals) - 4
    for i, (lab, v, col) in enumerate(stg):
        if v is None:
            ax.text(i, ymin + 0.4, "n/a", ha="center", va="bottom", fontsize=10,
                    color="#888")
        else:
            ax.bar(i, v, color=col)
            ax.text(i, v + 0.5, f"{v:.1f}", ha="center", va="bottom", fontsize=9.5)
    ax.set_xticks(range(4)); ax.set_xticklabels([s[0] for s in stg], fontsize=8.5)
    ax.set_ylim(ymin, 101.5)
    ax.set_title("recall cascade, pooled"); ax.set_ylabel("% of traced length")

    # recalled/omit stacked, label mask + skeleton
    ax = fig.add_subplot(gs[0, 1:]); w = 0.4
    tot_mm = np.array([gt_mm[c] for c in cells])
    ffn_rec = np.array([rec_ffn[c] / 100 for c in cells]) * tot_mm
    have_sk = all(rec_skel[c] is not None for c in cells)
    ax.bar(x - w/2, ffn_rec, w, color=FFN, label="recalled (label mask)")
    ax.bar(x - w/2, tot_mm - ffn_rec, w, bottom=ffn_rec, color=OMIT, label="omitted")
    if have_sk:
        sk_rec = np.array([rec_skel[c] / 100 for c in cells]) * tot_mm
        ax.bar(x + w/2, sk_rec, w, color=SKEL, label="recalled (skeleton)")
        ax.bar(x + w/2, tot_mm - sk_rec, w, bottom=sk_rec, color=OMIT)
    ax.set_xticks(x); ax.set_xticklabels(short, fontsize=8, rotation=40, ha="right")
    ax.set_ylim(0, tot_mm.max() * 1.16)
    ax.set_title("recalled vs omitted -- label mask (left) & skeleton (right)")
    ax.set_ylabel("length (mm)")
    ax.legend(frameon=False, fontsize=8.5, loc="upper right", ncol=3)

    # predicted vs traced (skeleton level)
    ax = fig.add_subplot(gs[1, :]); w = 0.38
    gtl = tot_mm
    pdl = np.array([pred_mm[c] for c in cells]); mrg = np.array([merged_mm[c] for c in cells])
    on = np.clip(pdl - mrg, 0, None)
    ax.bar(x - w/2, gtl, w, color=GT_C, label="ground truth")
    ax.bar(x + w/2, on, w, color=FFN, label="predicted on the neuron")
    ax.bar(x + w/2, np.clip(mrg, 0, None), w, bottom=on, color=MERGED, label="merged excess")
    ax.set_xticks(x); ax.set_xticklabels(short, fontsize=8, rotation=40, ha="right")
    ax.set_ylim(0, max(pdl.max(), gtl.max()) * 1.16)
    ax.set_title("predicted length vs traced length (skeleton level)")
    ax.set_ylabel("length (mm)"); ax.legend(frameon=False, fontsize=9, loc="upper right")

    # component length distribution
    ax = fig.add_subplot(gs[2, :2])
    data = [np.array(comp_lens[c]) * 1000 for c in cells]
    data = [d[d > 0] if len(d) else np.array([1.0]) for d in data]
    bp = ax.boxplot(data, positions=x, widths=0.6, showfliers=False, patch_artist=True,
                    medianprops=dict(color="#222", lw=1.2))
    for patch in bp["boxes"]:
        patch.set_facecolor(SKEL); patch.set_alpha(0.55)
    ax.set_yscale("log")
    ytop = ax.get_ylim()[1]
    for i, c in enumerate(cells):
        ax.text(i, ytop * 0.72, f"n={ncomp[c]}", ha="center", va="bottom", fontsize=7)
    ax.set_xticks(x); ax.set_xticklabels(short, fontsize=8, rotation=40, ha="right")
    ax.set_title("predicted component length distribution", pad=10)
    ax.set_ylabel("component length (um, log)")

    # label-mask intensity at GT nodes
    ax = fig.add_subplot(gs[2, 2])
    ipath = RUN_DIR / "intensity-npys"
    cc = [np.load(ipath / f"{c}_correct.npy") for c in cells if (ipath / f"{c}_correct.npy").exists()]
    oo = [np.load(ipath / f"{c}_omit.npy") for c in cells if (ipath / f"{c}_omit.npy").exists()]
    if cc and oo:
        cc = np.concatenate(cc); oo = np.concatenate(oo)
        lo = max(1.0, float(min(cc.min(), oo.min()))); hi = float(max(cc.max(), oo.max()))
        edges = np.logspace(np.log10(lo), np.log10(hi), 60)
        for v, col, nm in ((cc, FFN, "recalled"), (oo, OMIT, "omitted")):
            ax.hist(v, bins=edges, weights=np.full(len(v), 1/len(v)), color=col, alpha=0.5, label=nm)
            ax.hist(v, bins=edges, weights=np.full(len(v), 1/len(v)), histtype="step", color=col, lw=1.4)
        ax.set_xscale("log"); ax.set_xlim(lo, hi)
        ax.legend(frameon=False, fontsize=8.5)
    ax.set_title("label-mask intensity at GT nodes")
    ax.set_xlabel("intensity (16-bit, log)"); ax.set_ylabel("fraction of nodes")

    for a in fig.axes:
        a.grid(axis="y", color="#e6e6e6", lw=0.8); a.set_axisbelow(True)
        for sp in ("top", "right"):
            a.spines[sp].set_visible(False)

    fig.subplots_adjust(left=0.05, right=0.99, top=0.9, bottom=0.05)
    fig.suptitle("three-level recall: binary mask -> label mask -> skeleton", fontsize=19, y=0.965)
    note = ("skeleton recall = GT length within "
            f"{TOL_UM:g} um of a predicted component; misalignment counts as recalled.  ")
    note += ("binary-mask level computed from FIGURE_BINARY_MASK"
             if any_binary else "binary-mask level not provided (shown n/a)")
    fig.text(0.5, 0.925, note, ha="center", fontsize=10.5, color="#666")

    fig.savefig(OUT_DIR / "three_level_recall.png", dpi=140)
    plt.close(fig)
    print(f"wrote three_level_recall.png | FFN {ffn_all:.1f}% | "
          f"skel {None if skel_all is None else round(skel_all,1)} | "
          f"bin {None if bin_all is None else round(bin_all,1)}")


if __name__ == "__main__":
    main()
