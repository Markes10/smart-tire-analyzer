package com.example.ui.screens

import android.text.format.DateFormat
import android.widget.Toast
import android.graphics.Paint
import android.graphics.Typeface
import androidx.compose.animation.*
import androidx.compose.foundation.*
import androidx.compose.foundation.gestures.detectTapGestures
import androidx.compose.ui.input.pointer.pointerInput
import com.example.ui.components.TelemetryTooltipDialog
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material.icons.outlined.Delete
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.graphics.nativeCanvas
import androidx.compose.ui.graphics.toArgb
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.graphics.PathEffect
import com.example.ui.theme.StatusCritical
import com.example.ui.theme.StatusInfo
import com.example.ui.theme.StatusSuccess
import com.example.ui.theme.StatusWarning
import com.example.data.TireScan
import com.example.viewmodel.TireTwinViewModel
import java.util.Calendar

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun HistoryScreen(
    viewModel: TireTwinViewModel,
    onNavigateBack: () -> Unit,
    onNavigateToHome: () -> Unit
) {
    val context = LocalContext.current
    val historyScans by viewModel.historyScans.collectAsState()
    val useMetric by viewModel.useMetricUnits.collectAsState()
    var selectedTab by remember { mutableStateOf(0) }

    Scaffold(
        topBar = {
            TopAppBar(
                title = {
                    Text(
                        text = "DEGRADATION TRACKER",
                        style = LocalTextStyle.current.copy(
                            fontFamily = FontFamily.Monospace,
                            fontWeight = FontWeight.Bold,
                            fontSize = 15.sp,
                            letterSpacing = 1.5.sp,
                            color = MaterialTheme.colorScheme.onSurface
                        )
                    )
                },
                navigationIcon = {
                    IconButton(
                        onClick = onNavigateBack,
                        modifier = Modifier.testTag("history_back_button")
                    ) {
                        Icon(
                            imageVector = Icons.Default.ArrowBack,
                            contentDescription = "Return",
                            tint = MaterialTheme.colorScheme.onSurface
                        )
                    }
                },
                colors = TopAppBarDefaults.topAppBarColors(
                    containerColor = MaterialTheme.colorScheme.surface,
                    titleContentColor = MaterialTheme.colorScheme.onSurface
                )
            )
        },
        containerColor = MaterialTheme.colorScheme.background
    ) { paddingValues ->
        if (historyScans.isEmpty()) {
            Box(
                modifier = Modifier
                    .fillMaxSize()
                    .padding(paddingValues)
                    .background(MaterialTheme.colorScheme.background)
                    .padding(24.dp),
                contentAlignment = Alignment.Center
            ) {
                Column(
                    horizontalAlignment = Alignment.CenterHorizontally,
                    verticalArrangement = Arrangement.spacedBy(16.dp),
                    modifier = Modifier.fillMaxWidth()
                ) {
                    Box(
                        modifier = Modifier
                            .size(70.dp)
                            .background(MaterialTheme.colorScheme.surfaceVariant, CircleShape),
                        contentAlignment = Alignment.Center
                    ) {
                        Icon(
                            imageVector = Icons.Default.HistoryToggleOff,
                            contentDescription = "Empty History",
                            tint = MaterialTheme.colorScheme.onSurfaceVariant.copy(alpha = 0.6f),
                            modifier = Modifier.size(36.dp)
                        )
                    }

                    Text(
                        text = "NO DIAGNOSTIC LOGS YET",
                        color = MaterialTheme.colorScheme.onSurface,
                        fontSize = 13.sp,
                        fontFamily = FontFamily.Monospace,
                        fontWeight = FontWeight.Bold,
                        letterSpacing = 1.sp
                    )

                    Text(
                        text = "Click 'Scan Profile' with the camera scanner on HomeScreen to observe tire wear degradation cycles across trips.",
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                        fontSize = 11.sp,
                        textAlign = TextAlign.Center,
                        lineHeight = 16.sp,
                        modifier = Modifier.widthIn(max = 280.dp)
                    )

                    Button(
                        onClick = {
                            // Seed demo logs to quickly populated and facilitate testing
                            viewModel.seedDemoData()
                            Toast.makeText(context, "Seeded past wear profiles successfully!", Toast.LENGTH_SHORT).show()
                        },
                        colors = ButtonDefaults.buttonColors(
                            containerColor = MaterialTheme.colorScheme.surfaceVariant,
                            contentColor = MaterialTheme.colorScheme.primary
                        ),
                        border = BorderStroke(1.dp, MaterialTheme.colorScheme.outline.copy(alpha = 0.3f)),
                        shape = RoundedCornerShape(8.dp)
                    ) {
                        Text("SEED HISTORICAL CYCLES", fontSize = 11.sp, fontFamily = FontFamily.Monospace)
                    }
                }
            }
        } else {
            Column(
                modifier = Modifier
                    .fillMaxSize()
                    .padding(paddingValues)
                    .background(MaterialTheme.colorScheme.background)
            ) {
                // Sleek futuristic selection tabs
                TabRow(
                    selectedTabIndex = selectedTab,
                    containerColor = MaterialTheme.colorScheme.surface,
                    contentColor = MaterialTheme.colorScheme.primary,
                    modifier = Modifier.fillMaxWidth().testTag("history_tab_row")
                ) {
                    Tab(
                        selected = selectedTab == 0,
                        onClick = { selectedTab = 0 },
                        text = { Text("DIAGNOSTICS LOG", fontSize = 11.sp, fontFamily = FontFamily.Monospace, fontWeight = FontWeight.Bold) },
                        icon = { Icon(Icons.Default.List, contentDescription = "Log List") },
                        modifier = Modifier.testTag("tab_diagnostics_list")
                    )
                    Tab(
                        selected = selectedTab == 1,
                        onClick = { selectedTab = 1 },
                        text = { Text("ROUTE GEOMAP", fontSize = 11.sp, fontFamily = FontFamily.Monospace, fontWeight = FontWeight.Bold) },
                        icon = { Icon(Icons.Default.Map, contentDescription = "Map tracking due to scan history") },
                        modifier = Modifier.testTag("tab_route_geomap")
                    )
                    Tab(
                        selected = selectedTab == 2,
                        onClick = { selectedTab = 2 },
                        text = { Text("THERMAL COMPARISON", fontSize = 11.sp, fontFamily = FontFamily.Monospace, fontWeight = FontWeight.Bold) },
                        icon = { Icon(Icons.Default.Compare, contentDescription = "Compare thermal profiles") },
                        modifier = Modifier.testTag("tab_thermal_comparison")
                    )
                }

                when (selectedTab) {
                    0 -> {
                        // Header help tip
                        Box(
                            modifier = Modifier
                                .fillMaxWidth()
                                .padding(horizontal = 16.dp, vertical = 8.dp)
                                .background(MaterialTheme.colorScheme.surface, RoundedCornerShape(8.dp))
                                .border(0.5.dp, MaterialTheme.colorScheme.outline.copy(alpha = 0.15f), RoundedCornerShape(8.dp))
                                .padding(12.dp)
                        ) {
                            Row(
                                verticalAlignment = Alignment.CenterVertically,
                                horizontalArrangement = Arrangement.spacedBy(10.dp)
                            ) {
                                Icon(
                                    imageVector = Icons.Default.Info,
                                    contentDescription = "info",
                                    tint = MaterialTheme.colorScheme.primary,
                                    modifier = Modifier.size(16.dp)
                                )
                                Text(
                                    text = "Select any past log item to restore the 3D main canvas model to that profile’s specifications. Let's observe deterioration rates over months.",
                                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                                    fontSize = 10.5.sp,
                                    lineHeight = 15.sp,
                                    modifier = Modifier.weight(1f)
                                )
                            }
                        }

                        // Scrollable List
                        LazyColumn(
                            modifier = Modifier
                                .fillMaxSize()
                                .weight(1f)
                                .testTag("history_list"),
                            contentPadding = PaddingValues(horizontal = 16.dp, vertical = 8.dp),
                            verticalArrangement = Arrangement.spacedBy(12.dp)
                        ) {
                            item {
                                TrendLineChart(scans = historyScans)
                            }

                            item {
                                TireWearProjectionChart(scans = historyScans)
                            }

                            items(historyScans, key = { it.id }) { scan ->
                                HistoryScanItem(
                                    scan = scan,
                                    useMetric = useMetric,
                                    onSelect = {
                                        viewModel.loadHistoricalScan(scan)
                                        Toast.makeText(context, "Twin loaded: ${scan.title}", Toast.LENGTH_SHORT).show()
                                        onNavigateToHome() // Route back to see the restored model
                                    },
                                    onDelete = {
                                        viewModel.deleteScan(scan.id)
                                        Toast.makeText(context, "Log removed", Toast.LENGTH_SHORT).show()
                                    }
                                )
                            }
                        }
                    }
                    1 -> {
                        GeographicRouteMap(
                            scans = historyScans,
                            onSelectScan = { scan ->
                                viewModel.loadHistoricalScan(scan)
                                onNavigateToHome()
                            },
                            context = context
                        )
                    }
                    2 -> {
                        ThermalComparisonView(
                            viewModel = viewModel,
                            historyScans = historyScans,
                            onNavigateToHome = onNavigateToHome
                        )
                    }
                }
            }
        }
    }
}

