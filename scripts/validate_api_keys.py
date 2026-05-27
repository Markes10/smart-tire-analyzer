# scripts/validate_api_keys.py
"""
Utility script to validate essential API keys for the Smart Tire Analyzer project.
It loads environment variables from `.env`, checks that required keys are present,
and performs lightweight test calls to each service to ensure the keys are functional.

Running this script will print a status report for each key.
"""

import os
import sys
import json
from urllib.parse import quote_plus

try:
    from dotenv import load_dotenv
except ImportError:
    print("python-dotenv is not installed. Installing now...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "python-dotenv"])
    from dotenv import load_dotenv

import requests

# Load .env file
load_dotenv()

# Helper to print results
def report(name, ok, message=""):
    status = "✅" if ok else "❌"
    print(f"{status} {name}: {message}")

# 1. Gemini API key validation
GEMINI_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_KEY:
    report("Gemini API Key", False, "Missing GEMINI_API_KEY in .env")
else:
    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models?key={GEMINI_KEY}"
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            report("Gemini API Key", True, "Valid and reachable")
        else:
            report("Gemini API Key", False, f"HTTP {resp.status_code}: {resp.text[:100]}")
    except Exception as e:
        report("Gemini API Key", False, str(e))

# 2. Google Maps API key validation
GMAPS_KEY = os.getenv("GOOGLE_MAPS_API_KEY")
if not GMAPS_KEY or "your_google_maps_api_key_here" in GMAPS_KEY:
    report("Google Maps API Key", False, "Missing or placeholder value")
else:
    try:
        address = quote_plus("New York")
        url = f"https://maps.googleapis.com/maps/api/geocode/json?address={address}&key={GMAPS_KEY}"
        resp = requests.get(url, timeout=10)
        data = resp.json()
        if resp.status_code == 200 and data.get("status") == "OK":
            report("Google Maps API Key", True, "Valid and returned results")
        else:
            report("Google Maps API Key", False, f"HTTP {resp.status_code}, status={data.get('status')}")
    except Exception as e:
        report("Google Maps API Key", False, str(e))

# 3. OpenWeatherMap API key validation
OW_KEY = os.getenv("OPENWEATHER_API_KEY")
if not OW_KEY or "your_openweather_api_key_here" in OW_KEY:
    report("OpenWeather API Key", False, "Missing or placeholder value")
else:
    try:
        city = quote_plus("London")
        url = f"https://api.openweathermap.org/data/2.5/weather?q={city}&appid={OW_KEY}"
        resp = requests.get(url, timeout=10)
        data = resp.json()
        if resp.status_code == 200 and data.get("cod") == 200:
            report("OpenWeather API Key", True, "Valid and returned weather data")
        else:
            report("OpenWeather API Key", False, f"HTTP {resp.status_code}, msg={data.get('message')}")
    except Exception as e:
        report("OpenWeather API Key", False, str(e))

print("\nValidation complete.")
