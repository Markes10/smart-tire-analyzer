import React, { useRef, useState, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ActivityIndicator,
  PanResponder,
  TouchableOpacity,
  Dimensions,
} from 'react-native';
import { GLView } from 'expo-gl';
import * as THREE from 'three';

interface TireDigitalTwin3DProps {
  speed?: number;       // km/h
  pressure?: number;    // PSI
  temperature?: number; // Celsius
  wearPattern?: 'Normal' | 'Center Wear' | 'Edge Wear' | 'Camber Wear' | 'Cupping Wear';
  isThermalMode?: boolean;
  isExplodedView?: boolean;
}

export default function TireDigitalTwin3D({
  speed = 0,
  pressure = 32,
  temperature = 25,
  wearPattern = 'Normal',
  isThermalMode = false,
  isExplodedView = false,
}: TireDigitalTwin3DProps) {
  const [compiling, setCompiling] = useState(true);
  const [progress, setProgress] = useState(0);
  const [waitingForPacket, setWaitingForPacket] = useState(false);
  const [shimmerAlpha, setShimmerAlpha] = useState(0.35);
  const [showLegend, setShowLegend] = useState(false);
  const [showConfig, setShowConfig] = useState(false);

  // Custom user-configurable alarm thresholds
  const [pressMin, setPressMin] = useState(28);
  const [pressMax, setPressMax] = useState(35);
  const [tempMax, setTempMax] = useState(80);

  // Interaction rotation tracker
  const rotationRef = useRef({ x: 0.4, y: 0.8 });
  const isDragging = useRef(false);

  // Zoom control & gesture state references
  const cameraZRef = useRef(4.2);
  const lastTapRef = useRef(0);
  const initialDistanceRef = useRef<number | null>(null);
  const initialCameraZRef = useRef(4.2);

  // References to pass dynamic updates into the Three.js render loop without re-renders
  const speedRef = useRef(speed);
  const pressureRef = useRef(pressure);
  const temperatureRef = useRef(temperature);
  const thermalModeRef = useRef(isThermalMode);
  const explodedViewRef = useRef(isExplodedView);
  const wearPatternRef = useRef(wearPattern);

  // Configurable thresholds ref sync
  const pressMinRef = useRef(pressMin);
  const pressMaxRef = useRef(pressMax);
  const tempMaxRef = useRef(tempMax);

  // Update refs when props change
  useEffect(() => { speedRef.current = speed; }, [speed]);
  useEffect(() => { pressureRef.current = pressure; }, [pressure]);
  useEffect(() => { temperatureRef.current = temperature; }, [temperature]);
  useEffect(() => { thermalModeRef.current = isThermalMode; }, [isThermalMode]);
  useEffect(() => { explodedViewRef.current = isExplodedView; }, [isExplodedView]);
  useEffect(() => { wearPatternRef.current = wearPattern; }, [wearPattern]);

  // Sync thresholds refs with state changes
  useEffect(() => { pressMinRef.current = pressMin; }, [pressMin]);
  useEffect(() => { pressMaxRef.current = pressMax; }, [pressMax]);
  useEffect(() => { tempMaxRef.current = tempMax; }, [tempMax]);

  // Handle smooth 60fps shimmer opacity pulse loop for skeleton guides
  useEffect(() => {
    let animId: number;
    let dir = 0.04;
    const pulse = () => {
      setShimmerAlpha((prev) => {
        let next = prev + dir;
        if (next >= 0.75) {
          dir = -0.04;
          return 0.75;
        }
        if (next <= 0.2) {
          dir = 0.04;
          return 0.2;
        }
        return next;
      });
      animId = requestAnimationFrame(pulse);
    };
    animId = requestAnimationFrame(pulse);
    return () => cancelAnimationFrame(animId);
  }, []);

  // Cyberpunk shader compilation and telemetry bind timeline setup
  useEffect(() => {
    const interval = setInterval(() => {
      setProgress((prev) => {
        if (prev >= 100) {
          clearInterval(interval);
          setCompiling(false);
          // Auto transition to "Awaiting IoT telemetry data packet" phase
          setWaitingForPacket(true);
          return 100;
        }
        return prev + Math.floor(Math.random() * 20) + 12;
      });
    }, 120);

    return () => clearInterval(interval);
  }, []);

  // Stage 3 automatic bind lock-on timer
  useEffect(() => {
    if (waitingForPacket) {
      const timer = setTimeout(() => {
        setWaitingForPacket(false);
      }, 3500); // Wait 3.5s for secure sensor link, then activate
      return () => clearTimeout(timer);
    }
  }, [waitingForPacket]);

  // Fast skip: skip waiting phase immediately once actual IoT packet updates arrive
  useEffect(() => {
    if (speed > 0 || pressure !== 32 || temperature !== 25) {
      setWaitingForPacket(false);
    }
  }, [speed, pressure, temperature]);

  // Gestures mapping to rotation matrix and Zoom/State parameters
  const panResponder = useRef(
    PanResponder.create({
      onStartShouldSetPanResponder: () => true,
      onMoveShouldSetPanResponder: () => true,
      onPanResponderGrant: (evt) => {
        isDragging.current = true;

        // Double-tap reset logic
        const now = Date.now();
        const DOUBLE_TAP_DELAY = 300; // ms
        if (now - lastTapRef.current < DOUBLE_TAP_DELAY) {
          // Reset orientation & camera zoom level smoothly
          rotationRef.current = { x: 0.4, y: 0.8 };
          cameraZRef.current = 4.2;
          initialDistanceRef.current = null;
        }
        lastTapRef.current = now;
      },
      onPanResponderMove: (evt, gestureState) => {
        const touches = evt.nativeEvent.touches;
        if (touches && touches.length === 2) {
          // Pinch-to-zoom computation
          const dx = touches[0].pageX - touches[1].pageX;
          const dy = touches[0].pageY - touches[1].pageY;
          const distance = Math.sqrt(dx * dx + dy * dy);

          if (initialDistanceRef.current === null) {
            initialDistanceRef.current = distance;
            initialCameraZRef.current = cameraZRef.current;
          } else {
            const ratio = initialDistanceRef.current / distance;
            // Clamp camera zoom distance (lower Z value means closer / zoomed in)
            cameraZRef.current = Math.max(1.8, Math.min(8.5, initialCameraZRef.current * ratio));
          }
        } else {
          // Reset multi-touch tracking if less than 2 fingers present
          initialDistanceRef.current = null;

          // Standard drag rotation logic
          rotationRef.current.y += gestureState.dx * 0.007;
          rotationRef.current.x += gestureState.dy * 0.007;
          // Dampen vertical rotation to avoid flipping upside down
          rotationRef.current.x = Math.max(-Math.PI / 3, Math.min(Math.PI / 3, rotationRef.current.x));
        }
      },
      onPanResponderRelease: () => {
        isDragging.current = false;
        initialDistanceRef.current = null;
      },
      onPanResponderTerminate: () => {
        isDragging.current = false;
        initialDistanceRef.current = null;
      },
    })
  ).current;

  // GL Context Creator & Scene Initialization
  const onContextCreate = async (gl: any) => {
    const { drawingBufferWidth: width, drawingBufferHeight: height } = gl;
    const renderer = new THREE.WebGLRenderer({
      canvas: {
        width,
        height,
        style: {},
        addEventListener: () => {},
        removeEventListener: () => {},
        clientHeight: height,
      } as any,
      context: gl,
      antialias: true,
      alpha: true,
    });
    renderer.setSize(width, height);
    renderer.setPixelRatio(gl.pixelRatio || 1);

    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(50, width / height, 0.1, 1000);
    camera.position.set(0, 0, 4.2);

    // Dynamic Lights configuration
    const ambientLight = new THREE.AmbientLight(0xffffff, 0.55);
    scene.add(ambientLight);

    const dirLight = new THREE.DirectionalLight(0xffffff, 1.4);
    dirLight.position.set(5, 10, 5);
    scene.add(dirLight);

    const pointLight = new THREE.PointLight(0x58a6ff, 0.6, 20);
    pointLight.position.set(-5, -3, -3);
    scene.add(pointLight);

    // Central Tire Component meshes grouping
    const tireGroup = new THREE.Group();
    scene.add(tireGroup);

    // 1. Torus segment for tread
    const torusGeom = new THREE.TorusGeometry(1.2, 0.38, 16, 64);
    const torusMat = new THREE.MeshStandardMaterial({
      color: 0x21262d,
      roughness: 0.75,
      metalness: 0.1,
    });
    const treadMesh = new THREE.Mesh(torusGeom, torusMat);
    tireGroup.add(treadMesh);

    // 2. Main rim core cylinder
    const rimGeom = new THREE.CylinderGeometry(0.7, 0.7, 0.52, 32);
    const rimMat = new THREE.MeshStandardMaterial({
      color: 0x8a9ba8,
      roughness: 0.3,
      metalness: 0.75,
    });
    const rimMesh = new THREE.Mesh(rimGeom, rimMat);
    rimMesh.rotation.x = Math.PI / 2;
    tireGroup.add(rimMesh);

    // 3. Spoke rails supporting the rims
    const spokesGroup = new THREE.Group();
    for (let i = 0; i < 8; i++) {
      const angle = (i * Math.PI) / 4;
      const spokeGeom = new THREE.CylinderGeometry(0.045, 0.045, 1.35, 8);
      const spokeMat = new THREE.MeshStandardMaterial({
        color: 0x8a9ba8,
        roughness: 0.25,
        metalness: 0.85,
      });
      const spokeMesh = new THREE.Mesh(spokeGeom, spokeMat);
      spokeMesh.rotation.z = angle;
      spokesGroup.add(spokeMesh);
    }
    tireGroup.add(spokesGroup);

    // 4. Thread-belts representing inner layers in exploded view mode
    const beltGeom = new THREE.CylinderGeometry(1.35, 1.35, 0.45, 24, 2, true);
    const beltMat = new THREE.MeshStandardMaterial({
      color: 0xffd43f,
      roughness: 0.3,
      metalness: 0.9,
      wireframe: true,
      transparent: true,
      opacity: 0.0,
    });
    const beltMesh = new THREE.Mesh(beltGeom, beltMat);
    beltMesh.rotation.x = Math.PI / 2;
    tireGroup.add(beltMesh);

    let animationId: number;

    // Real-time render loop updating physical geometry state values
    const render = () => {
      animationId = requestAnimationFrame(render);

      // Handle continuous automatic spin based on telemetry live speed
      const curSpeed = speedRef.current;
      const curPressure = pressureRef.current;
      const curThermalMode = thermalModeRef.current;
      const curExplodedView = explodedViewRef.current;
      const curWearPattern = wearPatternRef.current;

      if (curSpeed > 0 && !isDragging.current) {
        // Continuous rotation around rolling axis
        rotationRef.current.y += (curSpeed / 3.6) * 0.003;
      }

      // Assign interactive mouse / drag rotation inputs
      tireGroup.rotation.x = rotationRef.current.x;
      tireGroup.rotation.y = rotationRef.current.y;

      // Assign dynamic zoom level properties to camera distance
      camera.position.z = cameraZRef.current;

      // Real-time structural deformation depending on pressure telemetry
      // Simulation of sag under deflection at bottom and side bloating
      const sagFactor = curPressure < 28 ? (28 - curPressure) / 13 : 0;
      const balloonFactor = curPressure > 35 ? (curPressure - 35) * 0.01 : 0;
      
      const widthScale = 1.0 + balloonFactor;
      const heightScale = 1.0 - sagFactor * 0.07;
      
      treadMesh.scale.set(widthScale, heightScale, widthScale);

      // Skew tread mesh parameters based on current wear pattern
      if (curWearPattern === 'Camber Wear') {
        treadMesh.rotation.z = 0.09;
      } else {
        treadMesh.rotation.z = 0.0;
      }

      if (curWearPattern === 'Center Wear') {
        treadMesh.scale.set(widthScale * 0.93, heightScale * 1.03, widthScale * 0.93);
      } else if (curWearPattern === 'Edge Wear') {
        treadMesh.scale.set(widthScale * 1.04, heightScale * 0.94, widthScale * 1.04);
      }

      // Dynamic Material Shader profiles (Normal slate vs Thermal Mode mapping)
      if (curThermalMode) {
        // Glowing hot red tread, chilling cool blue structural rim hub
        (treadMesh.material as THREE.MeshStandardMaterial).color.setHex(0xff5e36);
        (rimMesh.material as THREE.MeshStandardMaterial).color.setHex(0x58a6ff);
        (treadMesh.material as THREE.MeshStandardMaterial).wireframe = true;
      } else {
        (treadMesh.material as THREE.MeshStandardMaterial).color.setHex(0x21262d);
        (rimMesh.material as THREE.MeshStandardMaterial).color.setHex(0x8a9ba8);
        (treadMesh.material as THREE.MeshStandardMaterial).wireframe = false;
      }

      // Exploded views expand components along displacement vectors
      if (curExplodedView) {
        // Outer tread splits away from spoke hubs
        treadMesh.position.y = 0.5;
        rimMesh.position.y = -0.5;
        spokesGroup.position.y = -0.5;
        beltMesh.position.y = 0.0;
        (beltMesh.material as THREE.MeshStandardMaterial).opacity = 0.85;
        (rimMesh.material as THREE.MeshStandardMaterial).wireframe = true;
      } else {
        treadMesh.position.y = 0.0;
        rimMesh.position.y = 0.0;
        spokesGroup.position.y = 0.0;
        beltMesh.position.y = 0.0;
        (beltMesh.material as THREE.MeshStandardMaterial).opacity = 0.0;
        (rimMesh.material as THREE.MeshStandardMaterial).wireframe = false;
      }

      // Visual shake animation on the 3D model if any threshold is exceeded
      const isThresholdExceeded =
        temperatureRef.current > tempMaxRef.current ||
        pressureRef.current < pressMinRef.current ||
        pressureRef.current > pressMaxRef.current;

      if (isThresholdExceeded) {
        const timeFactor = Date.now() * 0.085;
        // Apply high frequency, erratic vibration offsets representing structural overload
        tireGroup.position.x = Math.sin(timeFactor) * 0.08;
        tireGroup.position.y = Math.cos(timeFactor * 1.3) * 0.08;
        tireGroup.position.z = Math.sin(timeFactor * 2.1) * 0.05;
      } else {
        tireGroup.position.set(0, 0, 0); // Reset position to origin
      }

      renderer.render(scene, camera);
      gl.endFrameEXP();
    };

    render();

    // Clean up animation frame buffer reference on component lifecycle terminate
    return () => {
      cancelAnimationFrame(animationId);
    };
  };

  // Status visual attributes
  const pressureColor = pressure < pressMin ? '#ff3333' : pressure > pressMax ? '#ffaa00' : '#00ff66';
  const temperatureColor = temperature > tempMax ? '#ff3333' : temperature > (tempMax - 30) ? '#ff6b00' : '#58a6ff';
  const isUIThresholdExceeded = temperature > tempMax || pressure < pressMin || pressure > pressMax;

  return (
    <View style={styles.container}>
      {/* 3D Viewport with Gesture Handler bounds */}
      <View style={styles.viewport} {...panResponder.panHandlers}>
        <GLView style={styles.glView} onContextCreate={onContextCreate} />
      </View>

      {/* Embedded Real-time Telemetry Floating HUD Panels */}
      {!compiling && !waitingForPacket && (
        <View style={StyleSheet.absoluteFillObject} pointerEvents="box-none">
          {/* Top Center: Core Heat Temperature Widget */}
          <View style={styles.topHudContainer} pointerEvents="box-none">
            <View style={[styles.hudCard, { borderColor: temperatureColor }]}>
              <View style={styles.hudCardHeader}>
                <Text style={[styles.hudCardLabel, { color: temperatureColor }]}>CORE TEMP</Text>
                <View style={[styles.statusDot, { backgroundColor: temperatureColor }]} />
              </View>
              <Text style={styles.hudCardValue}>
                {temperature.toFixed(1)}<Text style={styles.hudCardUnit}> °C</Text>
              </Text>
              <View style={styles.barBackground}>
                <View style={[styles.barFill, { width: `${Math.min(100, (temperature / 110) * 100)}%`, backgroundColor: temperatureColor }]} />
              </View>
            </View>
          </View>

          {/* Real-time Threshold Warning Banner */}
          {isUIThresholdExceeded && (
            <View style={styles.warningBannerContainer} pointerEvents="none">
              <View style={styles.warningBadge}>
                <Text style={styles.warningText}>
                  ⚠️ METRICS ALERT: DEVICE VIBRATING DUE TO ANOMALOUS OVERLOAD
                </Text>
              </View>
            </View>
          )}

          {/* Floating Config Thresholds Toggle and Panel (Collapsible) */}
          <View style={styles.configAnchorContainer} pointerEvents="box-none">
            <TouchableOpacity
              style={[styles.configToggleButton, showConfig && styles.configToggleButtonActive]}
              onPress={() => setShowConfig(prev => !prev)}
              activeOpacity={0.8}
            >
              <Text style={styles.configToggleText}>
                {showConfig ? '✕ HIDE CONFIG' : '⚙️ CONFIG LIMITS'}
              </Text>
            </TouchableOpacity>

            {showConfig && (
              <View style={styles.configCard}>
                <Text style={styles.configHeader}>ALARM SENSITIVITY</Text>
                
                {/* Temp limit */}
                <View style={styles.configRow}>
                  <Text style={styles.configLabel}>MAX TEMP: {tempMax}°C</Text>
                  <View style={styles.configControls}>
                    <TouchableOpacity
                      style={styles.stepButton}
                      onPress={() => setTempMax(t => Math.max(30, t - 5))}
                    >
                      <Text style={styles.stepButtonText}>-5</Text>
                    </TouchableOpacity>
                    <TouchableOpacity
                      style={styles.stepButton}
                      onPress={() => setTempMax(t => Math.min(120, t + 5))}
                    >
                      <Text style={styles.stepButtonText}>+5</Text>
                    </TouchableOpacity>
                  </View>
                </View>

                {/* Min Pressure limit */}
                <View style={styles.configRow}>
                  <Text style={styles.configLabel}>MIN PRESS: {pressMin} PSI</Text>
                  <View style={styles.configControls}>
                    <TouchableOpacity
                      style={styles.stepButton}
                      onPress={() => setPressMin(p => Math.max(15, p - 1))}
                    >
                      <Text style={styles.stepButtonText}>-1</Text>
                    </TouchableOpacity>
                    <TouchableOpacity
                      style={styles.stepButton}
                      onPress={() => setPressMin(p => Math.min(pressMax - 1, p + 1))}
                    >
                      <Text style={styles.stepButtonText}>+1</Text>
                    </TouchableOpacity>
                  </View>
                </View>

                {/* Max Pressure limit */}
                <View style={styles.configRow}>
                  <Text style={styles.configLabel}>MAX PRESS: {pressMax} PSI</Text>
                  <View style={styles.configControls}>
                    <TouchableOpacity
                      style={styles.stepButton}
                      onPress={() => setPressMax(p => Math.max(pressMin + 1, p - 1))}
                    >
                      <Text style={styles.stepButtonText}>-1</Text>
                    </TouchableOpacity>
                    <TouchableOpacity
                      style={styles.stepButton}
                      onPress={() => setPressMax(p => Math.min(60, p + 1))}
                    >
                      <Text style={styles.stepButtonText}>+1</Text>
                    </TouchableOpacity>
                  </View>
                </View>

                <View style={styles.legendDivider} />
                <Text style={styles.configHelpText}>
                  Model shakes physically when current metrics exceed these custom limits.
                </Text>
              </View>
            )}
          </View>

          {/* Floating Diagnostic Legend Toggle and Panel (Collapsible) */}
          <View style={styles.legendAnchorContainer} pointerEvents="box-none">
            <TouchableOpacity
              style={[styles.legendToggleButton, showLegend && styles.legendToggleButtonActive]}
              onPress={() => setShowLegend(prev => !prev)}
              activeOpacity={0.8}
            >
              <Text style={styles.legendToggleText}>
                {showLegend ? '✕ HIDE LEGEND' : '📊 ROAD LEGEND'}
              </Text>
            </TouchableOpacity>

            {showLegend && (
              <View style={styles.legendCard}>
                <Text style={styles.legendHeader}>THERMAL SCALE</Text>
                
                <View style={styles.legendRow}>
                  <View style={[styles.legendIndicator, { backgroundColor: '#58a6ff' }]} />
                  <View style={styles.legendTexts}>
                    <Text style={styles.legendLabel}>COOL / NORMAL</Text>
                    <Text style={styles.legendDesc}>&lt; 50°C · Standard ambient load</Text>
                  </View>
                </View>

                <View style={styles.legendRow}>
                  <View style={[styles.legendIndicator, { backgroundColor: '#ff6b00' }]} />
                  <View style={styles.legendTexts}>
                    <Text style={styles.legendLabel}>WARM / HIGH LOAD</Text>
                    <Text style={styles.legendDesc}>50°C - 80°C · High highway rate</Text>
                  </View>
                </View>

                <View style={styles.legendRow}>
                  <View style={[styles.legendIndicator, { backgroundColor: '#ff3333' }]} />
                  <View style={styles.legendTexts}>
                    <Text style={styles.legendLabel}>CRITICAL OVERHEAT</Text>
                    <Text style={styles.legendDesc}>&gt; 80°C · Severe blowout risk</Text>
                  </View>
                </View>

                <View style={styles.legendDivider} />

                <Text style={styles.legendHeader}>WEAR INDICATORS</Text>

                <View style={styles.legendRow}>
                  <Text style={styles.legendIcon}>🟢</Text>
                  <View style={styles.legendTexts}>
                    <Text style={styles.legendLabel}>NORMAL</Text>
                    <Text style={styles.legendDesc}>Optimal contact distribution</Text>
                  </View>
                </View>

                <View style={styles.legendRow}>
                  <Text style={styles.legendIcon}>⚠️</Text>
                  <View style={styles.legendTexts}>
                    <Text style={styles.legendLabel}>CENTER WEAR</Text>
                    <Text style={styles.legendDesc}>Over-inflation tread bulge</Text>
                  </View>
                </View>

                <View style={styles.legendRow}>
                  <Text style={styles.legendIcon}>⚠️</Text>
                  <View style={styles.legendTexts}>
                    <Text style={styles.legendLabel}>EDGE WEAR</Text>
                    <Text style={styles.legendDesc}>Under-inflation shoulder stress</Text>
                  </View>
                </View>

                <View style={styles.legendRow}>
                  <Text style={styles.legendIcon}>⚠️</Text>
                  <View style={styles.legendTexts}>
                    <Text style={styles.legendLabel}>CAMBER WEAR</Text>
                    <Text style={styles.legendDesc}>Suspension alignment wheel skew</Text>
                  </View>
                </View>
              </View>
            )}
          </View>

          {/* Bottom Row: Life Speed Control & Dynamic Pressure State */}
          <View style={styles.bottomHudContainer} pointerEvents="box-none">
            {/* Left: Speed readout */}
            <View style={[styles.hudCard, { borderColor: '#58a6ff' }]}>
              <View style={styles.hudCardHeader}>
                <Text style={[styles.hudCardLabel, { color: '#58a6ff' }]}>LIVE SPD</Text>
                <View style={[styles.statusDot, { backgroundColor: speed > 0 ? '#00ff66' : '#8a9ba8' }]} />
              </View>
              <Text style={styles.hudCardValue}>
                {speed.toFixed(0)}<Text style={styles.hudCardUnit}> km/h</Text>
              </Text>
              <View style={styles.barBackground}>
                <View style={[styles.barFill, { width: `${Math.min(100, (speed / 120) * 100)}%`, backgroundColor: '#58a6ff' }]} />
              </View>
            </View>

            {/* Right: Pressure readout */}
            <View style={[styles.hudCard, { borderColor: pressureColor }]}>
              <View style={styles.hudCardHeader}>
                <Text style={[styles.hudCardLabel, { color: pressureColor }]}>PRESSURE</Text>
                <Text style={[styles.statusBadge, { backgroundColor: pressureColor }]}>
                  {pressure < 28 ? 'LOW' : pressure > 35 ? 'HIGH' : 'OK'}
                </Text>
              </View>
              <Text style={styles.hudCardValue}>
                {pressure.toFixed(1)}<Text style={styles.hudCardUnit}> PSI</Text>
              </Text>
              <View style={styles.barBackground}>
                <View style={[styles.barFill, { width: `${Math.min(100, (pressure / 45) * 100)}%`, backgroundColor: pressureColor }]} />
              </View>
            </View>
          </View>

          {/* Quick HUD guide tip */}
          <View style={styles.tipContainer} pointerEvents="none">
            <Text style={styles.tipText}>Drag to rotate · Pinch to zoom · Double-tap to reset view</Text>
          </View>
        </View>
      )}

      {/* Interactive, Shimmering Blueprint Skeleton Loader for Telemetry Hydration */}
      {!compiling && waitingForPacket && (
        <View style={StyleSheet.absoluteFillObject} pointerEvents="box-none">
          {/* Subtle dim outline on back, letting rotating model drift through */}
          <View style={[StyleSheet.absoluteFillObject, { backgroundColor: 'rgba(13, 17, 23, 0.4)' }]} pointerEvents="none" />

          {/* Top Center: Core Temp Skeleton Card */}
          <View style={styles.topHudContainer} pointerEvents="box-none">
            <View style={[styles.hudCard, { borderColor: '#21262D', borderStyle: 'dashed', backgroundColor: 'rgba(10, 14, 20, 0.75)' }]}>
              <View style={styles.hudCardHeader}>
                <View style={{ width: 62, height: 8, backgroundColor: '#21262D', borderRadius: 4, opacity: shimmerAlpha }} />
                <View style={{ width: 6, height: 6, borderRadius: 3, backgroundColor: '#ffaa00', opacity: shimmerAlpha }} />
              </View>
              <View style={{ width: 80, height: 16, backgroundColor: '#21262D', borderRadius: 4, marginTop: 6, opacity: shimmerAlpha }} />
              <View style={[styles.barBackground, { opacity: shimmerAlpha }]}>
                <View style={{ width: '40%', height: '100%', backgroundColor: '#21262D' }} />
              </View>
            </View>
          </View>

          {/* Center Connection Lock overlay banner */}
          <View style={{ position: 'absolute', top: '35%', left: 20, right: 20, alignItems: 'center' }} pointerEvents="box-none">
            <View style={{
              backgroundColor: 'rgba(10, 14, 20, 0.95)',
              borderWidth: 1,
              borderColor: '#ffaa00',
              borderRadius: 8,
              paddingVertical: 10,
              paddingHorizontal: 16,
              alignItems: 'center',
              shadowColor: '#000',
              shadowOffset: { width: 0, height: 4 },
              shadowOpacity: 0.3,
              shadowRadius: 6,
              elevation: 4,
            }}>
              <Text style={{ fontSize: 10, fontFamily: 'monospace', color: '#ffaa00', fontWeight: 'bold', letterSpacing: 0.6, marginBottom: 4 }}>
                🛰️ [AWAITING IoT SENSORS DISPATCH]
              </Text>
              <Text style={{ fontSize: 8, fontFamily: 'monospace', color: '#8a9ba8', textAlign: 'center', marginBottom: 8 }}>
                Listening on UDP broadcast port 1904...
              </Text>
              <TouchableOpacity
                onPress={() => setWaitingForPacket(false)}
                style={{
                  backgroundColor: '#ffaa00',
                  borderRadius: 4,
                  paddingVertical: 4,
                  paddingHorizontal: 10,
                  borderWidth: 1,
                  borderColor: '#fff',
                }}
              >
                <Text style={{ fontSize: 9, fontFamily: 'monospace', fontWeight: '900', color: '#0d1117' }}>
                  ⚡ BYPASS & SECURE LINK
                </Text>
              </TouchableOpacity>
            </View>
          </View>

          {/* Bottom Row: Speed & Pressure Skeleton Cards */}
          <View style={styles.bottomHudContainer} pointerEvents="box-none">
            {/* Left: Speed Skeleton */}
            <View style={[styles.hudCard, { borderColor: '#21262D', borderStyle: 'dashed', backgroundColor: 'rgba(10, 14, 20, 0.75)' }]}>
              <View style={styles.hudCardHeader}>
                <View style={{ width: 52, height: 8, backgroundColor: '#21262D', borderRadius: 4, opacity: shimmerAlpha }} />
                <View style={{ width: 6, height: 6, borderRadius: 3, backgroundColor: '#8a9ba8', opacity: shimmerAlpha }} />
              </View>
              <View style={{ width: 70, height: 16, backgroundColor: '#21262D', borderRadius: 4, marginTop: 6, opacity: shimmerAlpha }} />
              <View style={[styles.barBackground, { opacity: shimmerAlpha }]}>
                <View style={{ width: '30%', height: '100%', backgroundColor: '#21262D' }} />
              </View>
            </View>

            {/* Right: Pressure Skeleton */}
            <View style={[styles.hudCard, { borderColor: '#21262D', borderStyle: 'dashed', backgroundColor: 'rgba(10, 14, 20, 0.75)' }]}>
              <View style={styles.hudCardHeader}>
                <View style={{ width: 58, height: 8, backgroundColor: '#21262D', borderRadius: 4, opacity: shimmerAlpha }} />
                <View style={{ width: 22, height: 8, borderRadius: 3, backgroundColor: '#21262D', opacity: shimmerAlpha }} />
              </View>
              <View style={{ width: 75, height: 16, backgroundColor: '#21262D', borderRadius: 4, marginTop: 6, opacity: shimmerAlpha }} />
              <View style={[styles.barBackground, { opacity: shimmerAlpha }]}>
                <View style={{ width: '55%', height: '100%', backgroundColor: '#21262D' }} />
              </View>
            </View>
          </View>
        </View>
      )}

      {/* Cyberpunk GPU Compiler Splash Progress Overlay */}
      {compiling && (
        <View style={[StyleSheet.absoluteFillObject, styles.compilerOverlay]}>
          {/* Concentric rings represent scanning framework */}
          <View style={styles.outerRing}>
            <View style={styles.innerRing}>
              <View style={styles.rimCoreDot} />
            </View>
          </View>

          <ActivityIndicator size="small" color="#58a6ff" style={styles.loadingSpinner} />
          <Text style={styles.compilerHeader}>Initializing GPU Canvas...</Text>
          <Text style={styles.compilerProgress}>Compiling Shaders: {Math.min(100, progress)}%</Text>

          <View style={styles.logsBox}>
            <Text style={styles.logLine}>[SYSTEM_LOG] Loading procedural tire torus model...</Text>
            <Text style={styles.logLine}>[SYSTEM_LOG] Mapping steel-belt vertex structures...</Text>
            <Text style={styles.logLine}>[SYSTEM_LOG] Binding real-time telemetry animation hooks...</Text>
          </View>
        </View>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#0D1117',
    borderRadius: 16,
    borderWidth: 1,
    borderColor: '#21262D',
    overflow: 'hidden',
  },
  viewport: {
    flex: 1,
  },
  glView: {
    flex: 1,
  },
  topHudContainer: {
    position: 'absolute',
    top: 14,
    left: 0,
    right: 0,
    alignItems: 'center',
  },
  configAnchorContainer: {
    position: 'absolute',
    top: 74,
    left: 14,
    width: 210,
    zIndex: 100,
    alignItems: 'flex-start',
  },
  configToggleButton: {
    backgroundColor: 'rgba(10, 14, 20, 0.9)',
    borderWidth: 1.2,
    borderColor: 'rgba(88, 166, 255, 0.4)',
    borderRadius: 6,
    paddingVertical: 5,
    paddingHorizontal: 10,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.25,
    shadowRadius: 3,
    elevation: 3,
  },
  configToggleButtonActive: {
    borderColor: '#58a6ff',
    backgroundColor: '#161b22',
  },
  configToggleText: {
    color: '#58a6ff',
    fontSize: 8,
    fontWeight: 'bold',
    fontFamily: 'monospace',
    letterSpacing: 0.5,
  },
  configCard: {
    backgroundColor: 'rgba(10, 14, 20, 0.95)',
    borderWidth: 1,
    borderColor: 'rgba(88, 166, 255, 0.35)',
    borderRadius: 8,
    padding: 10,
    marginTop: 6,
    width: '100%',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.4,
    shadowRadius: 5,
    elevation: 8,
  },
  configHeader: {
    color: '#58a6ff',
    fontSize: 8,
    fontWeight: '900',
    fontFamily: 'monospace',
    letterSpacing: 0.8,
    marginBottom: 6,
  },
  configRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginVertical: 4,
  },
  configLabel: {
    color: '#ffffff',
    fontSize: 8,
    fontWeight: 'bold',
    fontFamily: 'monospace',
  },
  configControls: {
    flexDirection: 'row',
    gap: 4,
    alignItems: 'center',
  },
  stepButton: {
    backgroundColor: '#21262d',
    borderWidth: 1,
    borderColor: 'rgba(88, 166, 255, 0.3)',
    borderRadius: 4,
    paddingHorizontal: 6,
    paddingVertical: 3,
    minHeight: 18,
    minWidth: 24,
    justifyContent: 'center',
    alignItems: 'center',
  },
  stepButtonText: {
    color: '#58a6ff',
    fontSize: 7.5,
    fontWeight: '900',
    fontFamily: 'monospace',
  },
  configHelpText: {
    color: '#8a9ba8',
    fontSize: 6.5,
    fontFamily: 'monospace',
    fontStyle: 'italic',
    marginTop: 2,
  },
  warningBannerContainer: {
    position: 'absolute',
    top: 135,
    left: 14,
    right: 14,
    alignItems: 'center',
    zIndex: 90,
  },
  warningBadge: {
    backgroundColor: 'rgba(255, 51, 51, 0.95)',
    borderWidth: 1.2,
    borderColor: '#ffffff',
    borderRadius: 6,
    paddingVertical: 4,
    paddingHorizontal: 10,
    shadowColor: '#ff3333',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.5,
    shadowRadius: 4,
    elevation: 5,
  },
  warningText: {
    color: '#ffffff',
    fontSize: 7,
    fontWeight: '900',
    fontFamily: 'monospace',
    letterSpacing: 0.3,
    textAlign: 'center',
  },
  legendAnchorContainer: {
    position: 'absolute',
    top: 74,
    right: 14,
    width: 210,
    zIndex: 100,
    alignItems: 'flex-end',
  },
  legendToggleButton: {
    backgroundColor: 'rgba(10, 14, 20, 0.9)',
    borderWidth: 1.2,
    borderColor: 'rgba(88, 166, 255, 0.4)',
    borderRadius: 6,
    paddingVertical: 5,
    paddingHorizontal: 10,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.25,
    shadowRadius: 3,
    elevation: 3,
  },
  legendToggleButtonActive: {
    borderColor: '#58a6ff',
    backgroundColor: '#161b22',
  },
  legendToggleText: {
    color: '#58a6ff',
    fontSize: 8,
    fontWeight: 'bold',
    fontFamily: 'monospace',
    letterSpacing: 0.5,
  },
  legendCard: {
    backgroundColor: 'rgba(10, 14, 20, 0.95)',
    borderWidth: 1,
    borderColor: 'rgba(88, 166, 255, 0.35)',
    borderRadius: 8,
    padding: 10,
    marginTop: 6,
    width: '100%',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.4,
    shadowRadius: 5,
    elevation: 8,
  },
  legendHeader: {
    color: '#58a6ff',
    fontSize: 8,
    fontWeight: '900',
    fontFamily: 'monospace',
    letterSpacing: 0.8,
    marginBottom: 6,
  },
  legendRow: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 6,
  },
  legendIndicator: {
    width: 7,
    height: 7,
    borderRadius: 3.5,
    marginRight: 6,
  },
  legendIcon: {
    fontSize: 9,
    marginRight: 6.5,
  },
  legendTexts: {
    flex: 1,
  },
  legendLabel: {
    color: '#ffffff',
    fontSize: 7.5,
    fontWeight: 'bold',
    fontFamily: 'monospace',
  },
  legendDesc: {
    color: '#8a9ba8',
    fontSize: 6.5,
    fontFamily: 'monospace',
    marginTop: 1,
  },
  legendDivider: {
    height: 0.5,
    backgroundColor: '#21262d',
    marginVertical: 6,
  },
  bottomHudContainer: {
    position: 'absolute',
    bottom: 40,
    left: 14,
    right: 14,
    flexDirection: 'row',
    justifyContent: 'space-between',
  },
  hudCard: {
    width: 125,
    backgroundColor: 'rgba(10, 14, 20, 0.9)',
    borderWidth: 1.5,
    borderRadius: 8,
    padding: 8,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.35,
    shadowRadius: 5,
    elevation: 6,
  },
  hudCardHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 4,
  },
  hudCardLabel: {
    fontSize: 9,
    fontWeight: 'bold',
    fontFamily: 'monospace',
    letterSpacing: 0.5,
  },
  statusDot: {
    width: 6,
    height: 6,
    borderRadius: 3,
  },
  statusBadge: {
    fontSize: 7,
    fontWeight: 'bold',
    paddingHorizontal: 3,
    paddingVertical: 1,
    borderRadius: 3,
    color: '#0d1117',
    overflow: 'hidden',
  },
  hudCardValue: {
    color: '#ffffff',
    fontSize: 16,
    fontWeight: '900',
    fontFamily: 'monospace',
  },
  hudCardUnit: {
    fontSize: 10,
    color: '#8a9ba8',
    fontWeight: 'normal',
  },
  barBackground: {
    width: '100%',
    height: 3,
    backgroundColor: '#21262d',
    borderRadius: 1.5,
    marginTop: 6,
    overflow: 'hidden',
  },
  barFill: {
    height: '100%',
    borderRadius: 1.5,
  },
  tipContainer: {
    position: 'absolute',
    bottom: 12,
    left: 14,
    right: 14,
    alignItems: 'center',
  },
  tipText: {
    color: '#8A9BA8',
    fontSize: 9,
    fontFamily: 'monospace',
    textAlign: 'center',
    opacity: 0.75,
  },
  compilerOverlay: {
    backgroundColor: '#0D1117',
    justifyContent: 'center',
    alignItems: 'center',
    paddingHorizontal: 24,
  },
  outerRing: {
    width: 140,
    height: 140,
    borderRadius: 70,
    borderWidth: 1.5,
    borderColor: 'rgba(88, 166, 255, 0.2)',
    borderStyle: 'dashed',
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: 20,
  },
  innerRing: {
    width: 90,
    height: 90,
    borderRadius: 45,
    borderWidth: 1,
    borderColor: 'rgba(88, 166, 255, 0.35)',
    borderStyle: 'dashed',
    justifyContent: 'center',
    alignItems: 'center',
  },
  rimCoreDot: {
    width: 40,
    height: 40,
    borderRadius: 20,
    borderWidth: 2,
    borderColor: '#58a6ff',
    backgroundColor: 'transparent',
    shadowColor: '#58a6ff',
    shadowOffset: { width: 0, height: 0 },
    shadowOpacity: 0.6,
    shadowRadius: 8,
  },
  loadingSpinner: {
    marginBottom: 8,
  },
  compilerHeader: {
    fontSize: 11,
    fontWeight: 'bold',
    fontFamily: 'monospace',
    color: '#58a6ff',
    letterSpacing: 1.2,
    textTransform: 'uppercase',
    marginBottom: 4,
  },
  compilerProgress: {
    fontSize: 13,
    fontWeight: 'bold',
    fontFamily: 'monospace',
    color: '#ffffff',
    marginBottom: 16,
  },
  logsBox: {
    alignItems: 'center',
    gap: 3,
  },
  logLine: {
    fontSize: 8,
    fontFamily: 'monospace',
    color: 'rgba(138, 155, 168, 0.6)',
  },
});
