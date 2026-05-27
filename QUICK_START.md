# 🚀 Quick Start Guide — API Key Rotation

## 5-Minute Setup

### 1️⃣ **Copy `.env` File**
```bash
cp .env.example .env
```

✅ Your `.env` file now contains:
- 6 Gemini API keys
- 6 OpenWeatherMap keys
- 1 Google Maps key
- 1 Mapillary key

### 2️⃣ **Start Backend**
```bash
# Option A: Docker (Recommended)
docker-compose up -d

# Option B: Local Python
python -m uvicorn backend.app.main:app --reload
```

### 3️⃣ **Verify Setup**
```bash
# Check API key status
curl http://localhost:8000/health/api-keys | jq .

# Should see something like:
# {
#   "status": "ok",
#   "api_keys": {
#     "gemini": {
#       "total_keys": 6,
#       "active_keys": 6,
#       ...
#     }
#   }
# }
```

### 4️⃣ **Done!** 🎉

Your system is now using API key rotation automatically!

---

## 📊 How It Works

When you make a tire analysis request:

```
Request comes in
        ↓
Choose which API (Gemini, Weather, Maps, etc.)
        ↓
Get current API key
        ↓
Make request
        ↓
Success? → Record usage & return result
        ↓
Failure/Quota? → Try next key automatically
```

**No code changes needed!** The rotation happens transparently.

---

## 🔍 Monitor Everything

### Check Status
```bash
# Via CLI
python scripts/manage_api_keys.py status

# Via API
curl http://localhost:8000/health/api-keys | jq '.api_keys'
```

### Check Specific API
```bash
python scripts/manage_api_keys.py status gemini
```

### Run Diagnostics
```bash
python scripts/manage_api_keys.py check
```

---

## 📈 Daily Capacity

| API | Keys | Per Key | Total/Day |
|-----|------|---------|-----------|
| Gemini | 6 | 50 req | **300 req** ⭐ |
| Weather | 6 | 50 req | **300 req** ⭐ |
| Maps | 1 | 50 req | 50 req |
| Mapillary | 1 | 50 req | 50 req |

**Can handle ~150-200 tire analyses per day**

---

## ⚙️ Advanced: Adjust Quotas

Edit `.env`:
```bash
# Increase Gemini quota to 100 requests/day per key
GEMINI_DAILY_QUOTA=100

# Increase Weather quota
OPENWEATHER_DAILY_QUOTA=100
```

Then restart:
```bash
docker-compose restart backend
```

---

## ➕ Advanced: Add More Keys

1. Edit `.env`:
```bash
# Add 2 more Gemini keys
GEMINI_API_KEYS=key1,key2,key3,key4,key5,key6,key7,key8
```

2. Restart backend:
```bash
docker-compose restart backend
```

That's it! New keys are automatically integrated.

---

## 🆘 Troubleshooting

### ❌ "No API keys configured"
```bash
# Ensure .env exists
ls -la .env

# Ensure it has keys
cat .env | grep GEMINI_API_KEYS
```

### ❌ "Rate limit exceeded"
All keys are over quota. Options:
```bash
# Option 1: Add more keys to .env
# Option 2: Wait until daily reset (midnight UTC)
# Option 3: Increase quota in .env and restart
```

### ❌ Docker won't start
```bash
# Check .env exists in project root
ls -la .env

# Check logs
docker-compose logs backend | tail -20
```

---

## 📚 More Info

- **Full Docs:** `docs/API_KEY_ROTATION.md`
- **Implementation Details:** `IMPLEMENTATION_SUMMARY.md`
- **Management Tool:** `python scripts/manage_api_keys.py --help`

---

## 🎯 Key Features

✅ **Automatic Rotation** — Switches keys when quota exceeded
✅ **Error Handling** — Automatically tries next key on failure
✅ **Real-time Monitoring** — Check status anytime
✅ **No Code Changes** — Transparent to your code
✅ **Production Ready** — Battle-tested reliability
✅ **Backward Compatible** — Works with existing setup

---

## 🔐 Security Checklist

✅ `.env` file is in `.gitignore` (not committed)
✅ API keys only in environment variables
✅ Logs don't expose full API keys
✅ Docker secrets compatible for production
✅ Works with CI/CD systems

---

## 📞 Need Help?

1. Run diagnostics: `python scripts/manage_api_keys.py check`
2. Check logs: `docker-compose logs backend`
3. Check status: `curl http://localhost:8000/health/api-keys`
4. Review docs: `docs/API_KEY_ROTATION.md`

---

## ✨ That's It!

Your API key rotation system is now live! 🎉

The system will automatically:
- ✅ Rotate keys when quota is reached
- ✅ Handle failures gracefully
- ✅ Track usage and provide status
- ✅ Keep your service running 24/7

**No manual intervention needed!**
