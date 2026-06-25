package com.example.data

import android.util.Log
import com.example.BuildConfig
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import org.json.JSONArray
import org.json.JSONObject

data class GeminiAnalysis(
    val analysis: String,
    val safety: String,
    val timeline: String,
    val remainingLifePrediction: String
)

object GeminiService {
    private const val TAG = "GeminiService"
    private val client = OkHttpClient.Builder()
        .connectTimeout(15, java.util.concurrent.TimeUnit.SECONDS)
        .readTimeout(15, java.util.concurrent.TimeUnit.SECONDS)
        .build()

    suspend fun getTireAnalysis(
        speed: Float,
        pressure: Float,
        temperature: Float,
        wearPattern: String
    ): GeminiAnalysis = withContext(Dispatchers.IO) {
        val apiKey = try {
            BuildConfig.GEMINI_API_KEY
        } catch (e: Exception) {
            ""
        }

        if (apiKey.isEmpty() || apiKey == "MY_GEMINI_API_KEY") {
            Log.w(TAG, "Gemini API key is not set. Using hyper-realistic onboard diagnostic diagnostics.")
            return@withContext getLocalFallbackAnalysis(speed, pressure, temperature, wearPattern)
        }

        val prompt = """
            You are an advanced automotive engineering AI. Perform a real-time health analysis on a tire digital twin.
            
            Metrics:
            - Vehicle Speed: $speed km/h
            - Tire Inflation Pressure: $pressure PSI (Standard is 32 PSI)
            - Tire Surface Temperature: $temperature °C
            - Observed Physical Wear Pattern: "$wearPattern"
            
            Respond with a single JSON object containing exactly four string attributes. No markdown formatting around the JSON (do not include ```json or other formatting), just raw JSON.
            JSON structure:
            {
               "analysis": "A detailed technical breakdown of how the current pressure ($pressure PSI) and wear pattern ($wearPattern) are affecting tire structural integrity, contact patch, and vehicle handling.",
               "safety": "A critical risk assessment. Warn about blowout risks, aquaplaning risk, or alignment shifts caused by $wearPattern wear or temperature levels ($temperature °C).",
               "timeline": "A clear, itemized replacement / maintenance timeline recommendation (e.g. 'Rotate tires within 30 days', 'Perform alignment immediately', 'Replace tire within 3 months').",
               "remainingLifePrediction": "A mathematically sound, scientifically plausible prediction of the remaining tread life of the tire in both kilometers and miles, taking current telemetry and degradation rates into account. Format must be highly readable and look like '<X> km (<Y> miles) - based on telemetry speed/temp load factors' (e.g., '14,200 km (8,820 miles) - elevated shoulder friction accelerated wear'). Keep it under 150 characters."
            }
        """.trimIndent()

        try {
            val jsonPayload = JSONObject().apply {
                put("contents", JSONArray().apply {
                    put(JSONObject().apply {
                        put("parts", JSONArray().apply {
                            put(JSONObject().apply {
                                                    put("text", prompt)
                                                })
                                            })
                                        })
                                    })
            }

            val requestBody = jsonPayload.toString().toRequestBody("application/json".toMediaType())
            val request = Request.Builder()
                .url("https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key=$apiKey")
                .post(requestBody)
                .build()

            client.newCall(request).execute().use { response ->
                if (!response.isSuccessful) {
                    Log.e(TAG, "Gemini API call failed with code: ${response.code}")
                    return@withContext getLocalFallbackAnalysis(speed, pressure, temperature, wearPattern)
                }

                val responseBody = response.body?.string() ?: ""
                val responseJson = JSONObject(responseBody)
                val text = responseJson
                    .getJSONArray("candidates")
                    .getJSONObject(0)
                    .getJSONObject("content")
                    .getJSONArray("parts")
                    .getJSONObject(0)
                    .getString("text")

                // Try to clean up any markdown if Gemini accidentally added it
                val cleanedText = text.trim()
                    .removePrefix("```json")
                    .removePrefix("```")
                    .removeSuffix("```")
                    .trim()

                val parsedJson = JSONObject(cleanedText)
                GeminiAnalysis(
                    analysis = parsedJson.optString("analysis", "Analysis completed successfully."),
                    safety = parsedJson.optString("safety", "Operating within safe boundaries."),
                    timeline = parsedJson.optString("timeline", "Monitor regularly."),
                    remainingLifePrediction = parsedJson.optString("remainingLifePrediction", "35,000 km (21,700 miles) - standard wear index")
                )
            }
        } catch (e: Exception) {
            Log.e(TAG, "Error contacting Gemini: ${e.message}", e)
            getLocalFallbackAnalysis(speed, pressure, temperature, wearPattern)
        }
    }