@Composable
fun HistoryScanItem(
    scan: TireScan,
    useMetric: Boolean = false,
    onSelect: () -> Unit,
    onDelete: () -> Unit
) {
    val dateString = remember(scan.timestamp) {
        val cal = Calendar.getInstance().apply { timeInMillis = scan.timestamp }
        DateFormat.format("MMM dd, yyyy · hh:mm a", cal).toString()
    }

    Card(
        modifier = Modifier
            .fillMaxWidth()
            .clickable(onClick = onSelect)
            .testTag("history_item_${scan.id}"),
        shape = RoundedCornerShape(12.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
        border = BorderStroke(1.dp, MaterialTheme.colorScheme.outline.copy(alpha = 0.15f))
    ) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(14.dp),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.SpaceBetween
        ) {
            Column(modifier = Modifier.weight(1f)) {
                // Name and timestamp
                Row(
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    Box(
                        modifier = Modifier
                            .background(evaluateHealthColor(scan.overallHealth).copy(alpha = 0.15f), RoundedCornerShape(4.dp))
                            .border(0.5.dp, evaluateHealthColor(scan.overallHealth).copy(alpha = 0.6f), RoundedCornerShape(4.dp))
                            .padding(horizontal = 6.dp, vertical = 2.dp)
                    ) {
                        Text(
                            text = "${scan.overallHealth}%",
                            color = evaluateHealthColor(scan.overallHealth),
                            fontSize = 11.sp,
                            fontWeight = FontWeight.Bold,
                            fontFamily = FontFamily.Monospace
                        )
                    }

                    Text(
                        text = scan.title,
                        color = MaterialTheme.colorScheme.onSurface,
                        fontSize = 14.sp,
                        fontWeight = FontWeight.SemiBold,
                        maxLines = 1,
                        overflow = TextOverflow.Ellipsis
                    )
                }

                Spacer(modifier = Modifier.height(4.dp))

                Text(
                    text = dateString,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                    fontSize = 11.sp
                )

                Spacer(modifier = Modifier.height(8.dp))

                // Diagnostic metrics indicators row
                Row(
                    horizontalArrangement = Arrangement.spacedBy(14.dp),
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    MetricIndicator(
                        icon = Icons.Default.Speed,
                        value = if (useMetric) "${scan.speed.toInt()} km/h" else "${(scan.speed * 0.621f).toInt()} mph"
                    )
                    MetricIndicator(
                        icon = Icons.Default.CompassCalibration,
                        value = if (useMetric) "${(scan.pressure * 0.0689f).toInt()} BAR" else "${scan.pressure.toInt()} PSI"
                    )
                    MetricIndicator(
                        icon = Icons.Default.DeviceThermostat,
                        value = if (useMetric) "${scan.temperature.toInt()}°C" else "${(scan.temperature * 9 / 5 + 32).toInt()}°F"
                    )
                }

                Spacer(modifier = Modifier.height(8.dp))

                // Degradation Wear Pattern Tag
                Box(
                    modifier = Modifier
                        .background(MaterialTheme.colorScheme.background, RoundedCornerShape(4.dp))
                        .padding(horizontal = 8.dp, vertical = 4.dp)
                ) {
                    Text(
                        text = "PATTERN: ${scan.wearPattern.uppercase()}",
                        color = MaterialTheme.colorScheme.primary,
                        fontSize = 9.sp,
                        fontFamily = FontFamily.Monospace,
                        fontWeight = FontWeight.Bold
                    )
                }
            }

            // Right actions column
            IconButton(
                onClick = onDelete,
                modifier = Modifier
                    .testTag("delete_scan_btn_${scan.id}")
                    .padding(start = 8.dp)
            ) {
                Icon(
                    imageVector = Icons.Outlined.Delete,
                    contentDescription = "Remove Log",
                    tint = Color(0xFF, 0x4B, 0x4B).copy(alpha = 0.8f)
                )
            }
        }
    }
}

@Composable
fun MetricIndicator(
    icon: androidx.compose.ui.graphics.vector.ImageVector,
    value: String
) {
    Row(
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(4.dp)
    ) {
        Icon(
            imageVector = icon,
            contentDescription = null,
            tint = MaterialTheme.colorScheme.onSurfaceVariant,
            modifier = Modifier.size(12.dp)
        )
        Text(
            text = value,
            color = MaterialTheme.colorScheme.onSurface,
            fontSize = 11.sp,
            fontFamily = FontFamily.Monospace
        )
    }
}

