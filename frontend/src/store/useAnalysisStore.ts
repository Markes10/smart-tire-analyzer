/**
 * useAnalysisStore — Zustand store for current analysis session.
 * Tracks the latest analysis result and loading/error state.
 */

import { create } from "zustand";
import { AnalysisResult } from "../api/analyze";

interface AnalysisState {
  latestAnalysis: AnalysisResult | null;
  isAnalyzing: boolean;
  error: string | null;
  setLatestAnalysis: (result: AnalysisResult) => void;
  setAnalyzing: (loading: boolean) => void;
  setError: (message: string | null) => void;
  clearAnalysis: () => void;
}

export const useAnalysisStore = create<AnalysisState>((set: any) => ({
  latestAnalysis: null,
  isAnalyzing: false,
  error: null,

  setLatestAnalysis: (result: AnalysisResult) =>
    set({ latestAnalysis: result, isAnalyzing: false, error: null }),

  setAnalyzing: (loading: boolean) => set({ isAnalyzing: loading }),

  setError: (message: string | null) => set({ error: message, isAnalyzing: false }),

  clearAnalysis: () =>
    set({ latestAnalysis: null, isAnalyzing: false, error: null }),
}));
