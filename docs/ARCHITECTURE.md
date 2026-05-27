# API Key Rotation System — Architecture & Design

## System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Backend API Server                        │
│                   (FastAPI + Uvicorn)                        │
└─────────────────────────────────────────────────────────────┘
                           ↓
        ┌──────────────────┼──────────────────┐
        ↓                  ↓                   ↓
   ┌─────────┐        ┌─────────┐        ┌──────────┐
   │ Rotator │        │ Rotator │        │ Rotator  │
   │ Manager │        │ Manager │        │ Manager  │
   │(Gemini) │        │(Weather)│        │ (Maps)   │
   └────┬────┘        └────┬────┘        └────┬─────┘
        │                  │                   │
   ┌────┴────────────────────────────────────┘
   ↓
┌──────────────────────────────────────────┐
│     API Key Rotator (Core Engine)        │
│  backend/app/services/api_key_rotator.py │
│                                          │
│  • Track usage per key                   │
│  • Manage daily quotas                   │
│  • Handle errors & deactivation          │
│  • Rotate to next available key          │
└──────────────────────────────────────────┘
        ↓
   ┌────┴────────────────────────┐
   ↓                             ↓
┌──────────────────┐    ┌─────────────────────┐
│  Usage Tracking  │    │  Key Selection      │
│                  │    │                     │
│ • Requests/day   │    │ 1. Check quota      │
│ • Error counts   │    │ 2. Get current key  │
│ • Last used      │    │ 3. Try next on fail │
└──────────────────┘    └─────────────────────┘
```

## Request Flow

```
User Tire Analysis Request
    ↓
    ├─ Preprocess Image
    │
    └─ Inference Service
        ├─ CNN (Feature extraction)
        ├─ ViT (Vision transformer)
        └─ Needs AI reasoning? → Yes
            ↓
            ├─ Get Gemini Rotator
            │   ↓
            │   ├─ Check if Gemini keys available
            │   ├─ Get current key
            │   │   ├─ Has quota? → Use it
            │   │   └─ No quota? → Get next key
            │   └─ Make API request
            │       ├─ Success? → Record usage → Return
            │       └─ Failure? → Try next key (up to N keys)
            │
            ├─ Get Weather Rotator
            │   ├─ Check weather at tire location
            │   └─ (same rotation logic)
            │
            └─ Get Maps Rotator
                ├─ Check terrain/road type
                └─ (same rotation logic)
    ↓
    └─ Return analysis with all context
```

## Component Interaction

```
┌──────────────┐
│  .env File   │
│              │
│ GEMINI_API_KEYS=
│   key1,key2,key3
│ WEATHER_API_KEYS=
│   ...
└──────┬───────┘
       ↓
┌──────────────────────┐
│  Settings (Config)   │
│                      │
│ get_gemini_keys()    │
│ get_weather_keys()   │
│ get_maps_keys()      │
└──────┬───────────────┘
       ↓
┌──────────────────────────────────┐
│  Main App (Startup/Lifespan)     │
│                                  │
│ initialize_rotators()            │
│   ├─ Create Gemini rotator       │
│   ├─ Create Weather rotator      │
│   ├─ Create Maps rotator         │
│   └─ Create Mapillary rotator    │
└──────┬───────────────────────────┘
       ↓
┌──────────────────────────────────┐
│  Update API Clients              │
│                                  │
│ get_gemini_client(rotator)       │
│ get_weather_client(rotator)      │
│ get_maps_client(rotator)         │
└──────┬───────────────────────────┘
       ↓
┌──────────────────────────────────┐
│  Inference Service               │
│  Ready to serve requests with    │
│  automatic key rotation          │
└──────────────────────────────────┘
```

## Key Rotation Logic

```
Request for API call
    ↓
    ├─ Get rotator for API type
    │   ↓
    │   ├─ Get available keys (active & has quota)
    │   ├─ Get current key
    │   │   ↓
    │   │   └─ Try request with key
    │   │       ├─ Success?
    │   │       │   ├─ Record success
    │   │       │   └─ Return result
    │   │       │
    │   │       └─ Failure?
    │   │           ├─ Record error
    │   │           ├─ Consecutive errors >= 3?
    │   │           │   ├─ Yes: Deactivate key
    │   │           │   └─ No: Continue
    │   │           └─ More keys available?
    │   │               ├─ Yes: Rotate & retry
    │   │               └─ No: Return error
    │   │
    │   └─ All keys exhausted?
    │       ├─ Use key with most remaining quota
    │       └─ Warn in logs
    │
    └─ Return result or error
