/**
 * FeedbackModal â€” User correction dialog for self-correcting learning.
 * Allows users to flag wrong predictions and submit corrections.
 */

import React, { useReducer } from "react";
import {
  Modal, View, Text, TextInput, TouchableOpacity,
  ScrollView, StyleSheet, ActivityIndicator, Alert,
} from "react-native";
import { submitFeedback } from "../api/feedback";

const COLORS = {
  bg: "#0D1117",
  card: "#161B22",
  border: "#30363D",
  accent: "#58A6FF",
  red: "#F85149",
  green: "#3FB950",
  textPrimary: "#F0F6FC",
  textSecondary: "#8B949E",
};

const WEAR_PATTERNS = [
  "center_wear", "edge_wear", "patchy_wear",
  "uniform_wear", "side_wall_wear", "one_side_wear", "cupping_wear",
];

interface FeedbackModalProps {
  visible: boolean;
  onClose: () => void;
  sessionId: string;
  originalPrediction: any;
}

type FeedbackType = "wrong" | "inaccurate" | "correct" | "partial";
type TreadPositionKey = "tread_1" | "tread_2" | "tread_3" | "tread_4";
type TreadPositions = Record<TreadPositionKey, string>;

type FeedbackModalState = {
  feedbackType: FeedbackType;
  correctedTread: string;
  treadPositions: TreadPositions;
  correctedWear: string;
  comment: string;
  submitting: boolean;
};

type FeedbackModalAction =
  | { type: "setFeedbackType"; value: FeedbackType }
  | { type: "setCorrectedTread"; value: string }
  | { type: "setTreadPosition"; key: TreadPositionKey; value: string }
  | { type: "setCorrectedWear"; value: string }
  | { type: "setComment"; value: string }
  | { type: "submitStarted" }
  | { type: "submitFinished" };

const initialFeedbackModalState: FeedbackModalState = {
  feedbackType: "wrong",
  correctedTread: "",
  treadPositions: {
    tread_1: "",
    tread_2: "",
    tread_3: "",
    tread_4: "",
  },
  correctedWear: "",
  comment: "",
  submitting: false,
};

function feedbackModalReducer(
  state: FeedbackModalState,
  action: FeedbackModalAction,
): FeedbackModalState {
  switch (action.type) {
    case "setFeedbackType":
      return { ...state, feedbackType: action.value };
    case "setCorrectedTread":
      return { ...state, correctedTread: action.value };
    case "setTreadPosition":
      return {
        ...state,
        treadPositions: { ...state.treadPositions, [action.key]: action.value },
      };
    case "setCorrectedWear":
      return { ...state, correctedWear: action.value };
    case "setComment":
      return { ...state, comment: action.value };
    case "submitStarted":
      return { ...state, submitting: true };
    case "submitFinished":
      return { ...state, submitting: false };
    default:
      return state;
  }
}

