package com.example.ui.components

import androidx.compose.animation.*
import androidx.compose.animation.core.*
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.*
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.drawscope.DrawScope
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.input.pointer.positionChange
import androidx.compose.ui.graphics.nativeCanvas
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.platform.testTag
import androidx.compose.foundation.gestures.awaitEachGesture
import androidx.compose.foundation.gestures.awaitFirstDown
import androidx.compose.foundation.gestures.detectTapGestures
import androidx.compose.foundation.gestures.detectTransformGestures
import androidx.compose.ui.hapticfeedback.HapticFeedbackType
import androidx.compose.ui.platform.LocalHapticFeedback
import android.graphics.Paint
import android.graphics.Typeface
import android.graphics.RectF
import kotlin.math.cos
import kotlin.math.sin
import kotlin.math.sqrt

// Representation of a 3D point in space
data class Point3D(val x: Float, val y: Float, val z: Float) {
    fun rotateX(angle: Float): Point3D {
        val rad = angle * (Math.PI / 180).toFloat()
        val cos = cos(rad)
        val sin = sin(rad)
        return Point3D(x, y * cos - z * sin, y * sin + z * cos)
    }

    fun rotateY(angle: Float): Point3D {
        val rad = angle * (Math.PI / 180).toFloat()
        val cos = cos(rad)
        val sin = sin(rad)
        return Point3D(x * cos + z * sin, y, -x * sin + z * cos)
    }

    fun rotateZ(angle: Float): Point3D {
        val rad = angle * (Math.PI / 180).toFloat()
        val cos = cos(rad)
        val sin = sin(rad)
        return Point3D(x * cos - y * sin, x * sin + y * cos, z)
    }
}

// Projection metadata for 2D drawing
data class ProjectedPoint(val screenOffset: Offset, val zDepth: Float, val rawPoint: Point3D, val normal: Point3D)

// 3D Line representing a mesh segment
data class Segment3D(
    val p1Index: Int,
    val p2Index: Int,
    val color: Color,
    val thickness: Float = 1.5f,
    val isSteelBelt: Boolean = false,
    val isSpoke: Boolean = false
)

