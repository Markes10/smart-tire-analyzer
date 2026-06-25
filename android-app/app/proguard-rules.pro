# TFLite — keep the interpreter and support library
-keep class org.tensorflow.lite.** { *; }
-keep class org.tensorflow.lite.support.** { *; }
-keep class org.tensorflow.lite.gpu.** { *; }
-keepclassmembers class * { @org.tensorflow.lite.annotations.UsedByReflection *; }

# Keep model file assets
-keepclassmembers class com.example.util.TireInferenceEngine { *; }
