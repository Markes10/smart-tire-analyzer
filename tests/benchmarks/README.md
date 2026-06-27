# Performance Benchmarks

## API Benchmarks
```bash
# Install deps
pip install pytest-benchmark

# Run all benchmarks
pytest tests/benchmarks/ --benchmark-only

# Compare with baseline
pytest tests/benchmarks/ --benchmark-compare --benchmark-compare-fail=min:5%
```

## Model Inference Benchmarks
```bash
python -m tests.benchmarks.test_model_inference
```

## API Load Tests (Locust)
```bash
# Start backend first
python scripts/start_server.py

# Run locust
locust -f tests/load_testing/locustfile.py --host=http://localhost:8000
# Open http://localhost:8089 for web UI
```