@Composable
fun TireDigitalTwin3D(
    modifier: Modifier = Modifier,
    speed: Float,       // 0 to 120+ km/h
    pressure: Float,    // 15 to 45 PSI (ideal 32)
    temperature: Float, // 15 to 110 °C
    wearPattern: String,// "Normal", "Center Wear", "Edge Wear", "Camber Wear", "Cupping Wear"
    isThermalMode: Boolean = false,
    isExplodedView: Boolean = false,
    isDarkTheme: Boolean = true,
    useMetric: Boolean = false
) {
    // Camera angle states
    var yaw by remember { mutableStateOf(45f) }   // horizontal rotation
    var pitch by remember { mutableStateOf(-15f) } // vertical rotation
    val haptic = LocalHapticFeedback.current
    var zoomScale by remember { mutableStateOf(1.0f) }
    var activeTouchPoints by remember { mutableStateOf<List<Offset>>(emptyList()) }

    // Autorotation rolling angle powered by speed
    var rollAngle by remember { mutableStateOf(0f) }

    // Floating scanners sweeps animations
    val transition = rememberInfiniteTransition(label = "scanner")
    val laserSweep by transition.animateFloat(
        initialValue = -150f,
        targetValue = 150f,
        animationSpec = infiniteRepeatable(
            animation = tween(4000, easing = LinearEasing),
            repeatMode = RepeatMode.Reverse
        ),
        label = "laser"
    )

    // Exploded view animation state
    val explosionProgress by animateFloatAsState(
        targetValue = if (isExplodedView) 1f else 0f,
        animationSpec = spring(dampingRatio = Spring.DampingRatioMediumBouncy, stiffness = Spring.StiffnessLow),
        label = "explosion"
    )

    // Animated telemetry for smooth transitions between wheel positions
    val animatedSpeed by animateFloatAsState(targetValue = speed, animationSpec = tween(800, easing = FastOutSlowInEasing), label = "anim_speed")
    val animatedPressure by animateFloatAsState(targetValue = pressure, animationSpec = tween(800, easing = FastOutSlowInEasing), label = "anim_pressure")
    val animatedTemperature by animateFloatAsState(targetValue = temperature, animationSpec = tween(800, easing = FastOutSlowInEasing), label = "anim_temp")

    // Interactive telemetry local states for HUD adjustments
    var localSpeed by remember(animatedSpeed) { mutableStateOf(animatedSpeed) }
    var localPressure by remember(animatedPressure) { mutableStateOf(animatedPressure) }
    var localTemperature by remember(animatedTemperature) { mutableStateOf(animatedTemperature) }
    var localThermalMode by remember(isThermalMode) { mutableStateOf(isThermalMode) }
    var activeChannel by remember { mutableStateOf<String?>(null) }
    val plateBounds = remember { PlateBounds() }
    
    // Web Three.js Engine state
    var useWebEngine by remember { mutableStateOf(false) }
    var webViewRef by remember { mutableStateOf<android.webkit.WebView?>(null) }
    
    LaunchedEffect(localTemperature) {
        webViewRef?.evaluateJavascript("setTemperature($localTemperature)", null)
    }

    // Update spin rotation in real time based on speed
    LaunchedEffect(localSpeed) {
        if (localSpeed > 0) {
            val frameTimeMs = 16L
            while (true) {
                val deltaAngle = (localSpeed / 3.6f) * 0.15f * frameTimeMs / 16.67f
                rollAngle = (rollAngle + deltaAngle) % 360f
                kotlinx.coroutines.delay(frameTimeMs)
            }
        }
    }

    Box(
        modifier = modifier
            .fillMaxSize()
            .background(MaterialTheme.colorScheme.background) // adaptive theme background
            .pointerInput(Unit) {
                detectTapGestures(
                    onDoubleTap = {
                        yaw = 45f
                        pitch = -15f
                        zoomScale = 1.0f
                        haptic.performHapticFeedback(HapticFeedbackType.LongPress)
                    },
                    onTap = { offset ->
                        val tapX = offset.x
                        val tapY = offset.y
                        if (plateBounds.speedBounds.contains(tapX, tapY)) {
                            activeChannel = if (activeChannel == "SPEED") null else "SPEED"
                        } else if (plateBounds.pressureBounds.contains(tapX, tapY)) {
                            activeChannel = if (activeChannel == "PRESSURE") null else "PRESSURE"
                        } else if (plateBounds.temperatureBounds.contains(tapX, tapY)) {
                            activeChannel = if (activeChannel == "TEMPERATURE") null else "TEMPERATURE"
                        } else {
                            activeChannel = null
                        }
                    }
                )
            }
            .pointerInput(Unit) {
                detectTransformGestures { _, pan, zoom, _ ->
                    if (pan != Offset.Zero) {
                        yaw = (yaw + pan.x * 0.4f) % 360f
                        pitch = (pitch - pan.y * 0.4f).coerceIn(-85f, 85f)
                    }
                    if (zoom != 1.0f) {
                        val oldZoom = zoomScale
                        val newZoom = (zoomScale * zoom).coerceIn(0.5f, 2.5f)
                        if (newZoom != oldZoom) {
                            zoomScale = newZoom
                            if (newZoom == 0.5f || newZoom == 2.5f) {
                                haptic.performHapticFeedback(HapticFeedbackType.LongPress)
                            }
                        } else {
                            // If user tries to zoom past limits, trigger gentle boundary cues
                            if (zoom > 1.0f && oldZoom == 2.5f) {
                                haptic.performHapticFeedback(HapticFeedbackType.LongPress)
                            } else if (zoom < 1.0f && oldZoom == 0.5f) {
                                haptic.performHapticFeedback(HapticFeedbackType.LongPress)
                            }
                        }
                    }
                }
            }
            .pointerInput(Unit) {
                awaitEachGesture {
                    while (true) {
                        val event = awaitPointerEvent()
                        val pressedPointers = event.changes.filter { it.pressed }.map { it.position }
                        activeTouchPoints = pressedPointers
                    }
                }
            },
        contentAlignment = Alignment.Center
    ) {
        // 1. TOP-LEFT HUD: Live Telemetry Feeds
        Column(
            modifier = Modifier
                .align(Alignment.TopStart)
                .padding(12.dp)
                .width(160.dp)
                .clip(RoundedCornerShape(8.dp))
                .background(Color(0x0F, 0x14, 0x1C).copy(alpha = 0.82f))
                .border(1.dp, Color(0x21, 0x26, 0x2D).copy(alpha = 0.6f), RoundedCornerShape(8.dp))
                .padding(10.dp),
            verticalArrangement = Arrangement.spacedBy(6.dp)
        ) {
            Text(
                text = "IOT TELEMETRY HUD",
                color = Color(0x58, 0xA6, 0xFF),
                fontSize = 9.sp,
                fontFamily = FontFamily.Monospace,
                fontWeight = FontWeight.Bold,
                letterSpacing = 1.sp
            )

            // Speed item
            Column {
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Text(text = "SPEED", color = Color(0x8A, 0x9B, 0xA8), fontSize = 8.sp, fontFamily = FontFamily.Monospace)
                    Text(
                        text = if (useMetric) "${speed.toInt()} km/h" else "${(speed * 0.621f).toInt()} mph",
                        color = Color.White,
                        fontSize = 10.sp,
                        fontFamily = FontFamily.Monospace,
                        fontWeight = FontWeight.Bold
                    )
                }
                Spacer(modifier = Modifier.height(2.dp))
                // Speed mini bar
                Box(
                    modifier = Modifier
                        .fillMaxWidth()
                        .height(3.dp)
                        .background(Color(0x21, 0x26, 0x2D))
                ) {
                    Box(
                        modifier = Modifier
                            .fillMaxWidth(fraction = (speed / 120f).coerceIn(0f, 1f))
                            .fillMaxHeight()
                            .background(Color(0x58, 0xA6, 0xFF))
                    )
                }
            }

            // Pressure item
            val pColor = when {
                pressure < 22f || pressure > 38f -> Color(0xFF, 0x4B, 0x4B)
                pressure < 27.5f || pressure > 35.5f -> Color(0xFF, 0xD4, 0x3F)
                else -> Color(0x28, 0xB4, 0x82)
            }
            Column {
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Text(text = "PRESSURE", color = Color(0x8A, 0x9B, 0xA8), fontSize = 8.sp, fontFamily = FontFamily.Monospace)
                    Text(
                        text = if (useMetric) "${(pressure * 0.0689f).toInt()} bar" else "${pressure.toInt()} psi",
                        color = pColor,
                        fontSize = 10.sp,
                        fontFamily = FontFamily.Monospace,
                        fontWeight = FontWeight.Bold
                    )
                }
                Spacer(modifier = Modifier.height(2.dp))
                // Pressure mini bar
                Box(
                    modifier = Modifier
                        .fillMaxWidth()
                        .height(3.dp)
                        .background(Color(0x21, 0x26, 0x2D))
                ) {
                    Box(
                        modifier = Modifier
                            .fillMaxWidth(fraction = ((pressure - 15f) / 30f).coerceIn(0f, 1f))
                            .fillMaxHeight()
                            .background(pColor)
                    )
                }
            }

            // Temp item
            val tColor = when {
                temperature > 80f -> Color(0xFF, 0x4B, 0x4B)
                temperature > 50f -> Color(0xFF, 0x5E, 0x36)
                else -> Color(0x58, 0xA6, 0xFF)
            }
            Column {
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Text(text = "SYS TEMP", color = Color(0x8A, 0x9B, 0xA8), fontSize = 8.sp, fontFamily = FontFamily.Monospace)
                    Text(
                        text = if (useMetric) "${temperature.toInt()} °C" else "${(temperature * 9 / 5 + 32).toInt()} °F",
                        color = tColor,
                        fontSize = 10.sp,
                        fontFamily = FontFamily.Monospace,
                        fontWeight = FontWeight.Bold
                    )
                }
                Spacer(modifier = Modifier.height(2.dp))
                // Temp mini bar
                Box(
                    modifier = Modifier
                        .fillMaxWidth()
                        .height(3.dp)
                        .background(Color(0x21, 0x26, 0x2D))
                ) {
                    Box(
                        modifier = Modifier
                            .fillMaxWidth(fraction = ((temperature - 15f) / 95f).coerceIn(0f, 1f))
                            .fillMaxHeight()
                            .background(tColor)
                    )
                }
            }
        }

        // 2. TOP-RIGHT HUD: Core Status & Orientation Matrix
        Column(
            modifier = Modifier
                .align(Alignment.TopEnd)
                .padding(12.dp)
                .width(160.dp)
                .clip(RoundedCornerShape(8.dp))
                .background(Color(0x0F, 0x14, 0x1C).copy(alpha = 0.82f))
                .border(1.dp, Color(0x21, 0x26, 0x2D).copy(alpha = 0.6f), RoundedCornerShape(8.dp))
                .padding(10.dp),
            verticalArrangement = Arrangement.spacedBy(6.dp)
        ) {
            Text(
                text = "TWIN SYSTEM STATUS",
                color = Color(0x50, 0xFA, 0x7B),
                fontSize = 9.sp,
                fontFamily = FontFamily.Monospace,
                fontWeight = FontWeight.Bold,
                letterSpacing = 1.sp
            )

            // Dynamic anomaly summary alert badge
            val (alertText, alertColor) = when {
                pressure < 22f -> "CRIT UNDER-INFLATION" to Color(0xFF, 0x4B, 0x4B)
                pressure > 38f -> "CRIT OVER-INFLATION" to Color(0xFF, 0x4B, 0x4B)
                temperature > 80f -> "CRIT OVERHEAT" to Color(0xFF, 0x4B, 0x4B)
                speed > 100f -> "HIGH SPIN RATE" to Color(0xFF, 0x5E, 0x36)
                else -> "NOMINAL STATE - OK" to Color(0x28, 0xB4, 0x82)
            }

            Box(
                modifier = Modifier
                    .fillMaxWidth()
                    .clip(RoundedCornerShape(4.dp))
                    .background(alertColor.copy(alpha = 0.15f))
                    .border(0.5.dp, alertColor.copy(alpha = 0.4f), RoundedCornerShape(4.dp))
                    .padding(vertical = 3.dp, horizontal = 5.dp)
            ) {
                Text(
                    text = alertText,
                    color = alertColor,
                    fontSize = 8.sp,
                    fontFamily = FontFamily.Monospace,
                    fontWeight = FontWeight.Bold
                )
            }

            // Key-Value rows of system properties
            Column(verticalArrangement = Arrangement.spacedBy(3.dp)) {
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween
                ) {
                    Text(text = "RENDER:", color = Color(0x8A, 0x9B, 0xA8), fontSize = 8.sp, fontFamily = FontFamily.Monospace)
                    Text(text = if (isThermalMode) "THERMAL" else "VECTOR GL", color = if (isThermalMode) Color(0xFF, 0x5E, 0x36) else Color(0x58, 0xA6, 0xFF), fontSize = 8.sp, fontFamily = FontFamily.Monospace, fontWeight = FontWeight.Bold)
                }
                
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween
                ) {
                    Text(text = "PROFILE:", color = Color(0x8A, 0x9B, 0xA8), fontSize = 8.sp, fontFamily = FontFamily.Monospace)
                    Text(text = wearPattern.uppercase(), color = if (wearPattern == "Normal") Color(0x28, 0xB4, 0x82) else Color(0xFF, 0xD4, 0x3F), fontSize = 8.sp, fontFamily = FontFamily.Monospace, fontWeight = FontWeight.Bold)
                }

                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween
                ) {
                    Text(text = "YAW / PITCH:", color = Color(0x8A, 0x9B, 0xA8), fontSize = 8.sp, fontFamily = FontFamily.Monospace)
                    Text(text = "${yaw.toInt()}° / ${pitch.toInt()}°", color = Color.White, fontSize = 8.sp, fontFamily = FontFamily.Monospace, fontWeight = FontWeight.Bold)
                }

                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween
                ) {
                    Text(text = "EXPLODED:", color = Color(0x8A, 0x9B, 0xA8), fontSize = 8.sp, fontFamily = FontFamily.Monospace)
                    Text(text = if (isExplodedView) "ACTIVE" else "OFF", color = if (isExplodedView) Color(0xFF, 0xD4, 0x3F) else Color(0x8A, 0x9B, 0xA8), fontSize = 8.sp, fontFamily = FontFamily.Monospace, fontWeight = FontWeight.Bold)
                }
            }
        }

        Column(
            modifier = Modifier
                .align(Alignment.BottomCenter)
                .padding(bottom = 12.dp),
            horizontalAlignment = Alignment.CenterHorizontally
        ) {
            TextButton(onClick = { useWebEngine = !useWebEngine }) {
                Text(
                    text = if (useWebEngine) "SWITCH TO NATIVE ENGINE" else "SWITCH TO THREE.JS ENGINE",
                    color = Color(0x58, 0xA6, 0xFF),
                    fontSize = 10.sp,
                    fontFamily = FontFamily.Monospace,
                    fontWeight = FontWeight.Bold
                )
            }
            Text(
                text = "◄ DRAG TO ROTATE // PINCH TO ZOOM // DOUBLE TAP TO RESET ►",
                color = Color(0x80, 0x9A, 0xAD).copy(alpha = 0.7f),
                fontSize = 10.sp,
                fontFamily = FontFamily.Monospace,
                letterSpacing = 1.sp
            )
        }

        if (useWebEngine) {
            WebComponent(
                url = "file:///android_asset/tire_model.html",
                modifier = Modifier.fillMaxSize(),
                onWebViewCreated = { webViewRef = it }
            )
        } else {
            Canvas(modifier = Modifier.fillMaxSize()) {
            val cx = size.width / 2f
            val cy = size.height / 2f
            val scaleFactor = size.width.coerceAtMost(size.height) * 0.38f * zoomScale

            // Generate tire mesh vertices
            val vertices = mutableListOf<Point3D>()
            val vertexColors = mutableListOf<Color>()

            // Dimensions:
            val stepsTheta = 40  // steps around the wheel
            val stepsWidth = 7   // segments across tire width (shoulders, carcass, treads)
            val outerRadiusMax = 110f
            val innerRadiusMax = 70f
            val widthOffsetMax = 32f

            // Calculate state impact factors:
            // Under-inflation flattening factor at the bottom of the tire
            val isUnderInflated = localPressure < 28f
            val sagInfluence = if (isUnderInflated) {
                (28f - localPressure) / 13f // 0f to 1.0f
            } else 0f

            // Over-inflation central crowning factor
            val isOverInflated = localPressure > 34f
            val crowningInfluence = if (isOverInflated) {
                (localPressure - 34f) / 11f // 0f to 1.0f
            } else 0f

            // Radial coordinates generator
            fun getRadiusForVertex(thetaRad: Float, wIndex: Int, numW: Int): Float {
                // normalize cross-section index to -1.0 to 1.0
                val wNorm = (wIndex - (numW - 1) / 2f) / ((numW - 1) / 2f) // lateral position
                // Tire profile shape: curved from center (crown) down to shoulders
                val profileCurvature = 1f - 0.28f * wNorm * wNorm // curved profile

                var radius = innerRadiusMax + (outerRadiusMax - innerRadiusMax) * profileCurvature

                // Over-inflation ballooning center expansion
                if (crowningInfluence > 0) {
                    val centerFactor = cos(wNorm * (Math.PI / 2).toFloat()).coerceAtLeast(0f)
                    radius += centerFactor * 12f * crowningInfluence
                }

                // Under-inflation flatting/deflation at the bottom
                // thetaRad of -pi/2 is the contact point with road
                if (sagInfluence > 0) {
                    val contactAngle = -Math.PI.toFloat() / 2f
                    // Angular distance to bottom contact point
                    var angleDiff = thetaRad - contactAngle
                    while (angleDiff < -Math.PI) angleDiff += (2 * Math.PI).toFloat()
                    while (angleDiff > Math.PI) angleDiff -= (2 * Math.PI).toFloat()

                    val angularProximity = cos(angleDiff).coerceAtLeast(0f) // close to bottom
                    val contactFlattening = angularProximity * angularProximity * angularProximity
                    radius -= contactFlattening * 14f * sagInfluence
                }

                return radius
            }

            // Outer tire surface generation
            for (i in 0 until stepsTheta) {
                val theta = (i * 2 * Math.PI / stepsTheta).toFloat()
                val spinRad = rollAngle * (Math.PI / 180).toFloat()
                val rollingTheta = theta + spinRad // Rotated base coordinate

                for (j in 0 until stepsWidth) {
                    val wNorm = (j - (stepsWidth - 1) / 2f) / ((stepsWidth - 1) / 2f)
                    val baseRadius = getRadiusForVertex(rollingTheta, j, stepsWidth)

                    // Compute unrotated 3D position
                    // We spin along the tire rotation axis (Z-axis revolves it vertically)
                    var xVal = wNorm * widthOffsetMax
                    var yVal = baseRadius * sin(rollingTheta)
                    var zVal = baseRadius * cos(rollingTheta)

                    // Sidewall bulge behavior representing low pressure:
                    if (sagInfluence > 0 && j in listOf(0, stepsWidth - 1)) {
                        val contactAngle = -Math.PI.toFloat() / 2f
                        var angleDiff = rollingTheta - contactAngle
                        while (angleDiff < -Math.PI) angleDiff += (2 * Math.PI).toFloat()
                        while (angleDiff > Math.PI) angleDiff -= (2 * Math.PI).toFloat()

                        val bulgeProximity = cos(angleDiff).coerceAtLeast(0f)
                        val extraBulge = bulgeProximity * bulgeProximity * 11f * sagInfluence
                        xVal += if (wNorm < 0) -extraBulge else extraBulge
                    }

                    // Separation layer displacement in Exploded View
                    if (explosionProgress > 0) {
                        // radially push outwards
                        val radPush = 15f * explosionProgress
                        yVal += radPush * sin(rollingTheta)
                        zVal += radPush * cos(rollingTheta)
                    }

                    val point = Point3D(xVal, yVal, zVal)
                    vertices.add(point)

                    // Vertex Shading Material Coloring
                    var vColor = Color(0xFF, 0xA0, 0xAB) // fallbacks
                    if (localThermalMode) {
                        // Temperature simulation spectrum (Cool blue to super hot red)
                        // Speed adds friction heat
                        val speedFriction = (localSpeed / 120f) * 15f
                        val effectiveTemp = localTemperature + speedFriction + (if (isUnderInflated) 18f * sagInfluence else 0f)
                        val ratio = (effectiveTemp - 15f) / 95f // 0.0 to 1.0 range
                        vColor = evaluateThermalColor(ratio.coerceIn(0f, 1f))
                    } else {
                        // Diagnostic Wear highlighting coloring
                        vColor = when (wearPattern) {
                            "Center Wear" -> {
                                if (j in listOf(3, 4)) {
                                    Color(0xFF, 0x4B, 0x4B) // Critical worn orange-red center
                                } else Color(0x40, 0x51, 0x61) // Tread baseline
                            }
                            "Edge Wear" -> {
                                if (j in listOf(1, 5)) {
                                    Color(0xFF, 0x5E, 0x36) // Shoulder alert zones
                                } else Color(0x40, 0x51, 0x61)
                            }
                            "Camber Wear" -> {
                                if (j <= 1) {
                                    Color(0xFF, 0x38, 0x60) // High wear on left inside shoulder
                                } else Color(0x40, 0x51, 0x61)
                            }
                            "Cupping Wear" -> {
                                // Scalloped patches around circumference
                                val patchFreq = 7
                                val isPatch = (i % patchFreq < 2) && j in listOf(1, 5)
                                if (isPatch) Color(0xFF, 0xD4, 0x3F) else Color(0x40, 0x51, 0x61)
                            }
                            else -> {
                                // Safe optimal cyan/teal aesthetic highlights
                                if (j in listOf(0, stepsWidth - 1)) {
                                    Color(0x3A, 0x3D, 0x50) // Darker rubber sidewalls
                                } else {
                                    Color(0x28, 0xB4, 0x82) // Healthy vibrant cyber green blocks
                                }
                            }
                        }
                    }
                    vertexColors.add(vColor)
                }
            }

            // Generate inner steel belt layer if Exploded View is active
            // The steel belts remain at true base coordinates, exposed under the casing
            val steelBeltOffsetIndex = vertices.size
            if (explosionProgress > 0) {
                for (i in 0 until stepsTheta) {
                    val theta = (i * 2 * Math.PI / stepsTheta).toFloat()
                    val rollingTheta = theta + rollAngle * (Math.PI / 180).toFloat()

                    for (j in 1 until stepsWidth - 1) { // steel wire strictly under tread, not sides
                        val wNorm = (j - (stepsWidth - 1) / 2f) / ((stepsWidth - 1) / 2f)
                        val radius = innerRadiusMax + (outerRadiusMax - innerRadiusMax - 12f) * (1f - 0.28f * wNorm * wNorm)

                        val xVal = wNorm * widthOffsetMax * 0.9f
                        val yVal = radius * sin(rollingTheta)
                        val zVal = radius * cos(rollingTheta)

                        vertices.add(Point3D(xVal, yVal, zVal))
                        vertexColors.add(Color(0xFF, 0xD7, 0x00)) // Steel Gold
                    }
                }
            }

            // Solid Metal Wheel Rim structure
            val rimOffsetIndex = vertices.size
            val rimStepsTheta = 24
            val rimLayers = 2 // front lip and inner flange
            for (layer in 0 until rimLayers) {
                val xVal = if (layer == 0) -widthOffsetMax * 0.72f else widthOffsetMax * 0.72f
                for (i in 0 until rimStepsTheta) {
                    val theta = (i * 2 * Math.PI / rimStepsTheta).toFloat()
                    val r = innerRadiusMax
                    val spinRad = rollAngle * (Math.PI / 180).toFloat()
                    val rotatedTheta = theta + spinRad

                    vertices.add(Point3D(xVal, r * sin(rotatedTheta), r * cos(rotatedTheta)))
                    vertexColors.add(Color(0x58, 0xA6, 0xFF)) // Chromium tech blue rim shade
                }
            }

            // Project all 3D vertices to 2D Screen Space
            val projected = vertices.mapIndexed { idx, p ->
                // Pitch and Yaw
                val cameraRotated = p.rotateY(yaw).rotateX(pitch)

                val focusDist = scaleFactor * 2.2f
                val scale = focusDist / (focusDist + cameraRotated.z)
                val screenOffset = Offset(
                    cx + cameraRotated.x * scale,
                    cy - cameraRotated.y * scale
                )
                ProjectedPoint(
                    screenOffset = screenOffset,
                    zDepth = cameraRotated.z,
                    rawPoint = p,
                    normal = Point3D(0f, 0f, 1f) // generic placeholder
                )
            }

            // Segments mapping rules
            val segments = mutableListOf<Segment3D>()

            // Outer Casing Grid Wireframe
            for (i in 0 until stepsTheta) {
                val nextI = (i + 1) % stepsTheta

                for (j in 0 until stepsWidth) {
                    val currentIdx = i * stepsWidth + j
                    val nextCircumferenceIdx = nextI * stepsWidth + j

                    // Circumference Lines (Groove tracks)
                    segments.add(Segment3D(currentIdx, nextCircumferenceIdx, vertexColors[currentIdx], thickness = 1.8f))

                    // Lateral lines (Cross threads) connecting width
                    if (j < stepsWidth - 1) {
                        segments.add(Segment3D(currentIdx, currentIdx + 1, vertexColors[currentIdx], thickness = 1f))
                    }
                }
            }

            // Inner Steel belt matrix if exploded view
            if (explosionProgress > 0) {
                val sbWidth = stepsWidth - 2
                for (i in 0 until stepsTheta) {
                    val nextI = (i + 1) % stepsTheta
                    for (j in 0 until sbWidth) {
                        val curr = steelBeltOffsetIndex + i * sbWidth + j
                        val nextCircum = steelBeltOffsetIndex + nextI * sbWidth + j

                        // Circumference Steel Belt Core
                        segments.add(
                            Segment3D(
                                curr,
                                nextCircum,
                                Color(0xFF, 0xD7, 0x00).copy(alpha = 0.8f * explosionProgress),
                                thickness = 2.2f,
                                isSteelBelt = true
                            )
                        )

                        // Diagonal intersecting structural steel wire crossing belts
                        if (j < sbWidth - 1) {
                            segments.add(
                                Segment3D(
                                    curr,
                                    curr + 1,
                                    Color(0xEE, 0xCB, 0x43).copy(alpha = 0.5f * explosionProgress),
                                    thickness = 1f,
                                    isSteelBelt = true
                                )
                            )
                        }
                    }
                }
            }

            // Alloy spokes and rims segments
            for (layer in 0 until rimLayers) {
                val layerBaseIdx = rimOffsetIndex + layer * rimStepsTheta
                for (i in 0 until rimStepsTheta) {
                    val currentIdx = layerBaseIdx + i
                    val nextIdx = layerBaseIdx + (i + 1) % rimStepsTheta

                    // Rim circle outline
                    segments.add(Segment3D(currentIdx, nextIdx, Color(0x58, 0xA6, 0xFF).copy(alpha = 0.6f), thickness = 2f, isSpoke = true))

                    // Cross support barrels connecting side rims
                    if (layer == 0) {
                        val matchingFlangeIdx = currentIdx + rimStepsTheta
                        segments.add(Segment3D(currentIdx, matchingFlangeIdx, Color(0x3B, 0x76, 0xB6).copy(alpha = 0.25f), thickness = 0.8f, isSpoke = true))
                    }
                }

                // Beautiful rim sports-spokes connected to axis center
                // Center can be computed as projection of (layer_X, 0, 0)
                if (layer == 0) { // draw center spokes on outer side only for aesthetics
                    val centerRotated = Point3D(
                        -widthOffsetMax * 0.72f,
                        0f,
                        0f
                    ).rotateY(yaw).rotateX(pitch)
                    val focusDist = scaleFactor * 2.2f
                    val scale = focusDist / (focusDist + centerRotated.z)
                    val centerOffset = Offset(cx + centerRotated.x * scale, cy - centerRotated.y * scale)

                    // Draw 8 solid thick spokes
                    val spokesCount = 8
                    for (k in 0 until spokesCount) {
                        val spokeVerIdx = layerBaseIdx + (k * (rimStepsTheta / spokesCount))
                        val rimProj = projected[spokeVerIdx]

                        // Sorted by spoke depth later, or simply direct draw
                        drawLine(
                            color = Color(0x76, 0xB9, 0xFF).copy(alpha = 0.85f),
                            start = centerOffset,
                            end = rimProj.screenOffset,
                            strokeWidth = 3.5f
                        )
                    }
                }
            }

            // Depth sorting the segments using Painter's Algorithm for perfect occlusion
            val sortedSegments = segments.sortedByDescending { seg ->
                (projected[seg.p1Index].zDepth + projected[seg.p2Index].zDepth) / 2f
            }

            // Draw all lines onto the canvas
            sortedSegments.forEach { seg ->
                val p1 = projected[seg.p1Index]
                val p2 = projected[seg.p2Index]

                // Clip lines that would wrap around behind camera focal point
                if (p1.zDepth > -160f && p2.zDepth > -160f) {
                    drawLine(
                        color = seg.color,
                        start = p1.screenOffset,
                        end = p2.screenOffset,
                        strokeWidth = seg.thickness
                    )
                }
            }

            // Floating 3D Gauge Markers and Labels in Exploded view (T1 - T4)
            if (isExplodedView) {
                // Pinpoint 4 distinctive points around circumference in 3D
                val markersAngle = listOf(-30f, 60f, 150f, 240f)
                val markerLabels = listOf("T1: Tread 1.8mm (Crit)", "T2: Tread 4.1mm (Good)", "T3: Center 1.2mm (Crit)", "T4: Flange Align ok")
                val markerColors = listOf(Color(0xFF, 0x4B, 0x4B), Color(0x28, 0xB4, 0x82), Color(0xFF, 0x4B, 0x4B), Color(0x58, 0xA6, 0xFF))

                markersAngle.forEachIndexed { markerIdx, angle ->
                    val angleRad = (angle + rollAngle) * (Math.PI / 180).toFloat()
                    // Locate on the outer crown profile
                    val radius = getRadiusForVertex(angleRad, 3, stepsWidth) + 18f * explosionProgress
                    val p3d = Point3D(10f, radius * sin(angleRad), radius * cos(angleRad))

                    val cameraRotated = p3d.rotateY(yaw).rotateX(pitch)
                    val focusDist = scaleFactor * 2.2f
                    val scale = focusDist / (focusDist + cameraRotated.z)

                    // Only draw markers on the front facing quadrant to prevent back-cluttering
                    if (cameraRotated.z < 100f) {
                        val sOffset = Offset(cx + cameraRotated.x * scale, cy - cameraRotated.y * scale)

                        // Marker anchor pointer circle
                        drawCircle(
                            color = markerColors[markerIdx],
                            radius = 5.dp.toPx(),
                            center = sOffset
                        )

                        // Floating scan line
                        val labelAngleRad = (angle + 15f + rollAngle) * (Math.PI / 180).toFloat()
                        val textRadius = radius + 30f
                        val label3d = Point3D(25f, textRadius * sin(labelAngleRad), textRadius * cos(labelAngleRad))
                        val labelRotated = label3d.rotateY(yaw).rotateX(pitch)
                        val lScale = focusDist / (focusDist + labelRotated.z)
                        val textOffset = Offset(cx + labelRotated.x * scale, cy - labelRotated.y * scale)

                        drawLine(
                            color = markerColors[markerIdx].copy(alpha = 0.5f),
                            start = sOffset,
                            end = textOffset,
                            strokeWidth = 2f
                        )

                        // text drawing on canvas:
                        // Draw horizontal tail
                        val textTailX = textOffset.x + (if (textOffset.x > cx) 25f else -25f)
                        drawLine(
                            color = markerColors[markerIdx].copy(alpha = 0.5f),
                            start = textOffset,
                            end = Offset(textTailX, textOffset.y),
                            strokeWidth = 2f
                        )

                        // Draw text marker circles
                        drawCircle(
                            color = Color.White,
                            radius = 2.dp.toPx(),
                            center = Offset(textTailX, textOffset.y)
                        )
                    }
                }
            }

            // 3D REAL-TIME SYSTEM HUD CHASSIS CHANNELS
            // SPEED CHASSIS CHANNEL
            val speedAnchorVec = Point3D(-widthOffsetMax * 1.5f, 65f, 15f).rotateY(yaw).rotateX(pitch)
            if (speedAnchorVec.z < 150f) {
                val speedScale = (scaleFactor * 2.2f) / ((scaleFactor * 2.2f) + speedAnchorVec.z)
                val speedScreenPos = Offset(cx + speedAnchorVec.x * speedScale, cy - speedAnchorVec.y * speedScale)
                
                // Clamped position for the floating readout plate to avoid edge clipping
                val plateX = (speedScreenPos.x - 142f).coerceIn(12f, size.width - 150f)
                val plateY = (speedScreenPos.y - 45f).coerceIn(12f, size.height - 75f)

                // Track screen position for taps
                plateBounds.speedBounds.set(plateX, plateY, plateX + 138f, plateY + 40f)

                // Render highlighting ring if Speed Channel is active
                if (activeChannel == "SPEED") {
                    drawRoundRect(
                        color = Color(0x58, 0xA6, 0xFF).copy(alpha = 0.85f),
                        topLeft = Offset(plateX - 3f, plateY - 3f),
                        size = androidx.compose.ui.geometry.Size(144f, 46f),
                        cornerRadius = androidx.compose.ui.geometry.CornerRadius(6.dp.toPx(), 6.dp.toPx()),
                        style = Stroke(width = 1.5f.dp.toPx())
                    )
                }

                // 1. Leader Line
                val path = Path().apply {
                    moveTo(speedScreenPos.x, speedScreenPos.y)
                    lineTo(speedScreenPos.x - 20f, speedScreenPos.y - 15f)
                    lineTo(if (speedScreenPos.x > cx) plateX + 138f else plateX, plateY + 15f)
                }
                drawPath(path, Color(0x58, 0xA6, 0xFF).copy(alpha = 0.5f), style = Stroke(width = 1.dp.toPx()))
                drawCircle(Color(0x58, 0xA6, 0xFF).copy(alpha = 0.8f), radius = 3.dp.toPx(), center = speedScreenPos)

                // 2. HUD Plate background (Glassmorphic look)
                drawRoundRect(
                    color = (if (isDarkTheme) Color(0x0F, 0x14, 0x1C) else Color(0xF3, 0xF4, 0xF6)).copy(alpha = 0.85f),
                    topLeft = Offset(plateX, plateY),
                    size = androidx.compose.ui.geometry.Size(138f, 40f),
                    cornerRadius = androidx.compose.ui.geometry.CornerRadius(4.dp.toPx(), 4.dp.toPx())
                )
                drawRoundRect(
                    color = Color(0x58, 0xA6, 0xFF).copy(alpha = if (isDarkTheme) 0.3f else 0.5f),
                    topLeft = Offset(plateX, plateY),
                    size = androidx.compose.ui.geometry.Size(138f, 40f),
                    cornerRadius = androidx.compose.ui.geometry.CornerRadius(4.dp.toPx(), 4.dp.toPx()),
                    style = Stroke(width = 0.8f.dp.toPx())
                )

                // 3. Mini visual gauge bar inside HUD plate
                val gaugeWidth = 118f
                drawRect(
                    color = if (isDarkTheme) Color(0x21, 0x26, 0x2D) else Color(0xDF, 0xE2, 0xE5),
                    topLeft = Offset(plateX + 10f, plateY + 28f),
                    size = androidx.compose.ui.geometry.Size(gaugeWidth, 2.5f.dp.toPx())
                )
                drawRect(
                    color = Color(0x58, 0xA6, 0xFF),
                    topLeft = Offset(plateX + 10f, plateY + 28f),
                    size = androidx.compose.ui.geometry.Size(gaugeWidth * (localSpeed / 120f).coerceIn(0f, 1f), 2.5f.dp.toPx())
                )

                // 4. Native text rendering (Title, Value)
                drawContext.canvas.nativeCanvas.apply {
                    val paintTitle = Paint().apply {
                        isAntiAlias = true
                        typeface = Typeface.create(Typeface.MONOSPACE, Typeface.BOLD)
                        color = android.graphics.Color.parseColor(if (isDarkTheme) "#8A9BA8" else "#4B5563")
                        textSize = 7.dp.toPx()
                    }
                    val paintVal = Paint().apply {
                        isAntiAlias = true
                        typeface = Typeface.create(Typeface.MONOSPACE, Typeface.BOLD)
                        color = if (isDarkTheme) android.graphics.Color.WHITE else android.graphics.Color.parseColor("#1F2328")
                        textSize = 9.5f.dp.toPx()
                    }
                    drawText(if (useMetric) "3D.SPD // KM/H" else "3D.SPD // MPH", plateX + 10f, plateY + 13f, paintTitle)
                    drawText(if (useMetric) "${localSpeed.toInt()} KM/H" else "${(localSpeed * 0.621f).toInt()} MPH", plateX + 10f, plateY + 25f, paintVal)
                }
            }

            // PRESSURE CHASSIS CHANNEL
            val pressAnchorVec = Point3D(-widthOffsetMax * 1.5f, -65f, 15f).rotateY(yaw).rotateX(pitch)
            if (pressAnchorVec.z < 150f) {
                val pressScale = (scaleFactor * 2.2f) / ((scaleFactor * 2.2f) + pressAnchorVec.z)
                val pressScreenPos = Offset(cx + pressAnchorVec.x * pressScale, cy - pressAnchorVec.y * pressScale)
                
                // Clamped position for floating readout plate
                val plateX = (pressScreenPos.x - 142f).coerceIn(12f, size.width - 150f)
                val plateY = (pressScreenPos.y + 15f).coerceIn(12f, size.height - 75f)

                // Track screen position for taps
                plateBounds.pressureBounds.set(plateX, plateY, plateX + 138f, plateY + 40f)

                val pColor = when {
                    localPressure < 22f || localPressure > 38f -> Color(0xFF, 0x4B, 0x4B)
                    localPressure < 27.5f || localPressure > 35.5f -> Color(0xFF, 0xD4, 0x3F)
                    else -> Color(0x28, 0xB4, 0x82)
                }

                // Render highlighting ring if Pressure Channel is active
                if (activeChannel == "PRESSURE") {
                    drawRoundRect(
                        color = pColor.copy(alpha = 0.85f),
                        topLeft = Offset(plateX - 3f, plateY - 3f),
                        size = androidx.compose.ui.geometry.Size(144f, 46f),
                        cornerRadius = androidx.compose.ui.geometry.CornerRadius(6.dp.toPx(), 6.dp.toPx()),
                        style = Stroke(width = 1.5f.dp.toPx())
                    )
                }

                // 1. Leader Line
                val path = Path().apply {
                    moveTo(pressScreenPos.x, pressScreenPos.y)
                    lineTo(pressScreenPos.x - 20f, pressScreenPos.y + 15f)
                    lineTo(if (pressScreenPos.x > cx) plateX + 138f else plateX, plateY + 15f)
                }
                drawPath(path, pColor.copy(alpha = 0.5f), style = Stroke(width = 1.dp.toPx()))
                drawCircle(pColor.copy(alpha = 0.8f), radius = 3.dp.toPx(), center = pressScreenPos)

                // 2. HUD Plate background
                drawRoundRect(
                    color = (if (isDarkTheme) Color(0x0F, 0x14, 0x1C) else Color(0xF3, 0xF4, 0xF6)).copy(alpha = 0.85f),
                    topLeft = Offset(plateX, plateY),
                    size = androidx.compose.ui.geometry.Size(138f, 40f),
                    cornerRadius = androidx.compose.ui.geometry.CornerRadius(4.dp.toPx(), 4.dp.toPx())
                )
                drawRoundRect(
                    color = pColor.copy(alpha = if (isDarkTheme) 0.3f else 0.5f),
                    topLeft = Offset(plateX, plateY),
                    size = androidx.compose.ui.geometry.Size(138f, 40f),
                    cornerRadius = androidx.compose.ui.geometry.CornerRadius(4.dp.toPx(), 4.dp.toPx()),
                    style = Stroke(width = 0.8f.dp.toPx())
                )

                // 3. Mini bar
                val gaugeWidth = 118f
                drawRect(
                    color = if (isDarkTheme) Color(0x21, 0x26, 0x2D) else Color(0xDF, 0xE2, 0xE5),
                    topLeft = Offset(plateX + 10f, plateY + 28f),
                    size = androidx.compose.ui.geometry.Size(gaugeWidth, 2.5f.dp.toPx())
                )
                drawRect(
                    color = pColor,
                    topLeft = Offset(plateX + 10f, plateY + 28f),
                    size = androidx.compose.ui.geometry.Size(gaugeWidth * ((localPressure - 15f) / 30f).coerceIn(0f, 1f), 2.5f.dp.toPx())
                )

                // 4. Text
                drawContext.canvas.nativeCanvas.apply {
                    val paintTitle = Paint().apply {
                        isAntiAlias = true
                        typeface = Typeface.create(Typeface.MONOSPACE, Typeface.BOLD)
                        color = android.graphics.Color.parseColor(if (isDarkTheme) "#8A9BA8" else "#4B5563")
                        textSize = 7.dp.toPx()
                    }
                    val paintVal = Paint().apply {
                        isAntiAlias = true
                        typeface = Typeface.create(Typeface.MONOSPACE, Typeface.BOLD)
                        color = android.graphics.Color.parseColor(
                            when {
                                localPressure < 22f || localPressure > 38f -> "#FF4B4B"
                                localPressure < 27.5f || localPressure > 35.5f -> "#FFD43F"
                                else -> "#28B482"
                            }
                        )
                        textSize = 9.5f.dp.toPx()
                    }
                    drawText(if (useMetric) "3D.BAR // PRESS" else "3D.PSI // COMPRESS", plateX + 10f, plateY + 13f, paintTitle)
                    drawText(
                        if (useMetric) "${(localPressure * 0.0689f).toInt()} BAR" else "${localPressure.toInt()} PSI",
                        plateX + 10f,
                        plateY + 25f,
                        paintVal
                    )
                }
            }

            // TEMPERATURE CHASSIS CHANNEL
            val tempAnchorVec = Point3D(widthOffsetMax * 1.5f, 55f, 15f).rotateY(yaw).rotateX(pitch)
            if (tempAnchorVec.z < 150f) {
                val tempScale = (scaleFactor * 2.2f) / ((scaleFactor * 2.2f) + tempAnchorVec.z)
                val tempScreenPos = Offset(cx + tempAnchorVec.x * tempScale, cy - tempAnchorVec.y * tempScale)
                
                // Clamped position for floating readout plate
                val plateX = (tempScreenPos.x + 15f).coerceIn(12f, size.width - 150f)
                val plateY = (tempScreenPos.y - 45f).coerceIn(12f, size.height - 75f)

                // Track screen position for taps
                plateBounds.temperatureBounds.set(plateX, plateY, plateX + 138f, plateY + 40f)

                val tColor = when {
                    localTemperature > 80f -> Color(0xFF, 0x4B, 0x4B)
                    localTemperature > 50f -> Color(0xFF, 0x5E, 0x36)
                    else -> Color(0x58, 0xA6, 0xFF)
                }

                // Render highlighting ring if Temperature Channel is active
                if (activeChannel == "TEMPERATURE") {
                    drawRoundRect(
                        color = tColor.copy(alpha = 0.85f),
                        topLeft = Offset(plateX - 3f, plateY - 3f),
                        size = androidx.compose.ui.geometry.Size(144f, 46f),
                        cornerRadius = androidx.compose.ui.geometry.CornerRadius(6.dp.toPx(), 6.dp.toPx()),
                        style = Stroke(width = 1.5f.dp.toPx())
                    )
                }

                // 1. Leader Line
                val path = Path().apply {
                    moveTo(tempScreenPos.x, tempScreenPos.y)
                    lineTo(tempScreenPos.x + 20f, tempScreenPos.y - 15f)
                    lineTo(if (tempScreenPos.x > cx) plateX else plateX + 138f, plateY + 15f)
                }
                drawPath(path, tColor.copy(alpha = 0.5f), style = Stroke(width = 1.dp.toPx()))
                drawCircle(tColor.copy(alpha = 0.8f), radius = 3.dp.toPx(), center = tempScreenPos)

                // 2. HUD Plate background
                drawRoundRect(
                    color = (if (isDarkTheme) Color(0x0F, 0x14, 0x1C) else Color(0xF3, 0xF4, 0xF6)).copy(alpha = 0.85f),
                    topLeft = Offset(plateX, plateY),
                    size = androidx.compose.ui.geometry.Size(138f, 40f),
                    cornerRadius = androidx.compose.ui.geometry.CornerRadius(4.dp.toPx(), 4.dp.toPx())
                )
                drawRoundRect(
                    color = tColor.copy(alpha = if (isDarkTheme) 0.3f else 0.5f),
                    topLeft = Offset(plateX, plateY),
                    size = androidx.compose.ui.geometry.Size(138f, 40f),
                    cornerRadius = androidx.compose.ui.geometry.CornerRadius(4.dp.toPx(), 4.dp.toPx()),
                    style = Stroke(width = 0.8f.dp.toPx())
                )

                // 3. Mini bar
                val gaugeWidth = 118f
                drawRect(
                    color = if (isDarkTheme) Color(0x21, 0x26, 0x2D) else Color(0xDF, 0xE2, 0xE5),
                    topLeft = Offset(plateX + 10f, plateY + 28f),
                    size = androidx.compose.ui.geometry.Size(gaugeWidth, 2.5f.dp.toPx())
                )
                drawRect(
                    color = tColor,
                    topLeft = Offset(plateX + 10f, plateY + 28f),
                    size = androidx.compose.ui.geometry.Size(gaugeWidth * ((localTemperature - 15f) / 95f).coerceIn(0f, 1f), 2.5f.dp.toPx())
                )

                // 4. Text
                drawContext.canvas.nativeCanvas.apply {
                    val paintTitle = Paint().apply {
                        isAntiAlias = true
                        typeface = Typeface.create(Typeface.MONOSPACE, Typeface.BOLD)
                        color = android.graphics.Color.parseColor(if (isDarkTheme) "#8A9BA8" else "#4B5563")
                        textSize = 7.dp.toPx()
                    }
                    val paintVal = Paint().apply {
                        isAntiAlias = true
                        typeface = Typeface.create(Typeface.MONOSPACE, Typeface.BOLD)
                        color = android.graphics.Color.parseColor(
                            when {
                                localTemperature > 80f -> "#FF4B4B"
                                localTemperature > 50f -> "#FF5E36"
                                else -> "#58A6FF"
                            }
                        )
                        textSize = 9.5f.dp.toPx()
                    }
                    drawText(if (useMetric) "3D.TMP // CELSIUS" else "3D.TMP // FAHR", plateX + 10f, plateY + 13f, paintTitle)
                    drawText(if (useMetric) "${localTemperature.toInt()} °C" else "${(localTemperature * 9 / 5 + 32).toInt()} °F", plateX + 10f, plateY + 25f, paintVal)
                }
            }

            // Green Holographic Laser scanning sweeps overlay simulation
            val scanY = cy + laserSweep
            drawLine(
                color = Color(0x30, 0xFF, 0x7E, 0x40),
                start = Offset(0f, scanY),
                end = Offset(size.width, scanY),
                strokeWidth = 10.dp.toPx()
            )
            drawLine(
                color = Color(0x50, 0xFA, 0x7B),
                start = Offset(0f, scanY),
                end = Offset(size.width, scanY),
                strokeWidth = 2.dp.toPx()
            )

            // Holographic 'Ghost' Contact Point Indicators
            activeTouchPoints.forEach { pt ->
                // Outer rotating/pulsating glow orbit ring
                drawCircle(
                    color = Color(0x58, 0xA6, 0xFF).copy(alpha = 0.35f), // Neon Slate Blue Glow
                    radius = 20.dp.toPx(),
                    center = pt,
                    style = Stroke(width = 1.dp.toPx())
                )
                
                // Very subtle wider halo
                drawCircle(
                    color = Color(0x58, 0xA6, 0xFF).copy(alpha = 0.12f),
                    radius = 30.dp.toPx(),
                    center = pt
                )
                
                // Draw 4 precise modern crosshair tick marks
                val tickLength = 5.dp.toPx()
                val gap = 4.dp.toPx()
                
                // Top tick
                drawLine(
                    color = Color.White.copy(alpha = 0.7f),
                    start = Offset(pt.x, pt.y - gap - tickLength),
                    end = Offset(pt.x, pt.y - gap),
                    strokeWidth = 1.5f.dp.toPx()
                )
                // Bottom tick
                drawLine(
                    color = Color.White.copy(alpha = 0.7f),
                    start = Offset(pt.x, pt.y + gap),
                    end = Offset(pt.x, pt.y + gap + tickLength),
                    strokeWidth = 1.5f.dp.toPx()
                )
                // Left tick
                drawLine(
                    color = Color.White.copy(alpha = 0.7f),
                    start = Offset(pt.x - gap - tickLength, pt.y),
                    end = Offset(pt.x - gap, pt.y),
                    strokeWidth = 1.5f.dp.toPx()
                )
                // Right tick
                drawLine(
                    color = Color.White.copy(alpha = 0.7f),
                    start = Offset(pt.x + gap, pt.y),
                    end = Offset(pt.x + gap + tickLength, pt.y),
                    strokeWidth = 1.5f.dp.toPx()
                )

                // Inner sharp core dot
                drawCircle(
                    color = Color.White,
                    radius = 2.5f.dp.toPx(),
                    center = pt
                )
            }
        }
    }

        // 4. INTERACTIVE DETAILED OVERLAY CARD FOR SELECTED HUD CHANNEL
        AnimatedVisibility(
            visible = activeChannel != null,
            enter = slideInVertically(initialOffsetY = { it }) + fadeIn(),
            exit = slideOutVertically(targetOffsetY = { it }) + fadeOut(),
            modifier = Modifier
                .align(Alignment.BottomCenter)
                .fillMaxWidth()
                .padding(12.dp)
        ) {
            Card(
                shape = RoundedCornerShape(12.dp),
                colors = CardDefaults.cardColors(containerColor = Color(0xFF, 0xFF, 0xFF).copy(alpha = 0.08f)),
                border = BorderStroke(
                    1.dp,
                    when (activeChannel) {
                        "SPEED" -> Color(0x58, 0xA6, 0xFF)
                        "PRESSURE" -> Color(0x28, 0xB4, 0x82)
                        else -> Color(0xFF, 0x5E, 0x36)
                    }.copy(alpha = 0.6f)
                ),
                modifier = Modifier
                    .fillMaxWidth()
                    .animateContentSize()
            ) {
                Column(
                    modifier = Modifier.padding(14.dp)
                ) {
                    // Header with title and close button
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Row(
                            verticalAlignment = Alignment.CenterVertically,
                            horizontalArrangement = Arrangement.spacedBy(8.dp)
                        ) {
                            val channelIcon = when (activeChannel) {
                                "SPEED" -> Icons.Default.PlayArrow
                                "PRESSURE" -> Icons.Default.Build
                                else -> Icons.Default.Thermostat
                            }
                            val channelColor = when (activeChannel) {
                                "SPEED" -> Color(0x58, 0xA6, 0xFF)
                                "PRESSURE" -> Color(0x28, 0xB4, 0x82)
                                else -> Color(0xFF, 0x5E, 0x36)
                            }
                            Icon(
                                imageVector = channelIcon,
                                contentDescription = null,
                                tint = channelColor,
                                modifier = Modifier.size(16.dp)
                            )
                            Text(
                                text = when (activeChannel) {
                                    "SPEED" -> "SYSTEM OVERDRIVE // ROTATIONAL FREQUENCY"
                                    "PRESSURE" -> "PNEUMATIC MANIFOLD PRESSURE BALANCER"
                                    else -> "THERMAL SIGNATURE EMISSIONS SPECTRA"
                                },
                                color = Color.White,
                                fontSize = 11.sp,
                                fontFamily = FontFamily.Monospace,
                                fontWeight = FontWeight.Bold
                            )
                        }
                        
                        // Close button
                        IconButton(
                            onClick = { activeChannel = null },
                            modifier = Modifier.size(24.dp)
                        ) {
                            Icon(
                                imageVector = Icons.Default.Close,
                                contentDescription = "Close",
                                tint = Color(0x8A, 0x9B, 0xA8),
                                modifier = Modifier.size(14.dp)
                            )
                        }
                    }
                    
                    Spacer(modifier = Modifier.height(8.dp))
                    
                    when (activeChannel) {
                        "SPEED" -> {
                            Text(
                                text = "Experience real-time rotational telemetry. Drag the slider to accelerate or stall the digital twin speed to test structural integrity at velocity.",
                                color = Color(0x8A, 0x9B, 0xA8),
                                fontSize = 10.sp,
                                fontFamily = FontFamily.Monospace,
                                lineHeight = 13.sp
                            )
                            Spacer(modifier = Modifier.height(12.dp))
                            Row(
                                modifier = Modifier.fillMaxWidth(),
                                verticalAlignment = Alignment.CenterVertically,
                                horizontalArrangement = Arrangement.spacedBy(10.dp)
                            ) {
                                Icon(Icons.Default.PlayArrow, contentDescription = null, tint = Color(0x58, 0xA6, 0xFF), modifier = Modifier.size(14.dp))
                                Spacer(modifier = Modifier.width(2.dp))
                                Slider(
                                    value = localSpeed,
                                    onValueChange = { localSpeed = it },
                                    valueRange = 0f..150f,
                                    modifier = Modifier.weight(1f),
                                    colors = SliderDefaults.colors(
                                        thumbColor = Color(0x58, 0xA6, 0xFF),
                                        activeTrackColor = Color(0x58, 0xA6, 0xFF),
                                        inactiveTrackColor = Color(0x1F, 0x24, 0x2C)
                                    )
                                )
                                Text(
                                    text = if (useMetric) "${localSpeed.toInt()} KM/H" else "${(localSpeed * 0.621f).toInt()} MPH",
                                    color = Color.White,
                                    fontSize = 11.sp,
                                    fontFamily = FontFamily.Monospace,
                                    fontWeight = FontWeight.Bold,
                                    modifier = Modifier.width(60.dp)
                                )
                            }
                        }
                        "PRESSURE" -> {
                            Text(
                                text = "Adjust active chamber pressure. Low pressure sags sidewalls (increasing rolling resistance); high pressure swells tread (causing localized wear).",
                                color = Color(0x8A, 0x9B, 0xA8),
                                fontSize = 10.sp,
                                fontFamily = FontFamily.Monospace,
                                lineHeight = 13.sp
                            )
                            Spacer(modifier = Modifier.height(12.dp))
                            Row(
                                modifier = Modifier.fillMaxWidth(),
                                verticalAlignment = Alignment.CenterVertically,
                                horizontalArrangement = Arrangement.spacedBy(10.dp)
                            ) {
                                Icon(Icons.Default.Build, contentDescription = null, tint = Color(0x28, 0xB4, 0x82), modifier = Modifier.size(14.dp))
                                Spacer(modifier = Modifier.width(2.dp))
                                Slider(
                                    value = localPressure,
                                    onValueChange = { localPressure = it },
                                    valueRange = 15f..45f,
                                    modifier = Modifier.weight(1f),
                                    colors = SliderDefaults.colors(
                                        thumbColor = Color(0x28, 0xB4, 0x82),
                                        activeTrackColor = Color(0x28, 0xB4, 0x82),
                                        inactiveTrackColor = Color(0x1F, 0x24, 0x2C)
                                    )
                                )
                                Text(
                                    text = if (useMetric) "${(localPressure * 0.0689f).toInt()} BAR" else "${localPressure.toInt()} PSI",
                                    color = Color.White,
                                    fontSize = 11.sp,
                                    fontFamily = FontFamily.Monospace,
                                    fontWeight = FontWeight.Bold,
                                    modifier = Modifier.width(60.dp)
                                )
                            }
                        }
                        "TEMPERATURE" -> {
                            Text(
                                text = "Tweak thermodynamic energy signatures inside the tire structure. Increased temperature creates high friction thermal signatures across the crown mesh.",
                                color = Color(0x8A, 0x9B, 0xA8),
                                fontSize = 10.sp,
                                fontFamily = FontFamily.Monospace,
                                lineHeight = 13.sp
                            )
                            Spacer(modifier = Modifier.height(12.dp))
                            Row(
                                modifier = Modifier.fillMaxWidth(),
                                verticalAlignment = Alignment.CenterVertically,
                                horizontalArrangement = Arrangement.spacedBy(10.dp)
                            ) {
                                Icon(Icons.Default.Thermostat, contentDescription = null, tint = Color(0xFF, 0x5E, 0x36), modifier = Modifier.size(14.dp))
                                Spacer(modifier = Modifier.width(2.dp))
                                Slider(
                                    value = localTemperature,
                                    onValueChange = { localTemperature = it },
                                    valueRange = 15f..110f,
                                    modifier = Modifier.weight(1f),
                                    colors = SliderDefaults.colors(
                                        thumbColor = Color(0xFF, 0x5E, 0x36),
                                        activeTrackColor = Color(0xFF, 0x5E, 0x36),
                                        inactiveTrackColor = Color(0x1F, 0x24, 0x2C)
                                    )
                                )
                                Text(
                                    text = if (useMetric) "${localTemperature.toInt()} °C" else "${(localTemperature * 9 / 5 + 32).toInt()} °F",
                                    color = Color.White,
                                    fontSize = 11.sp,
                                    fontFamily = FontFamily.Monospace,
                                    fontWeight = FontWeight.Bold,
                                    modifier = Modifier.width(60.dp)
                                )
                            }
                            
                            Spacer(modifier = Modifier.height(8.dp))
                            // Interactive toggle: Tapping thermal spectrum can overwrite active model state
                            Button(
                                onClick = { localThermalMode = !localThermalMode },
                                colors = ButtonDefaults.buttonColors(
                                    containerColor = if (localThermalMode) Color(0xFF, 0x5E, 0x36) else Color(0x21, 0x26, 0x2D),
                                    contentColor = Color.White
                                ),
                                modifier = Modifier.fillMaxWidth(),
                                shape = RoundedCornerShape(6.dp),
                                contentPadding = PaddingValues(vertical = 4.dp, horizontal = 12.dp)
                            ) {
                                Text(
                                    text = if (localThermalMode) "ACTIVE SPECTRA: THERMAL HEATMAP ON" else "ACTIVE SPECTRA: HIGH-CONTRAST MESH ON",
                                    fontSize = 9.sp,
                                    fontFamily = FontFamily.Monospace,
                                    fontWeight = FontWeight.Bold
                                )
                            }
                        }
                    }
                }
            }
        }
    }
}

