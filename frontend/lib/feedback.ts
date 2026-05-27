import { getApiBaseUrl } from "@/lib/analyze"

export type FeedbackType = "wrong" | "inaccurate" | "correct" | "partial"

export interface FeedbackParams {
  session_id: string
  feedback_type: FeedbackType
  corrected_tread_depth_mm?: number
  corrected_tread_depths_mm?: {
    tread_1?: number
    tread_2?: number
    tread_3?: number
    tread_4?: number
  }
  corrected_wear_pattern?: string
  corrected_health_score?: number
  original_prediction?: Record<string, any>
  confidence_override?: number
  comment?: string
}

export interface FeedbackResponse {
  feedback_id: string
  session_id: string
  stored: boolean
  retrain_triggered: boolean
  dataset_refresh_scheduled?: boolean
  pending_learning_rows?: number
  retrain_threshold?: number
  message: string
}

export interface FeedbackStats {
  total_feedback: number
  wrong_predictions: number
  correct_predictions: number
  accuracy_rate: number
  pending_training?: number
  pending_learning_rows?: number
  trainable_learning_rows?: number
  retrain_threshold?: number
  retrain_ready: boolean
  dataset_refresh_scheduled?: boolean
  retrain_running?: boolean
  auto_retrain_refresh?: boolean
  corrections_needed?: number
}

async function parseError(res: Response, fallback: string): Promise<string> {
  let message = await res.text()
  try {
    const json = JSON.parse(message)
    message = json.detail || json.error || message
  } catch {
    // Keep the raw response text.
  }
  return message || fallback
}

export async function submitFeedback(params: FeedbackParams): Promise<FeedbackResponse> {
  const res = await fetch(`${getApiBaseUrl()}/feedback`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Accept: "application/json",
    },
    body: JSON.stringify(params),
  })

  if (!res.ok) {
    throw new Error(await parseError(res, `Feedback request failed: ${res.status}`))
  }

  return (await res.json()) as FeedbackResponse
}

export async function getFeedbackStats(): Promise<FeedbackStats> {
  const res = await fetch(`${getApiBaseUrl()}/feedback/stats`, {
    headers: {
      Accept: "application/json",
    },
  })

  if (!res.ok) {
    throw new Error(await parseError(res, `Feedback stats request failed: ${res.status}`))
  }

  return (await res.json()) as FeedbackStats
}
