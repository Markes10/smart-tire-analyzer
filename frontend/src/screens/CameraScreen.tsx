/**
 * Camera Screen — Tire photo capture with live preview and quality feedback.
 * Supports: camera capture, gallery pick, and photo quality guidance.
 */

import React, { useState, useRef, useCallback } from "react";
import {
  View, Text, TouchableOpacity, StyleSheet,
  Alert, ActivityIndicator,
} from "react-native";
import Dimensions from "react-native";
import Platform from "react-native";
import { CameraView, useCameraPermissions } from "expo-camera";
import * as ImagePicker from "expo-image-picker";
import { SafeAreaView } from "react-native-safe-area-context";
import { useNavigation } from "@react-navigation/native";
import { analyzeImage } from "../api/analyze";
import { validateImage } from "../utils/imageHelpers";
import { useAnalysisStore } from "../store/useAnalysisStore";
import { useHistoryStore } from "../store/useHistoryStore";

const { width, height } = Dimensions.get("window");
const VIEWFINDER_SIZE = width * 0.8;

const TIPS = [
  "📏  Fill the frame with the tire tread",
  "💡  Ensure good lighting — avoid shadows",
  "🎯  Keep camera still for sharp focus",
  "📐  Photograph at 90° to the tread surface",
];

export default function CameraScreen() {
  const navigation = useNavigation();
  const cameraRef = useRef<any>(null);
  const [permission, requestPermission] = useCameraPermissions();
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [currentTip, setCurrentTip] = useState(0);
  const { setLatestAnalysis, setError } = useAnalysisStore();
  const { addToHistory } = useHistoryStore();

  const runAnalysis = useCallback(async (imageUri: string) => {
    // Validate size
    const { valid, error } = await validateImage(imageUri);
    if (!valid) {
      Alert.alert("Invalid Image", error);
      return;
    }

    setIsAnalyzing(true);
    try {
      const result = await analyzeImage({ imageUri });
      setLatestAnalysis(result);
      addToHistory(result);
      navigation.navigate("Result", { data: result });
    } catch (err: any) {
      setError(err.message);
      Alert.alert(
        "Analysis Failed",
        err.message || "Could not analyze image. Please try again.",
        [{ text: "OK" }]
      );
    } finally {
      setIsAnalyzing(false);
    }
  }, [addToHistory, navigation, setError, setLatestAnalysis]);

  const handleCapture = async () => {
    if (!cameraRef.current) return;
    try {
      const photo = await cameraRef.current.takePictureAsync({
        quality: 0.9,
        base64: false,
        skipProcessing: false,
      });
      await runAnalysis(photo.uri);
    } catch (e) {
      Alert.alert("Capture Failed", "Could not take photo. Please try again.");
    }
  };

  const handlePickGallery = async () => {
    const result = await ImagePicker.launchImageLibraryAsync({
      mediaTypes: ImagePicker.MediaTypeOptions.Images,
      quality: 0.9,
      allowsEditing: false,
    });
    if (!result.canceled && result.assets[0]) {
      await runAnalysis(result.assets[0].uri);
    }
  };

  // Permission flow
  if (!permission) return <View style={styles.container} />;

  if (!permission.granted) {
    return (
      <SafeAreaView style={styles.container}>
        <View style={styles.permissionBox}>
          <Text style={styles.permIcon}>📷</Text>
          <Text style={styles.permTitle}>Camera Access Required</Text>
          <Text style={styles.permText}>
            Smart Tire Analyzer needs camera access to photograph tire treads for analysis.
          </Text>
          <TouchableOpacity style={styles.permBtn} onPress={requestPermission}>
            <Text style={styles.permBtnText}>Allow Camera Access</Text>
          </TouchableOpacity>
          <TouchableOpacity style={styles.galleryFallback} onPress={handlePickGallery}>
            <Text style={styles.galleryFallbackText}>Or pick from Gallery</Text>
          </TouchableOpacity>
        </View>
      </SafeAreaView>
    );
  }

  return (
    <View style={styles.container}>
      {/* Camera preview */}
      <CameraView
        ref={cameraRef}
        style={{ position: "absolute", top: 0, left: 0, right: 0, bottom: 0 }}
        facing="back"
        autofocus="on"
      />

      {/* Overlay */}
      <View style={styles.overlay}>
        {/* Viewfinder */}
        <View style={styles.viewfinder}>
          {/* Corner markers */}
          {["topLeft", "topRight", "bottomLeft", "bottomRight"].map((pos) => (
            <View
              key={pos}
              style={[
                styles.corner,
                pos.includes("top") ? { top: 0 } : { bottom: 0 },
                pos.includes("Left") ? { left: 0 } : { right: 0 },
              ]}
            />
          ))}
        </View>

        {/* Tip carousel */}
        <View style={styles.tipBox}>
          <Text style={styles.tipText}>{TIPS[currentTip % TIPS.length]}</Text>
        </View>
      </View>

      {/* Controls */}
      <SafeAreaView style={styles.controls} edges={["bottom"]}>
        {/* Gallery button */}
        <TouchableOpacity style={styles.galleryBtn} onPress={handlePickGallery} disabled={isAnalyzing}>
          <Text style={styles.galleryIcon}>🖼</Text>
          <Text style={styles.galleryLabel}>Gallery</Text>
        </TouchableOpacity>

        {/* Capture button */}
        <TouchableOpacity
          style={[styles.captureBtn, isAnalyzing && styles.captureBtnDisabled]}
          onPress={handleCapture}
          disabled={isAnalyzing}
        >
          {isAnalyzing ? (
            <ActivityIndicator color="#fff" size="large" />
          ) : (
            <View style={styles.captureInner} />
          )}
        </TouchableOpacity>

        {/* Back button */}
        <TouchableOpacity
          style={styles.backBtn}
          onPress={() => navigation.goBack()}
          disabled={isAnalyzing}
        >
          <Text style={styles.backIcon}>✕</Text>
          <Text style={styles.backLabel}>Back</Text>
        </TouchableOpacity>
      </SafeAreaView>

      {/* Analyzing overlay */}
      {isAnalyzing && (
        <View style={styles.analyzingOverlay}>
          <ActivityIndicator color="#58A6FF" size="large" />
          <Text style={styles.analyzingText}>Analyzing tire…</Text>
          <Text style={styles.analyzingSubText}>Running AI model</Text>
        </View>
      )}
    </View>
  );
}

