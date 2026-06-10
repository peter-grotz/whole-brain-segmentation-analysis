#!/usr/bin/env python3
"""Split the GT "omit" length into MISALIGNMENT vs PURE OMIT, per run.

partition_gt_errors labels every GT node by the segmentation mask value at its voxel
(label 0 = background) and calls any edge touching a zero node an "omit". But some of
those zero gaps are not real omissions: if a connected zero-label region is bordered on
both ends by the SAME segment id, a single continuous fragment runs through the gap and
the GT skeleton has merely drifted off it (a GT-vs-segmentation MISALIGNMENT). Only zero
regions that are a tip, or that sit between *different* segments, are genuine omissions.

This reproduces partition's labeling exactly (same `open_ts` mask, same integer
`mask[z,y,x]` lookup -- voxel-size is only applied on SWC output), classifies each zero
region, and:
  * writes <neuron>_misaligned.swc and rewrites <neuron>_omit.swc to PURE omit only,
    into the partitioned-swcs dir (physical microns, matching the other partitioned SWCs);
  * writes misalignment_metrics.csv (per-neuron + aggregate): omit / misalign / pure-omit
    length and misalign % of omit;
  * prints a consistency check of recomputed omit fraction vs partition's results.csv.

Run after partition_gt_errors. Uses tensorstore via open_ts (no JVM).
"""
from __future__ import annotations

import argparse
import csv
import math
from collections import deque
from pathlib import Path

import numpy as np


def parse_swc_full(path: Path):
    """Return dicts keyed by node id: coord(x,y,z voxel), radius, type, parent."""
    coord, radius, typ, parent = {}, {}, {}, {}
    for raw in path.read_text(errors="ignore").splitlines():
        s = raw.strip()
        if not s or s.startswith("#"):
            continue
        p = s.split()
        if len(p) < 7:
            continue
        nid = int(float(p[0]))
        typ[nid] = int(float(p[1]))
        coord[nid] = (float(p[2]), float(p[3]), float(p[4]))
        radius[nid] = float(p[5])
        parent[nid] = int(float(p[6]))
    return coord, radius, typ, parent


def edges_of(parent, coord):
    """Undirected edge set (frozensets) from SWC parent links, both endpoints present."""
    E = set()
    for n, par in parent.items():
        if par != -1 and par in coord and n in coord:
            E.add(frozenset((n, par)))
    return E


def query_labels(label_mask, ids, coord):
    """node_label[id] = int mask value at int(x,y,z), read as mask[z,y,x] (partition order)."""
    xs = np.array([int(coord[i][0]) for i in ids])
    ys = np.array([int(coord[i][1]) for i in ids])
    zs = np.array([int(coord[i][2]) for i in ids])
    vals = np.asarray(label_mask[zs, ys, xs].read().result()).reshape(-1)
    return {i: int(v) for i, v in zip(ids, vals)}


def classify(coord, parent, node_label, voxel_size):
    """Classify omit edges into 'misaligned' vs 'pure_omit' by the both-ends-same-id rule.

    Returns (misaligned_edges, pure_omit_edges, lengths_um) where lengths_um has keys
    misalign, pure_omit, omit (=misalign+pure), total.
    """
    ids = list(coord)
    E = edges_of(parent, coord)

    adj = {i: set() for i in ids}
    for e in E:
        a, b = tuple(e)
        adj[a].add(b)
        adj[b].add(a)

    is_zero = {i: (node_label.get(i, 0) == 0) for i in ids}

    # connected components of zero nodes (zero-zero adjacency)
    comp_id = {}
    components = []
    for i in ids:
        if is_zero[i] and i not in comp_id:
            members = []
            q = deque([i])
            comp_id[i] = len(components)
            while q:
                j = q.popleft()
                members.append(j)
                for k in adj[j]:
                    if is_zero[k] and k not in comp_id:
                        comp_id[k] = len(components)
                        q.append(k)
            components.append(members)

    # per component: distinct nonzero boundary neighbors + their labels
    comp_misaligned = []
    for members in components:
        border_nodes = set()
        for j in members:
            for k in adj[j]:
                if not is_zero[k]:
                    border_nodes.add(k)
        border_labels = {node_label[k] for k in border_nodes}
        # misaligned: bordered on >=2 sides, all by the same single segment id
        comp_misaligned.append(len(border_nodes) >= 2 and len(border_labels) == 1)

    def seg_len_um(e):
        a, b = tuple(e)
        d = np.asarray(coord[a]) - np.asarray(coord[b])
        return float(math.sqrt(float((d * d * np.asarray(voxel_size) ** 2).sum())))

    misaligned_edges, pure_omit_edges = set(), set()
    L = {"misalign": 0.0, "pure_omit": 0.0, "total": 0.0}
    for e in E:
        a, b = tuple(e)
        L["total"] += seg_len_um(e)
        if not (is_zero[a] or is_zero[b]):
            continue  # correct/split edge, not omit
        znode = a if is_zero[a] else b
        if comp_misaligned[comp_id[znode]]:
            misaligned_edges.add(e)
            L["misalign"] += seg_len_um(e)
        else:
            pure_omit_edges.add(e)
            L["pure_omit"] += seg_len_um(e)
    L["omit"] = L["misalign"] + L["pure_omit"]
    return misaligned_edges, pure_omit_edges, L


