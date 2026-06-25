package com.example.ui.components

import androidx.compose.animation.*
import androidx.compose.animation.core.*
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.gestures.detectTapGestures
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
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch

@Composable
fun TelemetryTooltipDialog(
    metricName: String,
    explanation: String,
    onDismiss: () -> Unit
) {
    AlertDialog(
        onDismissRequest = onDismiss,
        confirmButton = {
            TextButton(
                onClick = onDismiss,
                colors = ButtonDefaults.textButtonColors(
                    contentColor = MaterialTheme.colorScheme.primary
                )
            ) {
                Text(
                    text = "DISMISS",
                    fontFamily = FontFamily.Monospace,
                    fontWeight = FontWeight.Bold,
                    fontSize = 12.sp,
                    letterSpacing = 1.sp
                )
            }
        },
        title = {
            Row(
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.spacedBy(8.dp)
            ) {
                Icon(
                    imageVector = Icons.Default.Info,
                    contentDescription = null,
                    tint = MaterialTheme.colorScheme.primary,
                    modifier = Modifier.size(18.dp)
                )
                Text(
                    text = metricName,
                    fontSize = 13.sp,
                    fontFamily = FontFamily.Monospace,
                    fontWeight = FontWeight.Bold,
                    letterSpacing = 0.5.sp,
                    color = MaterialTheme.colorScheme.onSurface
                )
            }
        },
        text = {
            Text(
                text = explanation,
                fontSize = 11.sp,
                fontFamily = FontFamily.Monospace,
                lineHeight = 16.sp,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )
        },
        containerColor = MaterialTheme.colorScheme.surface,
        textContentColor = MaterialTheme.colorScheme.onSurfaceVariant,
        titleContentColor = MaterialTheme.colorScheme.onSurface,
        shape = RoundedCornerShape(12.dp)
    )
}