@Composable
fun TrendLineChart(scans: List<TireScan>) {
    if (scans.isEmpty()) return

    var selectedFilter by remember { mutableStateOf("30-DAY") }
    var tooltipToShow by remember { mutableStateOf<Pair<String, String>?>(null) }

    val chartData = remember(scans, selectedFilter) {
        val now = System.currentTimeMillis()
        val thirtyDaysAgo = now - 30L * 24 * 60 * 60 * 1000
        val filtered = when (selectedFilter) {
            "30-DAY" -> scans.filter { it.timestamp >= thirtyDaysAgo }
            "ALL CYCLES" -> scans
            "HIGH TEMP" -> scans.filter { it.temperature > 50f || it.pressure < 28f || it.speed > 90f }
            "WEAR DEFECT" -> scans.filter { it.overallHealth < 80 || it.wearPattern != "Normal" }
            else -> scans
        }
        if (filtered.size >= 2) {
            filtered.sortedBy { it.timestamp }
        } else {
            scans.sortedBy { it.timestamp }
        }
    }

    if (chartData.isEmpty()) return

    // Dynamic rising coordinate animation trigger on layout transition
    var animationProgress by remember { mutableStateOf(0f) }
    LaunchedEffect(selectedFilter, scans.size) {
        animationProgress = 0f
        androidx.compose.animation.core.animate(
            initialValue = 0f,
            targetValue = 1f,
            animationSpec = androidx.compose.animation.core.tween(
                durationMillis = 650,
                easing = androidx.compose.animation.core.LinearOutSlowInEasing
            )
        ) { value, _ ->
            animationProgress = value
        }
    }

    val currentTitle = when (selectedFilter) {
        "30-DAY" -> "30-DAY TREND ANALYTICS"
        "ALL CYCLES" -> "ALL CYCLES GRAPH"
        "HIGH TEMP" -> "HIGH TEMPERATURE TRENDS"
        "WEAR DEFECT" -> "CRITICAL WEAR METRICS"
        else -> "TREND ANALYSIS"
    }

    Card(
        modifier = Modifier
            .fillMaxWidth()
            .padding(vertical = 4.dp)
            .testTag("historical_cycles_chart_card"),
        shape = RoundedCornerShape(12.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
        border = BorderStroke(1.dp, MaterialTheme.colorScheme.outline.copy(alpha = 0.15f))
    ) {
        Column(
            modifier = Modifier.padding(14.dp)
        ) {
            // Header Row
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text(
                    text = currentTitle,
                    color = MaterialTheme.colorScheme.primary,
                    fontSize = 11.sp,
                    fontFamily = FontFamily.Monospace,
                    fontWeight = FontWeight.Bold,
                    letterSpacing = 1.sp
                )
                Text(
                    text = "ACTIVE SYNAPSE",
                    color = Color(0x28, 0xB4, 0x82),
                    fontSize = 8.sp,
                    fontFamily = FontFamily.Monospace,
                    fontWeight = FontWeight.Bold
                )
            }

            Spacer(modifier = Modifier.height(8.dp))

            // Selector Chips Row
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(4.dp)
            ) {
                val filters = listOf("30-DAY", "ALL CYCLES", "HIGH TEMP", "WEAR DEFECT")
                filters.forEach { filter ->
                    val isActive = selectedFilter == filter
                    Box(
                        modifier = Modifier
                            .weight(1f)
                            .clip(RoundedCornerShape(6.dp))
                            .background(
                                if (isActive) MaterialTheme.colorScheme.primary.copy(alpha = 0.12f)
                                else MaterialTheme.colorScheme.background
                            )
                            .border(
                                width = 1.dp,
                                color = if (isActive) MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.outline.copy(alpha = 0.2f),
                                shape = RoundedCornerShape(6.dp)
                            )
                            .clickable { selectedFilter = filter }
                            .padding(vertical = 6.dp),
                        contentAlignment = Alignment.Center
                    ) {
                        Text(
                            text = filter,
                            color = if (isActive) MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.onSurfaceVariant,
                            fontSize = 8.sp,
                            fontWeight = FontWeight.Bold,
                            fontFamily = FontFamily.Monospace
                        )
                    }
                }
            }

            Spacer(modifier = Modifier.height(12.dp))

            // Legends Indicator Row
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(16.dp),
                verticalAlignment = Alignment.CenterVertically
            ) {
                // Pressure Legend
                Row(
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.spacedBy(5.dp),
                    modifier = Modifier.pointerInput(Unit) {
                        detectTapGestures(
                            onLongPress = {
                                tooltipToShow = Pair(
                                    "CHART LEGEND: PRESSURE",
                                    "Pressure level trend line graphed in dynamic cyan/green. Normal operational variance bounds hover securely around 32-35 PSI."
                                )
                            }
                        )
                    }
                ) {
                    Box(
                        modifier = Modifier
                            .size(7.dp)
                            .background(StatusSuccess, CircleShape)
                    )
                    Text(
                        text = "PRESSURE (PSI)",
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                        fontSize = 8.5.sp,
                        fontFamily = FontFamily.Monospace,
                        fontWeight = FontWeight.SemiBold
                    )
                }

                // Temp Legend
                Row(
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.spacedBy(5.dp),
                    modifier = Modifier.pointerInput(Unit) {
                        detectTapGestures(
                            onLongPress = {
                                tooltipToShow = Pair(
                                    "CHART LEGEND: TEMPERATURE",
                                    "Dynamic carcass thermal profile represented by the orange/red trend line. Temperatures exceeding 80°C indicate severe mechanical shear strain."
                                )
                            }
                        )
                    }
                ) {
                    Box(
                        modifier = Modifier
                            .size(7.dp)
                            .background(StatusWarning, CircleShape)
                    )
                    Text(
                        text = "TEMPERATURE (°C)",
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                        fontSize = 8.5.sp,
                        fontFamily = FontFamily.Monospace,
                        fontWeight = FontWeight.SemiBold
                    )
                }
            }

            Spacer(modifier = Modifier.height(14.dp))

            // The Chart Canvas
            val sdf = remember { java.text.SimpleDateFormat("MMM dd", java.util.Locale.US) }
            val minTime = chartData.first().timestamp
            val maxTime = chartData.last().timestamp
            val timeDiff = if (maxTime == minTime) 1L else (maxTime - minTime)

            val minPressure = remember(chartData) {
                (chartData.map { it.pressure }.minOrNull() ?: 15f).coerceAtMost(15f)
            }
            val maxPressure = remember(chartData) {
                (chartData.map { it.pressure }.maxOrNull() ?: 45f).coerceAtLeast(45f)
            }
            val minTemp = remember(chartData) {
                (chartData.map { it.temperature }.minOrNull() ?: 15f).coerceAtMost(15f)
            }
            val maxTemp = remember(chartData) {
                (chartData.map { it.temperature }.maxOrNull() ?: 90f).coerceAtLeast(90f)
            }

            val axisColor = MaterialTheme.colorScheme.outline.copy(alpha = 0.15f)
            val labelColor = MaterialTheme.colorScheme.onSurfaceVariant.toArgb()
            val dotInnerColor = MaterialTheme.colorScheme.surface

            Canvas(
                modifier = Modifier
                    .fillMaxWidth()
                    .height(140.dp)
            ) {
                val leftPx = 32.dp.toPx()
                val rightPx = size.width - 32.dp.toPx()
                val topPx = 8.dp.toPx()
                val bottomPx = size.height - 18.dp.toPx()

                val plotWidth = rightPx - leftPx
                val plotHeight = bottomPx - topPx

                // 1. Draw horizontal grid lines and value labels
                val gridLinesCount = 4
                for (i in 0 until gridLinesCount) {
                    val fraction = i.toFloat() / (gridLinesCount - 1)
                    val yGrid = bottomPx - fraction * plotHeight

                    // Grid line
                    drawLine(
                        color = axisColor,
                        start = Offset(leftPx, yGrid),
                        end = Offset(rightPx, yGrid),
                        strokeWidth = 1.dp.toPx()
                    )

                    // Left Label (Pressure scale)
                    val pValue = minPressure + fraction * (maxPressure - minPressure)
                    drawContext.canvas.nativeCanvas.apply {
                        val paint = Paint().apply {
                            color = labelColor
                            textSize = 8.dp.toPx()
                            typeface = Typeface.MONOSPACE
                            textAlign = Paint.Align.RIGHT
                        }
                        drawText(
                            "${pValue.toInt()}",
                            leftPx - 6.dp.toPx(),
                            yGrid + 3.dp.toPx(),
                            paint
                        )
                    }

                    // Right Label (Temperature scale)
                    val tValue = minTemp + fraction * (maxTemp - minTemp)
                    drawContext.canvas.nativeCanvas.apply {
                        val paint = Paint().apply {
                            color = labelColor
                            textSize = 8.dp.toPx()
                            typeface = Typeface.MONOSPACE
                            textAlign = Paint.Align.LEFT
                        }
                        drawText(
                            "${tValue.toInt()}°",
                            rightPx + 6.dp.toPx(),
                            yGrid + 3.dp.toPx(),
                            paint
                        )
                    }
                }

                // 2. Define coordinate lists
                val pressurePoints = mutableListOf<Offset>()
                val tempPoints = mutableListOf<Offset>()

                chartData.forEachIndexed { idx, scan ->
                    val t = scan.timestamp
                    val x = if (chartData.size > 1) {
                        leftPx + ((t - minTime).toFloat() / timeDiff.toFloat()) * plotWidth
                    } else {
                        leftPx + plotWidth * 0.5f
                    }

                    val yP = bottomPx - (((scan.pressure - minPressure) / (maxPressure - minPressure)) * plotHeight * animationProgress)
                    val yT = bottomPx - (((scan.temperature - minTemp) / (maxTemp - minTemp)) * plotHeight * animationProgress)

                    pressurePoints.add(Offset(x, yP))
                    tempPoints.add(Offset(x, yT))
                }

                // Draw curve lines if we have multiple points
                if (chartData.size > 1) {
                    val pPath = Path().apply {
                        pressurePoints.forEachIndexed { i, offset ->
                            if (i == 0) moveTo(offset.x, offset.y) else lineTo(offset.x, offset.y)
                        }
                    }
                    val tPath = Path().apply {
                        tempPoints.forEachIndexed { i, offset ->
                            if (i == 0) moveTo(offset.x, offset.y) else lineTo(offset.x, offset.y)
                        }
                    }

                    drawPath(
                        path = pPath,
                        color = StatusSuccess,
                        style = Stroke(width = 2.dp.toPx())
                    )
                    drawPath(
                        path = tPath,
                        color = StatusWarning,
                        style = Stroke(width = 2.dp.toPx())
                    )
                }

                // 3. Draw dot markers
                pressurePoints.forEach { center ->
                    drawCircle(color = StatusSuccess, radius = 3.5f.dp.toPx(), center = center)
                    drawCircle(color = dotInnerColor, radius = 1.8f.dp.toPx(), center = center)
                }
                tempPoints.forEach { center ->
                    drawCircle(color = StatusWarning, radius = 3.5f.dp.toPx(), center = center)
                    drawCircle(color = dotInnerColor, radius = 1.8f.dp.toPx(), center = center)
                }

                // 4. Draw labels on horizontal axis
                val firstDate = sdf.format(java.util.Date(minTime))
                val lastDate = sdf.format(java.util.Date(maxTime))
                val midDate = if (chartData.size >= 3) sdf.format(java.util.Date((minTime + maxTime) / 2)) else ""

                val paintX = Paint().apply {
                    color = labelColor
                    textSize = 8.dp.toPx()
                    typeface = Typeface.MONOSPACE
                }

                paintX.textAlign = Paint.Align.LEFT
                drawContext.canvas.nativeCanvas.drawText(
                    firstDate,
                    leftPx,
                    bottomPx + 14.dp.toPx(),
                    paintX
                )

                paintX.textAlign = Paint.Align.RIGHT
                drawContext.canvas.nativeCanvas.drawText(
                    lastDate,
                    rightPx,
                    bottomPx + 14.dp.toPx(),
                    paintX
                )

                if (midDate.isNotEmpty()) {
                    paintX.textAlign = Paint.Align.CENTER
                    drawContext.canvas.nativeCanvas.drawText(
                        midDate,
                        leftPx + plotWidth * 0.5f,
                        bottomPx + 14.dp.toPx(),
                        paintX
                    )
                }
            }
        }
    }

    // Modal dialogue popup rendering for tooltips
    tooltipToShow?.let { (title, explanation) ->
        TelemetryTooltipDialog(
            metricName = title,
            explanation = explanation,
            onDismiss = { tooltipToShow = null }
        )
    }
}

