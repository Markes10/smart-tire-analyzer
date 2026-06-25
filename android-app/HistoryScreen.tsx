import React, { useState, useMemo, useEffect, useRef } from 'react';
import {
  View,
  Text,
  StyleSheet,
  FlatList,
  TouchableOpacity,
  SafeAreaView,
  StatusBar,
  Alert,
  Share,
  Animated,
} from 'react-native';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';

export interface TireScan {
  id: number;
  timestamp: number;
  title: string;
  speed: number;
  pressure: number;
  temperature: number;
  wearPattern: 'Normal' | 'Center Wear' | 'Edge Wear' | 'Camber Wear' | 'Cupping Wear';
  overallHealth: number; // 0 to 100
  notes: string;
}

interface HistoryScreenProps {
  onSelectScan?: (scan: TireScan) => void;
  onNavigateBack?: () => void;
  initialScans?: TireScan[];
}

// Initial mockup / demo records matching Android counterparts
const DEMO_SCANS: TireScan[] = [
  {
    id: 1,
    timestamp: Date.now() - 3600000 * 24 * 3, // 3 days ago
    title: "Post-Highway Diagnostics",
    speed: 110,
    pressure: 34.2,
    temperature: 42.5,
    wearPattern: 'Normal',
    overallHealth: 95,
    notes: "Tire temperatures stabilized. Standard inflation levels detected on long haul run.",
  },
  {
    id: 2,
    timestamp: Date.now() - 3600000 * 24 * 10, // 10 days ago
    title: "City Rush Hour Traffic",
    speed: 45,
    pressure: 26.8,
    temperature: 31.0,
    wearPattern: 'Center Wear',
    overallHealth: 82,
    notes: "Slight under-inflation on front axle. Recommend checking valve stem seals.",
  },
  {
    id: 3,
    timestamp: Date.now() - 3600000 * 24 * 25, // 25 days ago
    title: "Camber Alignment Test",
    speed: 80,
    pressure: 31.5,
    temperature: 58.0,
    wearPattern: 'Camber Wear',
    overallHealth: 67,
    notes: "Outer shoulder wear detected. Inner belt temperature elevated by 15°C.",
  },
  {
    id: 4,
    timestamp: Date.now() - 3600000 * 24 * 40, // 40 days ago
    title: "Mountain Pass Drift Log",
    speed: 95,
    pressure: 38.5,
    temperature: 82.1,
    wearPattern: 'Edge Wear',
    overallHealth: 74,
    notes: "High thermal loading detected on lateral sidewall. Over-inflated hot reading.",
  }
];

