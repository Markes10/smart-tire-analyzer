# Model Versioning Changelog

All model versions, training runs, and deployments are recorded here.
Auto-updated by `version_manager.py` on each training cycle.

---

## Format

Each entry follows this template:
```
## v{major}.{minor}.{patch} — YYYY-MM-DD

**Type:** full_retrain | incremental | quantization | rollback
**Training Samples:** N  
**Dataset:** vX.Y (hash: abc123)

### Metrics (Test Set)
- Tread MAE: X.XX mm
- Danger Zone Recall: X.XX
- Wear Pattern Accuracy: X.XX
- Health Score MAE: X.XX

### Changes
- Description of what changed

### Notes
- Deployment notes, caveats, observations
```

---

## v1.0.0 — 2026-04-09

**Type:** initial  
**Training Samples:** 0 (initial placeholder)
**Dataset:** synthetic

### Metrics (Test Set)
- Tread MAE: N/A (untrained)
- Danger Zone Recall: N/A
- Wear Pattern Accuracy: N/A
- Health Score MAE: N/A

### Changes
- Initial project scaffold — model architecture defined
- CNN (MobileNetV2) + ViT + Bidirectional LSTM + ANN fusion
- 4 output heads: tread depth, health, remaining life, wear pattern
- TurboQuant optimization pipeline ready

### Notes
- No real training data yet. Models will produce synthetic predictions.
- Training pipeline, loss functions, callbacks all implemented.
- Ready for dataset integration and first training run.

---

*This file is auto-updated. Do not edit manually during active training.*