@Composable
fun GeographicRouteMap(
    scans: List<TireScan>,
    onSelectScan: (TireScan) -> Unit,
    context: android.content.Context
) {
    var selectedRoute by remember { mutableStateOf("All") }
    val routes = remember(scans) {
        listOf("All") + scans.map { it.routeName }.distinct()
    }

    val filteredScans = remember(scans, selectedRoute) {
        if (selectedRoute == "All") scans else scans.filter { it.routeName == selectedRoute }
    }

    // Active hovered/tapped scan on map
    var activeScanOnMap by remember(filteredScans) {
        mutableStateOf<TireScan?>(filteredScans.firstOrNull())
    }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(16.dp)
            .testTag("geo_route_map_container"),
        verticalArrangement = Arrangement.spacedBy(12.dp)
    ) {
        // Route Filters Row
        Row(
            modifier = Modifier.fillMaxWidth().horizontalScroll(rememberScrollState()),
            horizontalArrangement = Arrangement.spacedBy(8.dp)
        ) {
            routes.forEach { r ->
                RouteFilterChip(
                    selected = selectedRoute == r,
                    onClick = { selectedRoute = r },
                    label = r
                )
            }
        }

        // Canvas Map Container
        Box(
            modifier = Modifier
                .fillMaxWidth()
                .weight(1f)
                .background(
                    color = MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.15f),
                    shape = RoundedCornerShape(16.dp)
                )
                .border(1.dp, MaterialTheme.colorScheme.outline.copy(alpha = 0.2f), RoundedCornerShape(16.dp))
                .clip(RoundedCornerShape(16.dp))
        ) {
            // Drawn Coordinate Grid and Routes with Canvas
            if (filteredScans.isEmpty()) {
                Box(modifier = Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                    Text("No geoposition logs matched for route.", style = MaterialTheme.typography.bodyMedium)
                }
            } else {
                val minLat = remember(scans) { scans.minOfOrNull { it.latitude } ?: 32.0 }
                val maxLat = remember(scans) { scans.maxOfOrNull { it.latitude } ?: 38.0 }
                val minLng = remember(scans) { scans.minOfOrNull { it.longitude } ?: -123.0 }
                val maxLng = remember(scans) { scans.maxOfOrNull { it.longitude } ?: -115.0 }

                val latRange = remember(minLat, maxLat) { (maxLat - minLat).coerceAtLeast(0.001) }
                val lngRange = remember(minLng, maxLng) { (maxLng - minLng).coerceAtLeast(0.001) }

                // Keep local references for point calculations
                var pointsMapped by remember { mutableStateOf<List<Pair<TireScan, Offset>>>(emptyList()) }
                
                val primaryColor = MaterialTheme.colorScheme.primary
                val tertiaryColor = MaterialTheme.colorScheme.tertiary

                Canvas(
                    modifier = Modifier
                        .fillMaxSize()
                        .pointerInput(filteredScans) {
                            detectTapGestures { offset ->
                                // Detect if user clicked near any pin (radius of 30px)
                                val hit = pointsMapped.minByOrNull { (_, pt) ->
                                    val dx = pt.x - offset.x
                                    val dy = pt.y - offset.y
                                    dx * dx + dy * dy
                                }
                                if (hit != null) {
                                    val dx = hit.second.x - offset.x
                                    val dy = hit.second.y - offset.y
                                    if ((dx * dx + dy * dy) < 2500f) {
                                        activeScanOnMap = hit.first
                                    }
                                }
                            }
                        }
                ) {
                    // Draw modern digital tech background grid
                    val gridSpacing = 40.dp.toPx()
                    val gridWidth = size.width
                    val gridHeight = size.height

                    var currX = 0f
                    while (currX < gridWidth) {
                        drawLine(
                            color = primaryColor.copy(alpha = 0.05f),
                            start = Offset(currX, 0f),
                            end = Offset(currX, gridHeight),
                            strokeWidth = 1f
                        )
                        currX += gridSpacing
                    }

                    var currY = 0f
                    while (currY < gridHeight) {
                        drawLine(
                            color = primaryColor.copy(alpha = 0.05f),
                            start = Offset(0f, currY),
                            end = Offset(gridWidth, currY),
                            strokeWidth = 1f
                        )
                        currY += gridSpacing
                    }

                    // Map all scans of active route to local screen points (with padding to keep inside boundaries)
                    val pLeft = 80f
                    val pRight = 80f
                    val pTop = 80f
                    val pBottom = 80f
                    val uW = size.width - pLeft - pRight
                    val uH = size.height - pTop - pBottom

                    val computedPoints = filteredScans.map { s ->
                        val px = pLeft + ((s.longitude - minLng) / lngRange * uW).toFloat()
                        // Invert Y axes because top increases downwards
                        val py = pTop + ((1.0 - (s.latitude - minLat) / latRange) * uH).toFloat()
                        s to Offset(px, py)
                    }
                    pointsMapped = computedPoints

                    // Draw Trip Route lines grouped by routeName
                    val routesGrouped = computedPoints.groupBy { it.first.routeName }
                    routesGrouped.forEach { (_, rPoints) ->
                        val sortedPoints = rPoints.sortedBy { it.first.timestamp }
                        if (sortedPoints.size > 1) {
                            val routePath = Path()
                            sortedPoints.forEachIndexed { idx, (_, offset) ->
                                if (idx == 0) {
                                    routePath.moveTo(offset.x, offset.y)
                                } else {
                                    routePath.lineTo(offset.x, offset.y)
                                }
                            }

                            // Outline of the route with glowing vector neon trail
                            drawPath(
                                path = routePath,
                                color = primaryColor.copy(alpha = 0.4f),
                                style = Stroke(width = 4.dp.toPx())
                            )
                            drawPath(
                                path = routePath,
                                color = tertiaryColor.copy(alpha = 0.15f),
                                style = Stroke(width = 8.dp.toPx())
                            )
                        }
                    }

                    // Draw waypoint Pin markers with overall health color rings
                    computedPoints.forEach { (scan, pt) ->
                        val isHovered = activeScanOnMap == scan
                        val markerColor = evaluateHealthColor(scan.overallHealth)

                        // Outer pulsing glow if active selection
                        if (isHovered) {
                            drawCircle(
                                color = markerColor.copy(alpha = 0.25f),
                                radius = 20.dp.toPx(),
                                center = pt
                            )
                        }

                        // Outline Ring
                        drawCircle(
                            color = if (isHovered) Color.White else markerColor,
                            radius = 11.dp.toPx(),
                            center = pt
                        )

                        // Inner Dot
                        drawCircle(
                            color = if (isHovered) markerColor else Color(0xFF1E1E2E),
                            radius = 6.dp.toPx(),
                            center = pt
                        )
                    }
                }

                // Superimposed mini floating Route Map legend
                Box(
                    modifier = Modifier
                        .align(Alignment.TopEnd)
                        .padding(12.dp)
                        .background(MaterialTheme.colorScheme.surface.copy(alpha = 0.85f), RoundedCornerShape(8.dp))
                        .border(0.5.dp, MaterialTheme.colorScheme.outline.copy(alpha = 0.2f), RoundedCornerShape(8.dp))
                        .padding(horizontal = 10.dp, vertical = 6.dp)
                ) {
                    Column(verticalArrangement = Arrangement.spacedBy(4.dp)) {
                        Text("ROUTE COND.", fontSize = 9.sp, fontWeight = FontWeight.Black, fontFamily = FontFamily.Monospace, color = MaterialTheme.colorScheme.onSurfaceVariant)
                        Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                            Box(modifier = Modifier.size(7.dp).background(Color(0xFF50FA7B), CircleShape))
                            Text("Safe (>85%)", fontSize = 8.sp, fontFamily = FontFamily.Monospace, color = MaterialTheme.colorScheme.onSurface)
                        }
                        Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                            Box(modifier = Modifier.size(7.dp).background(Color(0xFFFFB86C), CircleShape))
                            Text("Caution (70-85%)", fontSize = 8.sp, fontFamily = FontFamily.Monospace, color = MaterialTheme.colorScheme.onSurface)
                        }
                        Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                            Box(modifier = Modifier.size(7.dp).background(Color(0xFFFF5555), CircleShape))
                            Text("Warning (<70%)", fontSize = 8.sp, fontFamily = FontFamily.Monospace, color = MaterialTheme.colorScheme.onSurface)
                        }
                    }
                }
            }
        }

        // Selected Pin Detail HUD Card
        activeScanOnMap?.let { scan ->
            Card(
                modifier = Modifier
                    .fillMaxWidth()
                    .testTag("route_map_active_card"),
                shape = RoundedCornerShape(12.dp),
                colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
                border = BorderStroke(1.dp, MaterialTheme.colorScheme.outline.copy(alpha = 0.2f))
            ) {
                Column(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(14.dp)
                ) {
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Column(modifier = Modifier.weight(1f)) {
                            Row(
                                verticalAlignment = Alignment.CenterVertically,
                                horizontalArrangement = Arrangement.spacedBy(8.dp)
                            ) {
                                Box(
                                    modifier = Modifier
                                        .background(evaluateHealthColor(scan.overallHealth).copy(alpha = 0.15f), RoundedCornerShape(4.dp))
                                        .border(0.5.dp, evaluateHealthColor(scan.overallHealth).copy(alpha = 0.6f), RoundedCornerShape(4.dp))
                                        .padding(horizontal = 6.dp, vertical = 2.dp)
                                ) {
                                    Text(
                                        text = "${scan.overallHealth}% Health",
                                        color = evaluateHealthColor(scan.overallHealth),
                                        fontSize = 11.sp,
                                        fontWeight = FontWeight.Bold,
                                        fontFamily = FontFamily.Monospace
                                    )
                                }
                                Text(
                                    text = scan.routeName.uppercase(),
                                    style = MaterialTheme.typography.labelSmall,
                                    fontFamily = FontFamily.Monospace,
                                    color = MaterialTheme.colorScheme.primary
                                )
                            }
                            Spacer(modifier = Modifier.height(4.dp))
                            Text(
                                text = scan.title,
                                style = MaterialTheme.typography.titleSmall,
                                fontWeight = FontWeight.Bold,
                                color = MaterialTheme.colorScheme.onSurface
                            )
                        }

                        // Restore digital twin configuration CTA
                        Button(
                            onClick = {
                                onSelectScan(scan)
                                Toast.makeText(context, "Twin restored to geographic scan!", Toast.LENGTH_SHORT).show()
                            },
                            contentPadding = PaddingValues(horizontal = 12.dp, vertical = 6.dp),
                            shape = RoundedCornerShape(8.dp),
                            colors = ButtonDefaults.buttonColors(
                                containerColor = MaterialTheme.colorScheme.primary,
                                contentColor = MaterialTheme.colorScheme.onPrimary
                            )
                        ) {
                            Text("TEST CONFIG", fontSize = 10.sp, fontFamily = FontFamily.Monospace, fontWeight = FontWeight.Bold)
                        }
                    }

                    // Separation Line
                    Box(
                        modifier = Modifier
                            .fillMaxWidth()
                            .height(1.dp)
                            .background(MaterialTheme.colorScheme.outline.copy(alpha = 0.15f))
                            .padding(vertical = 10.dp)
                    )

                    Spacer(modifier = Modifier.height(8.dp))

                    // Location summary detail values
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween
                    ) {
                        MapDetailField(label = "LATITUDE", value = "%.4f".format(scan.latitude))
                        MapDetailField(label = "LONGITUDE", value = "%.4f".format(scan.longitude))
                        MapDetailField(label = "VELOCITY", value = "${scan.speed.toInt()} km/h")
                        MapDetailField(label = "PRESSURE", value = "${scan.pressure.toInt()} PSI")
                    }
                }
            }
        }
    }
}

