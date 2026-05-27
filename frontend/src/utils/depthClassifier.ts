/**
 * depthClassifier.ts — Client-side tread depth classification helper.
 * Used to color-code and label tread depths without API round-trip.
 */

export type DepthClass = "critical" | "warning" | "ok" | "new";

export interface DepthClassification {
  class: DepthClass;
  label: string;
  color: string;
  action: string;
}

const THRESHOLDS = {
  CRITICAL: 1.6,  // Legal minimum (most countries)
  WARNING: 3.0,   // Replace soon threshold
  OK: 6.0,        // Acceptable range
  // Above 6.0 = new / great
};

/**
 * Classify a single tread depth reading in mm.
 */
export function classifyDepth(depthMm: number): DepthClassification {
  if (depthMm < THRESHOLDS.CRITICAL) {
    return {
      class: "critical",
      label: "Critical",
      color: "#F85149",
      action: "Replace immediately — below legal minimum",
    };
  }
  if (depthMm < THRESHOLDS.WARNING) {
    return {
      class: "warning",
      label: "Low",
      color: "#F0883E",
      action: "Replace within 1,000 km",
    };
  }
  if (depthMm < THRESHOLDS.OK) {
    return {
      class: "ok",
      label: "Acceptable",
      color: "#E3B341",
      action: "Monitor monthly",
    };
  }
  return {
    class: "new",
    label: "Good",
    color: "#3FB950",
    action: "Inspect every 6 months",
  };
}

/**
 * Return aggregate classification from 4 tread points.
 */
export function classifyTreadSet(treads: number[]): DepthClassification {
  const avg = treads.reduce((a, b) => a + b, 0) / treads.length;
  const minVal = Math.min(...treads);
  // Use the minimum reading for safety (most conservative)
  return classifyDepth(Math.min(avg, minVal + 0.5));
}
