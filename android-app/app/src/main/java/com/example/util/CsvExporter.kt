package com.example.util

import android.content.Context
import android.content.Intent
import android.net.Uri
import androidx.core.content.FileProvider
import com.example.data.TireScan
import java.io.File
import java.io.FileOutputStream
import java.text.SimpleDateFormat
import java.util.*

object CsvExporter {
    fun exportScansToCsv(context: Context, scans: List<TireScan>) {
        val fileName = "TireTelemetry_Export_${System.currentTimeMillis()}.csv"
        val file = File(context.cacheDir, fileName)
        
        try {
            FileOutputStream(file).use { out ->
                val header = "Timestamp,Title,Speed (km/h),Pressure (PSI),Temperature (C),Wear Pattern,Health Score,Route,Latitude,Longitude\n"
                out.write(header.toByteArray())
                
                val sdf = SimpleDateFormat("yyyy-MM-dd HH:mm:ss", Locale.getDefault())
                
                scans.forEach { scan ->
                    val line = "${sdf.format(Date(scan.timestamp))}," +
                            "\"${scan.title}\"," +
                            "${scan.speed}," +
                            "${scan.pressure}," +
                            "${scan.temperature}," +
                            "\"${scan.wearPattern}\"," +
                            "${scan.overallHealth}," +
                            "\"${scan.routeName}\"," +
                            "${scan.latitude}," +
                            "${scan.longitude}\n"
                    out.write(line.toByteArray())
                }
            }
            
            val uri: Uri = FileProvider.getUriForFile(
                context,
                "${context.packageName}.provider",
                file
            )
            
            val intent = Intent(Intent.ACTION_SEND).apply {
                type = "text/csv"
                putExtra(Intent.EXTRA_SUBJECT, "Tire IoT Telemetry Data Export")
                putExtra(Intent.EXTRA_STREAM, uri)
                addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
            }
            
            context.startActivity(Intent.createChooser(intent, "Export CSV"))
            
        } catch (e: Exception) {
            e.printStackTrace()
        }
    }
}
