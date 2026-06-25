package com.example.ui.components

import androidx.compose.animation.core.*
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.material3.Text
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp

@Composable
fun ScanOverlay(
    isScanning: Boolean,
    scanProgress: Float,
    modifier: Modifier = Modifier
) {
    // Laser sweep vertical animation
    val infiniteTransition = rememberInfiniteTransition(label = "laser")
    val laserY by infiniteTransition.animateFloat(
        initialValue = 0.1f,
        targetValue = 0.9f,
        animationSpec = infiniteRepeatable(
            animation = tween(1800, easing = LinearEasing),
            repeatMode = RepeatMode.Reverse
        ),
        label = "laser_y"
    )

    // Pulse alpha animation for wireframe corners
    val pulseAlpha by infiniteTransition.animateFloat(
        initialValue = 0.4f,
        targetValue = 1.0f,
        animationSpec = infiniteRepeatable(
            animation = tween(1000, easing = EaseInOutQuad),
            repeatMode = RepeatMode.Reverse
        ),
        label = "pulse_alpha"
    )

    Box(
        modifier = modifier.fillMaxSize()
    ) {
        // 1. Futuristic Scanner Wireframe Canvas (including green laser sweep)
        Canvas(modifier = Modifier.fillMaxSize()) {
            val cx = size.width / 2f
            val cy = size.height / 2f

            val rWidth = size.width * 0.76f
            val rHeight = size.height * 0.48f

            val rx = cx - rWidth / 2f
            val ry = cy - rHeight / 2f

            // Bounding box frame coordinates
            val length = 36.dp.toPx()
            val thickness = 3.dp.toPx()
            val themeAccent = if (isScanning) Color(0xFF, 0xBC, 0x00) else Color(0xFF, 0x70, 0x43)
            val cornerColor = if (isScanning) themeAccent.copy(alpha = pulseAlpha) else themeAccent

            // Custom futuristic corner design (drawing outer L brackets and inner dots)
            // Top-Left Corner
            val pathCornerTL = Path().apply {
                moveTo(rx, ry + length)
                lineTo(rx, ry)
                lineTo(rx + length, ry)
            }
            drawPath(pathCornerTL, cornerColor, style = Stroke(width = thickness))
            
            // Top-Right Corner
            val pathCornerTR = Path().apply {
                moveTo(rx + rWidth, ry + length)
                lineTo(rx + rWidth, ry)
                lineTo(rx + rWidth - length, ry)
            }
            drawPath(pathCornerTR, cornerColor, style = Stroke(width = thickness))

            // Bottom-Left Corner
            val pathCornerBL = Path().apply {
                moveTo(rx, ry + rHeight - length)
                lineTo(rx, ry + rHeight)
                lineTo(rx + length, ry + rHeight)
            }
            drawPath(pathCornerBL, cornerColor, style = Stroke(width = thickness))

            // Bottom-Right Corner
            val pathCornerBR = Path().apply {
                moveTo(rx + rWidth, ry + rHeight - length)
                lineTo(rx + rWidth, ry + rHeight)
                lineTo(rx + rWidth - length, ry + rHeight)
            }
            drawPath(pathCornerBR, cornerColor, style = Stroke(width = thickness))

            // Background subtle grid/mesh overlay inside scanner box or overall viewport
            if (isScanning) {
                // Outer glow rect
                drawRoundRect(
                    color = Color(0xFF, 0xBC, 0x00).copy(alpha = 0.05f),
                    topLeft = Offset(rx, ry),
                    size = Size(rWidth, rHeight),
                    style = Stroke(width = 1.dp.toPx())
                )

                // Subsections / grid lines
                val gridRows = 5
                val gridCols = 5
                for (r in 1 until gridRows) {
                    val yVal = ry + (rHeight / gridRows) * r
                    drawLine(
                        color = Color(0xFF, 0xBC, 0x00).copy(alpha = 0.12f),
                        start = Offset(rx, yVal),
                        end = Offset(rx + rWidth, yVal),
                        strokeWidth = 1.dp.toPx()
                    )
                }
                for (c in 1 until gridCols) {
                    val xVal = rx + (rWidth / gridCols) * c
                    drawLine(
                        color = Color(0xFF, 0xBC, 0x00).copy(alpha = 0.12f),
                        start = Offset(xVal, ry),
                        end = Offset(xVal, ry + rHeight),
                        strokeWidth = 1.dp.toPx()
                    )
                }
            } else {
                // Subtle blue bounding frame line
                drawRect(
                    color = Color(0xFF, 0x70, 0x43).copy(alpha = 0.15f),
                    topLeft = Offset(rx, ry),
                    size = Size(rWidth, rHeight),
                    style = Stroke(width = 1.dp.toPx())
                )
            }

            // Center targeting cybernetic circular design
            drawCircle(color = themeAccent.copy(alpha = 0.4f), radius = 6.dp.toPx(), center = Offset(cx, cy))
            // Nested rotating rings or status rings
            drawCircle(
                color = themeAccent.copy(alpha = 0.2f),
                radius = 35.dp.toPx(),
                center = Offset(cx, cy),
                style = Stroke(width = 1.5.dp.toPx())
            )
            drawCircle(
                color = themeAccent.copy(alpha = 0.1f),
                radius = 55.dp.toPx(),
                center = Offset(cx, cy),
                style = Stroke(width = 1.dp.toPx())
            )

            // Animated status ticks inside reticle
            if (isScanning) {
                val ticksCount = 8
                val radiusInner = 20.dp.toPx()
                val radiusOuter = 26.dp.toPx()
                val sweepRotationDeg = (scanProgress * 360f) % 360f
                for (t in 0 until ticksCount) {
                    val angleRad = Math.toRadians((t * (360f / ticksCount) + sweepRotationDeg).toDouble())
                    val scanCos = Math.cos(angleRad).toFloat()
                    val scanSin = Math.sin(angleRad).toFloat()
                    drawLine(
                        color = Color(0xFF, 0xBC, 0x00),
                        start = Offset(cx + radiusInner * scanCos, cy + radiusInner * scanSin),
                        end = Offset(cx + radiusOuter * scanCos, cy + radiusOuter * scanSin),
                        strokeWidth = 2.dp.toPx()
                    )
                }
            }

            // Simulated Green Laser swipe/bar sweep animation across the screen
            if (isScanning) {
                val laserYOffset = ry + rHeight * laserY
                
                // Outer blooming neon laser flare
                drawLine(
                    color = Color(0xFF, 0xBC, 0x00).copy(alpha = 0.35f),
                    start = Offset(rx - 8f, laserYOffset),
                    end = Offset(rx + rWidth + 8f, laserYOffset),
                    strokeWidth = 14.dp.toPx()
                )
                // Middle intense green laser glow
                drawLine(
                    color = Color(0xFF, 0xBC, 0x00).copy(alpha = 0.70f),
                    start = Offset(rx - 4f, laserYOffset),
                    end = Offset(rx + rWidth + 4f, laserYOffset),
                    strokeWidth = 6.dp.toPx()
                )
                // Inner pure core laser beam
                drawLine(
                    color = Color.White,
                    start = Offset(rx, laserYOffset),
                    end = Offset(rx + rWidth, laserYOffset),
                    strokeWidth = 1.5.dp.toPx()
                )
            }
        }

        // 2. Interactive holographic floating text indicators inside the bounds
        if (isScanning) {
            Column(
                modifier = Modifier
                    .align(Alignment.Center)
                    .offset(y = (-110).dp),
                horizontalAlignment = Alignment.CenterHorizontally
            ) {
                Text(
                    text = "ACTIVE DEPTH EXTRACTION",
                    color = Color(0xFF, 0xBC, 0x00),
                    fontWeight = FontWeight.Bold,
                    fontSize = 11.sp,
                    fontFamily = FontFamily.Monospace,
                    letterSpacing = 1.5.sp
                )
                Spacer(modifier = Modifier.height(6.dp))
                
                // Loading dots component
                LoadingDots(
                    color = Color(0xFF, 0xBC, 0x00),
                    modifier = Modifier.padding(top = 4.dp)
                )
            }
        }
    }
}

@Composable
fun LoadingDots(
    color: Color,
    modifier: Modifier = Modifier
) {
    val dotsCount = 4
    val dotAnimations = List(dotsCount) { index ->
        val infiniteTransition = rememberInfiniteTransition(label = "dot_$index")
        infiniteTransition.animateFloat(
            initialValue = 0.2f,
            targetValue = 1f,
            animationSpec = infiniteRepeatable(
                animation = keyframes {
                    durationMillis = 800
                    0.2f at index * 150 with FastOutSlowInEasing
                    1f at (index * 150 + 250).coerceAtMost(799) with FastOutSlowInEasing
                    0.2f at (index * 150 + 500).coerceAtMost(800) with FastOutSlowInEasing
                },
                repeatMode = RepeatMode.Restart
            ),
            label = "dot_alpha_$index"
        )
    }

    Row(
        modifier = modifier,
        horizontalArrangement = Arrangement.spacedBy(6.dp),
        verticalAlignment = Alignment.CenterVertically
    ) {
        dotAnimations.forEach { animState ->
            Box(
                modifier = Modifier
                    .size(6.dp)
                    .background(color.copy(alpha = animState.value), shape = CircleShape)
            )
        }
    }
}
