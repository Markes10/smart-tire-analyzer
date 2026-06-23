/**
 * api-keys.ts — Browser-side storage for user-provided API keys.
 *
 * Keys are persisted in localStorage so they survive page reloads.
 * The user enters these during sign-up and can update them in Settings.
 */

const STORAGE_KEY = "smart_tire_api_keys";

export interface UserApiKeys {
  gemini: string;
  mapillary: string;
  openweather: string;
  googleClientId: string;
  googleClientSecret: string;
}

const emptyKeys: UserApiKeys = {
  gemini: "",
  mapillary: "",
  openweather: "",
  googleClientId: "",
  googleClientSecret: "",
};

export function getApiKeys(): UserApiKeys {
  if (typeof window === "undefined") return emptyKeys;
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return emptyKeys;
    const parsed = JSON.parse(raw);
    return { ...emptyKeys, ...parsed };
  } catch {
    return emptyKeys;
  }
}

export function saveApiKeys(keys: Partial<UserApiKeys>): UserApiKeys {
  if (typeof window === "undefined") return emptyKeys;
  const current = getApiKeys();
  const updated = { ...current, ...keys };
  localStorage.setItem(STORAGE_KEY, JSON.stringify(updated));
  return updated;
}

export function hasApiKeys(): boolean {
  const keys = getApiKeys();
  return !!(
    keys.gemini ||
    keys.mapillary ||
    keys.openweather ||
    keys.googleClientId
  );
}

/**
 * Returns only the keys that are actually configured (non-empty).
 * Useful for sending to the backend when making analysis requests.
 */
export function getConfiguredApiKeys(): Partial<UserApiKeys> {
  const keys = getApiKeys();
  const configured: Partial<UserApiKeys> = {};
  for (const [key, value] of Object.entries(keys)) {
    if (value) {
      (configured as any)[key] = value;
    }
  }
  return configured;
}