@Composable
fun RouteFilterChip(
    selected: Boolean,
    onClick: () -> Unit,
    label: String
) {
    Box(
        modifier = Modifier
            .clip(RoundedCornerShape(8.dp))
            .background(
                if (selected) {
                    MaterialTheme.colorScheme.primary.copy(alpha = 0.25f)
                } else {
                    MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.3f)
                }
            )
            .border(
                1.dp,
                if (selected) MaterialTheme.colorScheme.primary else Color.Gray.copy(alpha = 0.2f),
                RoundedCornerShape(8.dp)
            )
            .clickable(onClick = onClick)
            .padding(horizontal = 12.dp, vertical = 6.dp)
            .testTag("route_filter_chip_${label.lowercase().replace(" ", "_")}")
    ) {
        Text(
            text = label,
            fontSize = 11.sp,
            fontFamily = FontFamily.Monospace,
            fontWeight = if (selected) FontWeight.Bold else FontWeight.Medium,
            color = if (selected) MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.onSurfaceVariant
        )
    }
}

@Composable
fun MapDetailField(label: String, value: String) {
    Column {
        Text(
            text = label,
            fontSize = 8.sp,
            fontFamily = FontFamily.Monospace,
            fontWeight = FontWeight.Bold,
            color = MaterialTheme.colorScheme.onSurfaceVariant.copy(alpha = 0.7f)
        )
        Text(
            text = value,
            fontSize = 12.sp,
            fontFamily = FontFamily.Monospace,
            fontWeight = FontWeight.SemiBold,
            color = MaterialTheme.colorScheme.onSurface
        )
    }
}

