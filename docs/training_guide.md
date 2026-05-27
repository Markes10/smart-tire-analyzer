# Smart Tire Analyzer — Training Guide

## Overview

The training pipeline uses multi-task learning on 4 simultaneous outputs:
tread depth (regression), health score (regression), remaining life (regression),
and wear pattern (6-class classification).

---

## Prerequisites

```bash
# Install training dependencies
pip install tensorflow==2.16.1 albumentations opencv-python-headless

# Activate virtual environment
source .venv/bin/activate  # Linux/macOS
.venv\Scripts\activate     # Windows
```

---

## Step 1: Prepare Your Dataset

### Required directory structure
```
dataset/
├── images/
│   ├── tire_001.jpg
│   ├── tire_002.jpg
│   └── ...
└── labels/
    ├── tread_depth.csv      ← T1-T4 measurements in mm
    ├── wear_pattern.csv     ← 0-5 class labels
    └── tire_health.csv      ← 0-10 health scores
```

### label CSV formats

**tread_depth.csv**
```csv
image_id,tread_1,tread_2,tread_3,tread_4,tread_average,brand,tire_size
tire_001,7.2,7.0,6.8,6.9,6.975,Michelin,185/65 R15
```

**wear_pattern.csv** — Class IDs:
| ID | Class | Cause |
|---|---|---|
| 0 | center_wear | Overinflation |
| 1 | edge_wear | Underinflation |
| 2 | patchy_wear | Misalignment |
| 3 | uniform_wear | Normal wear |
| 4 | one_side_wear | Camber issue |
| 5 | cupping_wear | Suspension damage |

### Step 2: Validate and Clean

```bash
python dataset/preprocessing/validate_images.py
python dataset/preprocessing/clean_dataset.py
python dataset/preprocessing/split_dataset.py
```

---

## Step 3: Configure Training

Edit `configs/training_config.yaml`:

```yaml
training:
  epochs: 50           # Reduce to 5-10 for quick tests
  batch_size: 16       # Reduce to 4-8 for low VRAM
  optimizer:
    peak_lr: 1.0e-4    # Learning rate
  mixed_precision: true  # Enable for GPU speedup
```

---

## Step 4: Train

```bash
# Standard training
python ai_model/training/train.py

# Custom parameters
python ai_model/training/train.py `
  --epochs 30 `
  --batch_size 8 `
  --config configs/training_config.yaml
```

**Training outputs:**
- `ai_model/saved_models/model_best.h5` — Best validation checkpoint
- `logs/training/` — TensorBoard logs
- `ai_model/saved_models/model_registry.json` — Version metadata

---

## Step 5: Evaluate

```bash
python ai_model/evaluation/evaluate.py \
  --model ai_model/saved_models/model_best.h5 \
  --split test
```

**Target metrics:**
| Metric | Target | Description |
|---|---|---|
| `tread_mae_mm` | < 0.5mm | Average tread depth error |
| `tread_within_0.5mm` | > 0.80 | 80%+ predictions within 0.5mm |
| `danger_zone_recall` | > 0.95 | 95%+ detection of dangerous tires |
| `wear_accuracy` | > 0.80 | 80%+ wear pattern accuracy |
| `health_mae` | < 0.5 | Health score error (0-10 scale) |

---

## Step 6: Export to TFLite (Mobile)

```bash
python ai_model/optimization/quantize.py \
  --model ai_model/saved_models/model_best.h5 \
  --output ai_model/saved_models/
```

**Output files:**
- `model_latest.tflite` — Standard FP32 (used by backend)  
- `model_fp16.tflite` — FP16 quantized (~2× smaller)
- `model_int8.tflite` — INT8 quantized (~4× smaller, for mobile)
- `benchmark_report.json` — Latency test results

---

## Minimum Dataset Requirements

| Wear Pattern | Min Samples |
|---|---|
| center_wear | 200 |
| edge_wear | 200 |
| patchy_wear | 150 |
| uniform_wear | 400 |
| one_side_wear | 150 |
| cupping_wear | 150 |
| **Total** | **1,250+** |

For production accuracy (MAE < 0.5mm), aim for 5,000+ labeled images.

---

## Transfer Learning (Recommended)

The active PyTorch hybrid uses ImageNet-pretrained EfficientNetV2-B0 and ViT-B/16
branches. The training pipeline handles this automatically:

1. Stage 1: EfficientNetV2-B0 and ViT-B/16 encoders stay frozen while the BiLSTM + TCN sequence branch, attention fusion, uncertainty loss weights, and heads train.
2. Stage 2: the last EfficientNetV2-B0 feature blocks and the last two ViT encoder blocks unfreeze for fine-tuning.
3. After training: validation predictions fit a per-position isotonic tread-depth calibrator, then the same calibrator is applied to final validation/test metrics and runtime inference.

---

## GPU Training

TensorFlow will automatically use CUDA GPUs. Check:

```bash
python -c "import tensorflow as tf; print(tf.config.list_physical_devices('GPU'))"
```

For Google Colab or Kaggle, enable GPU runtime and upload the dataset to the session.

---

## TensorBoard Monitoring

```bash
tensorboard --logdir logs/training/
# Open: http://localhost:6006
```

Watch for:
- `val_loss` decreasing each epoch
- No divergence between `train_loss` and `val_loss`
- `danger_zone_recall` staying above 0.90
