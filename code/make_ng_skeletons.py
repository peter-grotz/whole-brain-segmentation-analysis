#!/usr/bin/env python3
"""Generate Neuroglancer precomputed skeleton layers (in VOXEL space) from the capsule's
SWC outputs, plus a Neuroglancer link that overlays them on the sample-space volume.

Produces three precomputed segmentation/skeleton sources, mirroring the AIND
`*.precomputed` convention (verified against a public aind-open-data example):

  correct_omit.precomputed  <- partitioned-swcs/*_correct.swc (green) + *_omit.swc (red)
  fragments.precomputed     <- predicted-components/<neuron>/*.swc (one segment per fragment)
  gt_input.precomputed      <- input-swcs-flattened/*.swc (one segment per neuron)

Coordinate handling: the partitioned (correct/omit) and predicted-component SWCs are in
physical microns (x,y = voxel_index * 0.748); input-swcs-flattened is already voxel. All
vertices are written in VOXEL units (skeleton/info `transform` = diag(748,748,1000) nm
takes them to physical), matching the reference layout and the voxel-space NG view.

Format per segment (neuroglancer_skeletons, unsharded):
  uint32 num_vertices, uint32 num_edges,
  float32[num_vertices*3] vertices (x,y,z, voxel units),
  uint32[num_edges*2] edges (0-based vertex indices),
  float32[num_vertices] radius            # one declared vertex attribute
"""
from __future__ import annotations

import argparse
import json
import os
import struct
import urllib.parse
from pathlib import Path

import numpy as np

RESOLUTION_NM = [748.0, 748.0, 1000.0]          # x, y, z nm/voxel (matches reference)
SKELETON_TRANSFORM = [748.0, 0, 0, 0, 0, 748.0, 0, 0, 0, 0, 1000.0, 0]
GREEN = "#2ca02c"
RED = "#d62728"
ORANGE = "#ff7f0e"   # misaligned (GT drifts off a continuous fragment)
NG_HOST = "https://neuroglancer-demo.appspot.com/"


def parse_swc(path: Path):
    """Return (vertices Nx3 float64 in file-native coords, edges Mx2 int, radii N)."""
    coords: dict[int, tuple[float, float, float]] = {}
    parents: dict[int, int] = {}
    radii: dict[int, float] = {}
    for raw in path.read_text(errors="ignore").splitlines():
        s = raw.strip()
        if not s or s.startswith("#"):
            continue
        p = s.split()
        if len(p) < 7:
            continue
        nid = int(float(p[0]))
        coords[nid] = (float(p[2]), float(p[3]), float(p[4]))
        radii[nid] = float(p[5])
        parents[nid] = int(float(p[6]))
    if not coords:
        return np.empty((0, 3)), np.empty((0, 2), dtype=np.uint32), np.empty((0,))
    node_ids = sorted(coords)
    index = {nid: i for i, nid in enumerate(node_ids)}
    verts = np.array([coords[n] for n in node_ids], dtype=np.float64)
    rad = np.array([radii[n] for n in node_ids], dtype=np.float64)
    edges = []
    for nid in node_ids:
        par = parents[nid]
        if par != -1 and par in index:
            edges.append((index[nid], index[par]))
    edges = np.array(edges, dtype=np.uint32) if edges else np.empty((0, 2), dtype=np.uint32)
    return verts, edges, rad


def encode_skeleton(verts_voxel: np.ndarray, edges: np.ndarray, radii: np.ndarray) -> bytes:
    nv = verts_voxel.shape[0]
    ne = edges.shape[0]
    out = bytearray()
    out += struct.pack("<II", nv, ne)
    out += verts_voxel.astype("<f4").tobytes()
    out += edges.astype("<u4").tobytes()
    out += radii.astype("<f4").tobytes()
    return bytes(out)


def write_layer(out_dir: Path, items, volume_size):
    """items: list of dicts {seg_id:int, label:str, verts:Nx3 voxel, edges, radii}."""
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "skeleton").mkdir(exist_ok=True)
    (out_dir / "segment_properties").mkdir(exist_ok=True)

    (out_dir / "info").write_text(json.dumps({
        "data_type": "uint64",
        "num_channels": 1,
        "scales": [{
            "chunk_sizes": [[128, 128, 128]],
            "encoding": "raw",
            "key": "748.0_748.0_1000.0",
            "resolution": RESOLUTION_NM,
            "size": list(volume_size),
            "voxel_offset": [0, 0, 0],
        }],
        "segment_properties": "segment_properties",
        "skeletons": "skeleton",
        "type": "segmentation",
    }))

    (out_dir / "skeleton" / "info").write_text(json.dumps({
        "@type": "neuroglancer_skeletons",
        "transform": SKELETON_TRANSFORM,
        "vertex_attributes": [{"id": "radius", "data_type": "float32", "num_components": 1}],
        "spatial_index": None,
    }))

    ids, labels = [], []
    for it in items:
        (out_dir / "skeleton" / str(it["seg_id"])).write_bytes(
            encode_skeleton(it["verts"], it["edges"], it["radii"])
        )
        ids.append(str(it["seg_id"]))
        labels.append(it["label"])

    (out_dir / "segment_properties" / "info").write_text(json.dumps({
        "@type": "neuroglancer_segment_properties",
        "inline": {
            "ids": ids,
            "properties": [
                {"id": "label", "type": "label", "description": "source swc", "values": labels}
            ],
        },
    }))
    return ids


def to_voxel(verts: np.ndarray, voxel_size, already_voxel: bool) -> np.ndarray:
    if already_voxel or verts.size == 0:
        return verts
    vs = np.asarray(voxel_size, dtype=np.float64)
    return verts / vs  # x/0.748, y/0.748, z/1.0


