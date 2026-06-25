package com.example.util

import android.content.Context
import android.content.Intent
import android.graphics.Canvas
import android.graphics.Color
import android.graphics.Paint
import android.graphics.RectF
import android.graphics.Typeface
import android.graphics.pdf.PdfDocument
import android.widget.Toast
import androidx.core.content.FileProvider
import com.example.data.GeminiAnalysis
import java.io.File
import java.io.FileOutputStream
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

object PdfGenerator {
    fun generateAndSharePdf(
        context: Context,
        tireLabel: String,
        speed: Float,
        pressure: Float,
        temperature: Float,
        wearPattern: String,
        healthScore: Int,
        iotBattery: Float,
        analysis: GeminiAnalysis?
    ) {
        try {
            val pdfDocument = PdfDocument()
            // Canvas page size: A4 standard dimensions (595 x 842 points)
            val pageInfo = PdfDocument.PageInfo.Builder(595, 842, 1).create()
            val page = pdfDocument.startPage(pageInfo)
            val canvas = page.canvas

            // Paint definitions
            val textPaint = Paint().apply {
                color = Color.rgb(33, 37, 41)
                textSize = 10f
                typeface = Typeface.create(Typeface.MONOSPACE, Typeface.NORMAL)
                isAntiAlias = true
            }

            val boldPaint = Paint().apply {
                color = Color.rgb(13, 17, 23)
                textSize = 11f
                typeface = Typeface.create(Typeface.MONOSPACE, Typeface.BOLD)
                isAntiAlias = true
            }

            // Draw Header Block
            val headerPaint = Paint().apply {
                color = Color.rgb(26, 32, 44) // Tech Dark Navy
            }
            canvas.drawRect(RectF(15f, 15f, 580f, 95f), headerPaint)

            // Header Texts
            val headerTitlePaint = Paint().apply {
                color = Color.rgb(80, 250, 123) // Neo green / Cyan
                textSize = 15f
                typeface = Typeface.create(Typeface.MONOSPACE, Typeface.BOLD)
                isAntiAlias = true
            }
            canvas.drawText("TEK-TWIN 3D // $tireLabel DIAGNOSTICS", 30f, 48f, headerTitlePaint)

            val headerSubPaint = Paint().apply {
                color = Color.rgb(255, 255, 255)
                textSize = 9f
                typeface = Typeface.create(Typeface.MONOSPACE, Typeface.NORMAL)
                isAntiAlias = true
            }
            canvas.drawText("AUTOMOTIVE TELEMETRY PROFILE & AI LONG-TERM LIFETIME PREDICTIONS", 30f, 66f, headerSubPaint)

            val dateStr = SimpleDateFormat("yyyy-MM-dd HH:mm:ss", Locale.getDefault()).format(Date())
            canvas.drawText("REPORT GENERATION TIME: $dateStr UTC", 30f, 82f, headerSubPaint)

            // Layout Column 1: Telemetry Metrics Table
            // Background grid card for Telemetry parameters
            val cardBgPaint = Paint().apply {
                color = Color.rgb(248, 249, 250) // Crisp Warm Gray
            }
            val cardBorderPaint = Paint().apply {
                color = Color.rgb(222, 226, 230)
                style = Paint.Style.STROKE
                strokeWidth = 1f
            }
            val telemetryCard = RectF(15f, 110f, 320f, 260f)
            canvas.drawRect(telemetryCard, cardBgPaint)
            canvas.drawRect(telemetryCard, cardBorderPaint)

            val sectionTitlePaint = Paint().apply {
                color = Color.rgb(13, 17, 23)
                textSize = 12f
                typeface = Typeface.create(Typeface.MONOSPACE, Typeface.BOLD)
                isAntiAlias = true
            }
            canvas.drawText("> TELEMETRY READOUTS", 25f, 132f, sectionTitlePaint)

            // Table rows
            var rowY = 155f
            val rowHeight = 20f

            fun drawRow(label: String, value: String) {
                canvas.drawText(label, 25f, rowY, textPaint)
                canvas.drawText(value, 190f, rowY, boldPaint)
                canvas.drawLine(25f, rowY + 4f, 310f, rowY + 4f, cardBorderPaint)
                rowY += rowHeight
            }

            drawRow("VEHICLE SPEED", "${String.format(Locale.US, "%.1f", speed)} km/h")
            drawRow("TREATMENT PRESSURE", "${String.format(Locale.US, "%.1f", pressure)} PSI")
            drawRow("CORE TEMPERATURE", "${String.format(Locale.US, "%.1f", temperature)} °C")
            drawRow("OBSERVED WEAR", wearPattern)
            drawRow("IOT SENSOR BATT", "${String.format(Locale.US, "%.1f", iotBattery)}%")

            // Layout Column 2: Health Rating Gauge Card
            val scoreCard = RectF(335f, 110f, 580f, 260f)
            canvas.drawRect(scoreCard, cardBgPaint)
            canvas.drawRect(scoreCard, cardBorderPaint)

            canvas.drawText("> HEALTH RATING", 345f, 132f, sectionTitlePaint)

            // Draw a styled overall circular gauge representation
            val arcPaint = Paint().apply {
                style = Paint.Style.STROKE
                strokeWidth = 10f
                isAntiAlias = true
            }
            // Score color logic
            val scoreColor = when {
                healthScore >= 80 -> Color.rgb(40, 167, 69)   // Green
                healthScore >= 60 -> Color.rgb(255, 184, 108) // Warning amber
                else -> Color.rgb(255, 85, 85)                // Critical red
            }
            arcPaint.color = scoreColor

            val circleCenterBound = RectF(430f, 150f, 510f, 230f)

            // Track background arc
            val trackPaint = Paint().apply {
                style = Paint.Style.STROKE
                strokeWidth = 10f
                color = Color.rgb(218, 224, 233)
                isAntiAlias = true
            }
            canvas.drawArc(circleCenterBound, 135f, 270f, false, trackPaint)
            canvas.drawArc(circleCenterBound, 135f, 270f * (healthScore / 100f), false, arcPaint)

            // Inside circular text representing score
            val scoreTextPaint = Paint().apply {
                textSize = 24f
                typeface = Typeface.create(Typeface.MONOSPACE, Typeface.BOLD)
                color = Color.rgb(13, 17, 23)
                textAlign = Paint.Align.CENTER
                isAntiAlias = true
            }
            canvas.drawText("$healthScore%", 470f, 198f, scoreTextPaint)

            val healthLevelText = when {
                healthScore >= 90 -> "OPTIMAL NOMINAL"
                healthScore >= 75 -> "STANDBY WARN"
                healthScore >= 50 -> "HIGH DEGRADATION"
                else -> "CRITICAL FATIGUE"
            }
            val healthLabelPaint = Paint().apply {
                textSize = 9f
                typeface = Typeface.create(Typeface.MONOSPACE, Typeface.BOLD)
                color = scoreColor
                textAlign = Paint.Align.CENTER
                isAntiAlias = true
            }
            canvas.drawText(healthLevelText, 470f, 245f, healthLabelPaint)

            // AI Diagnosis & Prediction Card
            val aiCard = RectF(15f, 280f, 580f, 810f)
            canvas.drawRect(aiCard, cardBgPaint)
            canvas.drawRect(aiCard, cardBorderPaint)

            val aiTitlePaint = Paint().apply {
                color = Color.rgb(13, 17, 23) // Slate Deep Dark
                textSize = 12f
                typeface = Typeface.create(Typeface.MONOSPACE, Typeface.BOLD)
                isAntiAlias = true
            }
            canvas.drawText("> DIGITAL TWIN AI DIAGNOSTIC REPORT", 25f, 305f, aiTitlePaint)

            var lineY = 335f
            val maxTextWidth = 530f

            fun drawWrappedParagraph(header: String, text: String, headerColor: Int) {
                // Draw Section header
                val hp = Paint().apply {
                    color = headerColor
                    textSize = 10f
                    typeface = Typeface.create(Typeface.MONOSPACE, Typeface.BOLD)
                    isAntiAlias = true
                }
                canvas.drawText(header, 25f, lineY, hp)
                lineY += 15f

                // Draw wrapped block
                val pPaint = Paint().apply {
                    color = Color.rgb(51, 65, 85)
                    textSize = 9.5f
                    typeface = Typeface.create(Typeface.MONOSPACE, Typeface.NORMAL)
                    isAntiAlias = true
                }
                lineY = drawTextWrapped(canvas, text, 25f, lineY, maxTextWidth, pPaint, 14f)
                lineY += 12f
            }

            val rawAnalysis = analysis?.analysis ?: "No current active diagnostic logs compiled. Please initiate deep scanner on the main dashboard to synchronize."
            val rawSafety = analysis?.safety ?: "Standby for warning limits. Drive safely and maintain standard PSI boundaries."
            val rawTimeline = analysis?.timeline ?: "• Complete automated diagnostic sweeps weekly.\n• Check cold inflation pressures monthly."
            val rawRemainingLife = analysis?.remainingLifePrediction ?: "Estimating lifespan based on real-time operational telemetry and wear pattern vectors."

            // Render AI Analysis contents
            drawWrappedParagraph("1. REAL-TIME PHENOMENOLOGICAL SEGMENTATION:", rawAnalysis, Color.rgb(13, 17, 23))
            drawWrappedParagraph("2. SAFETY ALERT VECTORS:", rawSafety, Color.rgb(255, 85, 85))
            drawWrappedParagraph("3. REMEDIATION TIMELINE STRATEGY:", rawTimeline, Color.rgb(217, 119, 6))
            drawWrappedParagraph("4. REMAINING USEFUL LIFE EXPECTANCY (RUL):", rawRemainingLife, Color.rgb(40, 167, 69))

            // Footer
            val footerPaint = Paint().apply {
                color = Color.rgb(138, 155, 168)
                textSize = 8f
                typeface = Typeface.create(Typeface.MONOSPACE, Typeface.NORMAL)
                isAntiAlias = true
            }
            canvas.drawText("TEK-TWIN 3D AUTOMOTIVE LABS // VERIFIED SECURE DIGITAL CERTIFICATE", 25f, 792f, footerPaint)

            // Finish PDF
            pdfDocument.finishPage(page)

            // Save file in cache directory
            val cacheFile = File(context.cacheDir, "Tire_Diagnostic_Report_${System.currentTimeMillis()}.pdf")
            FileOutputStream(cacheFile).use { fos ->
                pdfDocument.writeTo(fos)
            }
            pdfDocument.close()

            // Trigger standard Share Intent
            val fileUri = FileProvider.getUriForFile(context, "${context.packageName}.fileprovider", cacheFile)
            val shareIntent = Intent(Intent.ACTION_SEND).apply {
                type = "application/pdf"
                putExtra(Intent.EXTRA_STREAM, fileUri)
                putExtra(Intent.EXTRA_SUBJECT, "Tire Diagnostics Report & AI Lifespan Prediction")
                putExtra(Intent.EXTRA_TEXT, "Hello, here is the secured PDF summary report detailing the live tire mechanical diagnostics and AI digital twin longevity predictions retrieved from Tek-Twin 3D.")
                addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
            }
            val chooserIntent = Intent.createChooser(shareIntent, "Share or Save PDF Diagnostic Report").apply {
                addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
            }
            context.startActivity(chooserIntent)

        } catch (e: Exception) {
            e.printStackTrace()
            Toast.makeText(context, "Failed to generate PDF: ${e.localizedMessage}", Toast.LENGTH_LONG).show()
        }
    }

    private fun drawTextWrapped(
        canvas: Canvas,
        text: String,
        x: Float,
        y: Float,
        maxWidth: Float,
        paint: Paint,
        lineHeight: Float
    ): Float {
        var currentY = y
        val paragraphs = text.split("\n")
        for (paragraph in paragraphs) {
            val words = paragraph.split("\\s+".toRegex())
            var line = ""
            for (word in words) {
                if (word.isEmpty()) continue
                val testLine = if (line.isEmpty()) word else "$line $word"
                val testWidth = paint.measureText(testLine)
                if (testWidth > maxWidth) {
                    canvas.drawText(line, x, currentY, paint)
                    currentY += lineHeight
                    line = word
                } else {
                    line = testLine
                }
            }
            if (line.isNotEmpty()) {
                canvas.drawText(line, x, currentY, paint)
                currentY += lineHeight
            }
        }
        return currentY
    }
}
