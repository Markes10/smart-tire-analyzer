// Lightweight module stubs for React Native / Expo packages used in this repo.
// These allow the TypeScript language server to resolve imports when full
// type packages are not installed. Replace with proper `@types` or library
// types when available.

declare module '@react-navigation/native';
declare module '@react-navigation/native-stack';
declare module 'expo-status-bar';
declare module 'react-native-gesture-handler';
declare module 'react-native-safe-area-context';
declare module '@react-native-async-storage/async-storage';
declare module 'expo-image-manipulator';
declare module 'expo-file-system';
declare module 'expo-camera';
declare module 'expo-image-picker';
declare module 'expo-media-library';

// Fall back for any other react-native named imports
declare module 'react-native' {
    const anyExport: any;
    export = anyExport;
}
