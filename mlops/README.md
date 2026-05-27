# MLOps Pipeline

This folder contains local-first MLOps artifacts for the Smart Tire Analyzer final-year project.

The production tools are represented as optional adapters so the main project still runs locally:

- MLflow / Weights & Biases: experiment tracking adapters
- DVC: dataset versioning pipeline
- Kubeflow: cloud training pipeline skeleton
- Airflow: scheduled lifecycle DAG skeleton
- FastAPI `/enterprise/dashboard`: runtime monitoring dashboard data

Local demo command:

```bash
python scripts/mlops_pipeline.py
```

The command records a lifecycle event under `training_logs/mlops_events/` and prints the dataset fingerprint, registry status, deployment status, and monitoring hooks.
