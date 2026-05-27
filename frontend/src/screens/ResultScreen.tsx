/**
 * Result Screen — Full tire analysis report display.
 * Shows tread depths, health gauge, wear pattern, Gemini reasoning,
 * risk level, alerts, and driving advice.
 */

import React, { useState } from "react";
import {
  View,
  Text,
  ScrollView,
  StyleSheet,
  TouchableOpacity,
} from "react-native";
import Dimensions from "react-native";
import Share from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { useRoute, useNavigation } from "@react-navigation/native";
import { TireHealthGauge } from "../components/TireHealthGauge";
import { WearPatternCard } from "../components/WearPatternCard";
import { RiskBadge } from "../components/RiskBadge";
import { FeedbackModal } from "../components/FeedbackModal";

const { width } = Dimensions.get("window");

const COLORS = {
  bg: "#0D1117",
  card: "#161B22",
  border: "#30363D",
  accent: "#58A6FF",
  green: "#3FB950",
  orange: "#F0883E",
  red: "#F85149",
  yellow: "#E3B341",
  textPrimary: "#F0F6FC",
  textSecondary: "#8B949E",
};

const RISK_COLORS: Record<string, string> = {
  CRITICAL: "#F85149",
  HIGH: "#F0883E",
  MODERATE: "#E3B341",
  LOW: "#3FB950",
};

