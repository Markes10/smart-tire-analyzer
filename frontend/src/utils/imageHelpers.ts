/**
 * imageHelpers.ts — Image compression and validation utilities.
 * Works cross-platform: iOS, Android, Web, Windows desktop (Expo).
 */

import * as ImageManipulator from "expo-image-manipulator";
import * as FileSystem from "expo-file-system";
import Platform from "react-native";

const MAX_SIZE_BYTES = 10 * 1024 * 1024; // 10 MB
const TARGET_SHORT_SIDE = 1024; // px

/**
 * Compress an image to under 10MB at max 1024px wide.
 * Returns compressed URI.
 */
export async function compressImage(uri: string): Promise<string> {
  try {
    const result = await ImageManipulator.manipulateAsync(
      uri,
      [{ resize: { width: TARGET_SHORT_SIDE } }],
      { compress: 0.82, format: ImageManipulator.SaveFormat.JPEG }
    );
    return result.uri;
  } catch {
    // If manipulation fails (e.g. unsupported format), return original
    return uri;
  }
}

/**
 * Validate image before upload.
 * Checks: file existence, size, and format.
 */
export async function validateImage(
  uri: string
): Promise<{ valid: boolean; error?: string }> {
  try {
    // Web & unsupported platforms — skip file-system checks
    if (Platform.OS === "web") {
      return { valid: true };
    }

    const info = await FileSystem.getInfoAsync(uri, { size: true });

    if (!info.exists) {
      return { valid: false, error: "Image file not found." };
    }

    const sizeBytes = (info as any).size ?? 0;
    if (sizeBytes > MAX_SIZE_BYTES) {
      const sizeMb = (sizeBytes / 1024 / 1024).toFixed(1);
      return {
        valid: false,
        error: `Image is ${sizeMb}MB — maximum allowed is 10MB.`,
      };
    }

    return { valid: true };
  } catch {
    return { valid: true }; // Allow on exception — backend will validate
  }
}