export default function HistoryScreen({
  onSelectScan,
  onNavigateBack,
  initialScans = [],
}: HistoryScreenProps) {
  const [scans, setScans] = useState<TireScan[]>(initialScans);
  const [activeFilter, setActiveFilter] = useState<'30day' | 'all' | 'highStress' | 'critical'>('30day');
  
  // Animation instance for the chart fade transition
  const fadeAnim = useRef(new Animated.Value(1)).current;

  useEffect(() => {
    // Elegant fade transition animation sequence when the selected dataset changes
    Animated.sequence([
      Animated.timing(fadeAnim, {
        toValue: 0.15,
        duration: 120,
        useNativeDriver: false,
      }),
      Animated.timing(fadeAnim, {
        toValue: 1,
        duration: 380,
        useNativeDriver: false,
      })
    ]).start();
  }, [activeFilter]);

  // Sort scans by timestamp in descending order (newest first)
  const sortedScans = useMemo(() => {
    return [...scans].sort((a, b) => b.timestamp - a.timestamp);
  }, [scans]);

  const handleSelect = (scan: TireScan) => {
    if (onSelectScan) {
      onSelectScan(scan);
      Alert.alert(
        "Twin Updated",
        `Restoring 3D Digital Twin configuration to:\nType: ${scan.title}\nWear: ${scan.wearPattern}\nPressure: ${scan.pressure} PSI`,
        [{ text: "OK", onPress: onNavigateBack }]
      );
    } else {
      Alert.alert(
        scan.title,
        `Telemetry Summary:\n• Health: ${scan.overallHealth}%\n• Speed: ${scan.speed} km/h\n• Pressure: ${scan.pressure} PSI\n• wearPattern: ${scan.wearPattern}\n\nNotes: ${scan.notes}`
      );
    }
  };

  const handleDelete = (id: number) => {
    Alert.alert(
      "Delete Log Record?",
      "Are you sure you want to permanently delete this telemetry scan from historical cycles?",
      [
        { text: "Cancel", style: "cancel" },
        {
          text: "Delete",
          style: "destructive",
          onPress: () => {
            setScans(prev => prev.filter(scan => scan.id !== id));
          }
        }
      ]
    );
  };

  const handleSeed = () => {
    setScans(DEMO_SCANS);
  };

  const handleShare = async (scan: TireScan) => {
    try {
      await Share.share({
        message: `[Digital Twin 3D Diagnostics Log]\n${scan.title}\nDate: ${new Date(scan.timestamp).toDateString()}\nOverall Health: ${scan.overallHealth}%\nWear Pattern: ${scan.wearPattern}\nTelemetry: ${scan.pressure} PSI | ${scan.speed} km/h | ${scan.temperature}°C\nNotes: ${scan.notes}`
      });
    } catch (error) {
      console.error("Error sharing diagnostics session:", error);
    }
  };

  // Helper designed to pick semantic health status color
  const evaluateHealthColor = (score: number) => {
    if (score >= 90) return '#00ff66'; // Green / Excellent
    if (score >= 75) return '#ffaa00'; // Amber / Warning
    return '#ff3333'; // Red / Critical
  };

  const formatDate = (timestamp: number) => {
    const d = new Date(timestamp);
    const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
    const month = months[d.getMonth()];
    const day = d.getDate();
    const year = d.getFullYear();
    let hours = d.getHours();
    const minutes = d.getMinutes().toString().padStart(2, '0');
    const ampm = hours >= 12 ? 'PM' : 'AM';
    hours = hours % 12;
    hours = hours ? hours : 12; // the hour '0' should be '12'
    return `${month} ${day}, ${year} · ${hours}:${minutes} ${ampm}`;
  };

  const chartData = useMemo(() => {
    let filtered = [...scans];
    const thirtyDaysAgo = Date.now() - 30 * 24 * 60 * 60 * 1000;
    
    if (activeFilter === '30day') {
      filtered = scans.filter(s => s.timestamp >= thirtyDaysAgo);
    } else if (activeFilter === 'highStress') {
      filtered = scans.filter(s => s.temperature > 50 || s.pressure < 28 || s.speed > 90);
    } else if (activeFilter === 'critical') {
      filtered = scans.filter(s => s.overallHealth < 80 || s.wearPattern !== 'Normal');
    }

    const sorted = filtered.length >= 2 ? filtered : [...scans];
    return sorted
      .sort((a, b) => a.timestamp - b.timestamp)
      .map(s => ({
        ...s,
        dateStr: new Date(s.timestamp).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
      }));
  }, [scans, activeFilter]);

  const projectionData = useMemo(() => {
    const latestHealth = scans.length > 0 ? scans[0].overallHealth : 90;
    const distances = [0, 2000, 4000, 6000, 8000, 10000];
    return distances.map((d) => ({
      distanceStr: `${d / 1000}k km`,
      nominal: Math.max(10, Math.round(latestHealth - (d / 1000) * 1.5)),
      stressed: Math.max(10, Math.round(latestHealth - (d / 1000) * 3.5)),
      thermal: Math.max(10, Math.round(latestHealth - (d / 1000) * 5.8)),
    }));
  }, [scans]);

  return (
    <SafeAreaView style={styles.container}>
      <StatusBar barStyle="light-content" />

      {/* Futuristic HUD Header Bar */}
      <View style={styles.header}>
        {onNavigateBack && (
          <TouchableOpacity onPress={onNavigateBack} style={styles.backButton}>
            <Text style={styles.backButtonText}>🗙</Text>
          </TouchableOpacity>
        )}
        <View style={styles.headerTitleContainer}>
          <Text style={styles.headerTitle}>DEGRADATION TRACKER</Text>
          <Text style={styles.headerSubtitle}>SAVED WEAR PROFILES & CYCLES</Text>
        </View>
      </View>

      {/* Screen Empty State Placeholder */}
      {scans.length === 0 ? (
        <View style={styles.emptyContainer}>
          <View style={styles.emptyIconCircle}>
            <Text style={styles.emptyIcon}>⏳</Text>
          </View>
          <Text style={styles.emptyTitle}>NO DIAGNOSTIC LOGS YET</Text>
          <Text style={styles.emptyDescription}>
            Observe tire wear patterns, heat loading parameters, and outer-edge chamber wear cycle history here.
          </Text>

          <TouchableOpacity style={styles.seedButton} onPress={handleSeed}>
            <Text style={styles.seedButtonText}>SEED HISTORICAL DATABASE</Text>
          </TouchableOpacity>
        </View>
      ) : (
        <View style={styles.listContainer}>
          {/* Header instructions help tip */}
          <View style={styles.infoBanner}>
            <Text style={styles.infoBannerIcon}>ℹ</Text>
            <Text style={styles.infoBannerText}>
              Select any past log item to restore the 3D main canvas model to that profile's specifications. Let's observe deterioration rates over months.
            </Text>
          </View>

          {/* Recharts Historical Trend Line Chart */}
          <View style={styles.chartContainer}>
            <View style={styles.chartHeaderRow}>
              <Text style={styles.chartTitle}>
                {activeFilter === '30day' && '30-DAY TREND ANALYTICS'}
                {activeFilter === 'all' && 'ALL CYCLES GRAPH'}
                {activeFilter === 'highStress' && 'HIGH STRESS RECORDINGS'}
                {activeFilter === 'critical' && 'CRITICAL WEAR METRICS'}
              </Text>
              <Text style={styles.chartTitleBadge}>ACTIVE SYNAPSES</Text>
            </View>

            {/* Interactive Dataset Switcher Chips */}
            <View style={styles.filterContainer}>
              <TouchableOpacity
                onPress={() => setActiveFilter('30day')}
                style={[styles.filterChip, activeFilter === '30day' && styles.filterChipActive]}
              >
                <Text style={[styles.filterText, activeFilter === '30day' && styles.filterTextActive]}>30-DAY</Text>
              </TouchableOpacity>
              <TouchableOpacity
                onPress={() => setActiveFilter('all')}
                style={[styles.filterChip, activeFilter === 'all' && styles.filterChipActive]}
              >
                <Text style={[styles.filterText, activeFilter === 'all' && styles.filterTextActive]}>ALL CYCLES</Text>
              </TouchableOpacity>
              <TouchableOpacity
                onPress={() => setActiveFilter('highStress')}
                style={[styles.filterChip, activeFilter === 'highStress' && styles.filterChipActive]}
              >
                <Text style={[styles.filterText, activeFilter === 'highStress' && styles.filterTextActive]}>HIGH TEMP</Text>
              </TouchableOpacity>
              <TouchableOpacity
                onPress={() => setActiveFilter('critical')}
                style={[styles.filterChip, activeFilter === 'critical' && styles.filterChipActive]}
              >
                <Text style={[styles.filterText, activeFilter === 'critical' && styles.filterTextActive]}>WEAR DEFECT</Text>
              </TouchableOpacity>
            </View>

            {/* Transition animated wrapper */}
            <Animated.View style={[styles.rechartsWrapper, { opacity: fadeAnim }]}>
              <ResponsiveContainer width="100%" height={150}>
                {/* Changing the key triggers standard Recharts entering transition redraw animations */}
                <LineChart key={activeFilter} data={chartData} margin={{ top: 10, right: 10, left: -25, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#21262D" />
                  <XAxis dataKey="dateStr" tick={{ fill: '#8A9BA8', fontSize: 9 }} stroke="#21262D" />
                  <YAxis yAxisId="left" tick={{ fill: '#28B482', fontSize: 9 }} stroke="#21262D" />
                  <YAxis yAxisId="right" orientation="right" tick={{ fill: '#FF5E36', fontSize: 9 }} stroke="#21262D" />
                  <Tooltip contentStyle={{ backgroundColor: '#151B23', borderColor: '#30363D', borderRadius: 8 }} labelStyle={{ color: '#FFFFFF', fontSize: 10, fontWeight: 'bold' }} itemStyle={{ fontSize: 9 }} />
                  <Legend wrapperStyle={{ fontSize: 9, fontFamily: 'monospace' }} />
                  <Line yAxisId="left" type="monotone" dataKey="pressure" name="Pressure" stroke="#28B482" strokeWidth={2} dot={{ r: 3 }} activeDot={{ r: 5 }} isAnimationActive={true} animationDuration={450} animationEasing="ease-out" />
                  <Line yAxisId="right" type="monotone" dataKey="temperature" name="Temp" stroke="#FF5E36" strokeWidth={2} dot={{ r: 3 }} activeDot={{ r: 5 }} isAnimationActive={true} animationDuration={450} animationEasing="ease-out" />
                </LineChart>
              </ResponsiveContainer>
            </Animated.View>
          </View>

          {/* AI-Reasoning Wear Projection Chart using Recharts */}
          <View style={styles.chartContainer}>
            <View style={styles.chartHeaderRow}>
              <Text style={styles.chartTitle}>AI-ENGINE 10,000 KM WEAR PROJECTION</Text>
              <Text style={styles.chartTitleBadge}>PROGNOSTIC SYNAPSE</Text>
            </View>
            <Text style={{ color: '#8A9BA8', fontSize: 9, fontFamily: 'monospace', marginBottom: 12, lineHeight: 13 }}>
              Continuous predictive modeling based on telemetry history, localized heat loading patterns, and degradation indexes.
            </Text>
            
            <ResponsiveContainer width="100%" height={150}>
              <LineChart data={projectionData} margin={{ top: 10, right: 10, left: -25, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#21262D" />
                <XAxis dataKey="distanceStr" tick={{ fill: '#8A9BA8', fontSize: 9 }} stroke="#21262D" />
                <YAxis tick={{ fill: '#8A9BA8', fontSize: 9 }} stroke="#21262D" domain={[0, 100]} />
                <Tooltip contentStyle={{ backgroundColor: '#151B23', borderColor: '#30363D', borderRadius: 8 }} labelStyle={{ color: '#FFFFFF', fontSize: 10, fontWeight: 'bold' }} itemStyle={{ fontSize: 9 }} />
                <Legend wrapperStyle={{ fontSize: 8.5, fontFamily: 'monospace' }} />
                <Line type="monotone" dataKey="nominal" name="Nominal Load" stroke="#50FA7B" strokeWidth={2} dot={{ r: 3 }} activeDot={{ r: 5 }} />
                <Line type="monotone" dataKey="stressed" name="Low-PSI Stress" stroke="#FFB86C" strokeWidth={2} dot={{ r: 3 }} activeDot={{ r: 5 }} />
                <Line type="monotone" dataKey="thermal" name="Thermal Stress" stroke="#FF5555" strokeWidth={2} dot={{ r: 3 }} activeDot={{ r: 5 }} />
              </LineChart>
            </ResponsiveContainer>
          </View>

          {/* Core FlatList render */}
          <FlatList
            data={sortedScans}
            keyExtractor={(item) => item.id.toString()}
            contentContainerStyle={styles.listContent}
            renderItem={({ item }) => {
              const hColor = evaluateHealthColor(item.overallHealth);
              return (
                <View style={styles.card}>
                  <TouchableOpacity
                    style={styles.cardMain}
                    onPress={() => handleSelect(item)}
                    activeOpacity={0.7}
                  >
                    {/* Card Title & Health Indicator Badge */}
                    <View style={styles.cardHeader}>
                      <View style={[styles.healthBadge, { borderColor: hColor, backgroundColor: `${hColor}22` }]}>
                        <Text style={[styles.healthText, { color: hColor }]}>
                          {item.overallHealth}%
                        </Text>
                      </View>
                      <Text style={styles.cardTitle} numberOfLines={1}>
                        {item.title}
                      </Text>
                    </View>

                    {/* Format Timestamp Date string */}
                    <Text style={styles.cardDate}>{formatDate(item.timestamp)}</Text>

                    {/* Diagnostic Metrics HUD panel */}
                    <View style={styles.metricsRow}>
                      <View style={styles.metricItem}>
                        <Text style={styles.metricIcon}>⏱</Text>
                        <Text style={styles.metricValue}>{item.speed} km/h</Text>
                      </View>
                      <View style={styles.metricItem}>
                        <Text style={styles.metricIcon}>⛽</Text>
                        <Text style={styles.metricValue}>{item.pressure.toFixed(1)} PSI</Text>
                      </View>
                      <View style={styles.metricItem}>
                        <Text style={styles.metricIcon}>🌡</Text>
                        <Text style={styles.metricValue}>{item.temperature.toFixed(1)}°C</Text>
                      </View>
                    </View>

                    {/* Degradation Wear Pattern Tag */}
                    <View style={styles.patternContainer}>
                      <Text style={styles.patternLabel}>WEAR PATTERN:</Text>
                      <Text style={styles.patternValue}>{item.wearPattern.toUpperCase()}</Text>
                    </View>

                    {item.notes ? (
                      <Text style={styles.notesText} numberOfLines={2}>
                        {item.notes}
                      </Text>
                    ) : null}
                  </TouchableOpacity>

                  {/* Actions Bar Footer on Card */}
                  <View style={styles.actionsRow}>
                    <TouchableOpacity
                      style={styles.actionButton}
                      onPress={() => handleShare(item)}
                    >
                      <Text style={styles.actionButtonText}>📤 SHARE</Text>
                    </TouchableOpacity>
                    <View style={styles.divider} />
                    <TouchableOpacity
                      style={[styles.actionButton, styles.deleteButton]}
                      onPress={() => handleDelete(item.id)}
                    >
                      <Text style={[styles.actionButtonText, styles.deleteButtonText]}>🗑 REMOVE</Text>
                    </TouchableOpacity>
                  </View>
                </View>
              );
            }}
          />
        </View>
      )}
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#0D1117',
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 16,
    paddingVertical: 14,
    borderBottomWidth: 1,
    borderBottomColor: '#21262D',
    backgroundColor: '#0D1117',
  },
  backButton: {
    marginRight: 14,
    padding: 6,
    borderRadius: 6,
    backgroundColor: '#161B22',
    borderWidth: 1,
    borderColor: '#30363D',
  },
  backButtonText: {
    color: '#8A9BA8',
    fontSize: 14,
    fontWeight: 'bold',
  },
  headerTitleContainer: {
    flex: 1,
    justifyContent: 'center',
  },
  headerTitle: {
    color: '#FFFFFF',
    fontSize: 14,
    fontWeight: 'bold',
    fontFamily: 'monospace',
    letterSpacing: 1.5,
  },
  headerSubtitle: {
    color: '#8A9BA8',
    fontSize: 9,
    fontFamily: 'monospace',
    letterSpacing: 0.8,
    marginTop: 2,
  },
  infoBanner: {
    flexDirection: 'row',
    alignItems: 'center',
    marginHorizontal: 16,
    marginTop: 12,
    marginBottom: 4,
    padding: 12,
    backgroundColor: '#151B23',
    borderRadius: 8,
    borderWidth: 0.5,
    borderColor: '#30363D',
  },
  infoBannerIcon: {
    color: '#58A6FF',
    fontSize: 14,
    marginRight: 10,
    fontWeight: 'bold',
  },
  infoBannerText: {
    flex: 1,
    color: '#8A9BA8',
    fontSize: 11,
    lineHeight: 16,
  },
  listContainer: {
    flex: 1,
  },
  listContent: {
    padding: 16,
    paddingBottom: 24,
  },
  card: {
    backgroundColor: '#151B23',
    borderRadius: 12,
    borderWidth: 1,
    borderColor: '#21262D',
    marginBottom: 14,
    overflow: 'hidden',
  },
  cardMain: {
    padding: 14,
  },
  cardHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 6,
  },
  healthBadge: {
    borderWidth: 1.2,
    borderRadius: 4,
    paddingHorizontal: 6,
    paddingVertical: 2,
    marginRight: 10,
  },
  healthText: {
    fontSize: 11,
    fontWeight: 'bold',
    fontFamily: 'monospace',
  },
  cardTitle: {
    flex: 1,
    color: '#FFFFFF',
    fontSize: 14,
    fontWeight: '600',
  },
  cardDate: {
    color: '#8A9BA8',
    fontSize: 11,
    marginBottom: 12,
  },
  metricsRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    backgroundColor: '#0D1117',
    borderRadius: 6,
    paddingVertical: 8,
    paddingHorizontal: 8,
    marginBottom: 10,
    borderWidth: 0.5,
    borderColor: '#21262D',
  },
  metricItem: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  metricIcon: {
    fontSize: 12,
    color: '#8A9BA8',
    marginRight: 4,
  },
  metricValue: {
    color: '#FFFFFF',
    fontSize: 11,
    fontFamily: 'monospace',
  },
  patternContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#0D1117',
    borderRadius: 4,
    paddingVertical: 4,
    paddingHorizontal: 6,
    alignSelf: 'flex-start',
    marginBottom: 8,
  },
  patternLabel: {
    color: '#8A9BA8',
    fontSize: 9,
    fontFamily: 'monospace',
    marginRight: 5,
  },
  patternValue: {
    color: '#58A6FF',
    fontSize: 9,
    fontFamily: 'monospace',
    fontWeight: 'bold',
  },
  notesText: {
    color: '#8A9BA8',
    fontSize: 11,
    lineHeight: 15,
    fontStyle: 'italic',
    marginTop: 4,
  },
  actionsRow: {
    flexDirection: 'row',
    alignItems: 'center',
    borderTopWidth: 1,
    borderTopColor: '#21262D',
    backgroundColor: '#121820',
  },
  actionButton: {
    flex: 1,
    paddingVertical: 10,
    alignItems: 'center',
    justifyContent: 'center',
  },
  deleteButton: {
    backgroundColor: 'rgba(255, 75, 75, 0.04)',
  },
  actionButtonText: {
    color: '#8a9ba8',
    fontSize: 10,
    fontWeight: 'bold',
    fontFamily: 'monospace',
    letterSpacing: 0.5,
  },
  deleteButtonText: {
    color: 'rgba(255, 75, 75, 0.95)',
  },
  divider: {
    width: 1,
    height: 18,
    backgroundColor: '#21262D',
  },
  emptyContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    paddingHorizontal: 32,
  },
  emptyIconCircle: {
    width: 64,
    height: 64,
    borderRadius: 32,
    backgroundColor: '#1F242C',
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: 16,
  },
  emptyIcon: {
    fontSize: 28,
  },
  emptyTitle: {
    color: '#FFFFFF',
    fontSize: 13,
    fontWeight: 'bold',
    fontFamily: 'monospace',
    letterSpacing: 1,
    marginBottom: 10,
  },
  emptyDescription: {
    color: '#8A9BA8',
    fontSize: 11,
    textAlign: 'center',
    lineHeight: 16,
    marginBottom: 24,
  },
  seedButton: {
    backgroundColor: '#21262D',
    borderWidth: 1,
    borderColor: '#30363D',
    borderRadius: 8,
    paddingVertical: 10,
    paddingHorizontal: 18,
  },
  seedButtonText: {
    color: '#58A6FF',
    fontSize: 11,
    fontFamily: 'monospace',
    fontWeight: 'bold',
  },
  chartContainer: {
    backgroundColor: '#151B23',
    borderColor: '#21262D',
    borderWidth: 1,
    borderRadius: 12,
    padding: 12,
    marginHorizontal: 16,
    marginTop: 8,
    marginBottom: 8,
  },
  chartHeaderRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 10,
  },
  chartTitleBadge: {
    backgroundColor: 'rgba(88, 166, 255, 0.1)',
    color: '#58A6FF',
    fontFamily: 'monospace',
    fontSize: 8.5,
    fontWeight: 'bold',
    paddingHorizontal: 6,
    paddingVertical: 2,
    borderRadius: 4,
    borderWidth: 0.5,
    borderColor: 'rgba(88, 166, 255, 0.25)',
  },
  chartTitle: {
    color: '#58A6FF',
    fontSize: 10,
    fontWeight: 'bold',
    fontFamily: 'monospace',
    letterSpacing: 1,
  },
  filterContainer: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginBottom: 12,
  },
  filterChip: {
    flex: 1,
    paddingVertical: 6,
    marginHorizontal: 2,
    borderRadius: 6,
    backgroundColor: '#161B22',
    borderWidth: 1,
    borderColor: '#30363D',
    alignItems: 'center',
    justifyContent: 'center',
  },
  filterChipActive: {
    backgroundColor: '#21262D',
    borderColor: '#58A6FF',
    shadowColor: '#58A6FF',
    shadowOffset: { width: 0, height: 0 },
    shadowOpacity: 0.3,
    shadowRadius: 3,
  },
  filterText: {
    color: '#8A9BA8',
    fontSize: 8,
    fontFamily: 'monospace',
    fontWeight: 'bold',
  },
  filterTextActive: {
    color: '#58A6FF',
  },
  rechartsWrapper: {
    width: '100%',
    height: 155,
  },
});