export default function ResultScreen() {
  const route = useRoute() as any;
  const navigation = useNavigation();
  const [feedbackVisible, setFeedbackVisible] = useState(false);
  const data = route.params?.data;

  if (!data) {
    return (
      <SafeAreaView style={styles.container}>
        <Text style={styles.errorText}>No analysis data available</Text>
      </SafeAreaView>
    );
  }

  const { risk_level, predictions, reasoning, alerts, context, confidence } = data;
  const tread = predictions?.tread_depths_mm || {};
  const wear = predictions?.wear_pattern || {};
  const health = predictions?.health_score || 0;
  const remaining = predictions?.remaining_life_km || 0;
  const riskColor = RISK_COLORS[risk_level] || COLORS.green;

  const handleShare = async () => {
    await Share.share({
      message: `Smart Tire Analysis Report\n\nHealth: ${health.toFixed(1)}/10\nAvg Tread: ${tread.average?.toFixed(1)}mm\nRisk: ${risk_level}\nRemaining Life: ~${remaining.toLocaleString()} km\n\nAdvice: ${reasoning?.driving_advice}`,
      title: "Tire Analysis Report",
    });
  };

  return (
    <SafeAreaView style={styles.container}>
      <ScrollView showsVerticalScrollIndicator={false} contentContainerStyle={styles.scroll}>

        {/* ── Risk Banner ───────────────────────────────────────────────── */}
        <View style={[styles.riskBanner, { backgroundColor: riskColor + "22", borderColor: riskColor }]}>
          <View style={styles.riskBannerLeft}>
            <Text style={[styles.riskLevel, { color: riskColor }]}>{risk_level}</Text>
            <Text style={styles.riskStatus}>{data.status}</Text>
          </View>
          <View style={styles.riskBannerRight}>
            <Text style={styles.confidenceLabel}>Confidence</Text>
            <Text style={styles.confidenceValue}>{Math.round((confidence || 0) * 100)}%</Text>
          </View>
        </View>

        {/* ── Alerts ───────────────────────────────────────────────────── */}
        {alerts?.length > 0 && (
          <View style={styles.section}>
            {alerts.map((alert: any, i: number) => (
              <View
                key={i}
                style={[
                  styles.alertItem,
                  { borderColor: RISK_COLORS[alert.level] || COLORS.orange }
                ]}
              >
                <Text style={[styles.alertLevel, { color: RISK_COLORS[alert.level] }]}>
                  ⚠ {alert.level}
                </Text>
                <Text style={styles.alertMsg}>{alert.message}</Text>
              </View>
            ))}
          </View>
        )}

        {/* ── Health Gauge + Life ──────────────────────────────────────── */}
        <View style={styles.gaugeRow}>
          <View style={styles.gaugeCard}>
            <TireHealthGauge score={health} size={100} />
            <Text style={styles.gaugeLabel}>Health Score</Text>
          </View>
          <View style={styles.lifeCard}>
            <Text style={styles.lifeValue}>{Math.round(remaining).toLocaleString()}</Text>
            <Text style={styles.lifeUnit}>km remaining</Text>
            <View style={styles.lifeDivider} />
            <Text style={styles.lifeSubValue}>~{Math.round(remaining / 15)} days</Text>
            <Text style={styles.lifeSubLabel}>at avg 15 km/day</Text>
          </View>
        </View>

        {/* ── Tread Depths ─────────────────────────────────────────────── */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Tread Depth Readings</Text>
          <View style={styles.treadGrid}>
            {["tread_1", "tread_2", "tread_3", "tread_4"].map((key, i) => {
              const val = tread[key] || 0;
              const color = val < 1.6 ? COLORS.red : val < 3.0 ? COLORS.orange : COLORS.green;
              return (
                <View key={i} style={[styles.treadCell, { borderColor: color }]}>
                  <Text style={styles.treadPos}>T{i + 1}</Text>
                  <Text style={[styles.treadVal, { color }]}>{val.toFixed(1)}</Text>
                  <Text style={styles.treadUnit}>mm</Text>
                </View>
              );
            })}
          </View>
          <View style={styles.treadAvgRow}>
            <Text style={styles.treadAvgLabel}>Average:</Text>
            <Text style={styles.treadAvgValue}>{tread.average?.toFixed(2)}mm</Text>
            <Text style={styles.treadAvgLabel}>Differential:</Text>
            <Text style={styles.treadAvgValue}>
              {((tread.max || 0) - (tread.min || 0)).toFixed(1)}mm
            </Text>
          </View>
        </View>

        {/* ── Wear Pattern ─────────────────────────────────────────────── */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Wear Pattern Analysis</Text>
          <WearPatternCard
            pattern={wear.label}
            cause={wear.cause}
            severity={wear.severity}
            confidence={wear.confidence}
          />
        </View>

        {/* ── AI Reasoning ─────────────────────────────────────────────── */}
        <View style={styles.section}>
          <View style={styles.reasoningHeader}>
            <Text style={styles.sectionTitle}>AI Driving Advice</Text>
            <Text style={styles.reasoningSource}>
              {reasoning?.source === "gemini" ? "✨ Gemini AI" : "📋 Rule-based"}
            </Text>
          </View>
          <View style={styles.reasoningCard}>
            <Text style={styles.reasoningText}>{reasoning?.driving_advice}</Text>
            {reasoning?.additional_notes && (
              <Text style={styles.reasoningNotes}>💡 {reasoning.additional_notes}</Text>
            )}
            {data.replace_immediately && (
              <View style={styles.replaceNow}>
                <Text style={styles.replaceNowText}>
                  🔴 REPLACE TIRES IMMEDIATELY — Safety Critical
                </Text>
              </View>
            )}
          </View>
        </View>

        {/* ── Context ──────────────────────────────────────────────────── */}
        {context && (context.weather_condition || context.road_condition) && (
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>Environmental Context</Text>
            <View style={styles.contextGrid}>
              {context.weather_condition && (
                <View style={styles.contextItem}>
                  <Text style={styles.contextLabel}>Weather</Text>
                  <Text style={styles.contextValue}>{context.weather_condition}</Text>
                </View>
              )}
              {context.temperature_c != null && (
                <View style={styles.contextItem}>
                  <Text style={styles.contextLabel}>Temperature</Text>
                  <Text style={styles.contextValue}>{context.temperature_c}°C</Text>
                </View>
              )}
              {context.road_condition && (
                <View style={styles.contextItem}>
                  <Text style={styles.contextLabel}>Road</Text>
                  <Text style={styles.contextValue}>{context.road_condition}</Text>
                </View>
              )}
              {context.terrain_type && (
                <View style={styles.contextItem}>
                  <Text style={styles.contextLabel}>Terrain</Text>
                  <Text style={styles.contextValue}>{context.terrain_type}</Text>
                </View>
              )}
            </View>
          </View>
        )}

        {/* ── Action Buttons ────────────────────────────────────────────── */}
        <View style={styles.actions}>
          <TouchableOpacity style={styles.feedbackBtn} onPress={() => setFeedbackVisible(true)}>
            <Text style={styles.feedbackBtnText}>✏️ Correct This Result</Text>
          </TouchableOpacity>
          <TouchableOpacity style={styles.shareBtn} onPress={handleShare}>
            <Text style={styles.shareBtnText}>📤 Share Report</Text>
          </TouchableOpacity>
        </View>

      </ScrollView>

      <FeedbackModal
        visible={feedbackVisible}
        onClose={() => setFeedbackVisible(false)}
        sessionId={data.session_id}
        originalPrediction={data}
      />
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: COLORS.bg },
  scroll: { paddingHorizontal: 16, paddingBottom: 40 },
  errorText: { color: COLORS.textSecondary, textAlign: "center", marginTop: 100, fontSize: 16 },
  riskBanner: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    borderRadius: 14,
    borderWidth: 1,
    padding: 16,
    marginTop: 16,
    marginBottom: 16,
  },
  riskBannerLeft: {},
  riskLevel: { fontSize: 22, fontWeight: "800" },
  riskStatus: { fontSize: 12, color: COLORS.textSecondary, marginTop: 4 },
  riskBannerRight: { alignItems: "flex-end" },
  confidenceLabel: { fontSize: 11, color: COLORS.textSecondary },
  confidenceValue: { fontSize: 22, fontWeight: "700", color: COLORS.textPrimary },
  section: { marginBottom: 20 },
  sectionTitle: { fontSize: 16, fontWeight: "600", color: COLORS.textPrimary, marginBottom: 12 },
  alertItem: {
    backgroundColor: COLORS.card,
    borderRadius: 10,
    borderWidth: 1,
    padding: 12,
    marginBottom: 8,
  },
  alertLevel: { fontSize: 11, fontWeight: "700", marginBottom: 4 },
  alertMsg: { fontSize: 13, color: COLORS.textPrimary },
  gaugeRow: { flexDirection: "row", gap: 12, marginBottom: 20 },
  gaugeCard: {
    flex: 1,
    backgroundColor: COLORS.card,
    borderRadius: 14,
    padding: 16,
    alignItems: "center",
    borderWidth: 1,
    borderColor: COLORS.border,
  },
  gaugeLabel: { fontSize: 12, color: COLORS.textSecondary, marginTop: 8 },
  lifeCard: {
    flex: 1,
    backgroundColor: COLORS.card,
    borderRadius: 14,
    padding: 16,
    alignItems: "center",
    justifyContent: "center",
    borderWidth: 1,
    borderColor: COLORS.border,
  },
  lifeValue: { fontSize: 28, fontWeight: "800", color: COLORS.accent },
  lifeUnit: { fontSize: 12, color: COLORS.textSecondary, marginTop: 2 },
  lifeDivider: { height: 1, backgroundColor: COLORS.border, width: "80%", marginVertical: 8 },
  lifeSubValue: { fontSize: 16, fontWeight: "600", color: COLORS.textPrimary },
  lifeSubLabel: { fontSize: 11, color: COLORS.textSecondary },
  treadGrid: { flexDirection: "row", gap: 8, marginBottom: 10 },
  treadCell: {
    flex: 1,
    backgroundColor: COLORS.card,
    borderRadius: 10,
    padding: 12,
    alignItems: "center",
    borderWidth: 1,
  },
  treadPos: { fontSize: 10, color: COLORS.textSecondary, marginBottom: 4 },
  treadVal: { fontSize: 20, fontWeight: "700" },
  treadUnit: { fontSize: 10, color: COLORS.textSecondary },
  treadAvgRow: {
    flexDirection: "row",
    gap: 12,
    backgroundColor: COLORS.card,
    borderRadius: 10,
    padding: 12,
    borderWidth: 1,
    borderColor: COLORS.border,
  },
  treadAvgLabel: { fontSize: 12, color: COLORS.textSecondary },
  treadAvgValue: { fontSize: 13, fontWeight: "600", color: COLORS.textPrimary, flex: 1 },
  reasoningHeader: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: 12,
  },
  reasoningSource: { fontSize: 12, color: COLORS.accent },
  reasoningCard: {
    backgroundColor: COLORS.card,
    borderRadius: 14,
    padding: 16,
    borderWidth: 1,
    borderColor: COLORS.border,
  },
  reasoningText: { fontSize: 14, color: COLORS.textPrimary, lineHeight: 22 },
  reasoningNotes: {
    fontSize: 13,
    color: COLORS.textSecondary,
    marginTop: 10,
    lineHeight: 20,
  },
  replaceNow: {
    marginTop: 12,
    backgroundColor: COLORS.red + "22",
    borderRadius: 8,
    padding: 10,
    borderWidth: 1,
    borderColor: COLORS.red,
  },
  replaceNowText: { fontSize: 13, fontWeight: "700", color: COLORS.red },
  contextGrid: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: 10,
  },
  contextItem: {
    width: (width - 44) / 2,
    backgroundColor: COLORS.card,
    borderRadius: 10,
    padding: 12,
    borderWidth: 1,
    borderColor: COLORS.border,
  },
  contextLabel: { fontSize: 11, color: COLORS.textSecondary, marginBottom: 4 },
  contextValue: { fontSize: 14, fontWeight: "600", color: COLORS.textPrimary, textTransform: "capitalize" },
  actions: { flexDirection: "row", gap: 10 },
  feedbackBtn: {
    flex: 1,
    backgroundColor: COLORS.card,
    borderRadius: 12,
    padding: 14,
    alignItems: "center",
    borderWidth: 1,
    borderColor: COLORS.border,
  },
  feedbackBtnText: { color: COLORS.textSecondary, fontSize: 13, fontWeight: "600" },
  shareBtn: {
    flex: 1,
    backgroundColor: COLORS.accent,
    borderRadius: 12,
    padding: 14,
    alignItems: "center",
  },
  shareBtnText: { color: "#fff", fontSize: 13, fontWeight: "600" },
});
