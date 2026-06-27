# UML Diagrams — Smart Tire Analyzer

## 1. Use Case Diagram

```mermaid
graph TD
    Actor1["👤 User / Technician"]
    Actor2["🌐 External APIs<br/>(Gemini, Google Maps,<br/>OpenWeather, Mapillary)"]
    Actor3["🤖 System (Auto Retrain)"]
    
    subgraph "Smart Tire Analyzer System"
        UC1["Upload Tire Image"]
        UC2["Analyze Tire Condition"]
        UC3["View Analysis Report"]
        UC4["Submit Feedback / Correction"]
        UC5["View History"]
        UC6["Authenticate (Login / Sign Up)"]
        UC7["Manage API Keys"]
        UC8["Monitor System Health"]
        UC9["View Enterprise Dashboard"]
        UC10["Retrain Model Automatically"]
        UC11["Fetch Road & Weather Context"]
        UC12["Generate AI Reasoning Report"]
    end

    Actor1 --> UC1
    Actor1 --> UC2
    Actor1 --> UC3
    Actor1 --> UC4
    Actor1 --> UC5
    Actor1 --> UC6
    Actor1 --> UC7
    Actor1 --> UC8
    Actor1 --> UC9
    
    UC2 --> UC11
    UC2 --> UC12
    UC11 --> Actor2
    UC12 --> Actor2
    
    Actor3 --> UC10
```

---

## 2. Class Diagram

```mermaid
classDiagram
    class AnalysisResult {
        +String id
        +String session_id
        +DateTime timestamp
        +Float health_score
        +Float avg_tread_mm
        +Float remaining_life_km
        +String wear_pattern_label
        +String wear_pattern_severity
        +String risk_level
        +Boolean replace_immediately
        +Float confidence
        +JSON full_report
        +Float latitude
        +Float longitude
        +String weather_condition
        +String tire_brand
        +String tire_model
        +String tire_size
        +String image_filename
        +String model_version
    }

    class User {
        +String id
        +String first_name
        +String last_name
        +String email
        +String password_hash
        +String gemini_key
        +String mapillary_token
        +String openweather_key
        +DateTime created_at
    }

    class FeedbackRecord {
        +String id
        +String session_id
        +DateTime timestamp
        +String feedback_type
        +Float corrected_tread_mm
        +String corrected_wear_pattern
        +Float corrected_health_score
        +Float confidence_override
        +String comment
        +JSON original_prediction
        +JSON corrected_prediction
    }

    class AppSettings {
        +List~str~ GEMINI_API_KEYS
        +List~str~ GOOGLE_MAPS_API_KEYS
        +List~str~ OPENWEATHER_API_KEYS
        +List~str~ MAPILLARY_API_KEYS
        +String DATABASE_URL
        +String JWT_SECRET
        +Float CONFIDENCE_THRESHOLD
        +Float BLUR_THRESHOLD
        +Boolean AUTH_ENABLED
        +get_gemini_keys()
        +get_cors_origins()
        +get_feature_flags()
    }

    class SecurityService {
        -String secret
        +create_demo_token()
        +verify_token()
        +verify_api_key()
        +verify_authorization_header()
        +status()
    }

    class InferenceService {
        -Model model
        -Boolean ready
        -String load_error
        +initialize()
        +predict()
        +is_ready()
        +cleanup()
    }

    class ReportService {
        +build_report()
    }

    class GeminiService {
        +reason()
    }

    class MapsService {
        +get_road_context()
        +get_route_road_context()
    }

    class WeatherService {
        +get_weather()
    }

    class APIKeyRotator {
        -List~str~ keys
        -Dict usage
        -Boolean active
        +get_current_key()
        +rotate()
        +record_usage()
        +get_status()
    }

    class EnterpriseAIService {
        +build_analysis_extensions()
    }

    class NotificationService {
        +notify_high_risk_analysis()
    }

    class HybridTorchModel {
        -CNNEncoder cnn
        -ViTEncoder vit
        -RNNEncoder rnn
        -AttentionFusion fusion
        -PredictionHeads heads
        +forward()
        +predict()
    }

    AnalysisResult --> User : analyzed_by
    FeedbackRecord --> AnalysisResult : references
    InferenceService --> HybridTorchModel : uses
    InferenceService --> APIKeyRotator : uses
    GeminiService --> APIKeyRotator : uses
    MapsService --> APIKeyRotator : uses
    WeatherService --> APIKeyRotator : uses
    ReportService --> InferenceService : uses result
    ReportService --> GeminiService : uses reasoning
    EnterpriseAIService --> AnalysisResult : extends
    SecurityService --> AppSettings : reads config
    AppSettings --> APIKeyRotator : provides keys
```

