/**
 * WearPatternCard — Visual card explaining detected tire wear pattern.
 */

import React from "react";
import { View, Text, StyleSheet } from "react-native";

interface WearPatternCardProps {
  pattern: string;
  cause: string;
  severity: string;
  confidence: number;
}

const WEAR_INFO: Record<string, { icon: string; desc: string; fix: string }> = {
  center_wear:   { icon: "⬛", desc: "Center tread worn faster than edges", fix: "Reduce tire inflation pressure" },
  edge_wear:     { icon: "◀▶", desc: "Edges worn faster than center tread", fix: "Increase tire inflation pressure" },
  side_wall_wear:{ icon: "SW", desc: "Outer shoulder wear concentrated on the tire edge", fix: "Inspect wheel alignment, camber, and outer shoulder condition" },
  patchy_wear:   { icon: "🔲", desc: "Irregular patches of heavy wear", fix: "Wheel balance and alignment check required" },
  uniform_wear:  { icon: "✅", desc: "Even tread wear across the tire", fix: "Normal wear — maintain regular inspections" },
  one_side_wear: { icon: "◀", desc: "One shoulder significantly more worn", fix: "Camber angle alignment adjustment needed" },
  cupping_wear:  { icon: "〜", desc: "Scalloped/cupped wear pattern", fix: "Inspect shock absorbers and suspension" },
};

const SEVERITY_COLORS: Record<string, string> = {
  low: "#3FB950",
  moderate: "#E3B341",
  high: "#F0883E",
  critical: "#F85149",
};

export function WearPatternCard({ pattern, cause, severity, confidence }: WearPatternCardProps) {
  const info = WEAR_INFO[pattern] ?? { icon: "❓", desc: cause, fix: "Consult a tire specialist" };
  const sevColor = SEVERITY_COLORS[severity?.toLowerCase()] ?? "#8B949E";
  const displayPattern = (pattern ?? "unknown").replace(/_/g, " ");

  return (
    <View style={styles.card}>
      <View style={styles.topRow}>
        <Text style={styles.icon}>{info.icon}</Text>
        <View style={styles.topInfo}>
          <Text style={styles.patternName}>{displayPattern}</Text>
          <View style={[styles.severityBadge, { backgroundColor: sevColor + "22", borderColor: sevColor }]}>
            <Text style={[styles.severityText, { color: sevColor }]}>
              {severity?.toUpperCase() ?? "UNKNOWN"}
            </Text>
          </View>
        </View>
        <View style={styles.confBox}>
          <Text style={styles.confVal}>{Math.round((confidence ?? 0) * 100)}%</Text>
          <Text style={styles.confLabel}>confidence</Text>
        </View>
      </View>

      <View style={styles.divider} />

      <Text style={styles.descLabel}>Description</Text>
      <Text style={styles.descText}>{info.desc}</Text>

      <Text style={styles.fixLabel}>Recommended Action</Text>
      <Text style={styles.fixText}>🔧 {info.fix}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: "#161B22",
    borderRadius: 14,
    padding: 16,
    borderWidth: 1,
    borderColor: "#30363D",
  },
  topRow: { flexDirection: "row", alignItems: "center", gap: 12, marginBottom: 12 },
  icon: { fontSize: 28 },
  topInfo: { flex: 1, gap: 6 },
  patternName: {
    fontSize: 15, fontWeight: "700", color: "#F0F6FC",
    textTransform: "capitalize",
  },
  severityBadge: {
    alignSelf: "flex-start", paddingHorizontal: 10,
    paddingVertical: 3, borderRadius: 20, borderWidth: 1,
  },
  severityText: { fontSize: 10, fontWeight: "700" },
  confBox: { alignItems: "center" },
  confVal: { fontSize: 20, fontWeight: "800", color: "#58A6FF" },
  confLabel: { fontSize: 10, color: "#8B949E" },
  divider: { height: 1, backgroundColor: "#30363D", marginBottom: 12 },
  descLabel: { fontSize: 11, color: "#8B949E", marginBottom: 4, fontWeight: "600" },
  descText: { fontSize: 13, color: "#F0F6FC", lineHeight: 20, marginBottom: 12 },
  fixLabel: { fontSize: 11, color: "#8B949E", marginBottom: 4, fontWeight: "600" },
  fixText: { fontSize: 13, color: "#3FB950", lineHeight: 20 },
});
