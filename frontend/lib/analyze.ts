/**
 * Browser API helpers for the Smart Tire backend.
 */

import { getConfiguredApiKeys } from "@/lib/api-keys";

export interface AnalyzeParams {
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
  timestamp: string;
  risk_level: "CRITICAL" | "HIGH" | "MODERATE" | "LOW";
  status: string;
  replace_immediately: boolean;
  confidence: number;
  predictions: {
    tread_depths_mm: {
      tread_1: number;
      tread_2: number;
      tread_3: number;
      tread_4: number;
      average: number;
      min: number;
      max: number;
    };
    health_score: number;
    remaining_life_km: number;
    remaining_life_km_raw?: number;
    wear_pattern: {
      class_id: number;
      label: string;
      label_display?: string;
      cause: string;
      advice?: string;
      severity: string;
      confidence: number;
      probabilities?: Record<string, number>;
    };
  };
  context?: Record<string, any>;
  reasoning: Record<string, any>;
  alerts: Array<{ level: string; message: string; class?: string }>;
  metadata?: Record<string, any>;
  enterprise_ai?: Record<string, any>;
  model_version?: string;
  blur_score?: number;
  source?: string;
}

export interface RouteRoadConditionParams {
  sourceLatitude: number;
  sourceLongitude: number;
  destinationLatitude: number;
  destinationLongitude: number;
}

export interface RouteRoadConditionResult {
  terrain_type?: string;
  road_condition?: string;
  road_condition_basis?: string;
  traffic_density?: string;
  elevation_m?: number | null;
  road_wear_multiplier?: number;
  latitude?: number;
  longitude?: number;
  route_source_latitude?: number;
  route_source_longitude?: number;
  route_destination_latitude?: number;
  route_destination_longitude?: number;
  route_distance_km?: number | null;
  route_duration_min?: number | null;
  route_analysis_source?: string;
  street_view_available?: boolean;
  street_view_sample_count?: number;
  street_view_covered_samples?: number;
  street_view_visual_summary?: string;
  street_view_samples?: Array<Record<string, any>>;
}

export interface HistoryItem {
  session_id: string;
  timestamp: string | null;
  risk_level: AnalysisResult["risk_level"];
  health_score: number | null;
  avg_tread_mm: number | null;
  remaining_life_km: number | null;
  wear_pattern: string | null;
}

export interface HistoryResponse {
  total: number;
  page: number;
  page_size: number;
  results: HistoryItem[];
}

export function getApiBaseUrl(): string {
  const configuredUrl = process.env.NEXT_PUBLIC_API_BASE_URL?.trim() || "http://localhost:8000";
  return configuredUrl.replace(/\/+$/, "");
}

async function fileFromInput(input: File | string, fallbackName: string): Promise<File> {
  if (typeof input !== "string") return input;

  const res = await fetch(input);
  const blob = await res.blob();
  return new File([blob], fallbackName, { type: blob.type || "image/jpeg" });
}

async function parseError(res: Response, fallback: string): Promise<string> {
  let message = await res.text();
  try {
    const json = JSON.parse(message);
    message = json.detail || json.error || message;
  } catch {
    // Keep the raw response text.
  }
  return message || fallback;
}

export async function analyzeImage(params: AnalyzeParams): Promise<AnalysisResult> {
  const fileToUpload = await fileFromInput(params.imageUri, "tire_scan.jpg");
  const formData = new FormData();
  formData.append("image", fileToUpload, fileToUpload.name);
  const contextPayload: Record<string, any> = { ...(params.context ?? {}) };

  // Include user's runtime API keys from localStorage
  const runtimeKeys = getConfiguredApiKeys();
  if (Object.keys(runtimeKeys).length > 0) {
    contextPayload.runtime_api_keys = runtimeKeys;
  }

  function setContextValue(key: string, value: unknown) {
    if (value != null) contextPayload[key] = value;
  }

  if (params.sidewallImage) {
    const sidewallFile = await fileFromInput(params.sidewallImage, "sidewall_scan.jpg");
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

  const res = await fetch(`${getApiBaseUrl()}/analyze`, {
    method: "POST",
    body: formData,
  });

  if (!res.ok) {
    throw new Error(await parseError(res, `Upload failed: ${res.status}`));
  }

  return (await res.json()) as AnalysisResult;
}

export async function analyzeRouteRoadCondition(
  params: RouteRoadConditionParams
): Promise<RouteRoadConditionResult> {
  const res = await fetch(`${getApiBaseUrl()}/analyze/route-road-condition`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      source_latitude: params.sourceLatitude,
      source_longitude: params.sourceLongitude,
      destination_latitude: params.destinationLatitude,
      destination_longitude: params.destinationLongitude,
    }),
  });

  if (!res.ok) {
    throw new Error(await parseError(res, `Route analysis failed: ${res.status}`));
  }

  return (await res.json()) as RouteRoadConditionResult;
}

export async function getAnalysisHistory(params: {
  page?: number;
  pageSize?: number;
  riskLevel?: string;
  fromDate?: string;
  toDate?: string;
} = {}): Promise<HistoryResponse> {
  const search = new URLSearchParams();
  search.set("page", String(params.page ?? 1));
  search.set("page_size", String(params.pageSize ?? 20));
  if (params.riskLevel) search.set("risk_level", params.riskLevel);
  if (params.fromDate) search.set("from_date", params.fromDate);
  if (params.toDate) search.set("to_date", params.toDate);

  const res = await fetch(`${getApiBaseUrl()}/history?${search.toString()}`);
  if (!res.ok) throw new Error(await parseError(res, `History request failed: ${res.status}`));
  return (await res.json()) as HistoryResponse;
}

export async function getAnalysisBySession(sessionId: string): Promise<AnalysisResult> {
  const res = await fetch(`${getApiBaseUrl()}/history/${encodeURIComponent(sessionId)}`);
  if (!res.ok) {
    if (res.status === 404) throw new Error("Analysis result was not found in history.");
    throw new Error(await parseError(res, `Analysis lookup failed: ${res.status}`));
  }
  return (await res.json()) as AnalysisResult;
}