```

## Usage Tracking

```
                Daily Reset (Midnight UTC)
                         ↓
    Start of Day: 0/50 requests
         ↓
    Request #1 → Increment to 1/50
         ↓
    Request #2 → Increment to 2/50
         ↓
         ...
         ↓
    Request #50 → Increment to 50/50 (Quota Reached!)
         ↓
    Request #51 → Can't use this key, switch to next
         ↓
    Next key: 0/50 requests available
         ↓
    Continue...
         ↓
    All keys hit 50/50 (300 total used)
         ↓
    Next day: Automatic reset to 0/50 per key
```

## Error Handling Strategy

```
Make Request with Key
    ↓
    ├─ 429 (Rate Limited)
    │   └─ Record error, mark quota exceeded
    │
    ├─ 401 (Invalid Key)
    │   └─ Record error, increment consecutive errors
    │
    ├─ 500 (Server Error)
    │   └─ Record error, retry with next key
    │
    ├─ Timeout
    │   └─ Record error, retry with next key
    │
    └─ Connection Error
        └─ Record error, retry with next key

After 3 Consecutive Errors
    ↓
    Deactivate key (is_active = False)
    ↓
    Use remaining active keys
    ↓
    On first success
    ↓
    Reactivate key (reset error counter)
```

## Status Monitoring

```
┌─────────────────────────────────────┐
│   Health Endpoint (/health/api-keys)│
└──────────────┬──────────────────────┘
               ↓
     ┌────────────────────────┐
     │  Collect Status from   │
     │  All Rotators          │
     └────────────┬───────────┘
                  ↓
        ┌─────────────────────────────┐
        │  For Each API:              │
        │  • Total keys               │
        │  • Active keys              │
        │  • Current key              │
        │  • Usage breakdown          │
        │  • Error counts             │
        └────────────┬────────────────┘
                     ↓
         ┌──────────────────────┐
         │  Return JSON Status  │
         │  • Overall status    │
         │  • Warnings if needed│
         │  • Timestamp         │
         └──────────────────────┘
```

## Deployment

```
┌─────────────┐
│   .env      │ (Local development & Docker)
└──────┬──────┘
       ├─ Loaded by config.py
       ├─ Passed to Docker via compose
       └─ Loaded on app startup
           ↓
       ┌─────────────────────┐
       │  Development        │
       │  (python -m uvicorn)│
       └─────────────────────┘
           OR
       ┌─────────────────────┐
       │  Docker             │
       │  (docker-compose)   │
       │  • Container reads  │
       │  • Env variables    │
       │  • Rotators init    │
       └─────────────────────┘
```

## File Structure

```
smart-tire-analyzer/
├── backend/
│   └── app/
│       ├── main.py                    ← Initialize rotators
│       ├── config.py                  ← Load API key config
│       ├── routes/
│       │   └── health.py              ← /health/api-keys endpoint
│       └── services/
│           └── api_key_rotator.py     ← Core rotation engine
│
├── api_integrations/
│   ├── gemini/
│   │   └── gemini_client.py           ← Updated with rotation
│   ├── weather/
│   │   └── weather_client.py          ← Updated with rotation
│   └── google_maps/
│       └── maps_client.py             ← Updated with rotation
│
├── scripts/
│   └── manage_api_keys.py             ← CLI management tool
│
├── deployment/
│   └── docker/
│       └── docker-compose.yml         ← Updated with multi-key support
│
├── docs/
│   └── API_KEY_ROTATION.md            ← Full documentation
│
├── .env.example                       ← Template with all keys
├── .env                               ← (You create this)
├── IMPLEMENTATION_SUMMARY.md          ← What was done
└── QUICK_START.md                     ← 5-minute setup
```

## Data Flow Example

```
User uploads tire photo
        ↓
