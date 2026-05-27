/**
 * App.tsx — Root navigation setup for Smart Tire Analyzer.
 * Supports: iOS, Android, Web (ChromeOS), Windows, macOS, Linux.
 */

import React from "react";
import { NavigationContainer } from "@react-navigation/native";
import { createNativeStackNavigator } from "@react-navigation/native-stack";
import { StatusBar } from "expo-status-bar";
import Platform from "react-native";
import { GestureHandlerRootView } from "react-native-gesture-handler";

import HomeScreen from "./src/screens/HomeScreen";
import CameraScreen from "./src/screens/CameraScreen";
import ResultScreen from "./src/screens/ResultScreen";
import HistoryScreen from "./src/screens/HistoryScreen";

const Stack = createNativeStackNavigator();

const DARK_THEME = {
  dark: true,
  colors: {
    primary: "#58A6FF",
    background: "#0D1117",
    card: "#161B22",
    text: "#F0F6FC",
    border: "#30363D",
    notification: "#F85149",
  },
};

export default function App() {
  React.useEffect(() => {
    if (Platform.OS === "web" && typeof document !== "undefined") {
      document.documentElement.style.backgroundColor = "#0D1117";
      document.body.style.backgroundColor = "#0D1117";
    }
  }, []);

  return (
    <GestureHandlerRootView
      style={{
        flex: 1,
        backgroundColor: "#0D1117",
        ...(Platform.OS === "web" ? { minHeight: "100vh" as any } : {}),
      }}
    >
      <NavigationContainer theme={DARK_THEME as any}>
        <StatusBar style="light" backgroundColor="#0D1117" />
        <Stack.Navigator
          initialRouteName="Home"
          screenOptions={{
            headerStyle: { backgroundColor: "#161B22" },
            headerTintColor: "#F0F6FC",
            headerTitleStyle: { fontWeight: "700" },
            headerShadowVisible: false,
            animation: "slide_from_right",
          }}
        >
          <Stack.Screen
            name="Home"
            component={HomeScreen}
            options={{ title: "Smart Tire", headerShown: false }}
          />
          <Stack.Screen
            name="Camera"
            component={CameraScreen}
            options={{ headerShown: false, gestureEnabled: false }}
          />
          <Stack.Screen
            name="Result"
            component={ResultScreen}
            options={{
              title: "Analysis Report",
              headerBackTitle: "Back",
            }}
          />
          <Stack.Screen
            name="History"
            component={HistoryScreen}
            options={{
              title: "Scan History",
              headerBackTitle: "Back",
            }}
          />
        </Stack.Navigator>
      </NavigationContainer>
    </GestureHandlerRootView>
  );
}
