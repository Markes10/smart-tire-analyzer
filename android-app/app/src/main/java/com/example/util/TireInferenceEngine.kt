package com.example.util

import android.content.Context
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.graphics.ImageFormat
import android.graphics.Matrix
import android.graphics.Rect
import android.graphics.YuvImage
import androidx.camera.core.ImageProxy
import java.io.ByteArrayOutputStream
import java.nio.ByteBuffer
import java.nio.ByteOrder
import org.tensorflow.lite.Interpreter

data class TireInferenceResult(
    val condition: String,
    val conditionConfidence: Float,
    val health: Float,
    val remainingLife: Float
)

class TireInferenceEngine(private val context: Context) {

    private var interpreter: Interpreter? = null
    private var isLoaded = false

    private val imageSize = 224
    private val labels = arrayOf("safe", "moderate", "replace")

    fun loadModel(modelName: String = "model_fp16.tflite") {
        if (isLoaded) return
        val modelBuffer = org.tensorflow.lite.support.common.FileUtil.loadMappedFile(context, modelName)
        val options = Interpreter.Options().apply { setNumThreads(4) }
        interpreter = Interpreter(modelBuffer, options)
        isLoaded = true
    }

    fun infer(bitmap: Bitmap): TireInferenceResult {
        val interpreter = interpreter ?: throw IllegalStateException("Model not loaded")

        val resized = Bitmap.createScaledBitmap(bitmap, imageSize, imageSize, true)

        val inputBuffer = ByteBuffer.allocateDirect(4 * imageSize * imageSize * 3)
        inputBuffer.order(ByteOrder.nativeOrder())
        val pixels = IntArray(imageSize * imageSize)
        resized.getPixels(pixels, 0, imageSize, 0, 0, imageSize, imageSize)
        for (pixel in pixels) {
            inputBuffer.putFloat(((pixel shr 16) and 0xFF).toFloat())
            inputBuffer.putFloat(((pixel shr 8) and 0xFF).toFloat())
            inputBuffer.putFloat((pixel and 0xFF).toFloat())
        }

        val outputCondition = Array(1) { FloatArray(3) }
        val outputHealth = Array(1) { FloatArray(1) }
        val outputLife = Array(1) { FloatArray(1) }

        interpreter.runForMultipleInputsOutputs(
            arrayOf(inputBuffer),
            mapOf(
                0 to outputHealth,
                1 to outputCondition,
                2 to outputLife
            )
        )

        val probs = outputCondition[0]
        val conditionIdx = probs.indices.maxByOrNull { probs[it] } ?: 0

        return TireInferenceResult(
            condition = labels[conditionIdx],
            conditionConfidence = probs[conditionIdx],
            health = outputHealth[0][0],
            remainingLife = outputLife[0][0]
        )
    }

    fun imageProxyToBitmap(imageProxy: ImageProxy): Bitmap? {
        val bitmap = when (imageProxy.format) {
            ImageFormat.JPEG -> {
                val buffer = imageProxy.planes[0].buffer
                val bytes = ByteArray(buffer.remaining())
                buffer.get(bytes)
                BitmapFactory.decodeByteArray(bytes, 0, bytes.size)
            }
            ImageFormat.YUV_420_888, ImageFormat.NV21 -> {
                val yBuffer = imageProxy.planes[0].buffer
                val uBuffer = imageProxy.planes[1].buffer
                val vBuffer = imageProxy.planes[2].buffer

                val ySize = yBuffer.remaining()
                val uSize = uBuffer.remaining()
                val vSize = vBuffer.remaining()

                val nv21 = ByteArray(ySize + uSize + vSize)
                yBuffer.get(nv21, 0, ySize)
                vBuffer.get(nv21, ySize, vSize)
                uBuffer.get(nv21, ySize + vSize, uSize)

                val yuvImage = YuvImage(nv21, ImageFormat.NV21, imageProxy.width, imageProxy.height, null)
                val out = ByteArrayOutputStream()
                yuvImage.compressToJpeg(Rect(0, 0, imageProxy.width, imageProxy.height), 100, out)
                val jpegBytes = out.toByteArray()
                BitmapFactory.decodeByteArray(jpegBytes, 0, jpegBytes.size)
            }
            else -> {
                val buffer = imageProxy.planes[0].buffer
                val bytes = ByteArray(buffer.remaining())
                buffer.get(bytes)
                BitmapFactory.decodeByteArray(bytes, 0, bytes.size)
            }
        }

        if (bitmap == null) return null

        val matrix = Matrix().apply { postRotate(imageProxy.imageInfo.rotationDegrees.toFloat()) }
        return Bitmap.createBitmap(bitmap, 0, 0, bitmap.width, bitmap.height, matrix, true)
    }

    fun close() {
        interpreter?.close()
        interpreter = null
        isLoaded = false
    }
}
