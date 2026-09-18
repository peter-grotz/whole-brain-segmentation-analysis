# Single-run figures

Downstream visualizations of one capsule run. Each script reads the run's
outputs and writes a PNG (plus CSVs) to the figures directory. They are driven
entirely by environment variables (see `figure_config.py`) so no script contains
a sample id, checkpoint name, or absolute path.

| script | output (prefixed with the sample id) |
|---|---|
| `make_visual_table.py` | `<sample>_visual_table.png` — per-neuron omit/recall, geometry, intensities, fragment lengths |
| `make_visual_table_compact.py` | `<sample>_visual_table_compact.png` — compact variant |
| `make_summary_panels.py` | `<sample>_summary_panels.png` — run-level summary |
| `make_omit_gap_characterization.py` | `omit_gap_characterization.png` — pure-omit split into interior gaps vs endpoint cable |
| `make_three_level_recall.py` | `three_level_recall.png` — recall at binary-mask / label-mask / skeleton levels |

## Environment
`FIGURE_RUN_DIR`, `FIGURE_OUT_DIR`, `FIGURE_SAMPLE`, `FIGURE_CHECKPOINT`,
`FIGURE_VOXEL_SIZE`, `FIGURE_SKELETON_TOL_UM`, `FIGURE_BINARY_MASK`, `FIGURE_FONT`.
`FIGURE_SAMPLE` is inferred from the neuron names when unset. Everything degrades
gracefully: a missing font falls back to the default, and the binary-mask recall
level is reported as `n/a` unless `FIGURE_BINARY_MASK` is provided and readable.

## Run standalone (outside the capsule)
```bash
FIGURE_RUN_DIR=/path/to/results FIGURE_OUT_DIR=/tmp/figs \
  PYTHONPATH=code/figures python3 code/figures/make_three_level_recall.py
```