@Composable
fun TelemetryControlPanel(
    speed: Float,
    pressure: Float,
    temperature: Float,
    wearPattern: String,
    useMetric: Boolean = false,
    onTelemetryChange: (speed: Float, pressure: Float, temperature: Float) -> Unit,
    modifier: Modifier = Modifier
) {
    var isLiveSimulationActive by remember { mutableStateOf(false) }
    var tooltipToShow by remember { mutableStateOf<Pair<String, String>?>(null) }
    val coroutineScope = rememberCoroutineScope()

    // Scintillating amber green scanner light for Simulation Mode
    val infiniteTransition = rememberInfiniteTransition(label = "pulse")
    val liveIndicatorAlpha by infiniteTransition.animateFloat(
        initialValue = 0.3f,
        targetValue = 1.0f,
        animationSpec = infiniteRepeatable(
            animation = tween(1000, easing = LinearEasing),
            repeatMode = RepeatMode.Reverse
        ),
        label = "pulse"
    )

    // Trigger simulation routine when live simulation is toggled on
    LaunchedEffect(isLiveSimulationActive) {
        if (isLiveSimulationActive) {
            var currentSpeed = speed
            var currentPressure = pressure
            var currentTemp = temperature
            var timeStep = 0f

            while (isLiveSimulationActive) {
                delay(120) // Update cycle every 120ms
                timeStep += 0.1f

                // Under live simulation, we drift values with controlled physics:
                // Speed oscillates like driving up and down hills
                val speedDrift = Math.sin(timeStep.toDouble() * 0.5).toFloat() * 1.5f
                currentSpeed = (currentSpeed + speedDrift).coerceIn(40f, 115f)

                // High speed causes friction which exponentially heats up the tire
                val tempTarget = 20f + (currentSpeed * 0.5f) + (Math.sin(timeStep.toDouble() * 0.2).toFloat() * 2f)
                val tempDrift = (tempTarget - currentTemp) * 0.05f
                currentTemp = (currentTemp + tempDrift).coerceIn(15f, 110f)

                // Pressure expands slightly as the tire gets hotter (Gay-Lussac's law simulation!)
                val standardPressure = 32f
                val thermalPressureOffset = (currentTemp - 20f) * 0.12f
                // Add a small dynamic road-bump noise to pressure
                val pressureNoise = Math.sin(timeStep.toDouble() * 2.0).toFloat() * 0.08f
                currentPressure = (standardPressure + thermalPressureOffset + pressureNoise).coerceIn(15f, 45f)

                onTelemetryChange(currentSpeed, currentPressure, currentTemp)
            }
        }
    }

    Column(
        modifier = modifier
            .fillMaxWidth()
            .background(MaterialTheme.colorScheme.surface, RoundedCornerShape(14.dp))
            .border(1.dp, MaterialTheme.colorScheme.outline.copy(alpha = 0.15f), RoundedCornerShape(14.dp))
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp)
    ) {
        // TOP CONTROL LEVER AND SIMULATOR ACTION ROW
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically
        ) {
            Column {
                Text(
                    text = "REAL-TIME TELEMETRY OVERRIDES",
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                    fontSize = 11.sp,
                    fontFamily = FontFamily.Monospace,
                    fontWeight = FontWeight.Bold,
                    letterSpacing = 1.2.sp
                )
                Text(
                    text = if (isLiveSimulationActive) "LIVE IOT TRANSMITTER FEED ACTIVE" else "MANUAL CONTROL MODE",
                    color = if (isLiveSimulationActive) Color(0x28, 0xB4, 0x82) else MaterialTheme.colorScheme.primary,
                    fontSize = 9.sp,
                    fontFamily = FontFamily.Monospace,
                    fontWeight = FontWeight.Bold,
                    letterSpacing = 0.5.sp
                )
            }

            // Live Simulator Toggle switch
            Row(
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.spacedBy(8.dp),
                modifier = Modifier
                    .clip(RoundedCornerShape(8.dp))
                    .background(
                        if (isLiveSimulationActive) Color(0x28, 0xB4, 0x82).copy(alpha = 0.12f)
                        else MaterialTheme.colorScheme.background
                    )
                    .border(
                        1.dp,
                        if (isLiveSimulationActive) Color(0x28, 0xB4, 0x82).copy(alpha = 0.4f)
                        else MaterialTheme.colorScheme.outline.copy(alpha = 0.3f),
                        RoundedCornerShape(8.dp)
                    )
                    .clickable { isLiveSimulationActive = !isLiveSimulationActive }
                    .padding(horizontal = 10.dp, vertical = 6.dp)
                    .testTag("live_simulation_toggle")
            ) {
                Box(
                    modifier = Modifier
                        .size(6.dp)
                        .clip(CircleShape)
                        .background(
                            if (isLiveSimulationActive) Color(0x28, 0xB4, 0x82)
                            else MaterialTheme.colorScheme.onSurfaceVariant.copy(alpha = 0.6f)
                        )
                )
                Text(
                    text = "SIM FEED",
                    color = if (isLiveSimulationActive) Color(0x28, 0xB4, 0x82) else MaterialTheme.colorScheme.onSurface,
                    fontSize = 9.sp,
                    fontFamily = FontFamily.Monospace,
                    fontWeight = FontWeight.Bold
                )
            }
        }

        // SCENARIOS PRESET DECK selectors
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.spacedBy(6.dp)
        ) {
            val presets = listOf(
                PresetScenario("STATIC", 0f, 32f, 20f),
                PresetScenario("HIGHWAY", 90f, 34f, 48f),
                PresetScenario("TRACK", 120f, 28f, 92f),
                PresetScenario("LEAK", 45f, 18f, 32f)
            )

            presets.forEach { preset ->
                val isSelected = !isLiveSimulationActive &&
                        Math.abs(speed - preset.s) < 1f &&
                        Math.abs(pressure - preset.p) < 0.5f &&
                        Math.abs(temperature - preset.t) < 1f

                Box(
                    modifier = Modifier
                        .weight(1f)
                        .clip(RoundedCornerShape(6.dp))
                        .background(
                            if (isSelected) MaterialTheme.colorScheme.primary.copy(alpha = 0.12f)
                            else MaterialTheme.colorScheme.background
                        )
                        .border(
                            0.5.dp,
                            if (isSelected) MaterialTheme.colorScheme.primary
                            else MaterialTheme.colorScheme.outline.copy(alpha = 0.2f),
                            RoundedCornerShape(6.dp)
                        )
                        .clickable {
                            isLiveSimulationActive = false
                            onTelemetryChange(preset.s, preset.p, preset.t)
                        }
                        .padding(vertical = 6.dp),
                    contentAlignment = Alignment.Center
                ) {
                    Text(
                        text = preset.name,
                        color = if (isSelected) MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.onSurfaceVariant,
                        fontSize = 9.sp,
                        fontFamily = FontFamily.Monospace,
                        fontWeight = FontWeight.Bold
                    )
                }
            }
        }

        HorizontalDivider(color = MaterialTheme.colorScheme.outline.copy(alpha = 0.15f), thickness = 0.5.dp)

        // 1. VEHICLE SPEED CONTROLLER
        Column(
            modifier = Modifier
                .pointerInput(Unit) {
                    detectTapGestures(
                        onLongPress = {
                            tooltipToShow = Pair(
                                "VEHICLE SPEED",
                                "Rotational frequency of the wheel hub assembly. Higher speed increases kinetic friction loads, leading to accelerated carcass thermal output."
                            )
                        }
                    )
                }
                .padding(vertical = 4.dp)
        ) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Icon(
                        imageVector = Icons.Default.Speed,
                        contentDescription = "Speed",
                        tint = if (speed > 100f) Color(0xFF, 0x5E, 0x36) else MaterialTheme.colorScheme.onSurfaceVariant,
                        modifier = Modifier.size(15.dp)
                    )
                    Spacer(modifier = Modifier.width(6.dp))
                    Text(
                        text = "Vehicle Velocity",
                        color = MaterialTheme.colorScheme.onSurface,
                        fontSize = 12.5.sp,
                        fontWeight = FontWeight.Medium
                    )
                    
                    // High rotation warning label
                    if (speed > 100f) {
                        Spacer(modifier = Modifier.width(6.dp))
                        Box(
                            modifier = Modifier
                                .background(Color(0xFF, 0x5E, 0x36).copy(alpha = 0.15f), RoundedCornerShape(3.dp))
                                .border(0.5.dp, Color(0xFF, 0x5E, 0x36).copy(alpha = 0.5f), RoundedCornerShape(3.dp))
                                .padding(horizontal = 4.dp, vertical = 1.dp)
                        ) {
                            Text(
                                text = "HIGH SPIN",
                                color = Color(0xFF, 0x5E, 0x36),
                                fontSize = 7.5.sp,
                                fontFamily = FontFamily.Monospace,
                                fontWeight = FontWeight.Bold
                            )
                        }
                    }
                }
                
                Text(
                    text = if (useMetric) "${speed.toInt()} km/h" else "${(speed * 0.621f).toInt()} mph",
                    color = if (speed > 100f) Color(0xFF, 0x5E, 0x36) else MaterialTheme.colorScheme.primary,
                    fontSize = 12.5.sp,
                    fontFamily = FontFamily.Monospace,
                    fontWeight = FontWeight.Bold
                )
            }

            Slider(
                value = speed,
                enabled = !isLiveSimulationActive,
                onValueChange = { onTelemetryChange(it, pressure, temperature) },
                valueRange = 0f..120f,
                colors = SliderDefaults.colors(
                    thumbColor = if (speed > 100f) Color(0xFF, 0x5E, 0x36) else MaterialTheme.colorScheme.primary,
                    activeTrackColor = if (speed > 100f) Color(0xFF, 0x5E, 0x36) else MaterialTheme.colorScheme.primary,
                    inactiveTrackColor = MaterialTheme.colorScheme.outline.copy(alpha = 0.24f),
                    disabledThumbColor = MaterialTheme.colorScheme.onSurfaceVariant.copy(alpha = 0.4f),
                    disabledActiveTrackColor = MaterialTheme.colorScheme.onSurfaceVariant.copy(alpha = 0.2f),
                    disabledInactiveTrackColor = MaterialTheme.colorScheme.outline.copy(alpha = 0.1f)
                ),
                modifier = Modifier
                    .testTag("speed_slider")
                    .height(24.dp)
            )
        }

        // 2. TIRE PRESSURE CONTROLLER
        Column(
            modifier = Modifier
                .pointerInput(Unit) {
                    detectTapGestures(
                        onLongPress = {
                            tooltipToShow = Pair(
                                "TREATMENT PRESSURE",
                                "Pneumatic pressure inside the primary tire chamber. Under-inflation (low PSI) causes sidewall sagging and edge wear shoulder stress. Over-inflation (high PSI) stretches the tread center, intensifying fatigue center wear."
                            )
                        }
                    )
                }
                .padding(vertical = 4.dp)
        ) {
            val label = getPressureLabel(pressure)
            val pColor = getPressureColor(pressure)

            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Icon(
                        imageVector = Icons.Default.CompassCalibration,
                        contentDescription = "Pressure",
                        tint = if (pressure < 22f || pressure > 38f) Color(0xFF, 0x4B, 0x4B) else MaterialTheme.colorScheme.onSurfaceVariant,
                        modifier = Modifier.size(15.dp)
                    )
                    Spacer(modifier = Modifier.width(6.dp))
                    Text(
                        text = "Inflation Pressure",
                        color = MaterialTheme.colorScheme.onSurface,
                        fontSize = 12.5.sp,
                        fontWeight = FontWeight.Medium
                    )

                    if (pressure < 22f || pressure > 38f) {
                        Spacer(modifier = Modifier.width(6.dp))
                        Box(
                            modifier = Modifier
                                .background(Color(0xFF, 0x4B, 0x4B).copy(alpha = 0.15f), RoundedCornerShape(3.dp))
                                .border(0.5.dp, Color(0xFF, 0x4B, 0x4B).copy(alpha = 0.5f), RoundedCornerShape(3.dp))
                                .padding(horizontal = 4.dp, vertical = 1.dp)
                        ) {
                            Text(
                                text = "CRITICAL",
                                color = Color(0xFF, 0x4B, 0x4B),
                                fontSize = 7.5.sp,
                                fontFamily = FontFamily.Monospace,
                                fontWeight = FontWeight.Bold
                            )
                        }
                    }
                }

                Text(
                    text = if (useMetric) {
                        "${(pressure * 0.0689f).toInt()} bar $label"
                    } else {
                        "${pressure.toInt()} psi $label"
                    },
                    color = pColor,
                    fontSize = 12.5.sp,
                    fontFamily = FontFamily.Monospace,
                    fontWeight = FontWeight.Bold
                )
            }

            Slider(
                value = pressure,
                enabled = !isLiveSimulationActive,
                onValueChange = { onTelemetryChange(speed, it, temperature) },
                valueRange = 15f..45f,
                colors = SliderDefaults.colors(
                    thumbColor = pColor,
                    activeTrackColor = pColor,
                    inactiveTrackColor = MaterialTheme.colorScheme.outline.copy(alpha = 0.24f),
                    disabledThumbColor = MaterialTheme.colorScheme.onSurfaceVariant.copy(alpha = 0.4f),
                    disabledActiveTrackColor = MaterialTheme.colorScheme.onSurfaceVariant.copy(alpha = 0.2f),
                    disabledInactiveTrackColor = MaterialTheme.colorScheme.outline.copy(alpha = 0.1f)
                ),
                modifier = Modifier
                    .testTag("pressure_slider")
                    .height(24.dp)
            )
        }

        // 3. CORE TEMPERATURE CONTROLLER
        Column(
            modifier = Modifier
                .pointerInput(Unit) {
                    detectTapGestures(
                        onLongPress = {
                            tooltipToShow = Pair(
                                "CARCASS TEMPERATURE",
                                "Active heat generated by tire road contact and internal rubber shear forces. Temperatures above 80°C trigger rapid rubber degradation and heighten blowout risks."
                            )
                        }
                    )
                }
                .padding(vertical = 4.dp)
        ) {
            val tColor = getTemperatureColor(temperature)

            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Icon(
                        imageVector = Icons.Default.DeviceThermostat,
                        contentDescription = "Temperature",
                        tint = if (temperature > 80f) Color(0xFF, 0x4B, 0x4B) else MaterialTheme.colorScheme.onSurfaceVariant,
                        modifier = Modifier.size(15.dp)
                    )
                    Spacer(modifier = Modifier.width(6.dp))
                    Text(
                        text = "Carcass Temperature",
                        color = MaterialTheme.colorScheme.onSurface,
                        fontSize = 12.5.sp,
                        fontWeight = FontWeight.Medium
                    )

                    if (temperature > 80f) {
                        Spacer(modifier = Modifier.width(6.dp))
                        Box(
                            modifier = Modifier
                                .background(Color(0xFF, 0x4B, 0x4B).copy(alpha = 0.15f), RoundedCornerShape(3.dp))
                                .border(0.5.dp, Color(0xFF, 0x4B, 0x4B).copy(alpha = 0.5f), RoundedCornerShape(3.dp))
                                .padding(horizontal = 4.dp, vertical = 1.dp)
                        ) {
                            Text(
                                text = "OVERHEAT",
                                color = Color(0xFF, 0x4B, 0x4B),
                                fontSize = 7.5.sp,
                                fontFamily = FontFamily.Monospace,
                                fontWeight = FontWeight.Bold
                            )
                        }
                    }
                }

                Text(
                    text = if (useMetric) "${temperature.toInt()} °C" else "${(temperature * 9 / 5 + 32).toInt()} °F",
                    color = tColor,
                    fontSize = 12.5.sp,
                    fontFamily = FontFamily.Monospace,
                    fontWeight = FontWeight.Bold
                )
            }

            Slider(
                value = temperature,
                enabled = !isLiveSimulationActive,
                onValueChange = { onTelemetryChange(speed, pressure, it) },
                valueRange = 15f..110f,
                colors = SliderDefaults.colors(
                    thumbColor = tColor,
                    activeTrackColor = tColor,
                    inactiveTrackColor = MaterialTheme.colorScheme.outline.copy(alpha = 0.24f),
                    disabledThumbColor = MaterialTheme.colorScheme.onSurfaceVariant.copy(alpha = 0.4f),
                    disabledActiveTrackColor = MaterialTheme.colorScheme.onSurfaceVariant.copy(alpha = 0.2f),
                    disabledInactiveTrackColor = MaterialTheme.colorScheme.outline.copy(alpha = 0.1f)
                ),
                modifier = Modifier
                    .testTag("temp_slider")
                    .height(24.dp)
            )
        }

        // Tooltip rendering logic
        tooltipToShow?.let { (title, explanation) ->
            TelemetryTooltipDialog(
                metricName = title,
                explanation = explanation,
                onDismiss = { tooltipToShow = null }
            )
        }
    }
}

// Data structures and helper functions matching the ones used in HomeScreen.kt
private data class PresetScenario(val name: String, val s: Float, val p: Float, val t: Float)

private fun getPressureLabel(psi: Float): String = when {
    psi < 27.5f -> "(Under)"
    psi > 36.5f -> "(Over)"
    else -> "(Standard)"
}

private fun getPressureColor(psi: Float): Color = when {
    psi < 27.5f -> Color(0xFF, 0x5E, 0x36)
    psi > 36.5f -> Color(0xFF, 0xD4, 0x3F)
    else -> Color(0x28, 0xB4, 0x82)
}

private fun getTemperatureColor(temp: Float): Color = when {
    temp > 80f -> Color(0xFF, 0x4B, 0x4B)
    temp > 50f -> Color(0xFF, 0x5E, 0x36)
    else -> Color(0x58, 0xA6, 0xFF)
}
