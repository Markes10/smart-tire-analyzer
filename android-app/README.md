# Smart Tire Analyzer — Android App

On-device TFLite inference pipeline for tire condition analysis.

## TFLite Offline Inference Pipeline

The app runs a MobileNetV2-based Keras model converted to TFLite entirely on-device, no cloud connectivity required.

### Model Variants (in `app/src/main/assets/`)

| Variant | Size  | Mean Latency | FPS   |
| ------- | ----- | ------------ | ----- |
| FP32    | 8.48MB| 9.67ms       | 103.4 |
| FP16    | 4.27MB| 10.39ms      | 96.2  |
| INT8    | 2.59MB| 12.65ms      | 79.1  |

- **Input:** 224×224×3 RGB (pixel values 0–255, normalized to `[-1, 1]` by the model)
- **Outputs:** `condition` (safe/moderate/replace), `health` (0–1), `remaining_life` (0–1)
- **Default model:** `model_fp16.tflite` (best size/accuracy trade-off)

### Inference Flow

1. `CameraScreen` captures a photo via CameraX `ImageCapture`
2. Frame is converted to `Bitmap` via `TireInferenceEngine.imageProxyToBitmap()`
3. `TireTwinViewModel.runTireInference(bitmap)` runs TFLite on `Dispatchers.IO`
4. Raw tensor outputs are mapped to a `GeminiAnalysis` object
5. Results surface in the UI through `tireInferenceResult` StateFlow

### Key Files

- `util/TireInferenceEngine.kt` — model loading, inference, Bitmap conversion
- `viewmodel/TireTwinViewModel.kt` — inference state + orchestration
- `ui/screens/CameraScreen.kt` — camera capture + scan trigger UI

## Run Locally

**Prerequisites:** [Android Studio](https://developer.android.com/studio)

1. Open Android Studio
2. Select **Open** and choose the `android-app/` directory
3. Allow Android Studio to fix any incompatibilities as it imports the project
4. Create a file named `.env` in the project root and set `GEMINI_API_KEY` in that file to your Gemini API key (see `.env.example` for an example)
5. Remove this line from `app/build.gradle.kts` if present: `signingConfig = signingConfigs.getByName("debugConfig")`
6. Build and run on an emulator or physical device (API 24+)