---

## 3. Sequence Diagram — Tire Analysis Flow

```mermaid
sequenceDiagram
    participant U as User
    participant F as Frontend (Next.js)
    participant B as Backend API (FastAPI)
    participant IS as Inference Service
    participant M as Hybrid AI Model
    participant GM as Gemini AI
    participant MP as Maps Service
    participant WT as Weather Service
    participant DB as SQLite Database

    U->>F: Upload tire image
    F->>B: POST /analyze (multipart image)
    B->>B: Validate image (size, type, blur)
    B->>IS: predict(image_bytes, context)
    IS->>IS: Preprocess (CLAHE, resize 224x224, normalize)
    IS->>M: forward(preprocessed_tensor)
    M->>M: CNN feature extraction
    M->>M: ViT global pattern encoding
    M->>M: RNN sequence analysis
    M->>M: Attention fusion
    M->>M: Prediction heads
    M-->>IS: {tread_depths, health, life, wear_pattern, confidence}
    
    alt has GPS coordinates
        B->>MP: get_road_context(lat, lon)
        MP-->>B: road_type, surface_condition
        B->>WT: get_weather(lat, lon)
        WT-->>B: temperature, humidity, conditions
    end

    alt has API keys
        B->>GM: reason(predictions, context)
        GM-->>B: driving_advice, urgency, recommendations
    end

    B->>B: Build final report
    B->>DB: save_analysis_result(report)
    B-->>F: AnalysisResponse JSON
    F-->>U: Display report
```

---

## 4. Activity Diagram — Tire Analysis Workflow

```mermaid
graph TD
    Start(["User Uploads Image"]) --> Validate{Validation Pass?}
    Validate -->|No| Reject["Reject: Bad Format / Size / Blur"]
    Validate -->|Yes| Preproc["Preprocess Image<br/>(Denoise, CLAHE, Resize, Normalize)"]
    Preproc --> CNN["CNN: Local Feature Extraction<br/>(EfficientNetV2-B0)"]
    CNN --> ViT["ViT: Global Pattern Encoding<br/>(ViT-B/16)"]
    ViT --> RNN["RNN: Sequential Analysis<br/>(BiLSTM + TCN)"]
    RNN --> Fusion["Cross-Modal Attention Fusion"]
    Fusion --> Predict["Multi-Task Prediction Heads"]
    Predict --> Tread["Tread Depth (T1-T4)"]
    Predict --> Health["Health Score (0-10)"]
    Predict --> Life["Remaining Life (km)"]
    Predict --> Wear["Wear Pattern (6-class)"]
    
    Tread --> Context{Has GPS?}
    Health --> Context
    Life --> Context
    Wear --> Context
    
    Context -->|Yes| Fetch["Fetch Road & Weather Context"]
    Context -->|No| Choose{Has Gemini?}
    Fetch --> Choose
    
    Choose -->|Yes| Reason["Gemini AI Reasoning"]
    Choose -->|No| Build["Build Final Report"]
    Reason --> Build
    
    Build --> Risk{Risk Level?}
    Risk -->|HIGH/CRITICAL| Notify["Send Notification"]
    Risk -->|LOW/MODERATE| Save["Save to Database"]
    Notify --> Save
    
    Save --> CL{Continuous Learning?}
    CL -->|Has Feedback| Retrain["Auto-Retrain Model"]
    CL -->|No| Done(["Return Report to User"])
    Retrain --> Done
```

---

## 5. Entity-Relationship (ER) Diagram