def write_category_swc(path: Path, edge_set, coord, radius, typ, parent, voxel_size):
    """Write the subgraph spanned by edge_set as an SWC in PHYSICAL microns."""
    nodes = set()
    for e in edge_set:
        nodes |= set(e)
    vs = np.asarray(voxel_size)
    lines = [f"# {path.name}: physical microns (voxel * {tuple(voxel_size)})"]
    for n in sorted(nodes):
        par = parent.get(n, -1)
        new_par = par if (par in nodes and frozenset((n, par)) in edge_set) else -1
        x, y, z = (np.asarray(coord[n]) * vs)
        lines.append(f"{n} {typ.get(n, 0)} {x:.6f} {y:.6f} {z:.6f} {radius.get(n, 1.0):.6f} {new_par}")
    path.write_text("\n".join(lines) + "\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--swc-dir", required=True, help="GT voxel SWCs (input-swcs-flattened)")
    ap.add_argument("--label-mask", required=True, help="segmentation mask (gs://...), same as partition")
    ap.add_argument("--partitioned-dir", required=True, help="/results/partitioned-swcs")
    ap.add_argument("--voxel-size", default="0.748,0.748,1.0")
    ap.add_argument("--out-csv", required=True)
    args = ap.parse_args()

    voxel_size = [float(x) for x in args.voxel_size.split(",")]
    swc_dir = Path(args.swc_dir)
    part_dir = Path(args.partitioned_dir)

    from neuron_tracing_utils.util.ioutil import open_ts
    label_mask = open_ts(args.label_mask)
    label_mask = label_mask[0]

    # partition's omit fractions, for a consistency check
    part_omit = {}
    res = part_dir / "results.csv"
    if res.exists():
        for row in csv.DictReader(res.open()):
            if "omit_proportion" in row:
                try:
                    part_omit[row["name"]] = float(row["omit_proportion"])
                except (ValueError, KeyError):
                    pass

    rows = []
    agg = {"omit": 0.0, "misalign": 0.0, "pure_omit": 0.0, "total": 0.0}
    for swc in sorted(swc_dir.glob("*.swc")):
        name = swc.stem
        coord, radius, typ, parent = parse_swc_full(swc)
        if not coord:
            continue
        node_label = query_labels(label_mask, list(coord), coord)
        mis_e, pure_e, L = classify(coord, parent, node_label, voxel_size)

        # write misaligned + pure-omit partitioned SWCs (physical microns)
        write_category_swc(part_dir / f"{name}_misaligned.swc", mis_e, coord, radius, typ, parent, voxel_size)
        write_category_swc(part_dir / f"{name}_omit.swc", pure_e, coord, radius, typ, parent, voxel_size)

        omit = L["omit"]
        pct = (100.0 * L["misalign"] / omit) if omit > 0 else 0.0
        recomputed_omit_frac = (omit / L["total"]) if L["total"] > 0 else 0.0
        delta = recomputed_omit_frac - part_omit.get(name, float("nan"))
        rows.append({
            "name": name,
            "total_um": round(L["total"], 3),
            "omit_um": round(omit, 3),
            "misalign_um": round(L["misalign"], 3),
            "pure_omit_um": round(L["pure_omit"], 3),
            "misalign_pct_of_omit": round(pct, 3),
            "recomputed_omit_frac": round(recomputed_omit_frac, 5),
            "partition_omit_frac": round(part_omit.get(name, float("nan")), 5),
            "omit_frac_delta": round(delta, 5) if delta == delta else "",
        })
        for k in agg:
            agg[k] += L[k]

    agg_pct = (100.0 * agg["misalign"] / agg["omit"]) if agg["omit"] > 0 else 0.0
    rows.append({
        "name": "ALL",
        "total_um": round(agg["total"], 3),
        "omit_um": round(agg["omit"], 3),
        "misalign_um": round(agg["misalign"], 3),
        "pure_omit_um": round(agg["pure_omit"], 3),
        "misalign_pct_of_omit": round(agg_pct, 3),
        "recomputed_omit_frac": "", "partition_omit_frac": "", "omit_frac_delta": "",
    })

    out = Path(args.out_csv)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    print(f"misalignment_metrics: {len(rows)-1} neurons -> {out}")
    print(f"  AGGREGATE: omit={agg['omit']:.1f}um  misalign={agg['misalign']:.1f}um "
          f"pure_omit={agg['pure_omit']:.1f}um  misalign={agg_pct:.1f}% of omit")
    # consistency check vs partition
    deltas = [r["omit_frac_delta"] for r in rows[:-1] if isinstance(r["omit_frac_delta"], float)]
    if deltas:
        md = max(abs(d) for d in deltas)
        print(f"  consistency vs partition results.csv: max |omit_frac delta| = {md:.4f} "
              f"({'OK' if md < 0.02 else 'WARNING: labeling may differ'})")


if __name__ == "__main__":
    main()
