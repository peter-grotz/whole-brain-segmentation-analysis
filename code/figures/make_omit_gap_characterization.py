#!/usr/bin/env python3
"""Characterize pure-omit length: interior gaps (splits between fragments) vs
endpoint cable (lost at branch tips).

The upstream misalignment stage has already rewritten <neuron>_omit.swc to PURE
omit (misalignment removed), so this reads those directly. Each pure-omit run is
a connected component of omitted nodes on the GT tree; its length is split at the
branch level, not labelled as a whole:

  * prune every dangling GT tip inside the run -> that cable is ENDPOINT (nothing
    beyond it to reconnect to);
  * the minimal subtree left connecting the run's recalled attachment points (the
    Steiner tree over them) is INTERIOR gap -- a split between two fragments;
  * a run with fewer than two attachment points cannot bridge anything, so it is
    all endpoint.

A single run may therefore contribute to BOTH kinds. "gap length" is arc length
of missing cable along the traced path between the two fragment ends (includes
the two bracketing edges to the recalled boundary), so summed gap length can
exceed partition's node-only pure_omit_um by those bracketing edges.

Reads FIGURE_RUN_DIR; writes to FIGURE_OUT_DIR:
    omit_gap_characterization.png
    omit_gap_characterization.csv      (every run: endpoint_mm, interior_gap_mm)
    omit_gap_per_cell.csv              (per neuron totals + %)

Topology comes from input-swcs-flattened (VOXEL units); the partitioned SWCs are
physical microns, so the GT is scaled by FIGURE_VOXEL_SIZE (default 0.748,0.748,1.0)
to match before the two are aligned by coordinate.
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
from matplotlib.patches import Patch

from figure_config import RUN_DIR, OUT_DIR, VOXEL_SIZE, apply_house_style

ENDPT, GAP = "#16a8a4", "#7cbf4d"
apply_house_style()
VOX = VOXEL_SIZE


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


def node_set(path: Path):
    if not path.exists():
        return set()
    x, _ = load_swc(path)
    return set(map(tuple, np.round(x, 2)))


def decompose(cell: str):
    """Per-run (endpoint_mm, interior_gap_mm) for one neuron."""
    gx, ge = load_swc(RUN_DIR / "input-swcs-flattened" / f"{cell}.swc")
    if len(ge) == 0:
        return []
    gx = gx * VOX  # voxel -> physical microns, to match the partitioned SWCs
    key = [tuple(t) for t in np.round(gx, 2)]
    O = node_set(RUN_DIR / "partitioned-swcs" / f"{cell}_omit.swc")  # already pure
    is_omit = np.array([k in O for k in key])
    adj = collections.defaultdict(list)
    for u, v in ge:
        adj[u].append(v); adj[v].append(u)
    L = np.linalg.norm(gx[ge[:, 0]] - gx[ge[:, 1]], axis=1) / 1000.0  # mm
    elen = {}
    for (u, v), l in zip(ge, L):
        elen[(u, v)] = l; elen[(v, u)] = l

    seen = np.zeros(len(gx), bool)
    out = []
    for s in np.nonzero(is_omit)[0]:
        if seen[s]:
            continue
        st, comp = [s], []
        seen[s] = True
        while st:
            u = st.pop(); comp.append(u)
            for v in adj[u]:
                if is_omit[v] and not seen[v]:
                    seen[v] = True; st.append(v)
        cs = set(comp)
        boundary = set()
        sub_adj = collections.defaultdict(set)
        for u in comp:
            for v in adj[u]:
                sub_adj[u].add(v); sub_adj[v].add(u)
                if v not in cs:
                    boundary.add(v)
        if len(boundary) < 2:
            ep = sum(elen[(u, v)] for u in comp for v in adj[u]
                     if (v in cs and u < v) or (v not in cs))
            out.append((len(comp), float(ep), 0.0))
            continue
        live = {u: set(vs) for u, vs in sub_adj.items()}
        dq = collections.deque(u for u in live
                               if len(live[u]) == 1 and u not in boundary)
        ep = 0.0
        while dq:
            u = dq.popleft()
            if u in boundary or len(live.get(u, ())) != 1:
                continue
            (v,) = tuple(live[u])
            ep += elen[(u, v)]
            live[v].discard(u); live.pop(u, None)
            if v not in boundary and len(live.get(v, ())) == 1:
                dq.append(v)
        interior = sum(elen[(u, v)] for u in live for v in live[u] if u < v)
        out.append((len(comp), float(ep), float(interior)))
    return out


def main():
    cells = sorted(p.stem for p in
                   (RUN_DIR / "input-swcs-flattened").glob("*.swc"))
    rows, per_cell = [], collections.defaultdict(lambda: [0.0, 0.0, 0, 0])
    for c in cells:
        runs = decompose(c)
        short = c.split("-")[0]
        for nn, ep, gap in runs:
            rows.append((short, nn, ep, gap))
            per_cell[short][0] += ep; per_cell[short][1] += gap
            if ep > 0:
                per_cell[short][2] += 1
            if gap > 0:
                per_cell[short][3] += 1
        print(f"  {short}: {len(runs)} pure-omit runs", flush=True)

    with (OUT_DIR / "omit_gap_characterization.csv").open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["cell", "n_nodes", "endpoint_mm", "interior_gap_mm"])
        for cell, nn, ep, gap in rows:
            w.writerow([cell, nn, f"{ep:.4f}", f"{gap:.4f}"])
    with (OUT_DIR / "omit_gap_per_cell.csv").open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["cell", "omit_mm", "endpoint_mm", "interior_gap_mm",
                    "endpoint_pct", "interior_pct", "n_endpoint_runs",
                    "n_interior_runs"])
        for cell in sorted(per_cell, key=lambda c: -sum(per_cell[c][:2])):
            ep, gap, ne, ng = per_cell[cell]
            t = ep + gap
            w.writerow([cell, f"{t:.3f}", f"{ep:.3f}", f"{gap:.3f}",
                        f"{100*ep/t:.1f}" if t else "0",
                        f"{100*gap/t:.1f}" if t else "0", ne, ng])

    ep_arr = np.array([r[2] for r in rows]); gap_arr = np.array([r[3] for r in rows])
    gap_mm = gap_arr[gap_arr > 0]; end_mm = ep_arr[ep_arr > 0]
    ep_len, gap_len = ep_arr.sum(), gap_arr.sum(); omit_len = ep_len + gap_len

    fig = plt.figure(figsize=(16.5, 9.6))
    gs = fig.add_gridspec(2, 3, height_ratios=[1, 1], hspace=0.55, wspace=0.32)

    def logbins(v, n=40):
        lo = max(0.5, float(v.min())); hi = max(float(v.max()), lo * 10)
        return np.logspace(np.log10(lo), np.log10(hi), n)

    ax = fig.add_subplot(gs[0, 0])
    g_um = gap_mm * 1000
    h, _, _ = ax.hist(g_um, bins=logbins(g_um), color=GAP, alpha=0.65)
    ax.set_ylim(0, h.max() * 1.15)
    ax.axvline(np.median(g_um), color="#222", ls="--", lw=1.4)
    ax.text(np.median(g_um) * 1.1, h.max() * 1.08, f"median {np.median(g_um):.0f} um",
            fontsize=9, va="top")
    ax.set_xscale("log")
    ax.set_title("interior gap length (splits between fragments)")
    ax.set_xlabel("gap length (um, log)"); ax.set_ylabel("number of gaps")

    ax = fig.add_subplot(gs[0, 1])
    sg = np.sort(g_um); cdf = np.cumsum(sg) / sg.sum() * 100
    ax.plot(sg, cdf, color=GAP, lw=2)
    for q in (50, 90):
        xt = np.interp(q, cdf, sg)
        ax.plot([xt, xt], [0, q], color="#888", ls=":", lw=1)
        ax.text(xt, q, f" {q}% by {xt:.0f} um", fontsize=8.5, va="top")
    ax.set_xscale("log"); ax.set_ylim(0, 108)
    ax.set_title("cumulative interior-gap length")
    ax.set_xlabel("gap length (um, log)"); ax.set_ylabel("% of gap length")

    ax = fig.add_subplot(gs[0, 2])
    e_um = end_mm * 1000
    ax.hist(e_um, bins=logbins(e_um), color=ENDPT, alpha=0.7)
    ax.set_xscale("log")
    ax.set_title("endpoint cable length (lost at branch tips)")
    ax.set_xlabel("cable length (um, log)"); ax.set_ylabel("number of endpoints")

    ax = fig.add_subplot(gs[1, 0])
    b = 0
    for lab, val, col in [("endpoint cable", ep_len, ENDPT),
                          ("interior gaps", gap_len, GAP)]:
        ax.bar(0, val, bottom=b, color=col, width=0.6)
        if val > 0:
            ax.text(0, b + val / 2, f"{100*val/omit_len:.0f}%", ha="center",
                    va="center", fontsize=12, color="white")
        b += val
    ax.set_xlim(-0.75, 0.75); ax.set_ylim(0, omit_len * 1.22)
    ax.set_xticks([0]); ax.set_xticklabels([f"omit\n{omit_len:.0f} mm"])
    ax.set_title("omitted length: endpoint vs interior"); ax.set_ylabel("length (mm)")
    ax.legend(handles=[Patch(facecolor=ENDPT, label="endpoint cable"),
                       Patch(facecolor=GAP, label="interior gaps")],
              frameon=False, fontsize=9, loc="upper right")

    ax = fig.add_subplot(gs[1, 1:])
    order = sorted(per_cell, key=lambda c: -sum(per_cell[c][:2]))
    x = np.arange(len(order))
    epv = np.array([per_cell[c][0] for c in order])
    gpv = np.array([per_cell[c][1] for c in order])
    ax.bar(x, epv, color=ENDPT, label="endpoint cable")
    ax.bar(x, gpv, bottom=epv, color=GAP, label="interior gaps")
    ax.set_ylim(0, (epv + gpv).max() * 1.22)
    ax.set_xticks(x); ax.set_xticklabels(order, fontsize=8, rotation=40, ha="right")
    ax.set_title("per cell: omitted length, endpoint vs interior")
    ax.set_ylabel("omitted length (mm)")
    ax.legend(frameon=False, fontsize=9, loc="upper right", ncol=2)

    for a in fig.axes:
        a.grid(axis="y", color="#e6e6e6", lw=0.8)
        a.set_axisbelow(True)
        for sp in ("top", "right"):
            a.spines[sp].set_visible(False)

    fig.subplots_adjust(left=0.055, right=0.99, top=0.855, bottom=0.11)
    fig.suptitle("omit characterization -- pure omit, interior gaps vs endpoints",
                 fontsize=18, y=0.965)
    fig.text(0.5, 0.905,
             f"{omit_len:.0f} mm pure omit = {100*ep_len/omit_len:.0f}% endpoint "
             f"cable + {100*gap_len/omit_len:.0f}% interior gaps.  gap length is "
             f"arc length between the two fragment ends",
             ha="center", fontsize=10.5, color="#666")

    fig.savefig(OUT_DIR / "omit_gap_characterization.png", dpi=150)
    plt.close(fig)
    print(f"wrote omit_gap_characterization.png | pure omit {omit_len:.0f} mm | "
          f"endpoint {100*ep_len/omit_len:.0f}% | interior {100*gap_len/omit_len:.0f}%")


if __name__ == "__main__":
    main()