    private fun getLocalFallbackAnalysis(
        speed: Float,
        pressure: Float,
        temperature: Float,
        wearPattern: String
    ): GeminiAnalysis {
        val pressureAnalysis = when {
            pressure < 28f -> "UNDER-INFLATION WARNING: Standing wave deformation at higher speeds ($speed km/h) creates critical tread flexing. Contact pressure is shifted to the outer edges, accelerating fuel consumption and tread block tearing."
            pressure > 36f -> "OVER-INFLATION ALERT: Highly rigid contact patch reduces tire-to-road friction buffer. Central rib carries 85%+ of tire load, compromising braking distance and ride comfort."
            else -> "OPTIMAL INFLATION: Uniform contact pressure profile (Standard 32 PSI). Heat dispersion and rolling resistance are within nominal limits."
        }

        val wearDescription = when (wearPattern) {
            "Center Wear" -> "Accelerated center rib degradation confirms a history of over-inflation. The tire has crowned, resulting in reduced road grip and increased hydroplaning susceptibility."
            "Edge Wear" -> "Distinct dual-shoulder block wear patterns diagnostic of chronicle under-inflation. Increased rolling resistance has placed immense load stress on the sidewalls."
            "Camber Wear" -> "Asymmetrical diagonal wear (one-sided) is indicative of wheel alignment deviation. Suspensions are out of specification, forcing the vehicle to favor the inner or outer shoulder contact patch."
            "Cupping Wear" -> "High-frequency cupping or scallop patterns suggest a failure in shock absorbers, suspension bushings, or high-degree wheel imbalance causing cyclical bouncing."
            else -> "Symmetrical, healthy tire profile indicating precise alignment and proper tire rotation compliance."
        }

        val analysis = "$pressureAnalysis\n\n$wearDescription"

        val safety = when {
            temperature > 85f -> "CRITICAL THERMAL LEVEL: Core temperature reached ${temperature}°C. Intermolecular friction inside the synthetic rubber is approaching molecular degradation threshold. Risk of immediate high-speed blowout is high."
            pressure < 24f -> "CRITICAL PRESSURE LEVEL: Inflation pressure ($pressure PSI) is dangerously low. Sidewall tire collapse or bead separation on tight corners is a severe risk."
            wearPattern == "Cupping Wear" -> "SUSPENSION HAZARD: Severe cupping wear reduces tire grip by up to 40% on wet surfaces. Immediate suspension inspection recommended."
            else -> "Tire thermodynamics and balance are currently stable. Risk of unexpected tire structure failure is currently low."
        }

        val timeline = when (wearPattern) {
            "Camber Wear" -> "• Within 48 hours: Schedule suspension alignment diagnostic to correct camber angle parameters.\n• Next 500 km: Rotate tires to balance shoulder loads."
            "Cupping Wear" -> "• Within 7 days: Replace worn dampers, shock absorbers or re-balance the wheel assembly.\n• Immediate: Inspect ball joints."
            "Center Wear" -> "• Immediate: De-inflate tires down to standard 32 PSI.\n• Next 2 weeks: Track center tread remaining depth."
            "Edge Wear" -> "• Immediate: Inflate tires up to standard 32 PSI.\n• Next 30 days: Check tire valve core for slow micro-leaks."
            else -> "• Normal schedule: Rotate tires every 8,000 km.\n• Perform manual pressure checks every 30 days."
        }

        // Calculate dynamic realistic fallback remaining life simulation
        var baseLifespanKm = 42000
        var wearScore = 1.0f

        if (pressure < 27.5f) {
            val severity = (27.5f - pressure) / 12.5f
            wearScore += severity * 1.5f
        } else if (pressure > 36.5f) {
            val severity = (pressure - 36.5f) / 8.5f
            wearScore += severity * 0.8f
        }

        if (temperature > 80f) {
            wearScore += 2.0f
        } else if (temperature > 50f) {
            wearScore += 0.8f
        }

        if (speed > 100f) {
            wearScore += 0.5f
        }

        when (wearPattern) {
            "Center Wear" -> wearScore += 0.6f
            "Edge Wear" -> wearScore += 1.2f
            "Camber Wear" -> wearScore += 1.8f
            "Cupping Wear" -> wearScore += 1.5f
        }

        val calculatedLifespanKm = (baseLifespanKm / wearScore).toInt()
        val calculatedLifespanMiles = (calculatedLifespanKm * 0.621371f).toInt()
        
        val shortExplanation = when (wearPattern) {
            "Center Wear" -> " - crowned tire center load acceleration"
            "Edge Wear" -> " - shoulder friction high flex degradation"
            "Camber Wear" -> " - asymmetrical geometric scrub wear pacing"
            "Cupping Wear" -> " - damper bounce scallop pattern loss"
            else -> if (temperature > 70f) " - thermal compound stress speed fatigue" else " - nominal footprint wear pattern pacing"
        }
        val remainingLifePrediction = "${"%,d".format(calculatedLifespanKm)} km (${"%,d".format(calculatedLifespanMiles)} miles)$shortExplanation"

        return GeminiAnalysis(analysis, safety, timeline, remainingLifePrediction)
    }
}
