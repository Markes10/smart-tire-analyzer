# API Key Rotation System

## Overview

The Smart Tire Analyzer now includes a robust **API Key Rotation System** that automatically manages multiple API keys across different services (Gemini, OpenWeatherMap, Google Maps, and Mapillary). This system:

- ✅ **Handles Rate Limits**: Automatically switches to the next available API key when a quota is exceeded
- ✅ **Tracks Usage**: Monitors daily request counts and quota consumption per key
- ✅ **Graceful Failover**: If a key fails, the system automatically tries the next available key
- ✅ **Request Monitoring**: Logs and tracks all API requests and errors
- ✅ **Status Reporting**: Provides real-time status of all API keys and their usage

## Supported APIs

### 1. **Gemini API** (AI Reasoning)
- **Default Quota**: 50 requests/day per key
- **Keys Provided**: 6 keys
- **Total Daily Capacity**: 300 requests/day

### 2. **OpenWeatherMap API** (Weather Context)
- **Default Quota**: 50 requests/day per key
- **Keys Provided**: 6 keys
- **Total Daily Capacity**: 300 requests/day

### 3. **Google Maps API** (Road & Location Context)
- **Default Quota**: 50 requests/day per key
- **Keys Provided**: 1 key (can be expanded)
- **Total Daily Capacity**: 50+ requests/day

### 4. **Mapillary API** (Street View Context)
- **Default Quota**: 50 requests/day per key
- **Keys Provided**: 1 key (can be expanded)
- **Total Daily Capacity**: 50+ requests/day

## Configuration

### Environment Variables

Set these in your `.env` file:

```bash
# Gemini API Keys (comma-separated)
GEMINI_API_KEYS=key1,key2,key3,key4,key5,key6

# OpenWeatherMap Keys (comma-separated)
OPENWEATHER_API_KEYS=key1,key2,key3,key4,key5,key6

# Google Maps Keys (comma-separated)
GOOGLE_MAPS_API_KEYS=key1,key2

# Mapillary Keys (comma-separated)
MAPILLARY_API_KEYS=key1,key2

# Custom Daily Quotas (optional)
GEMINI_DAILY_QUOTA=50
OPENWEATHER_DAILY_QUOTA=50
MAPS_DAILY_QUOTA=50
MAPILLARY_DAILY_QUOTA=50
```

### Docker Deployment

The keys are automatically passed to Docker through the `.env` file:

```bash
docker-compose up -d
```

Make sure your `.env` file contains all the API keys before deploying.

## How It Works

### Request Flow

```
User Request
    ↓
Inference Service
    ↓
Check which API is needed (Gemini, Weather, Maps, Mapillary)
    ↓
Get Current API Key Rotator
    ↓
Get Available Key with Quota
    ↓
Make API Request
    ↓
Success? → Record Success & Return Result
    ↓
Failure/Quota? → Try Next Key → Repeat
    ↓
All Keys Failed? → Return Error
```

### Key Selection Logic

1. **Primary Selection**: Use the current key if it has quota available
2. **Quota Check**: If current key is over quota, move to next active key
3. **Error Handling**: If a key fails, mark it and try the next one
4. **Fallback**: If all keys fail, log error and return failure

### Quota Tracking

- **Daily Reset**: Request counts reset at midnight (UTC)
- **Per-Key Tracking**: Each key's usage is tracked independently
- **Consecutive Errors**: Keys are temporarily deactivated after 3 consecutive errors
- **Error Recovery**: Keys can be reactivated after successful requests

## Monitoring API Key Status

### Health Endpoint

Check the status of all API keys:

```bash
curl http://localhost:8000/health/api-keys
```

Response Example:

```json
{
  "timestamp": 1715472000.123,
  "status": "ok",
  "api_keys": {
    "gemini": {
      "api_type": "gemini",
      "total_keys": 6,
      "active_keys": 6,
      "current_key": "AIzaSyAvLZ4...",
      "keys": {
        "AIzaSyAvLZ4...": {
          "key_preview": "AIzaSyAvLZ4...",
          "api_type": "gemini",
          "requests_today": 25,
          "daily_quota": 50,
          "remaining": 25,
          "is_active": true,
          "is_quota_exceeded": false,
          "error_count": 0,
          "consecutive_errors": 0,
          "last_used": "2025-05-12T10:30:00"
        }
      }
    },
    "weather": {...},
    "maps": {...},
    "mapillary": {...}
  }
}
```

### Logging

The system logs all activities:

```
2025-05-12 10:30:00 | INFO | smart_tire_api | ✅ API key rotators initialized
2025-05-12 10:30:01 | INFO | [gemini] Status: 6/6 active keys
2025-05-12 10:30:01 | DEBUG | AIzaSyAvLZ4...: 0/50 (active)
```

## Adding More Keys

### To add more keys to an existing API:

1. **Update `.env`**:
   ```bash
   GEMINI_API_KEYS=key1,key2,key3,key4,key5,key6,key7,key8
   ```

2. **Restart the service**:
   ```bash
   docker-compose restart backend
   ```

The rotator will automatically detect and use the new keys.

### To adjust daily quotas:

```bash
# In .env file
GEMINI_DAILY_QUOTA=100  # Increase from 50 to 100
OPENWEATHER_DAILY_QUOTA=100
```