```mermaid
erDiagram
    USERS ||--o{ ANALYSIS_RESULTS : "performs"
    ANALYSIS_RESULTS ||--o{ FEEDBACK_RECORDS : "receives"
    
    USERS {
        string id PK
        string first_name
        string last_name
        string email UK
        string password_hash
        string gemini_key
        string mapillary_token
        string openweather_key
        datetime created_at
    }
    
    ANALYSIS_RESULTS {
        string id PK
        string session_id UK
        datetime timestamp
        float health_score
        float avg_tread_mm
        float remaining_life_km
        string wear_pattern_label
        string wear_pattern_severity
        string risk_level
        boolean replace_immediately
        float confidence
        json full_report
        float latitude
        float longitude
        string weather_condition
        string tire_brand
        string tire_model
        string tire_size
        string image_filename
        string model_version
        string user_id FK
    }
    
    FEEDBACK_RECORDS {
        string id PK
        string session_id FK
        datetime timestamp
        string feedback_type
        float corrected_tread_mm
        string corrected_wear_pattern
        float corrected_health_score
        float confidence_override
        text comment
        json original_prediction
        json corrected_prediction
    }
```

---

## 6. Data Flow Diagram (DFD) — Level 0

```mermaid
graph TD
    U[("👤 User")]
    FE[("🌐 Frontend<br/>(Next.js)")]
    BE[("⚙️ Backend<br/>(FastAPI)")]
    DB[("💾 SQLite Database")]
    GM[("☁️ Gemini AI API")]
    MP[("🗺️ Google Maps API")]
    WT[("🌦️ OpenWeather API")]
    ML[("🔬 ML Model<br/>(Hybrid Torch)")]
    
    U -->|"Upload Image"| FE
    U -->|"View Reports"| FE
    U -->|"Submit Feedback"| FE
    U -->|"Login / Register"| FE
    
    FE -->|"HTTP Requests"| BE
    BE -->|"JSON Responses"| FE
    
    BE -->|"Read/Write"| DB
    BE -->|"Invoke"| ML
    
    BE -->|"Gemini API Calls"| GM
    BE -->|"Maps API Calls"| MP
    BE -->|"Weather API Calls"| WT
    
    GM -->|"AI Reasoning"| BE
    MP -->|"Road Context"| BE
    WT -->|"Weather Data"| BE
    ML -->|"Predictions"| BE
```

---

## 7. DFD Level 1 — Analysis Process

```mermaid
graph TD
    subgraph "Process: Analyze Tire"
        P1["1. Validate Image<br/>(Format, Size, Blur)"]
        P2["2. Preprocess<br/>(CLAHE, Resize, Normalize)"]
        P3["3. AI Inference<br/>(CNN + ViT + RNN)"]
        P4["4. Context Fetch<br/>(Maps + Weather)"]
        P5["5. Gemini Reasoning"]
        P6["6. Build Report"]
        P7["7. Save Result"]
    end
    
    D1[("Image Storage")]
    D2[("Database")]
    D3[("External APIs")]
    D4[("ML Models")]
    
    U["User Input"] --> P1
    P1 --> P2
    P2 --> P3
    P3 --> D4
    P3 --> P4
    P4 --> D3
    P4 --> P5
    P5 --> P6
    P6 --> P7
    P7 --> D2
    P6 -->|Response| U
```

---

## 8. Deployment Diagram

```mermaid
graph TD
    subgraph "User Device"
        BROWSER["🌐 Web Browser<br/>(Next.js Frontend)"]
        ANDROID["📱 Android App<br/>(Kotlin/Jetpack Compose)"]
    end

    subgraph "Server (Docker Host)"
        subgraph "Docker Containers"
            API["FastAPI Backend<br/>Port 8000"]
            NGINX["Nginx Reverse Proxy<br/>Port 80/443"]
        end
        
        subgraph "Storage"
            DB[("SQLite Database<br/>smart_tire.db")]
            MODELS[("AI Models<br/>saved_models/")]
            IMAGES[("Uploaded Images<br/>continuous_learning/")]
        end
        
        subgraph "GPU / CPU"
            ML["Hybrid Torch Model<br/>(TorchScript)"]
        end
    end

    subgraph "External Services"
        GEMINI["Gemini AI API"]
        MAPS["Google Maps API"]
        WEATHER["OpenWeather API"]
        MAPILLARY["Mapillary API"]
    end

    BROWSER --> API
    ANDROID --> API
    API --> NGINX
    API --> DB
    API --> MODELS
    API --> IMAGES
    API --> ML
    API --> GEMINI
    API --> MAPS
    API --> WEATHER
    API --> MAPILLARY
```