Backend receives request
        ↓
Inference Service processes image
        ↓
Needs Gemini reasoning? → YES
        ↓
Get Gemini Rotator:
  • Total keys: 6
  • Active keys: 5 (one deactivated)
  • Current key: Key #1
        ↓
Check Key #1:
  • Requests today: 48/50
  • Quota remaining: 2
  • Status: ACTIVE
        ↓
Make request with Key #1
        ↓
SUCCESS ✓
  • Record: requests_today = 49
  • Return: AI analysis
        ↓
Next request (49th to Key #1):
  • Requests today: 48/50
  • Quota remaining: 2
  • Make request with Key #1
  • SUCCESS
  • Record: requests_today = 50
        ↓
Next request (51st - OVER QUOTA):
  • Requests today: 50/50
  • Status: QUOTA_EXCEEDED
  • Rotate to Key #2
  • Check Key #2: 5/50 (fresh key)
  • Make request with Key #2
  • SUCCESS
  • Continue seamlessly...
```

## Performance Characteristics

```
Request Processing Time:

1. Key lookup & quota check:     < 1ms
2. Successful API call:           100-2000ms (API dependent)
3. Failed API call + retry:       1000-5000ms
4. Rotation overhead:             < 5ms

Total with rotation:
  • Success case:       ~100-2000ms (rotation adds < 1%)
  • Retry case:         ~1000-5000ms (includes timeout)
  • Worst case (retry): ~5000-10000ms (all keys fail)
```

## Scalability

```
Current Configuration:
├─ Gemini:   6 keys × 50 req/day = 300 req/day
├─ Weather:  6 keys × 50 req/day = 300 req/day
├─ Maps:     1 key × 50 req/day   = 50 req/day
└─ Mapillary:1 key × 50 req/day   = 50 req/day
   Total: 700 requests/day capacity

To Scale Up:
├─ Add more keys: GEMINI_API_KEYS=key1,key2,...,key10
├─ Increase quota: GEMINI_DAILY_QUOTA=100
└─ Combine both for 10 keys × 100 req = 1000 req/day

Estimated Tire Analyses:
└─ Each analysis ≈ 2 API calls average
└─ 700 requests ÷ 2 = ~350 analyses/day potential
```

## Security Architecture

```
API Keys in `.env`:
    ↓
Loaded into os.environ (memory only)
    ↓
NOT logged (only previews shown)
    ↓
Passed to API clients via rotator
    ↓
Never stored in database
    ↓
Never exposed in logs
    ↓
Docker passes via environment
    ↓
CI/CD can use secrets

Result:
✅ Keys kept secure
✅ No accidental exposure
✅ Production-grade security
```

## Extensibility

```
Add Support for New API:

1. Add new rotator function:
   └─ get_new_api_rotator() → APIKeyRotator

2. Update config.py:
   └─ NEW_API_KEYS_RAW = os.getenv("NEW_API_KEYS", "")
   └─ def get_new_api_keys(cls):

3. Update main.py:
   └─ initialize_rotators(..., new_api_keys)

4. Update API client:
   └─ Add rotator parameter
   └─ Implement retry logic

5. Update health endpoint:
   └─ Add new_api to status check

Done! New API now has automatic rotation!
```

## Maintenance Tasks

```
Daily:
└─ Monitor /health/api-keys endpoint

Weekly:
├─ Review error logs
├─ Check usage patterns
└─ Verify all keys active

Monthly:
├─ Analyze usage trends
├─ Plan quota adjustments
├─ Add keys if needed
└─ Review error patterns

Quarterly:
├─ Audit all configured keys
├─ Update documentation
├─ Test disaster recovery
└─ Plan capacity growth
```

---

This architecture provides:
✅ **Automatic rotation** with zero manual intervention
✅ **Transparent failover** invisible to users
✅ **Real-time monitoring** via health endpoints
✅ **Production reliability** with error handling
✅ **Easy scalability** by adding more keys
✅ **Backward compatibility** with existing code