// Bounds tracking helper class for clickable HUD plates
class PlateBounds {
    val speedBounds = android.graphics.RectF()
    val pressureBounds = android.graphics.RectF()
    val temperatureBounds = android.graphics.RectF()
}

// Thermal Spectrum Evaluator (Blue -> Green -> Yellow -> Orange -> Red)
fun evaluateThermalColor(factor: Float): Color {
    return when {
        factor < 0.25f -> {
            val ratio = factor / 0.25f
            Color(
                red = (0x2C + ratio * (0x1A - 0x2C)).toInt(),
                green = (0x3E + ratio * (0x9E - 0x3E)).toInt(),
                blue = (0x50 + ratio * (0xC4 - 0x50)).toInt() // cooler deep tech slate-blue
            )
        }
        factor < 0.5f -> {
            val ratio = (factor - 0.25f) / 0.25f
            Color(
                red = (0x1A + ratio * (0x4B - 0x1A)).toInt(),
                green = (0x9E + ratio * (0xD4 - 0x9E)).toInt(),
                blue = (0xC4 + ratio * (0x3F - 0xC4)).toInt() // transition into technical teal/yellow
            )
        }
        factor < 0.75f -> {
            val ratio = (factor - 0.5f) / 0.25f
            Color(
                red = (0x4B + ratio * (0xFF - 0x4B)).toInt(),
                green = (0xD4 + ratio * (0x7E - 0xD4)).toInt(),
                blue = (0x3F + ratio * (0x1A - 0x3F)).toInt() // yellow turning orange
            )
        }
        else -> {
            val ratio = (factor - 0.75f) / 0.25f
            Color(
                red = (0xFF + ratio * (0xFF - 0xFF)).toInt(),
                green = (0x7E + ratio * (0x38 - 0x7E)).toInt(),
                blue = (0x1A + ratio * (0x38 - 0x1A)).toInt() // hot alert red
            )
        }
    }
}