@Composable
fun TireWearProjectionChart(scans: List<TireScan>) {
    val latestHealth = remember(scans) {
        scans.firstOrNull()?.overallHealth ?: 90
    }

    var selectedProjectionMode by remember { mutableStateOf("ALL") }

    var animationProgress by remember { mutableStateOf(0f) }
    LaunchedEffect(selectedProjectionMode) {
        animationProgress = 0f
        androidx.compose.animation.core.animate(
            initialValue = 0f,
            targetValue = 1f,
            animationSpec = androidx.compose.animation.core.tween(
                durationMillis = 600,
                easing = androidx.compose.animation.core.LinearOutSlowInEasing
            )
        ) { value, _ ->
            animationProgress = value
        }
    }

    Card(
        modifier = Modifier
            .fillMaxWidth()
            .padding(vertical = 4.dp)
            .testTag("wear_projection_chart_card"),
        shape = RoundedCornerShape(12.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
        border = BorderStroke(1.dp, MaterialTheme.colorScheme.outline.copy(alpha = 0.15f))
    ) {
        Column(modifier = Modifier.padding(14.dp)) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text(
                    text = "AI WEAR PROJECTION (10,000 KM)",
                    color = MaterialTheme.colorScheme.primary,
                    fontSize = 11.sp,
                    fontFamily = FontFamily.Monospace,
                    fontWeight = FontWeight.Bold,
                    letterSpacing = 1.sp
                )
                Text(
                    text = "PROGNOSTIC LABS",
                    color = MaterialTheme.colorScheme.primary,
                    fontSize = 8.sp,
                    fontFamily = FontFamily.Monospace,
                    fontWeight = FontWeight.Bold
                )
            }

            Spacer(modifier = Modifier.height(6.dp))
            Text(
                text = "Continuous predictive models representing tread compound degradation based on stress vectors.",
                color = MaterialTheme.colorScheme.onSurfaceVariant.copy(alpha = 0.7f),
                fontSize = 9.sp,
                lineHeight = 13.sp
            )

            Spacer(modifier = Modifier.height(10.dp))

            // Selector row
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(4.dp)
            ) {
                val filters = listOf("ALL", "NOMINAL", "LOW PRESSURE", "THERMAL")
                filters.forEach { mode ->
                    val isActive = selectedProjectionMode == mode
                    Box(
                        modifier = Modifier
                            .weight(1f)
                            .clip(RoundedCornerShape(6.dp))
                            .background(
                                if (isActive) MaterialTheme.colorScheme.primary.copy(alpha = 0.12f)
                                else MaterialTheme.colorScheme.background
                            )
                            .border(
                                width = 1.dp,
                                color = if (isActive) MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.outline.copy(alpha = 0.2f),
                                shape = RoundedCornerShape(6.dp)
                            )
                            .clickable { selectedProjectionMode = mode }
                            .padding(vertical = 6.dp),
                        contentAlignment = Alignment.Center
                    ) {
                        Text(
                            text = mode,
                            color = if (isActive) MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.onSurfaceVariant,
                            fontSize = 8.sp,
                            fontWeight = FontWeight.Bold,
                            fontFamily = FontFamily.Monospace
                        )
                    }
                }
            }

            Spacer(modifier = Modifier.height(12.dp))

            // Legends Indicators
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(16.dp),
                verticalAlignment = Alignment.CenterVertically
            ) {
                if (selectedProjectionMode == "ALL" || selectedProjectionMode == "NOMINAL") {
                    LegendItemProjection(color = Color(0xFF50FA7B), label = "Nominal Load")
                }
                if (selectedProjectionMode == "ALL" || selectedProjectionMode == "LOW PRESSURE") {
                    LegendItemProjection(color = Color(0xFFFFB86C), label = "Low-PSI Stress")
                }
                if (selectedProjectionMode == "ALL" || selectedProjectionMode == "THERMAL") {
                    LegendItemProjection(color = Color(0xFFFF5555), label = "Thermal Overload")
                }
            }

            Spacer(modifier = Modifier.height(12.dp))

            // Canvas drawing
            Canvas(
                modifier = Modifier
                    .fillMaxWidth()
                    .height(130.dp)
            ) {
                val leftPx = 32.dp.toPx()
                val rightPx = size.width - 24.dp.toPx()
                val topPx = 10.dp.toPx()
                val bottomPx = size.height - 18.dp.toPx()

                val plotWidth = rightPx - leftPx
                val plotHeight = bottomPx - topPx

                val axisColor = Color.Gray.copy(alpha = 0.15f)
                val labelColor = android.graphics.Color.GRAY

                // 1. Draw horizontal grid lines and value labels (Health % scaled 0 to 100)
                val gridLinesCount = 5
                for (i in 0 until gridLinesCount) {
                    val fraction = i.toFloat() / (gridLinesCount - 1)
                    val yGrid = bottomPx - fraction * plotHeight

                    drawLine(
                        color = axisColor,
                        start = Offset(leftPx, yGrid),
                        end = Offset(rightPx, yGrid),
                        strokeWidth = 1.dp.toPx()
                    )

                    val healthPct = (fraction * 100).toInt()
                    drawContext.canvas.nativeCanvas.apply {
                        val paint = Paint().apply {
                            color = labelColor
                            textSize = 8.dp.toPx()
                            typeface = Typeface.MONOSPACE
                            textAlign = Paint.Align.RIGHT
                        }
                        drawText(
                            "$healthPct%",
                            leftPx - 6.dp.toPx(),
                            yGrid + 3.dp.toPx(),
                            paint
                        )
                    }
                }

                // 2. Plot Distance points (0 to 10,000 km in 2k increments)
                val distancePointsCount = 6
                val stepKm = 2000
                val nominalPoints = mutableListOf<Offset>()
                val lowPsiPoints = mutableListOf<Offset>()
                val thermalPoints = mutableListOf<Offset>()

                for (i in 0 until distancePointsCount) {
                    val km = i * stepKm
                    val x = leftPx + (i.toFloat() / (distancePointsCount - 1)) * plotWidth

                    // Invert and map values to graph coordinate height
                    val nominalHealth = (latestHealth - (km / 1000f) * 1.5f).coerceIn(10f, 100f)
                    val lowPsiHealth = (latestHealth - (km / 1000f) * 3.5f).coerceIn(10f, 100f)
                    val thermalHealth = (latestHealth - (km / 1000f) * 5.8f).coerceIn(10f, 100f)

                    val yNominal = bottomPx - ((nominalHealth / 100f) * plotHeight * animationProgress)
                    val yLowPsi = bottomPx - ((lowPsiHealth / 100f) * plotHeight * animationProgress)
                    val yThermal = bottomPx - ((thermalHealth / 100f) * plotHeight * animationProgress)

                    nominalPoints.add(Offset(x, yNominal))
                    lowPsiPoints.add(Offset(x, yLowPsi))
                    thermalPoints.add(Offset(x, yThermal))

                    // Draw distance labels
                    drawContext.canvas.nativeCanvas.apply {
                        val paint = Paint().apply {
                            color = labelColor
                            textSize = 7.5.dp.toPx()
                            typeface = Typeface.MONOSPACE
                            textAlign = Paint.Align.CENTER
                        }
                        drawText(
                            "${km / 1000}k",
                            x,
                            bottomPx + 12.dp.toPx(),
                            paint
                        )
                    }
                }

                // Draw curves
                if (selectedProjectionMode == "ALL" || selectedProjectionMode == "NOMINAL") {
                    drawCurvePathProjection(nominalPoints, Color(0xFF50FA7B))
                }
                if (selectedProjectionMode == "ALL" || selectedProjectionMode == "LOW PRESSURE") {
                    drawCurvePathProjection(lowPsiPoints, Color(0xFFFFB86C))
                }
                if (selectedProjectionMode == "ALL" || selectedProjectionMode == "THERMAL") {
                    drawCurvePathProjection(thermalPoints, Color(0xFFFF5555))
                }
            }

            Spacer(modifier = Modifier.height(14.dp))
            // Explanatory note
            Box(
                modifier = Modifier
                    .fillMaxWidth()
                    .background(MaterialTheme.colorScheme.background, RoundedCornerShape(8.dp))
                    .padding(8.dp)
            ) {
                Text(
                    text = when (selectedProjectionMode) {
                        "NOMINAL" -> "• NOMINAL PROJECTION: With correct 32-35 PSI settings and standard highway loads, the tire should maintain safe operational health levels (>75%) beyond the next 10,000 km."
                        "LOW PRESSURE" -> "• LOW-PRESSURE STRESS: Running continuously at under-inflated PSI values (such as 19-24 PSI) causes high sidewall friction and accelerates shoulder wear, losing 35% health over 10k km."
                        "THERMAL" -> "• THERMAL STRESS PROJECTION: Peak temperature stresses (such as running Death Valley tarmac peaks) degrade tire rubber structure sharply, risking rapid structural tire safety compromise within 6,000 km."
                        else -> "• PROACTIVE TELEMETRY: Normal driving retains high compound flexibility. Maintain 32-35 PSI across active road segments to extend tread lifespan significantly."
                    },
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                    fontSize = 9.sp,
                    lineHeight = 13.sp,
                    fontFamily = FontFamily.Monospace
                )
            }
        }
    }
}

@Composable
private fun LegendItemProjection(color: Color, label: String) {
    Row(
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(5.dp)
    ) {
        Box(
            modifier = Modifier
                .size(7.dp)
                .background(color, CircleShape)
        )
        Text(
            text = label.uppercase(),
            color = MaterialTheme.colorScheme.onSurfaceVariant,
            fontSize = 8.5.sp,
            fontFamily = FontFamily.Monospace,
            fontWeight = FontWeight.SemiBold
        )
    }
}

private fun androidx.compose.ui.graphics.drawscope.DrawScope.drawCurvePathProjection(
    points: List<Offset>, 
    color: Color
) {
    if (points.size < 2) return
    val path = Path().apply {
        points.forEachIndexed { idx, pt ->
            if (idx == 0) moveTo(pt.x, pt.y)
            else lineTo(pt.x, pt.y)
        }
    }
    drawPath(
        path = path,
        color = color,
        style = Stroke(width = 2.dp.toPx())
    )
    points.forEach { pt ->
        drawCircle(
            color = color,
            radius = 3.dp.toPx(),
            center = pt
        )
    }
}

