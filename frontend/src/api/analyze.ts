/**
 * analyze.ts — Web-friendly POST /analyze API helper using browser FormData.
 *
 * This avoids importing Expo/react-native helpers at module load time so Next
 * builds do not try to resolve mobile-only dependencies.
 */

export interface AnalyzeParams {
  // Accept either a browser File or a data-URL / fetchable URI string.
  imageUri: File | string;
  sidewallImage?: File | string | null;
  latitude?: number;
  longitude?: number;
  sourceLatitude?: number;
  sourceLongitude?: number;
  destinationLatitude?: number;
  destinationLongitude?: number;
  tireBrand?: string;
  tireModel?: string;
  tireSize?: string;
  mileageKm?: number;
  tirePressurePsi?: number;
  temperatureC?: number;
  vibrationG?: number;
  speedKmph?: number;
  context?: Record<string, any>;
}

export interface AnalysisResult {
  session_id: string;
  timestamp?: string;
  risk_level: "CRITICAL" | "HIGH" | "MODERATE" | "LOW";
  status: string;
  replace_immediately: boolean;
  confidence: number;
  predictions: {
    tread_depths_mm: {
      tread_1: number; tread_2: number; tread_3: number; tread_4: number;
      average: number; min: number; max: number;
    };
    health_score: number;
    remaining_life_km: number;
    remaining_life_km_raw?: number;
    wear_pattern: {
      class_id: number; label: string; cause: string;
      severity: string; confidence: number;
      probabilities: Record<string, number>;
    };
  };
  context?: Record<string, any>;
  reasoning: Record<string, any>;
  alerts: Array<{ level: string; message: string }>;
  metadata?: Record<string, any>;
  model_version?: string;
  processing_time_ms?: number;
  blur_score?: number;
  source?: string;
}

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

async function _fileFromInput(input: File | string, fallbackName: string): Promise<File> {
  if (typeof input !== "string") return input;

  const res = await fetch(input);
  const blob = await res.blob();
  return new File([blob], fallbackName, { type: blob.type || "image/jpeg" });
}

export async function analyzeImage(params: AnalyzeParams): Promise<AnalysisResult> {
  const fileToUpload = await _fileFromInput(params.imageUri, "tire_scan.jpg");
  const formData = new FormData();
  formData.append("image", fileToUpload, fileToUpload.name);
  const contextPayload: Record<string, any> = { ...(params.context ?? {}) };

  // SECURITY: API keys are NEVER stored in localStorage.
  // User's API key preferences (boolean toggles) indicate which server-side
  // keys to use. Actual key values are provided during signup/login and
  // stored encrypted (AES-256-GCM) in the database.
  try {
    const raw = typeof window !== "undefined" ? localStorage.getItem("smart_tire_api_key_prefs") : null;
    if (raw) {
      const prefs = JSON.parse(raw);
      contextPayload.api_key_preferences = prefs;
    }
  } catch {
    // localStorage unavailable or corrupt — skip
  }

  function setContextValue(key: string, value: unknown) {
    if (value != null) contextPayload[key] = value;
  }

  if (params.sidewallImage) {
    const sidewallFile = await _fileFromInput(params.sidewallImage, "sidewall_scan.jpg");
    formData.append("sidewall_image", sidewallFile, sidewallFile.name);
  }

  if (params.latitude != null) {
    formData.append("latitude", String(params.latitude));
    setContextValue("latitude", params.latitude);
  }
  if (params.longitude != null) {
    formData.append("longitude", String(params.longitude));
    setContextValue("longitude", params.longitude);
  }
  if (params.sourceLatitude != null) {
    formData.append("source_latitude", String(params.sourceLatitude));
    setContextValue("source_latitude", params.sourceLatitude);
  }
  if (params.sourceLongitude != null) {
    formData.append("source_longitude", String(params.sourceLongitude));
    setContextValue("source_longitude", params.sourceLongitude);
  }
  if (params.destinationLatitude != null) {
    formData.append("destination_latitude", String(params.destinationLatitude));
    setContextValue("destination_latitude", params.destinationLatitude);
  }
  if (params.destinationLongitude != null) {
    formData.append("destination_longitude", String(params.destinationLongitude));
    setContextValue("destination_longitude", params.destinationLongitude);
  }
  if (params.tireBrand) formData.append("tire_brand", params.tireBrand);
  if (params.tireModel) formData.append("tire_model", params.tireModel);
  if (params.tireSize) formData.append("tire_size", params.tireSize);
  if (params.mileageKm != null) {
    formData.append("mileage_km", String(params.mileageKm));
    setContextValue("mileage_km", params.mileageKm);
  }
  if (params.tirePressurePsi != null) {
    formData.append("tire_pressure_psi", String(params.tirePressurePsi));
    setContextValue("tire_pressure_psi", params.tirePressurePsi);
  }
  if (params.temperatureC != null) {
    formData.append("temperature_c", String(params.temperatureC));
    setContextValue("temperature_c", params.temperatureC);
  }
  if (params.vibrationG != null) {
    formData.append("vibration_g", String(params.vibrationG));
    setContextValue("vibration_g", params.vibrationG);
  }
  if (params.speedKmph != null) {
    formData.append("speed_kmph", String(params.speedKmph));
    setContextValue("speed_kmph", params.speedKmph);
  }
  if (Object.keys(contextPayload).length > 0) {
    formData.append("context", JSON.stringify(contextPayload));
  }

  const res = await fetch(`${API_BASE_URL}/analyze`, {
    method: "POST",
    body: formData,
  });

  if (!res.ok) {
    let msg = await res.text();
    try {
      const json = JSON.parse(msg);
      msg = json.detail || json.error || msg;
    } catch { }
    throw new Error(msg || `Upload failed: ${res.status}`);
  }

  return (await res.json()) as AnalysisResult;
}
