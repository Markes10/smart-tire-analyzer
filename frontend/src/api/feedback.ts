/**
 * feedback.ts — API calls for submitting user feedback.
 */

import apiClient from "./client";

export interface FeedbackParams {
  session_id: string;
  feedback_type: "wrong" | "inaccurate" | "correct" | "partial";
  corrected_tread_depth_mm?: number;
  corrected_tread_depths_mm?: {
    tread_1?: number;
    tread_2?: number;
    tread_3?: number;
    tread_4?: number;
  };
  corrected_wear_pattern?: string;
  corrected_health_score?: number;
  original_prediction?: Record<string, any>;
  confidence_override?: number;
  comment?: string;
}

export interface FeedbackResponse {
  feedback_id: string;
  session_id: string;
  stored: boolean;
  retrain_triggered: boolean;
  dataset_refresh_scheduled?: boolean;
  pending_learning_rows?: number;
  retrain_threshold?: number;
  message: string;
}

export async function submitFeedback(
  params: FeedbackParams
): Promise<FeedbackResponse> {
  const response = await apiClient.post<FeedbackResponse>("/feedback", params);
  return response.data as FeedbackResponse;
}

export async function getFeedbackStats(): Promise<{
  total_feedback: number;
  wrong_predictions: number;
  correct_predictions: number;
  accuracy_rate: number;
  pending_training?: number;
  pending_learning_rows?: number;
  trainable_learning_rows?: number;
  retrain_threshold?: number;
  retrain_ready: boolean;
  dataset_refresh_scheduled?: boolean;
  retrain_running?: boolean;
  auto_retrain_refresh?: boolean;
  corrections_needed?: number;
}> {
  const response = await apiClient.get("/feedback/stats");
  return response.data as {
    total_feedback: number;
    wrong_predictions: number;
    correct_predictions: number;
    accuracy_rate: number;
    pending_training?: number;
    pending_learning_rows?: number;
    trainable_learning_rows?: number;
    retrain_threshold?: number;
    retrain_ready: boolean;
    dataset_refresh_scheduled?: boolean;
    retrain_running?: boolean;
    auto_retrain_refresh?: boolean;
    corrections_needed?: number;
  };
}