const CORNER_SIZE = 24;
const CORNER_THICKNESS = 3;

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#000" },
  overlay: {
    position: "absolute", top: 0, left: 0, right: 0, bottom: 0,
    alignItems: "center",
    justifyContent: "center",
  },
  viewfinder: {
    width: VIEWFINDER_SIZE,
    height: VIEWFINDER_SIZE,
    position: "relative",
  },
  corner: {
    position: "absolute",
    width: CORNER_SIZE,
    height: CORNER_SIZE,
    borderColor: "#58A6FF",
    borderWidth: CORNER_THICKNESS,
  },
  tipBox: {
    marginTop: 20,
    backgroundColor: "rgba(0,0,0,0.65)",
    borderRadius: 12,
    paddingHorizontal: 16,
    paddingVertical: 10,
    maxWidth: width * 0.85,
  },
  tipText: { color: "#F0F6FC", fontSize: 13, textAlign: "center" },
  controls: {
    position: "absolute",
    bottom: 0,
    left: 0,
    right: 0,
    flexDirection: "row",
    justifyContent: "space-around",
    alignItems: "center",
    paddingBottom: 20,
    paddingHorizontal: 30,
    backgroundColor: "rgba(0,0,0,0.5)",
  },
  captureBtn: {
    width: 72,
    height: 72,
    borderRadius: 36,
    borderWidth: 4,
    borderColor: "#fff",
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: "rgba(255,255,255,0.15)",
  },
  captureBtnDisabled: { opacity: 0.5 },
  captureInner: {
    width: 54,
    height: 54,
    borderRadius: 27,
    backgroundColor: "#fff",
  },
  galleryBtn: { alignItems: "center", width: 56 },
  galleryIcon: { fontSize: 28 },
  galleryLabel: { color: "#fff", fontSize: 10, marginTop: 4 },
  backBtn: { alignItems: "center", width: 56 },
  backIcon: { color: "#fff", fontSize: 22, fontWeight: "300" },
  backLabel: { color: "#fff", fontSize: 10, marginTop: 4 },
  permissionBox: {
    flex: 1, alignItems: "center", justifyContent: "center",
    paddingHorizontal: 32, backgroundColor: "#0D1117",
  },
  permIcon: { fontSize: 60, marginBottom: 20 },
  permTitle: { fontSize: 22, fontWeight: "700", color: "#F0F6FC", marginBottom: 12 },
  permText: {
    fontSize: 14, color: "#8B949E", textAlign: "center", lineHeight: 22, marginBottom: 24,
  },
  permBtn: {
    backgroundColor: "#58A6FF", paddingHorizontal: 32, paddingVertical: 14,
    borderRadius: 12, width: "100%", alignItems: "center",
  },
  permBtnText: { color: "#fff", fontSize: 16, fontWeight: "700" },
  galleryFallback: { marginTop: 16, padding: 12 },
  galleryFallbackText: { color: "#58A6FF", fontSize: 14 },
  analyzingOverlay: {
    position: "absolute", top: 0, left: 0, right: 0, bottom: 0,
    backgroundColor: "rgba(0,0,0,0.82)",
    alignItems: "center",
    justifyContent: "center",
    gap: 16,
  },
  analyzingText: { color: "#F0F6FC", fontSize: 20, fontWeight: "700" },
  analyzingSubText: { color: "#8B949E", fontSize: 14 },
});