@Composable
fun ThermalComparisonView(
    viewModel: TireTwinViewModel,
    historyScans: List<TireScan>,
    onNavigateToHome: () -> Unit
) {
    val activeTire by viewModel.activeTire.collectAsState()
    val speed by viewModel.speed.collectAsState()
    val pressure by viewModel.pressure.collectAsState()
    val temperature by viewModel.temperature.collectAsState()
    val wearPattern by viewModel.wearPattern.collectAsState()

    var selectedSeason by remember { mutableStateOf("Summer") }

    val seasonColor = when (selectedSeason) {
        "Summer" -> Color(0xFFF97316)
        "Winter" -> Color(0xFF60A5FA)
        else -> StatusWarning
    }

    // Map month index (0-11) to season
    fun getSeasonForMonth(month: Int): String {
        return when (month) {
            Calendar.DECEMBER, Calendar.JANUARY, Calendar.FEBRUARY -> "Winter"
            Calendar.JUNE, Calendar.JULY, Calendar.AUGUST -> "Summer"
            else -> "Spring/Autumn"
        }
    }

    // Filter historical scans by selected season
    val seasonalScans = remember(historyScans, selectedSeason) {
        historyScans.filter { scan ->
            val cal = Calendar.getInstance().apply { timeInMillis = scan.timestamp }
            val month = cal.get(Calendar.MONTH)
            getSeasonForMonth(month) == selectedSeason
        }
    }

    // Calculate historical baseline temperature
    val historicalBaseTemp = remember(seasonalScans, selectedSeason) {
        if (seasonalScans.isNotEmpty()) {
            seasonalScans.map { it.temperature }.average().toFloat()
        } else {
            when (selectedSeason) {
                "Summer" -> 60f
                "Winter" -> 26f
                else -> 38f // Spring/Autumn
            }
        }
    }

    val historicalBaseWear = remember(seasonalScans, selectedSeason) {
        if (seasonalScans.isNotEmpty()) {
            // Find most common wear pattern
            seasonalScans.groupBy { it.wearPattern }
                .maxByOrNull { it.value.size }?.key ?: "Normal"
        } else {
            when (selectedSeason) {
                "Summer" -> "Center Wear"
                else -> "Normal"
            }
        }
    }

    val currentProfile = remember(temperature, wearPattern) {
        calculateThermalCrossSection(temperature, wearPattern)
    }

    val historicalProfile = remember(historicalBaseTemp, historicalBaseWear) {
        calculateThermalCrossSection(historicalBaseTemp, historicalBaseWear)
    }

    // Degradation Factor
    val degradationMultiplier = when (selectedSeason) {
        "Summer" -> 1.8f
        "Winter" -> 0.9f
        else -> 1.0f
    }

    // Ambient Temp approximation for explanation
    val ambientTempLabel = when (selectedSeason) {
        "Summer" -> "35°C (Peak Heat)"
        "Winter" -> "2°C (Freezing)"
        else -> "18°C (Mild)"
    }

    val context = LocalContext.current

    Column(
        modifier = Modifier
            .fillMaxSize()
            .verticalScroll(rememberScrollState())
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp)
    ) {
        // Active Tire Status Card
        Card(
            shape = RoundedCornerShape(12.dp),
            colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
            border = BorderStroke(1.dp, MaterialTheme.colorScheme.outline.copy(alpha = 0.15f))
        ) {
            Column(modifier = Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Text(
                        text = "ACTIVE MODEL STATE (${activeTire.code})",
                        color = MaterialTheme.colorScheme.primary,
                        fontSize = 11.sp,
                        fontFamily = FontFamily.Monospace,
                        fontWeight = FontWeight.Bold
                    )
                    Box(
                        modifier = Modifier
                            .background(Color(0x28, 0xB4, 0x82).copy(alpha = 0.15f), RoundedCornerShape(4.dp))
                            .padding(horizontal = 6.dp, vertical = 2.dp)
                    ) {
                        Text(
                            text = "LIVE SYNC",
                            color = Color(0x28, 0xB4, 0x82),
                            fontSize = 8.sp,
                            fontFamily = FontFamily.Monospace,
                            fontWeight = FontWeight.Bold
                        )
                    }
                }
                Spacer(modifier = Modifier.height(4.dp))
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween
                ) {
                    Column {
                        Text("Core Temperature", color = MaterialTheme.colorScheme.onSurfaceVariant, fontSize = 9.sp)
                        Text("${temperature.toInt()} °C", color = Color.White, fontSize = 16.sp, fontWeight = FontWeight.Bold, fontFamily = FontFamily.Monospace)
                    }
                    Column {
                        Text("Chamber Pressure", color = MaterialTheme.colorScheme.onSurfaceVariant, fontSize = 9.sp)
                        Text("${"%.1f".format(pressure)} PSI", color = Color.White, fontSize = 16.sp, fontWeight = FontWeight.Bold, fontFamily = FontFamily.Monospace)
                    }
                    Column {
                        Text("Wear Pattern", color = MaterialTheme.colorScheme.onSurfaceVariant, fontSize = 9.sp)
                        Text(wearPattern.uppercase(), color = Color.White, fontSize = 14.sp, fontWeight = FontWeight.Bold, fontFamily = FontFamily.Monospace)
                    }
                }
            }
        }

        // Season Selector Chips
        Column(verticalArrangement = Arrangement.spacedBy(6.dp)) {
            Text(
                text = "SELECT HISTORICAL REFERENCE SEASON",
                color = MaterialTheme.colorScheme.onSurfaceVariant,
                fontSize = 9.sp,
                fontFamily = FontFamily.Monospace,
                fontWeight = FontWeight.Bold
            )
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(8.dp)
            ) {
                val seasons = listOf("Summer", "Winter", "Spring/Autumn")
                seasons.forEach { season ->
                    val isSelected = selectedSeason == season
                    val seasonColor = when (season) {
                        "Summer" -> Color(0xFF, 0xB8, 0x6C)
                        "Winter" -> Color(0x58, 0xA6, 0xFF)
                        else -> Color(0x28, 0xB4, 0x82)
                    }
                    Box(
                        modifier = Modifier
                            .weight(1f)
                            .clip(RoundedCornerShape(8.dp))
                            .background(if (isSelected) seasonColor.copy(alpha = 0.15f) else MaterialTheme.colorScheme.surface)
                            .border(
                                width = 1.dp,
                                color = if (isSelected) seasonColor else MaterialTheme.colorScheme.outline.copy(alpha = 0.15f),
                                shape = RoundedCornerShape(8.dp)
                            )
                            .clickable { selectedSeason = season }
                            .padding(vertical = 10.dp),
                        contentAlignment = Alignment.Center
                    ) {
                        Text(
                            text = season.uppercase(),
                            color = if (isSelected) seasonColor else MaterialTheme.colorScheme.onSurfaceVariant,
                            fontSize = 10.sp,
                            fontWeight = FontWeight.Bold,
                            fontFamily = FontFamily.Monospace
                        )
                    }
                }
            }
        }

        // Canvas Overlaid Thermal profile chart
        Card(
            shape = RoundedCornerShape(12.dp),
            colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
            border = BorderStroke(1.dp, MaterialTheme.colorScheme.outline.copy(alpha = 0.15f))
        ) {
            Column(modifier = Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Text(
                        text = "THERMAL GRADIENT OVERLAY (CROSS-SECTION)",
                        color = Color.White,
                        fontSize = 10.sp,
                        fontFamily = FontFamily.Monospace,
                        fontWeight = FontWeight.Bold
                    )
                    Text(
                        text = "YAW: 0° (SIDE AXIAL)",
                        color = Color.Gray,
                        fontSize = 8.sp,
                        fontFamily = FontFamily.Monospace
                    )
                }

                // Legend row
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(16.dp),
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    // Current Legend
                    Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(4.dp)) {
                        Box(modifier = Modifier.size(6.dp).background(StatusWarning, CircleShape))
                        Text("Current Profile", color = MaterialTheme.colorScheme.onSurfaceVariant, fontSize = 8.5.sp, fontFamily = FontFamily.Monospace)
                    }
                    // Historical Legend
                    Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(4.dp)) {
                        Canvas(modifier = Modifier.size(width = 12.dp, height = 4.dp)) {
                            drawLine(
                                color = seasonColor,
                                start = Offset(0f, size.height/2),
                                end = Offset(size.width, size.height/2),
                                strokeWidth = 2.dp.toPx(),
                                pathEffect = androidx.compose.ui.graphics.PathEffect.dashPathEffect(floatArrayOf(5f, 5f), 0f)
                            )
                        }
                        Text("Season Avg ($selectedSeason)", color = MaterialTheme.colorScheme.onSurfaceVariant, fontSize = 8.5.sp, fontFamily = FontFamily.Monospace)
                    }
                }

                Spacer(modifier = Modifier.height(4.dp))

                // Chart Drawing
                Canvas(
                    modifier = Modifier
                        .fillMaxWidth()
                        .height(160.dp)
                ) {
                    val leftPx = 40.dp.toPx()
                    val rightPx = size.width - 24.dp.toPx()
                    val topPx = 10.dp.toPx()
                    val bottomPx = size.height - 20.dp.toPx()

                    val plotWidth = rightPx - leftPx
                    val plotHeight = bottomPx - topPx

                    val axisColor = Color.Gray.copy(alpha = 0.15f)
                    val labelColor = android.graphics.Color.GRAY

                    // Y Grid Lines & Labels
                    val yLines = 5
                    for (i in 0 until yLines) {
                        val fraction = i.toFloat() / (yLines - 1)
                        val y = bottomPx - fraction * plotHeight
                        drawLine(
                            color = axisColor,
                            start = Offset(leftPx, y),
                            end = Offset(rightPx, y),
                            strokeWidth = 1.dp.toPx()
                        )
                        val tempVal = (fraction * 100).toInt()
                        drawContext.canvas.nativeCanvas.apply {
                            val paint = Paint().apply {
                                color = labelColor
                                textSize = 8.dp.toPx()
                                typeface = Typeface.MONOSPACE
                                textAlign = Paint.Align.RIGHT
                            }
                            drawText("$tempVal°C", leftPx - 6.dp.toPx(), y + 3.dp.toPx(), paint)
                        }
                    }

                    // Map X Section Points: Inner, Center, Outer
                    val xPoints = listOf(
                        leftPx + 0.1f * plotWidth,
                        leftPx + 0.5f * plotWidth,
                        leftPx + 0.9f * plotWidth
                    )
                    val xLabels = listOf("INNER SHOULDER", "CENTER TREAD", "OUTER SHOULDER")

                    // Draw X axis labels
                    xPoints.forEachIndexed { idx, x ->
                        drawContext.canvas.nativeCanvas.apply {
                            val paint = Paint().apply {
                                color = labelColor
                                textSize = 7.5.dp.toPx()
                                typeface = Typeface.MONOSPACE
                                textAlign = Paint.Align.CENTER
                            }
                            drawText(xLabels[idx], x, bottomPx + 14.dp.toPx(), paint)
                        }
                    }

                    // Map Y coordinates for current & historical
                    val currentYCoords = currentProfile.map { temp ->
                        bottomPx - (temp.coerceIn(0f, 100f) / 100f) * plotHeight
                    }
                    val historicalYCoords = historicalProfile.map { temp ->
                        bottomPx - (temp.coerceIn(0f, 100f) / 100f) * plotHeight
                    }

                    val currentOffsets = xPoints.mapIndexed { idx, x -> Offset(x, currentYCoords[idx]) }
                    val historicalOffsets = xPoints.mapIndexed { idx, x -> Offset(x, historicalYCoords[idx]) }

                    // Draw curves
                    val currentPath = Path().apply {
                        currentOffsets.forEachIndexed { i, offset ->
                            if (i == 0) moveTo(offset.x, offset.y) else lineTo(offset.x, offset.y)
                        }
                    }
                    val historicalPath = Path().apply {
                        historicalOffsets.forEachIndexed { i, offset ->
                            if (i == 0) moveTo(offset.x, offset.y) else lineTo(offset.x, offset.y)
                        }
                    }

                    // Draw historical dashed line
                    drawPath(
                        path = historicalPath,
                        color = seasonColor,
                        style = Stroke(
                            width = 2.2f.dp.toPx(),
                            pathEffect = androidx.compose.ui.graphics.PathEffect.dashPathEffect(floatArrayOf(12f, 10f), 0f)
                        )
                    )
                    // Draw historical dots
                    historicalOffsets.forEach { offset ->
                        drawCircle(color = seasonColor, radius = 3.5f.dp.toPx(), center = offset)
                        drawCircle(color = Color(0xFF1E1E2E), radius = 1.8f.dp.toPx(), center = offset)
                    }

                    // Draw current solid line
                    drawPath(
                        path = currentPath,
                        color = StatusWarning,
                        style = Stroke(width = 2.5f.dp.toPx())
                    )
                    // Draw current glowing dots
                    currentOffsets.forEach { offset ->
                        drawCircle(color = StatusWarning.copy(alpha = 0.3f), radius = 6.dp.toPx(), center = offset)
                        drawCircle(color = StatusWarning, radius = 4f.dp.toPx(), center = offset)
                        drawCircle(color = Color.White, radius = 1.8f.dp.toPx(), center = offset)
                    }
                }
            }
        }

        // Weather Impact Degradation Report
        Card(
            shape = RoundedCornerShape(12.dp),
            colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.2f)),
            border = BorderStroke(1.dp, MaterialTheme.colorScheme.outline.copy(alpha = 0.1f))
        ) {
            Column(modifier = Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
                Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    Icon(Icons.Default.Analytics, contentDescription = null, tint = MaterialTheme.colorScheme.primary, modifier = Modifier.size(16.dp))
                    Text(
                        text = "DEGRADATION RATE REPORT",
                        color = Color.White,
                        fontSize = 11.sp,
                        fontFamily = FontFamily.Monospace,
                        fontWeight = FontWeight.Bold
                    )
                }

                Divider(color = MaterialTheme.colorScheme.outline.copy(alpha = 0.15f))

                // Comparison grid
                Column(verticalArrangement = Arrangement.spacedBy(6.dp)) {
                    ComparisonDetailRow(label = "Reference Ambient Temp:", value = ambientTempLabel)
                    ComparisonDetailRow(label = "Carcass Temperature Delta:", value = "${"%.1f".format(temperature - historicalBaseTemp)} °C")
                    
                    val rateChangeText = if (degradationMultiplier > 1f) {
                        "+${((degradationMultiplier - 1f) * 100).toInt()}% (ACCELERATED)"
                    } else if (degradationMultiplier < 1f) {
                        "-${((1f - degradationMultiplier) * 100).toInt()}% (SLOWER)"
                    } else {
                        "NOMINAL BASELINE"
                    }
                    ComparisonDetailRow(
                        label = "Estimated Degradation Rate:", 
                        value = "${degradationMultiplier}x ($rateChangeText)",
                        valueColor = if (degradationMultiplier > 1f) Color(0xFF, 0x4B, 0x4B) else Color(0x28, 0xB4, 0x82)
                    )
                }

                Box(
                    modifier = Modifier
                        .fillMaxWidth()
                        .clip(RoundedCornerShape(6.dp))
                        .background(MaterialTheme.colorScheme.background)
                        .padding(10.dp)
                ) {
                    Text(
                        text = when (selectedSeason) {
                            "Summer" -> "WEATHER IMPACT: Hot weather (Summer) heats the tarmac, elevating tire base temperature and speeding up vulcanized rubber compound wear. The digital twin predicts a tread life loss of ~4.5% per 1,000 km under these conditions. Keep your tire PSI closely balanced at 32-35 PSI to prevent lateral crowning wear."
                            "Winter" -> "WEATHER IMPACT: Cold winter temperatures keep the tire rubber stiff, which minimizes normal thermal rubber wear. However, severe tire under-inflation is extremely common due to cold air compression (-1 PSI per 5°C drop), which can buckle shoulders and trigger severe edge wear if unchecked. Watch out for cold-start rubber chipping."
                            else -> "WEATHER IMPACT: Standard spring/autumn temperatures represent ideal operational conditions. The tire twin operates at a nominal wear factor. Regular tire alignment and standard tire rotation cycles every 10,000 km are recommended to achieve maximum compound longevity."
                        },
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                        fontSize = 9.sp,
                        fontFamily = FontFamily.Monospace,
                        lineHeight = 13.sp
                    )
                }

                // CTA button to restore seasonal configuration parameters
                Button(
                    onClick = {
                        viewModel.updateTelemetry(
                            spd = if (selectedSeason == "Summer") 85f else 50f,
                            pres = if (selectedSeason == "Winter") 26f else 32f,
                            temp = historicalBaseTemp,
                            wear = historicalBaseWear
                        )
                        Toast.makeText(context, "Twin synced to $selectedSeason baseline!", Toast.LENGTH_SHORT).show()
                        onNavigateToHome()
                    },
                    modifier = Modifier.fillMaxWidth(),
                    shape = RoundedCornerShape(6.dp),
                    colors = ButtonDefaults.buttonColors(containerColor = MaterialTheme.colorScheme.primary)
                ) {
                    Text("SYNC TWIN TO SEASON BASELINE", fontSize = 10.sp, fontFamily = FontFamily.Monospace, fontWeight = FontWeight.Bold)
                }
            }
        }
    }
}

@Composable
private fun ComparisonDetailRow(label: String, value: String, valueColor: Color = Color.White) {
    Row(
        modifier = Modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.SpaceBetween,
        verticalAlignment = Alignment.CenterVertically
    ) {
        Text(text = label, color = MaterialTheme.colorScheme.onSurfaceVariant, fontSize = 9.sp, fontFamily = FontFamily.Monospace)
        Text(text = value, color = valueColor, fontSize = 10.sp, fontFamily = FontFamily.Monospace, fontWeight = FontWeight.Bold)
    }
}

fun calculateThermalCrossSection(baseTemp: Float, wearPattern: String): List<Float> {
    return when (wearPattern) {
        "Center Wear" -> listOf(baseTemp - 3f, baseTemp + 8f, baseTemp - 3f)
        "Edge Wear" -> listOf(baseTemp + 6f, baseTemp - 4f, baseTemp + 6f)
        "Camber Wear" -> listOf(baseTemp + 11f, baseTemp - 1f, baseTemp - 6f)
        "Cupping Wear" -> listOf(baseTemp + 4f, baseTemp - 2f, baseTemp + 4f)
        else -> listOf(baseTemp - 2f, baseTemp, baseTemp - 2f) // Normal
    }
}


