/**
 * useHistoryStore — Zustand store for analysis history.
 * Manages local cache of scan history with pagination and API sync.
 */

import { create } from "zustand";
import { persist, createJSONStorage } from "zustand/middleware";
import AsyncStorage from "@react-native-async-storage/async-storage";
import apiClient from "../api/client";

export interface HistoryItem {
    session_id: string;
    timestamp: string;
    risk_level: "CRITICAL" | "HIGH" | "MODERATE" | "LOW";
    health_score: number;
    avg_tread_mm: number;
    remaining_life_km: number;
    wear_pattern: string;
}

interface HistoryState {
    history: HistoryItem[];
    isLoading: boolean;
    error: string | null;
    totalCount: number;
    currentPage: number;
    loadHistory: (page?: number, riskFilter?: string) => Promise<void>;
    addToHistory: (result: any) => void;
    clearHistory: () => void;
}

export const useHistoryStore = create<HistoryState>()(
    persist<HistoryState>(
        (set: any, get: any) => ({
            history: [],
            isLoading: false,
            error: null,
            totalCount: 0,
            currentPage: 1,

            loadHistory: async (page = 1, riskFilter?: string) => {
                set({ isLoading: true, error: null });
                try {
                    const params: Record<string, any> = { page, page_size: 20 };
                    if (riskFilter && riskFilter !== "ALL") {
                        params.risk_level = riskFilter;
                    }
                    const response = await apiClient.get("/history", { params });
                    const data = response.data as { results: HistoryItem[]; total: number };

                    set({
                        history: page === 1 ? data.results : [...get().history, ...data.results],
                        totalCount: data.total,
                        currentPage: page,
                        isLoading: false,
                    });
                } catch (err: any) {
                    // If API is unavailable, keep local cache silently
                    set({ isLoading: false, error: null });
                }
            },

            addToHistory: (result: any) => {
                const item: HistoryItem = {
                    session_id: result.session_id,
                    timestamp: result.timestamp || new Date().toISOString(),
                    risk_level: result.risk_level,
                    health_score: result.predictions?.health_score || 0,
                    avg_tread_mm: result.predictions?.tread_depths_mm?.average || 0,
                    remaining_life_km: result.predictions?.remaining_life_km || 0,
                    wear_pattern: result.predictions?.wear_pattern?.label || "unknown",
                };
                set((state: any) => ({
                    history: [item, ...state.history].slice(0, 200), // Keep last 200 locally
                    totalCount: state.totalCount + 1,
                }));
            },

            clearHistory: () => set({ history: [], totalCount: 0, currentPage: 1 }),
        }),
        {
            name: "smart-tire-history",
            storage: createJSONStorage(() => AsyncStorage),
            partialize: (state: HistoryState) => ({ history: state.history, totalCount: state.totalCount }),
        }
    )
);
