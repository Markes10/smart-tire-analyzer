/**
 * History Screen — Browse and filter past tire analysis records.
 */

import React, { useEffect, useState, useCallback } from "react";
import {
  View, Text, TouchableOpacity,
  StyleSheet, TextInput,
} from "react-native";
import FlatList from "react-native";
import RefreshControl from "react-native";
import Dimensions from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { useNavigation } from "@react-navigation/native";
import { useHistoryStore } from "../store/useHistoryStore";
import { RiskBadge } from "../components/RiskBadge";


const RISK_LEVELS = ["ALL", "LOW", "MODERATE", "HIGH", "CRITICAL"];
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
  textMuted: "#484F58",
};


export default function HistoryScreen() {
  const navigation = useNavigation();
  const { history, isLoading, loadHistory } = useHistoryStore();
  const [filter, setFilter] = useState("ALL");
  const [search, setSearch] = useState("");
  const [refreshing, setRefreshing] = useState(false);

  useEffect(() => {
    loadHistory();
  }, []);

  const onRefresh = useCallback(async () => {
    setRefreshing(true);
    await loadHistory(1);
    setRefreshing(false);
  }, []);

  // Filter + search
  const filtered = history.filter((item: any) => {
    const matchRisk = filter === "ALL" || item.risk_level === filter;
    const matchSearch =
      !search ||
      item.wear_pattern?.toLowerCase().includes(search.toLowerCase()) ||
      item.session_id?.toLowerCase().includes(search.toLowerCase());
    return matchRisk && matchSearch;
  });

  const renderItem = ({ item, index }: { item: any; index: number }) => {
    const avgTread = item.avg_tread_mm || 0;
    const health = item.health_score || 0;
    const date = new Date(item.timestamp);
    const isToday = new Date().toDateString() === date.toDateString();
    // ...existing code...

    const displayDate = isToday
      ? `Today ${date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}`
      : date.toLocaleDateString([], { month: "short", day: "2-digit", year: "numeric" });

    return (
      <TouchableOpacity
        style={styles.card}
        onPress={() => navigation.navigate("Result", { sessionId: item.session_id })}
        activeOpacity={0.75}
      >
        <View style={styles.cardTop}>
          <View style={styles.cardLeft}>
            <RiskBadge level={item.risk_level} />
            <Text style={styles.treadText}>{avgTread.toFixed(1)}mm avg tread</Text>
            <Text style={styles.dateText}>{displayDate}</Text>
          </View>
          <View style={styles.cardRight}>
            <View style={styles.healthCircle}>
              <Text style={[styles.healthVal, { color: health >= 7 ? COLORS.green : health >= 5 ? COLORS.orange : COLORS.red }]}>\n                {health.toFixed(1)}
              </Text>
              <Text style={styles.healthLabel}>Health</Text>
            </View>
          </View>
        </View>

        <View style={styles.cardBottom}>
          <View style={styles.pill}>
            <Text style={styles.pillText}>
              {item.wear_pattern?.replace(/_/g, " ") || "—"}
            </Text>
          </View>
          <Text style={styles.remainingText}>
            ~{Math.round(item.remaining_life_km || 0).toLocaleString()} km left
          </Text>
        </View>
      </TouchableOpacity>
    );
  };

  const renderEmpty = (): React.ReactElement => (
    <View style={styles.emptyState}>
      <Text style={styles.emptyIcon}>📋</Text>
      <Text style={styles.emptyTitle}>No records found</Text>
      <Text style={styles.emptyText}>
        {filter !== "ALL" || search
          ? "Try changing your filter or search term"
          : "Complete a tire scan to see history here"}
      </Text>
    </View>
  );

  // Summary stats
  const totalScans = filtered.length;
  const avgHealth = totalScans > 0
    ? (filtered.reduce((s: number, h: any) => s + (h.health_score || 0), 0) / totalScans).toFixed(1)
    : "—";
  const criticalCount = filtered.filter((h: any) => h.risk_level === "CRITICAL").length;

  return (
    <SafeAreaView style={styles.container}>
      {/* ── Header ─────────────────────────────────────────────────────── */}
      <View style={styles.header}>
        <Text style={styles.headerTitle}>Analysis History</Text>
        <Text style={styles.headerSub}>{totalScans} records</Text>
      </View>

      {/* ── Summary Bar ─────────────────────────────────────────────────── */}
      <View style={styles.summaryBar}>
        <View style={styles.summaryItem}>
          <Text style={styles.summaryValue}>{totalScans}</Text>
          <Text style={styles.summaryLabel}>Total Scans</Text>
        </View>
        <View style={styles.summaryDivider} />
        <View style={styles.summaryItem}>
          <Text style={[styles.summaryValue, { color: COLORS.accent }]}>{avgHealth}</Text>
          <Text style={styles.summaryLabel}>Avg Health</Text>
        </View>
        <View style={styles.summaryDivider} />
        <View style={styles.summaryItem}>
          <Text style={[styles.summaryValue, { color: criticalCount > 0 ? COLORS.red : COLORS.green }]}>\n            {criticalCount}
          </Text>
          <Text style={styles.summaryLabel}>Critical</Text>
        </View>
      </View>

      {/* ── Search ──────────────────────────────────────────────────────── */}
      <View style={styles.searchBox}>
        <Text style={styles.searchIcon}>🔍</Text>
        <TextInput
          style={styles.searchInput}
          value={search}
          onChangeText={setSearch}
          placeholder="Search by wear pattern or session ID..."
          placeholderTextColor={COLORS.textMuted}
        />
        {search.length > 0 && (
          <TouchableOpacity onPress={() => setSearch("")}>\n            <Text style={styles.clearSearch}>✕</Text>
          </TouchableOpacity>
        )}
      </View>

      {/* ── Risk Filter Tabs ─────────────────────────────────────────────── */}
      <View style={styles.filterRow}>
        {RISK_LEVELS.map((level: string) => (
          <TouchableOpacity
            key={level}
            style={[styles.filterTab, filter === level && styles.filterTabActive]}
            onPress={() => setFilter(level)}
          >
            <Text style={[styles.filterTabText, filter === level && styles.filterTabTextActive]}>
              {level}
            </Text>
          </TouchableOpacity>
        ))}
      </View>

      {/* ── List ────────────────────────────────────────────────────────── */}
      <FlatList
        data={filtered}
        keyExtractor={(item: any) => item.session_id}
        renderItem={renderItem}
        ListEmptyComponent={renderEmpty}
        contentContainerStyle={styles.list}
        refreshControl={
          <RefreshControl
            refreshing={refreshing}
            onRefresh={onRefresh}
            tintColor={COLORS.accent}
          />
        }
        showsVerticalScrollIndicator={false}
        ItemSeparatorComponent={() => <View style={{ height: 10 }} />}
      />
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: COLORS.bg },
  header: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    paddingHorizontal: 16,
    paddingTop: 16,
    paddingBottom: 8,
  },
  headerTitle: { fontSize: 22, fontWeight: "700", color: COLORS.textPrimary },
  headerSub: { fontSize: 12, color: COLORS.textSecondary },
  summaryBar: {
    flexDirection: "row",
    marginHorizontal: 16,
    marginBottom: 12,
    backgroundColor: COLORS.card,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: COLORS.border,
    padding: 12,
  },
  summaryItem: { flex: 1, alignItems: "center" },
  summaryValue: { fontSize: 20, fontWeight: "800", color: COLORS.textPrimary },
  summaryLabel: { fontSize: 11, color: COLORS.textSecondary, marginTop: 2 },
  summaryDivider: { width: 1, backgroundColor: COLORS.border, marginHorizontal: 8 },
  searchBox: {
    flexDirection: "row",
    alignItems: "center",
    marginHorizontal: 16,
    marginBottom: 10,
    backgroundColor: COLORS.card,
    borderRadius: 10,
    borderWidth: 1,
    borderColor: COLORS.border,
    paddingHorizontal: 12,
    height: 42,
    gap: 8,
  },
  searchIcon: { fontSize: 16 },
  searchInput: { flex: 1, color: COLORS.textPrimary, fontSize: 13 },
  clearSearch: { color: COLORS.textMuted, fontSize: 16, padding: 4 },
  filterRow: {
    flexDirection: "row",
    paddingHorizontal: 16,
    gap: 8,
    marginBottom: 12,
  },
  filterTab: {
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 20,
    backgroundColor: COLORS.card,
    borderWidth: 1,
    borderColor: COLORS.border,
  },
  filterTabActive: { backgroundColor: COLORS.accent + "22", borderColor: COLORS.accent },
  filterTabText: { fontSize: 11, color: COLORS.textSecondary, fontWeight: "600" },
  filterTabTextActive: { color: COLORS.accent },
  list: { paddingHorizontal: 16, paddingBottom: 32 },
  card: {
    backgroundColor: COLORS.card,
    borderRadius: 14,
    padding: 14,
    borderWidth: 1,
    borderColor: COLORS.border,
  },
  cardTop: { flexDirection: "row", justifyContent: "space-between", marginBottom: 10 },
  cardLeft: { gap: 6 },
  cardRight: { alignItems: "flex-end" },
  treadText: { fontSize: 15, fontWeight: "700", color: COLORS.textPrimary },
  dateText: { fontSize: 11, color: COLORS.textMuted },
  healthCircle: {
    width: 56, height: 56, borderRadius: 28,
    backgroundColor: "#0D1117", alignItems: "center", justifyContent: "center",
    borderWidth: 2, borderColor: COLORS.border,
  },
  healthVal: { fontSize: 16, fontWeight: "800" },
  healthLabel: { fontSize: 9, color: COLORS.textSecondary },
  cardBottom: { flexDirection: "row", alignItems: "center", justifyContent: "space-between" },
  pill: {
    backgroundColor: "#30363D", borderRadius: 20,
    paddingHorizontal: 10, paddingVertical: 4,
  },
  pillText: { fontSize: 11, color: COLORS.textSecondary, textTransform: "capitalize" },
  remainingText: { fontSize: 12, color: COLORS.accent, fontWeight: "600" },
  emptyState: { flex: 1, alignItems: "center", paddingTop: 80 },
  emptyIcon: { fontSize: 48, marginBottom: 16 },
  emptyTitle: { fontSize: 18, fontWeight: "600", color: COLORS.textPrimary },
  emptyText: { fontSize: 13, color: COLORS.textSecondary, textAlign: "center", marginTop: 8, lineHeight: 20 },
});
