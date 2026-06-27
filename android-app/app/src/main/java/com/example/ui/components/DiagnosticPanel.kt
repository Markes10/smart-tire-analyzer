package com.example.ui.components

import androidx.compose.animation.*
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.example.ui.theme.StatusCritical
import com.example.ui.theme.StatusInfo
import com.example.ui.theme.StatusSuccess
import com.example.ui.theme.StatusWarning

@Composable
fun DiagnosticPanel(
    speed: Float,
    pressure: Float,
    temperature: Float,
    wearPattern: String,
    analysisState: com.example.data.GeminiAnalysis? = null,
    isAnalyzing: Boolean = false,
    useMetric: Boolean = false,
    modifier: Modifier = Modifier
) {
    // Dynamically evaluate telemetry anomalies to populate predictive AI copy
    val metrics = remember(speed, pressure, temperature, wearPattern, useMetric) {
        evaluateDiagnostics(speed, pressure, temperature, wearPattern, useMetric)
    }

    val isDark = MaterialTheme.colorScheme.background.let { 
        (it.red * 0.2126f + it.green * 0.7152f + it.blue * 0.0722f) < 0.5f
    }

    Card(
        modifier = modifier
            .fillMaxWidth()
            .testTag("diagnostic_panel_card"),
        shape = RoundedCornerShape(16.dp),
        border = BorderStroke(1.dp, MaterialTheme.colorScheme.outline.copy(alpha = 0.15f)),
        colors = CardDefaults.cardColors(
            containerColor = Color.Transparent // Ground color is supplied by gradient brush
        )
    ) {
        Box(
            modifier = Modifier
                .background(
                    Brush.verticalGradient(
                        colors = if (isDark) {
                            listOf(
                                Color(255, 255, 255, 12), // Frosted white reflection
                                Color(255, 255, 255, 4)
                            )
                        } else {
                            listOf(
                                Color(0, 0, 0, 10),
                                Color(0, 0, 0, 4)
                            )
                        }
                    )
                )
                .padding(16.dp)
        ) {
            Column(verticalArrangement = Arrangement.spacedBy(14.dp)) {
                // Header of the Diagnostics Card
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Row(
                        verticalAlignment = Alignment.CenterVertically,
                        horizontalArrangement = Arrangement.spacedBy(8.dp)
                    ) {
                        Box(
                            modifier = Modifier
                                .size(32.dp)
                                .clip(RoundedCornerShape(8.dp))
                                .background(metrics.hazardColor.copy(alpha = 0.15f)),
                            contentAlignment = Alignment.Center
                        ) {
                            Icon(
                                imageVector = if (metrics.hazardLevel == "CRITICAL") Icons.Default.WarningAmber else Icons.Default.Analytics,
                                contentDescription = "Diagnostic Icon",
                                tint = metrics.hazardColor,
                                modifier = Modifier.size(18.dp)
                            )
                        }

                        Column {
                            Text(
                                text = "TEK-TWIN DIAGNOSTICS",
                                color = MaterialTheme.colorScheme.onSurfaceVariant,
                                fontSize = 10.sp,
                                fontFamily = FontFamily.Monospace,
                                fontWeight = FontWeight.Bold,
                                letterSpacing = 1.2.sp
                            )
                            Text(
                                text = "PREDICTIVE MAINTENANCE ENGINE",
                                color = MaterialTheme.colorScheme.onSurface,
                                fontSize = 12.sp,
                                fontWeight = FontWeight.Bold
                            )
                        }
                    }

                    // Hazard level Badge
                    Box(
                        modifier = Modifier
                            .clip(RoundedCornerShape(4.dp))
                            .background(metrics.hazardColor.copy(alpha = 0.2f))
                            .border(0.5.dp, metrics.hazardColor, RoundedCornerShape(4.dp))
                            .padding(horizontal = 6.dp, vertical = 2.dp)
                    ) {
                        Text(
                            text = metrics.hazardLevel,
                            color = metrics.hazardColor,
                            fontSize = 8.sp,
                            fontFamily = FontFamily.Monospace,
                            fontWeight = FontWeight.Bold
                        )
                    }
                }

                HorizontalDivider(color = MaterialTheme.colorScheme.outline.copy(alpha = 0.15f), thickness = 0.5.dp)

                // Gemini AI Tread Life Prognosis Panel
                Column(
                    modifier = Modifier
                        .fillMaxWidth()
                        .clip(RoundedCornerShape(12.dp))
                        .background(
                            Brush.linearGradient(
                                colors = if (isDark) {
                                    listOf(
                                        Color(0x1F, 0x24, 0x2C),
                                        Color(0x11, 0x1B, 0x2E)
                                    )
                                } else {
                                    listOf(
                                        MaterialTheme.colorScheme.primary.copy(alpha = 0.08f),
                                        MaterialTheme.colorScheme.primary.copy(alpha = 0.02f)
                                    )
                                }
                            )
                        )
                        .border(1.dp, MaterialTheme.colorScheme.primary.copy(alpha = if (isDark) 0.25f else 0.4f), RoundedCornerShape(12.dp))
                        .padding(14.dp),
                    verticalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Row(
                            verticalAlignment = Alignment.CenterVertically,
                            horizontalArrangement = Arrangement.spacedBy(6.dp)
                        ) {
                            Icon(
                                imageVector = Icons.Default.AutoAwesome,
                                contentDescription = "Gemini AI",
                                tint = MaterialTheme.colorScheme.primary,
                                modifier = Modifier.size(16.dp)
                            )
                            Text(
                                text = "GEMINI ACTIVE TREAD PROGNOSIS",
                                color = MaterialTheme.colorScheme.primary,
                                fontSize = 10.sp,
                                fontFamily = FontFamily.Monospace,
                                fontWeight = FontWeight.Bold,
                                letterSpacing = 1.sp
                            )
                        }

                        if (isAnalyzing) {
                            CircularProgressIndicator(
                                color = MaterialTheme.colorScheme.primary,
                                strokeWidth = 1.5.dp,
                                modifier = Modifier.size(12.dp)
                            )
                        } else {
                            Box(
                                modifier = Modifier
                                    .clip(RoundedCornerShape(4.dp))
                                    .background(StatusSuccess.copy(alpha = 0.15f))
                                    .padding(horizontal = 5.dp, vertical = 2.dp)
                            ) {
                                Text(
                                    text = "AI SYNCED",
                                    color = StatusSuccess,
                                    fontSize = 7.5.sp,
                                    fontFamily = FontFamily.Monospace,
                                    fontWeight = FontWeight.Bold
                                )
                            }
                        }
                    }

                    Text(
                        text = if (analysisState != null) {
                            analysisState.remainingLifePrediction
                        } else {
                            "Syncing real-time neural thread estimate..."
                        },
                        color = MaterialTheme.colorScheme.onSurface,
                        fontSize = 15.sp,
                        fontWeight = FontWeight.Black,
                        fontFamily = FontFamily.Monospace
                    )

                    Text(
                        text = if (analysisState != null) {
                            "Analysis: ${analysisState.analysis.take(130)}..."
                        } else {
                            "Analyzing micro-friction, wear-rate parameters, and tire footprint pressure coefficients via direct Gemini API connectivity..."
                        },
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                        fontSize = 11.sp,
                        lineHeight = 15.sp
                    )
                }

                // Lifespan & Wear Rate Columns
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(12.dp)
                ) {
                    // Left Column: Lifespan Estimate
                    Column(
                        modifier = Modifier
                            .weight(1.5f)
                            .clip(RoundedCornerShape(8.dp))
                            .background(MaterialTheme.colorScheme.onSurface.copy(alpha = 0.05f))
                            .padding(10.dp)
                    ) {
                        Text(
                            text = "EST. REMAINING LIFE",
                            color = MaterialTheme.colorScheme.onSurfaceVariant,
                            fontSize = 8.sp,
                            fontFamily = FontFamily.Monospace,
                            fontWeight = FontWeight.Bold
                        )
                        Spacer(modifier = Modifier.height(3.dp))
                        Text(
                            text = if (analysisState != null) analysisState.remainingLifePrediction.substringBefore(" -") else metrics.remainingLife,
                            color = MaterialTheme.colorScheme.onSurface,
                            fontSize = 13.sp,
                            fontWeight = FontWeight.Black
                        )
                    }

                    // Right Column: Active Degradation Factor
                    Column(
                        modifier = Modifier
                            .weight(1f)
                            .clip(RoundedCornerShape(8.dp))
                            .background(MaterialTheme.colorScheme.onSurface.copy(alpha = 0.05f))
                            .padding(10.dp)
                    ) {
                        Text(
                            text = "DEGRADATION",
                            color = MaterialTheme.colorScheme.onSurfaceVariant,
                            fontSize = 8.sp,
                            fontFamily = FontFamily.Monospace,
                            fontWeight = FontWeight.Bold
                        )
                        Spacer(modifier = Modifier.height(3.dp))
                        Text(
                            text = metrics.degradationFactor,
                            color = metrics.hazardColor,
                            fontSize = 13.sp,
                            fontWeight = FontWeight.Black
                        )
                    }
                }

                // Dynamic AI Prognosis Box
                Column(
                    modifier = Modifier
                        .fillMaxWidth()
                        .clip(RoundedCornerShape(10.dp))
                        .background(MaterialTheme.colorScheme.onSurface.copy(alpha = 0.03f))
                        .padding(12.dp),
                    verticalArrangement = Arrangement.spacedBy(6.dp)
                ) {
                    Text(
                        text = "DEGRADATION FORECAST & ANALYSIS",
                        color = MaterialTheme.colorScheme.primary,
                        fontSize = 9.sp,
                        fontFamily = FontFamily.Monospace,
                        fontWeight = FontWeight.Bold,
                        letterSpacing = 0.5.sp
                    )

                    Text(
                        text = metrics.forecastText,
                        color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.9f),
                        fontSize = 12.sp,
                        lineHeight = 16.sp
                    )
                }

                // Maintenance Recommendations Checklist
                Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    Text(
                        text = "RECOMMENDED ACTION DECK",
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                        fontSize = 9.sp,
                        fontFamily = FontFamily.Monospace,
                        fontWeight = FontWeight.Bold
                    )

                    metrics.recommendations.forEach { recommendation ->
                        Row(
                            verticalAlignment = Alignment.Top,
                            modifier = Modifier.fillMaxWidth()
                        ) {
                            Box(
                                modifier = Modifier
                                    .padding(top = 3.dp)
                                    .size(6.dp)
                                    .clip(CircleShape)
                                    .background(metrics.hazardColor)
                            )
                            Spacer(modifier = Modifier.width(8.dp))
                            Text(
                                text = recommendation,
                                color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.85f),
                                fontSize = 11.5.sp,
                                lineHeight = 15.sp
                            )
                        }
                    }
                }
            }
        }
    }
}

