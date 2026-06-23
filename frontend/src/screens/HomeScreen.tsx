/**
 * Home Screen — Smart Tire Analyzer Dashboard
 * Entry point showing scan button, quick stats, and recent analysis.
 */

import React, { useEffect } from "react";
import {
  View,
  Text,
  TouchableOpacity,
  ScrollView,
  StyleSheet,
} from "react-native";
import Dimensions from "react-native";
import StatusBar from "react-native";
import Animated from "react-native";
import { useNavigation } from "@react-navigation/native";
import { SafeAreaView } from "react-native-safe-area-context";
import { useAnalysisStore } from "../store/useAnalysisStore";
import { useHistoryStore } from "../store/useHistoryStore";
import { RiskBadge } from "../components/RiskBadge";
import { TireHealthGauge } from "../components/TireHealthGauge";

const { width } = Dimensions.get("window");

const COLORS = {
  bg: "#0D1117",
  card: "#161B22",
  border: "#30363D",
  accent: "#58A6FF",
  accentGreen: "#3FB950",
  accentOrange: "#F0883E",
  accentRed: "#F85149",
  textPrimary: "#F0F6FC",
  textSecondary: "#8B949E",
  textMuted: "#484F58",
};

export default function HomeScreen() {
  const navigation = useNavigation();
  const { latestAnalysis } = useAnalysisStore();
  const { history, loadHistory } = useHistoryStore();
  const pulseAnimRef = React.useRef<any>(null);
  if (pulseAnimRef.current === null) {
    pulseAnimRef.current = new Animated.Value(1);
  }
  const pulseAnim = pulseAnimRef.current;

  useEffect(() => {
    loadHistory();
    // Pulse animation for scan button
    const pulse = Animated.loop(
      Animated.sequence([
        Animated.timing(pulseAnim, { toValue: 1.04, duration: 900, useNativeDriver: true }),
        Animated.timing(pulseAnim, { toValue: 1.0, duration: 900, useNativeDriver: true }),
      ])
    );
    pulse.start();
    return () => pulse.stop();
  }, [loadHistory, pulseAnim]);

  const recentItems = history.slice(0, 3);

  return (
    <SafeAreaView style={styles.container}>
      <StatusBar barStyle="light-content" backgroundColor={COLORS.bg} />
      <ScrollView showsVerticalScrollIndicator={false} contentContainerStyle={styles.scroll}>

        {/* ── Header ─────────────────────────────────────────────────────── */}
        <View style={styles.header}>
          <View>
            <Text style={styles.headerTitle}>Smart Tire</Text>
            <Text style={styles.headerSubtitle}>AI Tire Intelligence System</Text>
          </View>
          <TouchableOpacity
            style={styles.historyBtn}
            onPress={() => navigation.navigate("History")}
          >
            <Text style={styles.historyBtnText}>History</Text>
          </TouchableOpacity>
        </View>

        {/* ── Central Scan Button ─────────────────────────────────────────── */}
        <View style={styles.scanSection}>
          <Animated.View style={{ transform: [{ scale: pulseAnim }] }}>
            <TouchableOpacity
              style={styles.scanButton}
              onPress={() => navigation.navigate("Camera")}
              activeOpacity={0.85}
            >
              <Text style={styles.scanIcon}>📷</Text>
              <Text style={styles.scanButtonText}>SCAN TIRE</Text>
              <Text style={styles.scanButtonSub}>Point camera at tire tread</Text>
            </TouchableOpacity>
          </Animated.View>
        </View>

        {/* ── Latest Result Card ──────────────────────────────────────────── */}
        {latestAnalysis && (
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>Latest Analysis</Text>
            <TouchableOpacity
              style={styles.latestCard}
              onPress={() => navigation.navigate("Result", { data: latestAnalysis })}
            >
              <View style={styles.latestCardRow}>
                <TireHealthGauge
                  score={latestAnalysis.predictions?.health_score || 0}
                  size={72}
                />
                <View style={styles.latestCardInfo}>
                  <RiskBadge level={latestAnalysis.risk_level} />
                  <Text style={styles.latestTread}>
                    Avg Tread: {latestAnalysis.predictions?.tread_depths_mm?.average?.toFixed(1)}mm
                  </Text>
                  <Text style={styles.latestLife}>
                    ~{(latestAnalysis.predictions?.remaining_life_km || 0).toLocaleString()} km remaining
                  </Text>
                </View>
              </View>
              <Text style={styles.latestAdvice} numberOfLines={2}>
                {latestAnalysis.reasoning?.driving_advice}
              </Text>
            </TouchableOpacity>
          </View>
        )}

        {/* ── Quick Stats ─────────────────────────────────────────────────── */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Fleet Overview</Text>
          <View style={styles.statsRow}>
            <View style={[styles.statCard, { borderColor: COLORS.accentGreen }]}>
              <Text style={[styles.statValue, { color: COLORS.accentGreen }]}>
                {history.filter((h: any) => h.risk_level === "LOW").length}
              </Text>
              <Text style={styles.statLabel}>Safe</Text>
            </View>
            <View style={[styles.statCard, { borderColor: COLORS.accentOrange }]}>
              <Text style={[styles.statValue, { color: COLORS.accentOrange }]}>
                {history.filter((h: any) => ["MODERATE", "HIGH"].includes(h.risk_level)).length}
              </Text>
              <Text style={styles.statLabel}>Warning</Text>
            </View>
            <View style={[styles.statCard, { borderColor: COLORS.accentRed }]}>
              <Text style={[styles.statValue, { color: COLORS.accentRed }]}>
                {history.filter((h: any) => h.risk_level === "CRITICAL").length}
              </Text>
              <Text style={styles.statLabel}>Critical</Text>
            </View>
          </View>
        </View>

        {/* ── Recent Scans ────────────────────────────────────────────────── */}
        {recentItems.length > 0 && (
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>Recent Scans</Text>
            {recentItems.map((item: any) => (
              <TouchableOpacity
                key={item.session_id}
                style={styles.recentItem}
                onPress={() => navigation.navigate("Result", { sessionId: item.session_id })}
              >
                <View style={styles.recentLeft}>
                  <RiskBadge level={item.risk_level} compact />
                  <View style={styles.recentInfo}>
                    <Text style={styles.recentTread}>{item.avg_tread_mm?.toFixed(1)}mm avg tread</Text>
                    <Text style={styles.recentDate}>
                      {new Date(item.timestamp).toLocaleDateString()}
                    </Text>
                  </View>
                </View>
                <Text style={styles.recentArrow}>›</Text>
              </TouchableOpacity>
            ))}
          </View>
        )}

        {/* ── Empty State ─────────────────────────────────────────────────── */}
        {history.length === 0 && !latestAnalysis && (
          <View style={styles.emptyState}>
            <Text style={styles.emptyIcon}>🔍</Text>
            <Text style={styles.emptyTitle}>No scans yet</Text>
            <Text style={styles.emptyText}>
              Tap the SCAN TIRE button to analyze your first tire
            </Text>
          </View>
        )}

      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: COLORS.bg },
  scroll: { paddingHorizontal: 16, paddingBottom: 32 },
  header: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    paddingTop: 16,
    paddingBottom: 8,
  },
  headerTitle: { fontSize: 26, fontWeight: "700", color: COLORS.textPrimary },
  headerSubtitle: { fontSize: 12, color: COLORS.textSecondary, marginTop: 2 },
  historyBtn: {
    paddingHorizontal: 14,
    paddingVertical: 6,
    borderRadius: 20,
    borderWidth: 1,
    borderColor: COLORS.border,
  },
  historyBtnText: { color: COLORS.accent, fontSize: 13 },
  scanSection: { alignItems: "center", paddingVertical: 32 },
  scanButton: {
    width: 180,
    height: 180,
    borderRadius: 90,
    backgroundColor: COLORS.accent,
    alignItems: "center",
    justifyContent: "center",
    shadowColor: COLORS.accent,
    shadowOffset: { width: 0, height: 0 },
    shadowOpacity: 0.5,
    shadowRadius: 24,
    elevation: 12,
  },
  scanIcon: { fontSize: 40, marginBottom: 8 },
  scanButtonText: { fontSize: 18, fontWeight: "800", color: "#fff" },
  scanButtonSub: { fontSize: 11, color: "rgba(255,255,255,0.8)", marginTop: 4 },
  section: { marginBottom: 24 },
  sectionTitle: {
    fontSize: 16,
    fontWeight: "600",
    color: COLORS.textPrimary,
    marginBottom: 12,
  },
  latestCard: {
    backgroundColor: COLORS.card,
    borderRadius: 14,
    padding: 16,
    borderWidth: 1,
    borderColor: COLORS.border,
  },
  latestCardRow: { flexDirection: "row", alignItems: "center", marginBottom: 10 },
  latestCardInfo: { flex: 1, marginLeft: 16 },
  latestTread: { fontSize: 15, color: COLORS.textPrimary, fontWeight: "600", marginTop: 6 },
  latestLife: { fontSize: 12, color: COLORS.textSecondary, marginTop: 3 },
  latestAdvice: { fontSize: 12, color: COLORS.textSecondary, lineHeight: 18 },
  statsRow: { flexDirection: "row", gap: 12 },
  statCard: {
    flex: 1,
    backgroundColor: COLORS.card,
    borderRadius: 12,
    padding: 14,
    alignItems: "center",
    borderWidth: 1,
  },
  statValue: { fontSize: 28, fontWeight: "800" },
  statLabel: { fontSize: 11, color: COLORS.textSecondary, marginTop: 4 },
  recentItem: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    backgroundColor: COLORS.card,
    borderRadius: 10,
    padding: 12,
    marginBottom: 8,
    borderWidth: 1,
    borderColor: COLORS.border,
  },
  recentLeft: { flexDirection: "row", alignItems: "center", gap: 12 },
  recentInfo: {},
  recentTread: { fontSize: 13, color: COLORS.textPrimary, fontWeight: "600" },
  recentDate: { fontSize: 11, color: COLORS.textMuted, marginTop: 2 },
  recentArrow: { fontSize: 22, color: COLORS.textMuted },
  emptyState: { alignItems: "center", paddingTop: 60 },
  emptyIcon: { fontSize: 56, marginBottom: 16 },
  emptyTitle: { fontSize: 20, fontWeight: "600", color: COLORS.textPrimary },
  emptyText: {
    fontSize: 14,
    color: COLORS.textSecondary,
    textAlign: "center",
    marginTop: 8,
    lineHeight: 22,
  },
});