## Error Handling

### Common Scenarios

#### Scenario 1: One Key Hits Quota
- **Current Key**: 50/50 requests used
- **Action**: Rotator automatically switches to next key with available quota
- **User Impact**: No interruption, request continues with next key

#### Scenario 2: All Keys Hit Quota
- **Status**: All 6 Gemini keys used 50 requests each (300 total)
- **Action**: Uses key with most remaining quota (shows warning)
- **User Impact**: May see degraded performance or rate limits

#### Scenario 3: API Key Fails
- **Error**: 429 (Rate Limit) or 401 (Invalid Key)
- **Action**: Records error, tries next key if available
- **After 3 Errors**: Key is temporarily deactivated
- **Recovery**: Re-activated after first successful request

#### Scenario 4: No Valid Keys
- **Status**: All keys exhausted or failed
- **Action**: Falls back to rule-based system (no AI reasoning)
- **User Impact**: Basic tire analysis without AI enhancement

## Best Practices

### 1. **Key Distribution**
- Spread keys across different accounts if possible
- Avoid using the same account for all 6 keys (account-level limits)
- Monitor quota usage per account

### 2. **Quota Planning**
- 6 Gemini keys = 300 requests/day capacity
- Estimate ~1-2 requests per tire analysis
- Plan for 150-200 analyses/day safely

### 3. **Monitoring**
- Check `/health/api-keys` regularly
- Set up alerts if all keys are over quota
- Monitor error rates and patterns

### 4. **Maintenance**
- Update `.env` when adding new keys
- Test new keys before peak usage
- Keep backup keys ready for quick rotation

## Troubleshooting

### Issue: "No API keys configured"

**Solution**: Ensure `.env` file has the correct keys:
```bash
# Check .env file
cat .env | grep API_KEYS

# Verify keys are loaded
docker-compose logs backend | grep "API key rotators"
```

### Issue: All keys showing "INACTIVE"

**Solution**: Keys were deactivated due to errors. Check:
```bash
# Check the API keys endpoint
curl http://localhost:8000/health/api-keys | jq '.api_keys'

# Check logs for errors
docker-compose logs backend | grep "Error with key"
```

**Fix**: 
1. Verify API keys are correct
2. Check API service status (Gemini, OpenWeather, etc.)
3. Restart the service once fixed

### Issue: "Rate limit exceeded" errors

**Solution**: You've hit the daily quota for all keys
```bash
# Increase quota if supported by the API
# OR add more keys and restart
GEMINI_API_KEYS=key1,key2,key3,key4,key5,key6,key7,key8
docker-compose restart backend
```

### Issue: Requests are slow

**Possible Causes**:
1. Some keys are over quota (rotation adds latency)
2. Network issues with one key (retries slow things down)
3. API service is slow

**Solution**:
```bash
# Check status
curl http://localhost:8000/health/api-keys

# If many keys over quota, add more or increase quota
# If network issues, check Docker network
docker network ls
```

## Architecture

### Key Components

1. **APIKeyRotator** (`backend/app/services/api_key_rotator.py`)
   - Manages key rotation logic
   - Tracks usage per key
   - Handles error counts and deactivation
   - Provides status reporting

2. **API Clients** (Updated)
   - `api_integrations/gemini/gemini_client.py`
   - `api_integrations/weather/weather_client.py`
   - `api_integrations/google_maps/maps_client.py`
   - Now support rotation via `rotator` parameter

3. **Config** (`backend/app/config.py`)
   - Loads keys from `.env` file
   - Parses comma-separated key lists
   - Provides quota configuration

4. **Main App** (`backend/app/main.py`)
   - Initializes rotators on startup
   - Injects rotators into API clients
   - Logs status on startup

## Performance Impact

- **Minimal Overhead**: Rotation adds <5ms per request (key lookup only)
- **Error Retry**: Failed request adds ~1 second (timeout + retry)
- **Throughput**: Can handle 300+ requests/day with 6 keys

## Security Notes

- ⚠️ **Never commit `.env` to version control** (already in `.gitignore`)
- ⚠️ **API keys are sensitive** — keep them in environment variables
- ⚠️ **Logs may show partial key names** — full keys never logged for security
- ✅ **Docker secrets** can be used for production deployments

## API Reference

### Rotation Manager Methods

```python
from backend.app.services.api_key_rotator import get_gemini_rotator

rotator = get_gemini_rotator()

# Get current key with available quota
current_key = rotator.get_current_key()

# Get all active keys
active_keys = rotator.active_keys

# Get keys with available quota
available_keys = rotator.available_quota_keys

# Record successful request
rotator.record_successful_request(key)

# Record an error
rotator.record_error(key, error_message)

# Get full status
status = rotator.get_status()

# Reset all keys (for testing)
rotator.reset_all_keys()
```

## Next Steps

1. ✅ Set up `.env` with all API keys
2. ✅ Start the backend: `docker-compose up -d`
3. ✅ Check status: `curl http://localhost:8000/health/api-keys`
4. ✅ Monitor via logs: `docker-compose logs -f backend`
5. ✅ Set up alerts if needed

## Support

For issues or questions:
1. Check logs: `docker-compose logs backend`
2. Check status endpoint: `/health/api-keys`
3. Review configuration: `.env` file
4. See troubleshooting section above