// Internal structures and calculation engines matching physical IoT profiles
private data class DiagnosticMetrics(
    val hazardLevel: String,
    val hazardColor: Color,
    val remainingLife: String,
    val degradationFactor: String,
    val forecastText: String,
    val recommendations: List<String>
)

private fun evaluateDiagnostics(
    speed: Float,
    pressure: Float,
    temperature: Float,
    wearPattern: String,
    useMetric: Boolean = false
): DiagnosticMetrics {
    var baseLifespanKm = 38000
    var wearScore = 1.0f

    val recs = mutableListOf<String>()

    // Pressure wear parameters
    if (pressure < 27.5f) {
        val severity = (27.5f - pressure) / 12.5f // 0f to 1f
        wearScore += severity * 1.5f
        val pStr = if (useMetric) "2.2 BAR" else "32.0 PSI"
        recs.add("Low inflation pressure detected! Increase cold pressure immediately to $pStr.")
    } else if (pressure > 36.5f) {
        val severity = (pressure - 36.5f) / 8.5f
        wearScore += severity * 0.8f
        val pStr = if (useMetric) "2.2 BAR" else "32.0 PSI"
        recs.add("Tire contains excess pressure. Deflate cold tire to $pStr to offset center tread wear.")
    } else {
        recs.add("Maintain current optimal pressure. Re-check in 21 days.")
    }

    // Temperature degradation multipliers (Thermal damage)
    if (temperature > 80f) {
        wearScore += 2.0f
        recs.add("CRITICAL CONCERN: Thermal limit critical. Pull over or decrease driving speed to let tire cool down.")
    } else if (temperature > 50f) {
        wearScore += 0.8f
        recs.add("Thermal signature elevated. Reduce continuous speed to dissipate excess friction heat build-up.")
    }

    // Speed abrasion additions
    if (speed > 100f) {
        wearScore += 0.5f
        recs.add("High speed operation increases friction coefficient. Limit motorway sprints to preserve tire structural density.")
    }

    // Wear Pattern specific forecasts & adjustments
    val patternForecast: String
    when (wearPattern) {
        "Center Wear" -> {
            wearScore += 0.6f
            patternForecast = "Centerline thread depth is degrading rapidly due to chronic over-inflation, reducing braking surface traction area."
            recs.add("Perform tire rotation across axes to balance the center rib pressure loads.")
        }
        "Edge Wear" -> {
            wearScore += 1.2f
            patternForecast = "Dual shoulder thread wear patterns detected, pointing to severe under-inflation and excessive sidewall thread flexing."
            recs.add("Schedule immediate manual gauge validation to prevent shoulder bead fatigue.")
        }
        "Camber Wear" -> {
            wearScore += 1.8f
            patternForecast = "Unilateral inner/outer edge wash is progressing. Highly descriptive of negative camber chassis misalignment or worn out suspension bushings."
            recs.add("Schedule high-precision 4-wheel geometric tracking alignment to halt localized outer-diameter scrub.")
        }
        "Cupping Wear" -> {
            wearScore += 1.5f
            patternForecast = "Rotational diagonal tread scalloping detected. Strongly correlates with compromised damper shock absorbers or imbalanced wheel weights."
            recs.add("Inspect vehicle shocks/struts. Request machine dynamic balance service on the tire assembly.")
        }
        else -> {
            patternForecast = "All rubber footprints represent ideal uniform distributions. Mechanical suspension tracks and inflation thresholds match original factory profiles."
            recs.add("Run standard scheduled standard axis tire rotation in 5,000 kilometers.")
        }
    }

    // Final calculations
    val calculatedLifespan = (baseLifespanKm / wearScore).toInt()
    val calculatedMiles = (calculatedLifespan * 0.621371f).toInt()
    val finalLifeString = if (useMetric) {
        "${"%,d".format(calculatedLifespan)} km"
    } else {
        "${"%,d".format(calculatedMiles)} miles"
    }
    val multiplierString = "${"%.1f".format(wearScore)}x"

    val (lvl, col) = when {
        wearScore >= 3.0f || temperature > 80f || pressure < 22f -> "CRITICAL" to StatusCritical
        wearScore >= 1.8f -> "ALERT" to StatusWarning
        else -> "NOMINAL" to StatusSuccess
    }

    return DiagnosticMetrics(
        hazardLevel = lvl,
        hazardColor = col,
        remainingLife = finalLifeString,
        degradationFactor = multiplierString,
        forecastText = patternForecast,
        recommendations = recs.take(3) // Present top-3 recommendations neatly
    )
}
