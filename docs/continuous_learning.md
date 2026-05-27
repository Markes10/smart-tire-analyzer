# Continuous Learning

The normal app flow is automatic:

1. User analyzes a tire image.
2. User submits correction/feedback for that session.
3. Backend saves the original image and corrected tread labels under `dataset/continuous_learning/`.
4. Backend reports the corrected-sample queue through `/feedback/stats` and `/feedback/retrain/status`.
5. When enough corrected image samples exist, backend starts hybrid retraining automatically and refreshes prepared dataset artifacts as part of that run.

Default trigger:

```powershell
RETRAIN_THRESHOLD=10
```

Check status:

```powershell
curl http://localhost:8000/feedback/retrain/status
```

## Manual Intake Fallback

Use `scripts/add_learning_samples.py` only when the samples are outside the app and you want to import them directly.

Add one sample:

```powershell
.venv\Scripts\python scripts\add_learning_samples.py `
  --image "C:\path\front_tire.jpg" `
  --tread-1 5.2 --tread-2 5.1 --tread-3 5.0 --tread-4 5.1 `
  --brand MRF `
  --tire-model ZLX `
  --tire-size "165/80 R14" `
  --prepare
```

This copies the image into:

```text
dataset/raw/learning_samples/front_view/
```

and writes the label row into:

```text
dataset/raw/learning_samples/labels.csv
```

## Batch Fallback

Create a CSV template:

```powershell
.venv\Scripts\python scripts\add_learning_samples.py --write-template dataset\raw\learning_samples\new_samples.csv
```

Fill one row per tire image, then import it:

```powershell
.venv\Scripts\python scripts\add_learning_samples.py --csv dataset\raw\learning_samples\new_samples.csv --prepare
```

Required CSV columns:

```text
image_path,tread_1,tread_2,tread_3,tread_4
```

Optional CSV columns:

```text
brand,tire_model,tire_size,sidewall_image_path,ocr_text,tube_type
```

## Retrain Controls

Automatic training uses:

```text
AUTO_RETRAIN=true
AUTO_RETRAIN_TRAIN=true
AUTO_RETRAIN_REFRESH=false
AUTO_RETRAIN_STAGE1_EPOCHS=2
AUTO_RETRAIN_STAGE2_EPOCHS=1
```

Set `AUTO_RETRAIN_TRAIN=false` if you only want the threshold-triggered dataset refresh without launching model training.
Set `AUTO_RETRAIN_REFRESH=true` if you also want prepared dataset artifacts refreshed in the background before the threshold is reached.

Manual training is still available:

```powershell
.venv\Scripts\python scripts\prepare_and_train.py --fresh-hybrid --full-train
```

`scripts/prepare_dataset.py` merges app feedback and manual intake rows as long as they include front-view image paths and tread-depth correction data.
