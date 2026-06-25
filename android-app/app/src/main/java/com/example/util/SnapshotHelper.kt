package com.example.util

import android.app.Activity
import android.content.ContentValues
import android.content.Context
import android.content.ContextWrapper
import android.graphics.Bitmap
import android.graphics.Rect
import android.net.Uri
import android.os.Build
import android.os.Environment
import android.os.Handler
import android.os.Looper
import android.provider.MediaStore
import android.view.PixelCopy
import android.view.View
import android.widget.Toast
import androidx.compose.ui.layout.LayoutCoordinates
import androidx.compose.ui.layout.boundsInWindow

object SnapshotHelper {

    private tailrec fun Context.findActivity(): Activity? = when (this) {
        is Activity -> this
        is ContextWrapper -> baseContext.findActivity()
        else -> null
    }

    fun captureAndSaveSnapshot(
        context: Context,
        view: View,
        coordinates: LayoutCoordinates,
        fileName: String
    ) {
        val bounds = coordinates.boundsInWindow()
        val width = bounds.width.toInt().coerceAtLeast(1)
        val height = bounds.height.toInt().coerceAtLeast(1)
        val bitmap = Bitmap.createBitmap(width, height, Bitmap.Config.ARGB_8888)

        val location = IntArray(2)
        view.getLocationInWindow(location)
        val x = (bounds.left.toInt() - location[0]).coerceAtIn(0, view.width)
        val y = (bounds.top.toInt() - location[1]).coerceAtIn(0, view.height)

        val activity = context.findActivity()
        if (activity != null && Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val window = activity.window
            val right = (x + width).coerceAtMost(view.width)
            val bottom = (y + height).coerceAtMost(view.height)
            if (right <= x || bottom <= y) {
                Toast.makeText(context, "Failed to capture snapshot (bounds error)", Toast.LENGTH_SHORT).show()
                return
            }
            val rect = Rect(x, y, right, bottom)
            try {
                PixelCopy.request(
                    window,
                    rect,
                    bitmap,
                    { result ->
                        if (result == PixelCopy.SUCCESS) {
                            val savedUri = saveBitmapToGallery(context, bitmap, fileName)
                            if (savedUri != null) {
                                Toast.makeText(context, "Snapshot saved to gallery!", Toast.LENGTH_SHORT).show()
                            } else {
                                Toast.makeText(context, "Failed to save snapshot to gallery", Toast.LENGTH_SHORT).show()
                            }
                        } else {
                            Toast.makeText(context, "Failed to capture snapshot (PixelCopy err: $result)", Toast.LENGTH_SHORT).show()
                        }
                    },
                    Handler(Looper.getMainLooper())
                )
            } catch (e: Exception) {
                Toast.makeText(context, "Capture error: ${e.message}", Toast.LENGTH_SHORT).show()
            }
        } else {
            // Fallback draw
            try {
                val canvas = android.graphics.Canvas(bitmap)
                canvas.translate(-x.toFloat(), -y.toFloat())
                view.draw(canvas)
                val savedUri = saveBitmapToGallery(context, bitmap, fileName)
                if (savedUri != null) {
                    Toast.makeText(context, "Snapshot saved to gallery (Fallback)!", Toast.LENGTH_SHORT).show()
                } else {
                    Toast.makeText(context, "Failed to save fallback snapshot", Toast.LENGTH_SHORT).show()
                }
            } catch (e: Exception) {
                Toast.makeText(context, "Fallback capture error: ${e.message}", Toast.LENGTH_SHORT).show()
            }
        }
    }

    private fun saveBitmapToGallery(context: Context, bitmap: Bitmap, fileName: String): Uri? {
        val resolver = context.contentResolver
        val contentValues = ContentValues().apply {
            put(MediaStore.MediaColumns.DISPLAY_NAME, "$fileName.png")
            put(MediaStore.MediaColumns.MIME_TYPE, "image/png")
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
                put(MediaStore.MediaColumns.RELATIVE_PATH, Environment.DIRECTORY_PICTURES + "/TireTwinSnapshots")
                put(MediaStore.MediaColumns.IS_PENDING, 1)
            }
        }

        val uri = resolver.insert(MediaStore.Images.Media.EXTERNAL_CONTENT_URI, contentValues)
        if (uri != null) {
            try {
                resolver.openOutputStream(uri).use { out ->
                    if (out != null) {
                        bitmap.compress(Bitmap.CompressFormat.PNG, 100, out)
                    }
                }
                if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
                    contentValues.clear()
                    contentValues.put(MediaStore.MediaColumns.IS_PENDING, 0)
                    resolver.update(uri, contentValues, null, null)
                }
            } catch (e: Exception) {
                resolver.delete(uri, null, null)
                return null
            }
        }
        return uri
    }

    // Helper extension to coerce within bounds safely
    private fun Int.coerceAtIn(min: Int, max: Int): Int {
        return if (this < min) min else if (this > max) max else this
    }
}