export function FeedbackModal({
  visible,
  onClose,
  sessionId,
  originalPrediction,
}: FeedbackModalProps) {
  const [state, dispatch] = useReducer(feedbackModalReducer, initialFeedbackModalState);
  const {
    feedbackType,
    correctedTread,
    treadPositions,
    correctedWear,
    comment,
    submitting,
  } = state;

  const handleSubmit = async () => {
    if (!sessionId) {
      Alert.alert("Error", "No session to submit feedback for.");
      return;
    }
    dispatch({ type: "submitStarted" });
    try {
      const correctedDepths = Object.fromEntries(
        Object.entries(treadPositions).flatMap(([key, value]) => (
          value.trim() !== "" ? [[key, parseFloat(value)]] : []
        ))
      ) as Partial<Record<keyof typeof treadPositions, number>>;
      const depthValues = Object.values(correctedDepths).filter((value): value is number =>
        Number.isFinite(value)
      );
      const depthAverage = correctedTread
        ? parseFloat(correctedTread)
        : depthValues.length
          ? depthValues.reduce((sum, value) => sum + value, 0) / depthValues.length
          : undefined;

      await submitFeedback({
        session_id: sessionId,
        feedback_type: feedbackType,
        corrected_tread_depth_mm: depthAverage,
        corrected_tread_depths_mm: Object.keys(correctedDepths).length ? correctedDepths : undefined,
        corrected_wear_pattern: correctedWear || undefined,
        original_prediction: originalPrediction,
        comment: comment || undefined,
      });
      Alert.alert(
        "Thank you!",
        "Your feedback has been recorded. It helps improve the AI model.",
        [{ text: "OK", onPress: onClose }]
      );
    } catch (err: any) {
      Alert.alert("Error", err.message || "Failed to submit feedback.");
    } finally {
      dispatch({ type: "submitFinished" });
    }
  };

  return (
    <Modal visible={visible} animationType="slide" transparent presentationStyle="overFullScreen">
      <View style={styles.overlay}>
        <View style={styles.sheet}>
          <View style={styles.header}>
            <Text style={styles.title}>Correct This Result</Text>
            <TouchableOpacity onPress={onClose} style={styles.closeBtn}>
              <Text style={styles.closeTxt}>âœ•</Text>
            </TouchableOpacity>
          </View>

          <ScrollView showsVerticalScrollIndicator={false}>
            {/* Feedback Type */}
            <Text style={styles.label}>Feedback Type</Text>
            <View style={styles.typeRow}>
              {(["wrong", "inaccurate", "partial", "correct"] as const).map((t) => (
                <TouchableOpacity
                  key={t}
                  style={[styles.typeBtn, feedbackType === t && styles.typeBtnActive]}
                  onPress={() => dispatch({ type: "setFeedbackType", value: t })}
                >
                  <Text style={[styles.typeTxt, feedbackType === t && styles.typeTxtActive]}>
                    {t.charAt(0).toUpperCase() + t.slice(1)}
                  </Text>
                </TouchableOpacity>
              ))}
            </View>

            {/* Corrected Tread Depth */}
            <Text style={styles.label}>Actual Tread Depth (mm) â€” optional</Text>
            <TextInput
              style={styles.input}
              value={correctedTread}
              onChangeText={(value: string) => dispatch({ type: "setCorrectedTread", value })}
              keyboardType="decimal-pad"
              placeholder="e.g. 4.5"
              placeholderTextColor={COLORS.textSecondary}
            />

            <Text style={styles.label}>Position Readings (mm) - optional</Text>
            <View style={styles.depthGrid}>
              {(["tread_1", "tread_2", "tread_3", "tread_4"] as const).map((key, index) => (
                <View key={key} style={styles.depthCell}>
                  <Text style={styles.depthLabel}>T{index + 1}</Text>
                  <TextInput
                    style={[styles.input, styles.depthInput]}
                    value={treadPositions[key]}
                    onChangeText={(value: string) => dispatch({ type: "setTreadPosition", key, value })}
                    keyboardType="decimal-pad"
                    placeholder="mm"
                    placeholderTextColor={COLORS.textSecondary}
                  />
                </View>
              ))}
            </View>

            {/* Corrected Wear Pattern */}
            <Text style={styles.label}>Correct Wear Pattern â€” optional</Text>
            <View style={styles.wearGrid}>
              {WEAR_PATTERNS.map((p) => (
                <TouchableOpacity
                  key={p}
                  style={[styles.wearBtn, correctedWear === p && styles.wearBtnActive]}
                  onPress={() => dispatch({ type: "setCorrectedWear", value: correctedWear === p ? "" : p })}
                >
                  <Text style={[styles.wearTxt, correctedWear === p && styles.wearTxtActive]}>
                    {p.replace(/_/g, " ")}
                  </Text>
                </TouchableOpacity>
              ))}
            </View>

            {/* Comment */}
            <Text style={styles.label}>Additional Comment â€” optional</Text>
            <TextInput
              style={[styles.input, styles.textArea]}
              value={comment}
              onChangeText={(value: string) => dispatch({ type: "setComment", value })}
              placeholder="Describe what was wrong..."
              placeholderTextColor={COLORS.textSecondary}
              multiline
              numberOfLines={3}
            />

            {/* Submit */}
            <TouchableOpacity
              style={[styles.submitBtn, submitting && { opacity: 0.6 }]}
              onPress={handleSubmit}
              disabled={submitting}
            >
              {submitting ? (
                <ActivityIndicator color="#fff" size="small" />
              ) : (
                <Text style={styles.submitTxt}>Submit Feedback</Text>
              )}
            </TouchableOpacity>
          </ScrollView>
        </View>
      </View>
    </Modal>
  );
}

const styles = StyleSheet.create({
  overlay: { flex: 1, backgroundColor: "rgba(0,0,0,0.7)", justifyContent: "flex-end" },
  sheet: {
    backgroundColor: COLORS.card,
    borderTopLeftRadius: 20,
    borderTopRightRadius: 20,
    padding: 20,
    maxHeight: "85%",
  },
  header: { flexDirection: "row", justifyContent: "space-between", alignItems: "center", marginBottom: 20 },
  title: { fontSize: 18, fontWeight: "700", color: COLORS.textPrimary },
  closeBtn: { padding: 4 },
  closeTxt: { color: COLORS.textSecondary, fontSize: 18 },
  label: { fontSize: 12, color: COLORS.textSecondary, marginBottom: 8, marginTop: 16, fontWeight: "600" },
  typeRow: { flexDirection: "row", gap: 8, flexWrap: "wrap" },
  typeBtn: {
    paddingHorizontal: 14, paddingVertical: 8, borderRadius: 20,
    borderWidth: 1, borderColor: COLORS.border, backgroundColor: COLORS.bg,
  },
  typeBtnActive: { borderColor: COLORS.accent, backgroundColor: COLORS.accent + "22" },
  typeTxt: { color: COLORS.textSecondary, fontSize: 13 },
  typeTxtActive: { color: COLORS.accent, fontWeight: "600" },
  input: {
    backgroundColor: COLORS.bg, borderWidth: 1, borderColor: COLORS.border,
    borderRadius: 10, paddingHorizontal: 12, paddingVertical: 10,
    color: COLORS.textPrimary, fontSize: 14,
  },
  depthGrid: { flexDirection: "row", gap: 8 },
  depthCell: { flex: 1 },
  depthLabel: { color: COLORS.textSecondary, fontSize: 11, marginBottom: 4 },
  depthInput: { minWidth: 0, paddingHorizontal: 8 },
  textArea: { height: 80, textAlignVertical: "top" },
  wearGrid: { flexDirection: "row", flexWrap: "wrap", gap: 8 },
  wearBtn: {
    paddingHorizontal: 12, paddingVertical: 6, borderRadius: 20,
    borderWidth: 1, borderColor: COLORS.border, backgroundColor: COLORS.bg,
  },
  wearBtnActive: { borderColor: COLORS.green, backgroundColor: COLORS.green + "22" },
  wearTxt: { color: COLORS.textSecondary, fontSize: 11, textTransform: "capitalize" },
  wearTxtActive: { color: COLORS.green, fontWeight: "600" },
  submitBtn: {
    backgroundColor: COLORS.accent, borderRadius: 12,
    padding: 16, alignItems: "center", marginTop: 24, marginBottom: 8,
  },
  submitTxt: { color: "#fff", fontSize: 16, fontWeight: "700" },
});
