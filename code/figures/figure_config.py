"""Shared path configuration for the vendored single-run figure scripts.

These scripts originally hardcoded absolute macOS paths. Inside the capsule
pipeline they are driven by environment variables so a single capsule run can
produce its own figures with no per-run editing:

    FIGURE_RUN_DIR  directory holding this run's metric outputs (default /results)
    FIGURE_OUT_DIR  directory to write figures + figure CSVs (default /results/figures)

FIGURE_RUN_DIR is expected to contain the capsule outputs:
    partitioned-swcs/results.csv, merged-length.csv, predicted-components/,
    intensity-npys/, input-swcs-flattened/
"""
from __future__ import annotations

import os
from pathlib import Path

RUN_DIR = Path(os.environ.get("FIGURE_RUN_DIR", "/results"))
OUT_DIR = Path(os.environ.get("FIGURE_OUT_DIR", "/results/figures"))
OUT_DIR.mkdir(parents=True, exist_ok=True)
