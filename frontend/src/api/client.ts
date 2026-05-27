/**
 * Axios API Client — Base HTTP client for Smart Tire backend.
 */

import axios from "axios";

type AxiosErrorLike = {
  response?: {
    status?: number;
    data?: any;
  };
};

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: {
    "Content-Type": "application/json",
    Accept: "application/json",
  },
});

// Request interceptor — attach auth headers, log requests
apiClient.interceptors.request.use(
  (config: any) => {
    // Future: inject JWT token here
    return config;
  },
  (error: unknown) => Promise.reject(error)
);

// Response interceptor — handle global errors
apiClient.interceptors.response.use(
  (response: any) => response,
  (error: AxiosErrorLike) => {
    const status = error.response?.status;
    if (status === 422) {
      // Image quality / validation error
      return Promise.reject(new Error((error.response?.data as any)?.detail || "Invalid request"));
    }
    if (status === 413) {
      return Promise.reject(new Error("Image too large. Maximum 10MB."));
    }
    if (status && status >= 500) {
      return Promise.reject(new Error("Server error. Please try again."));
    }
    if (!error.response) {
      return Promise.reject(new Error("No connection. Check if the backend is running."));
    }
    return Promise.reject(error);
  }
);

export default apiClient;
export { API_BASE_URL };
