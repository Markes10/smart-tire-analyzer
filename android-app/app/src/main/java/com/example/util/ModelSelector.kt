package com.example.util

import android.content.Context
import android.util.Log

/**
 * Selects the best available model for the current device.
 * Priority: FP16 > INT8 > FP32 (based on performance)
 */
object ModelSelector {
    private const val TAG = "ModelSelector"

    enum class ModelType(val filename: String, val description: String) {
        FP16("model_fp16.tflite", "FP16 quantized (balanced)"),
        INT8("model_int8.tflite", "INT8 quantized (fastest)"),
        FP32("model_latest.tflite", "FP32 (most accurate)"),
    }

    fun selectModel(context: Context): ModelType {
        val available = ModelType.entries.filter {
            try {
                context.assets.open(it.filename).use { true }
            } catch (e: Exception) {
                false
            }
        }

        return when {
            ModelType.FP16 in available -> {
                Log.d(TAG, "Selected FP16 model (best balance)")
                ModelType.FP16
            }
            ModelType.INT8 in available -> {
                Log.d(TAG, "Selected INT8 model (fastest)")
                ModelType.INT8
            }
            ModelType.FP32 in available -> {
                Log.d(TAG, "Selected FP32 model (most accurate)")
                ModelType.FP32
            }
            else -> throw IllegalStateException("No TFLite model found in assets")
        }
    }
}