def build_items(swc_paths, label_fn, voxel_size, already_voxel, start_id=1):
    items = []
    seg = start_id
    for path in sorted(swc_paths):
        verts, edges, radii = parse_swc(path)
        if verts.shape[0] == 0:
            continue
        items.append({
            "seg_id": seg,
            "label": label_fn(path),
            "verts": to_voxel(verts, voxel_size, already_voxel),
            "edges": edges,
            "radii": radii,
        })
        seg += 1
    return items


def fetch_volume_size(image_source, fallback):
    """Read x,y,z voxel dims from the zarr level-0 .zarray (public, anon). Fall back on error."""
    try:
        import fsspec
        fs = fsspec.filesystem("s3", anon=True)
        with fs.open(image_source.rstrip("/") + "/0/.zarray") as f:
            shape = json.load(f)["shape"]
        return [int(shape[-1]), int(shape[-2]), int(shape[-3])]  # x, y, z
    except Exception as exc:
        print(f"make_ng_skeletons: could not read volume size from {image_source} "
              f"({exc}); using fallback {fallback}")
        return fallback


def ng_link(image_source, seg_layers):
    """seg_layers: list of dicts {name, source, segments(list[str]), colors(dict|None)}."""
    layers = [{
        "type": "image",
        "source": image_source + "/|zarr2:",
        "localDimensions": {"c'": [1, ""]},
        "localPosition": [0],
        "tab": "rendering",
        "name": "fused.zarr",
    }]
    for L in seg_layers:
        layer = {
            "type": "segmentation",
            "source": L["source"] + "/|neuroglancer-precomputed:",
            "tab": "segments",
            "skeletonRendering": {"lineWidth3d": 7},
            "segments": L["segments"],
            "name": L["name"],
        }
        if L.get("colors"):
            layer["segmentColors"] = L["colors"]
        layers.append(layer)
    state = {
        "dimensions": {"x": [7.48e-7, "m"], "y": [7.48e-7, "m"],
                       "z": [1e-6, "m"], "t": [0.001, "s"]},
        "layers": layers,
        "layout": "4panel-alt",
    }
    return NG_HOST + "#!" + urllib.parse.quote(json.dumps(state, separators=(",", ":")))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--results-dir", required=True)
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--voxel-size", default="0.748,0.748,1.0")
    ap.add_argument("--image-source", required=True,
                    help="s3://.../fused.zarr  (zarr2 adapter appended automatically)")
    ap.add_argument("--s3-base", required=True,
                    help="public base URL the .precomputed dirs will live under, "
                         "e.g. s3://aind-msma-morphology-data/794495/ng_skeletons")
    ap.add_argument("--volume-size", default="67530,40789,22973",
                    help="x,y,z voxel size of the sample volume (fused.zarr level 0)")
    args = ap.parse_args()

    voxel_size = [float(x) for x in args.voxel_size.split(",")]
    fallback_size = [int(x) for x in args.volume_size.split(",")]
    volume_size = fetch_volume_size(args.image_source, fallback_size)
    rdir = Path(args.results_dir)
    odir = Path(args.out_dir)
    base = args.s3_base.rstrip("/")

    seg_layers = []

    # 1) correct + omit + misaligned (physical um -> voxel)
    #    correct = green, pure omit = red, misaligned = orange
    part = rdir / "partitioned-swcs"
    correct = build_items(part.glob("*_correct.swc"), lambda p: p.stem, voxel_size, False, 1)
    omit = build_items(part.glob("*_omit.swc"), lambda p: p.stem, voxel_size, False,
                       start_id=1 + len(correct))
    misaligned = build_items(part.glob("*_misaligned.swc"), lambda p: p.stem, voxel_size, False,
                             start_id=1 + len(correct) + len(omit))
    co_items = correct + omit + misaligned
    if co_items:
        ids = write_layer(odir / "correct_omit.precomputed", co_items, volume_size)
        colors = {}
        for it in correct:
            colors[str(it["seg_id"])] = GREEN
        for it in omit:
            colors[str(it["seg_id"])] = RED
        for it in misaligned:
            colors[str(it["seg_id"])] = ORANGE
        seg_layers.append({"name": "correct_omit", "source": f"{base}/correct_omit.precomputed",
                           "segments": ids, "colors": colors})

    # 2) predicted components / fragments (physical um -> voxel); default per-segment colors
    comp = rdir / "predicted-components"
    frag_paths = sorted(comp.glob("*/*.swc"))
    frag_items = build_items(
        frag_paths,
        lambda p: f"{p.parent.name}/{p.stem}", voxel_size, False, 1)
    if frag_items:
        ids = write_layer(odir / "fragments.precomputed", frag_items, volume_size)
        seg_layers.append({"name": "fragments", "source": f"{base}/fragments.precomputed",
                           "segments": ids, "colors": None})

    # 3) GT input (already voxel); default per-segment (per-neuron) colors
    gt = rdir / "input-swcs-flattened"
    gt_items = build_items(gt.glob("*.swc"), lambda p: p.stem, voxel_size, True, 1)
    if gt_items:
        ids = write_layer(odir / "gt_input.precomputed", gt_items, volume_size)
        seg_layers.append({"name": "gt_input", "source": f"{base}/gt_input.precomputed",
                           "segments": ids, "colors": None})

    link = ng_link(args.image_source, seg_layers)
    (odir / "neuroglancer_link.txt").write_text(link + "\n")
    print("Layers written:")
    for L in seg_layers:
        print(f"  {L['name']}: {len(L['segments'])} skeletons -> {odir / (L['name'] + '.precomputed')}")
    print(f"\nNeuroglancer link written to {odir / 'neuroglancer_link.txt'}")


if __name__ == "__main__":
    main()
