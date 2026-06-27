/**
 * api-keys.ts — User API key preferences (which services to use).
 *
 * SECURITY: Actual API key values are NEVER stored in the browser.
 * Keys are sent securely to the backend where they are kept in-memory
 * for the duration of a session and encrypted at rest if persisted.
 *
 * The frontend only stores boolean flags indicating which services
 * the user wants to use their own keys for.
 */

export interface UserApiKeyPreferences {
  useOwnGemini: boolean;
  useOwnMapillary: boolean;
  useOwnOpenweather: boolean;
}

const STORAGE_KEY = "smart_tire_api_key_prefs";

const defaultPrefs: UserApiKeyPreferences = {
  useOwnGemini: false,
  useOwnMapillary: false,
  useOwnOpenweather: false,
};

/**
 * Get the user's API key preferences (which services they want to use their own keys for).
 */
export function getApiKeyPreferences(): UserApiKeyPreferences {
  if (typeof window === "undefined") return defaultPrefs;
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return defaultPrefs;
    const parsed = JSON.parse(raw);
    return { ...defaultPrefs, ...parsed };
  } catch {
    return defaultPrefs;
  }
}

/**
 * Save the user's API key preferences.
 */
export function saveApiKeyPreferences(prefs: Partial<UserApiKeyPreferences>): UserApiKeyPreferences {
  if (typeof window === "undefined") return defaultPrefs;
  const current = getApiKeyPreferences();
  const updated = { ...current, ...prefs };
  localStorage.setItem(STORAGE_KEY, JSON.stringify(updated));
  return updated;
}

/**
 * Check if the user has configured any API key preferences.
 */
export function hasApiKeyPreferences(): boolean {
  const prefs = getApiKeyPreferences();
  return prefs.useOwnGemini || prefs.useOwnMapillary || prefs.useOwnOpenweather;
}
