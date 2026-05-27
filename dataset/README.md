Dataset structure and class schemas

Overview:
- `schemas/`: YAML files defining class categories used across models and pipelines.
- `labels/`: per-category folders for human or automated label files (one label file per image/record).
- `images/`, `raw/`, `processed/`: existing image data folders remain unchanged.

Labeling conventions:
- Store categorical labels in `dataset/labels/<category>/` as JSON or CSV per example.
- For `tread_depth`, include both a `depth_mm` (float) regression value and `depth_class` (string).

Where to use:
- The YAML schema files in `dataset/schemas/` provide canonical class lists and thresholds for training, evaluation and inference pipelines.
