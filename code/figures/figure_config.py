"""Shared configuration and house style for the single-run figure scripts.

Every figure is driven entirely by environment variables so one capsule run
produces its own figures with no per-run source editing:

    FIGURE_RUN_DIR   run's metric outputs            (default /results)
    FIGURE_OUT_DIR   where figures + CSVs are written (default /results/figures)
    FIGURE_SAMPLE    sample id for titles/filenames   (default: inferred from
                     the neuron names, else "sample")
    FIGURE_CHECKPOINT model/checkpoint label for titles (default "checkpoint")
    FIGURE_VOXEL_SIZE x,y,z microns per GT voxel       (default 0.748,0.748,1.0)
    FIGURE_SKELETON_TOL_UM  match tolerance, skeleton recall (default 5)
    FIGURE_BINARY_MASK optional tensorstore/URL to the binary mask volume; when
                     unset the binary-mask recall level is reported as n/a

FIGURE_RUN_DIR is expected to contain the capsule outputs:
    partitioned-swcs/results.csv, merged-length.csv, predicted-components/,
    intensity-npys/, input-swcs-flattened/, misalignment_metrics.csv
"""
from __future__ import annotations

import os
from pathlib import Path

import numpy as np

RUN_DIR = Path(os.environ.get("FIGURE_RUN_DIR", "/results"))
OUT_DIR = Path(os.environ.get("FIGURE_OUT_DIR", "/results/figures"))
OUT_DIR.mkdir(parents=True, exist_ok=True)

VOXEL_SIZE = np.array([float(x) for x in
                       os.environ.get("FIGURE_VOXEL_SIZE", "0.748,0.748,1.0").split(",")])
SKELETON_TOL_UM = float(os.environ.get("FIGURE_SKELETON_TOL_UM", "5"))
BINARY_MASK = os.environ.get("FIGURE_BINARY_MASK", "").strip()
CHECKPOINT = os.environ.get("FIGURE_CHECKPOINT", "checkpoint").strip() or "checkpoint"

# Allen house palette (brand hex; no dependency on an external style package).
COLORS = {
    "gt": "#6660e5", "gt_light": "#9a94ff", "recall": "#7cbf4d",
    "omit": "#cd0f55", "merge": "#d81168", "skeleton": "#16a8a4",
    "binary": "#6660e5", "muted": "#666666", "ink": "#111111",
}


def _infer_sample() -> str:
    env = os.environ.get("FIGURE_SAMPLE", "").strip()
    if env:
        return env
    swc_dir = RUN_DIR / "input-swcs-flattened"
    if swc_dir.is_dir():
        for f in sorted(swc_dir.glob("*.swc")):
            parts = f.stem.split("-")          # N001-<sample>-XX-AXON
            if len(parts) >= 2 and parts[1]:
                return parts[1]
    return "sample"


SAMPLE = _infer_sample()


def out_path(basename: str) -> Path:
    """Output path prefixed with the sample id, e.g. <sample>_visual_table.png."""
    return OUT_DIR / f"{SAMPLE}_{basename}"


def neuron_short(name: str) -> str:
    """First field of a neuron name, e.g. N001-794495-JT-AXON -> N001."""
    return name.split("-")[0]


def neuron_label(name: str) -> str:
    """Two-line label with the sample field dropped, for per-neuron titles."""
    return name.replace(f"-{SAMPLE}-", "\n")


# Candidate locations for the Allen headline font, most-specific first. The
# macOS managed path only exists on a workstation; the capsule runs on Linux,
# so a hardcoded macOS path silently falls back to the default font there.
_FONT_CANDIDATES = [
    os.environ.get("FIGURE_FONT", ""),
    "/Library/Fonts/Managed/AllenInstitutePlusHead-Rg_357723850.otf",
    "/usr/share/fonts/opentype/allen/AllenInstitutePlusHead-Rg.otf",
    "/usr/share/fonts/truetype/allen/AllenInstitutePlusHead-Rg.otf",
]
_STYLE_APPLIED = False


def apply_house_style() -> None:
    """Register the Allen headline font if present, else leave the default.

    Idempotent and never raises: a missing font must not fail a figure.
    """
    global _STYLE_APPLIED
    if _STYLE_APPLIED:
        return
    _STYLE_APPLIED = True
    try:
        from matplotlib import font_manager, rcParams
        for cand in _FONT_CANDIDATES:
            if cand and Path(cand).exists():
                font_manager.fontManager.addfont(cand)
                rcParams["font.family"] = font_manager.FontProperties(fname=cand).get_name()
                break
    except Exception:
        pass
