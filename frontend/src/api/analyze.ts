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
  tireBrand?: string;
  tireModel?: string;
  tireSize?: string;
  mileageKm?: number;
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

  if (params.sidewallImage) {
    const sidewallFile = await _fileFromInput(params.sidewallImage, "sidewall_scan.jpg");
    formData.append("sidewall_image", sidewallFile, sidewallFile.name);
  }

  if (params.latitude != null) formData.append("latitude", String(params.latitude));
  if (params.longitude != null) formData.append("longitude", String(params.longitude));
  if (params.tireBrand) formData.append("tire_brand", params.tireBrand);
  if (params.tireModel) formData.append("tire_model", params.tireModel);
  if (params.tireSize) formData.append("tire_size", params.tireSize);
  if (params.mileageKm != null) formData.append("mileage_km", String(params.mileageKm));

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
