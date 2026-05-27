/**
 * RiskBadge — Compact or full badge showing risk level with color coding.
 */

import React from "react";
import { View, Text, StyleSheet } from "react-native";

interface RiskBadgeProps {
  level: string;
  compact?: boolean;
}

const RISK_CONFIG: Record<string, { color: string; bg: string; icon: string }> = {
  CRITICAL: { color: "#F85149", bg: "#F8514922", icon: "🔴" },
  HIGH:     { color: "#F0883E", bg: "#F0883E22", icon: "🟠" },
  MODERATE: { color: "#E3B341", bg: "#E3B34122", icon: "🟡" },
  LOW:      { color: "#3FB950", bg: "#3FB95022", icon: "🟢" },
};

export function RiskBadge({ level, compact = false }: RiskBadgeProps) {
  const cfg = RISK_CONFIG[level] ?? RISK_CONFIG["LOW"];

  if (compact) {
    return (
      <View style={[styles.compact, { backgroundColor: cfg.bg, borderColor: cfg.color }]}>
        <Text style={styles.compactIcon}>{cfg.icon}</Text>
      </View>
    );
  }

  return (
    <View style={[styles.badge, { backgroundColor: cfg.bg, borderColor: cfg.color }]}>
      <Text style={[styles.text, { color: cfg.color }]}>{level}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  badge: {
    alignSelf: "flex-start",
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: 20,
    borderWidth: 1,
  },
  text: { fontSize: 11, fontWeight: "700", letterSpacing: 0.5 },
  compact: {
    width: 30,
    height: 30,
    borderRadius: 15,
    alignItems: "center",
    justifyContent: "center",
    borderWidth: 1,
  },
  compactIcon: { fontSize: 14 },
});