---

## 9. Component Diagram

```mermaid
graph TD
    subgraph "Frontend Layer"
        WEB["Next.js Web App<br/>(React 19, Tailwind CSS)"]
        ANDROID["Android App<br/>(Kotlin, Jetpack Compose)"]
    end

    subgraph "API Layer (FastAPI)"
        AUTH["Auth Router<br/>/auth"]
        ANALYZE["Analyze Router<br/>/analyze"]
        FEEDBACK["Feedback Router<br/>/feedback"]
        HISTORY["History Router<br/>/history"]
        HEALTH["Health Router<br/>/health"]
        ENTERPRISE["Enterprise Router<br/>/enterprise"]
        METRICS["Metrics Router<br/>/metrics"]
    end

    subgraph "Service Layer"
        INFERENCE["Inference Service"]
        GEMINI_SVC["Gemini Service"]
        MAPS_SVC["Maps Service"]
        WEATHER_SVC["Weather Service"]
        REPORT_SVC["Report Service"]
        SECURITY_SVC["Security Service"]
        NOTIF_SVC["Notification Service"]
        ENTERPRISE_SVC["Enterprise AI Service"]
        ROTATOR["API Key Rotator"]
    end

    subgraph "Model Layer"
        CNN["CNN Encoder<br/>(EfficientNetV2-B0)"]
        VIT["ViT Encoder<br/>(ViT-B/16)"]
        RNN["RNN Encoder<br/>(BiLSTM + TCN)"]
        FUSION["Attention Fusion"]
        HEADS["Prediction Heads"]
    end

    subgraph "Data Layer"
        DB[("SQLite")]
        CL[("Continuous Learning<br/>Dataset")]
    end

    WEB --> AUTH
    WEB --> ANALYZE
    WEB --> FEEDBACK
    WEB --> HISTORY
    WEB --> ENTERPRISE
    
    ANDROID --> ANALYZE
    ANDROID --> AUTH
    ANDROID --> HISTORY

    ANALYZE --> INFERENCE
    ANALYZE --> GEMINI_SVC
    ANALYZE --> MAPS_SVC
    ANALYZE --> WEATHER_SVC
    ANALYZE --> REPORT_SVC
    ANALYZE --> NOTIF_SVC
    ANALYZE --> ENTERPRISE_SVC

    AUTH --> SECURITY_SVC
    ENTERPRISE --> SECURITY_SVC

    INFERENCE --> CNN
    INFERENCE --> VIT
    INFERENCE --> RNN
    INFERENCE --> FUSION
    INFERENCE --> HEADS

    GEMINI_SVC --> ROTATOR
    MAPS_SVC --> ROTATOR
    WEATHER_SVC --> ROTATOR

    ANALYZE --> DB
    FEEDBACK --> DB
    HISTORY --> DB
    FEEDBACK --> CL
```

---

## 10. State Diagram — Analysis Lifecycle

```mermaid
stateDiagram-v2
    [*] --> Uploaded: User uploads image
    Uploaded --> Validating: Image received
    
    Validating --> Preprocessing: Valid format & size
    Validating --> Rejected: Blurry / invalid format
    
    Preprocessing --> Inferring: Image optimized
    
    Inferring --> ContextFetching: Predictions ready
    Inferring --> Error: Model unavailable
    
    ContextFetching --> Reasoning: GPS data obtained
    ContextFetching --> BuildingReport: No GPS / keys
    
    Reasoning --> BuildingReport: AI analysis complete
    
    BuildingReport --> Saving: Report assembled
    
    Saving --> Notifying: High risk detected
    Saving --> Complete: Low / moderate risk
    
    Notifying --> Complete: Notification sent
    
    Complete --> [*]: Return to user
    Error --> [*]: Return error message
    Rejected --> [*]: Return rejection reason
```
