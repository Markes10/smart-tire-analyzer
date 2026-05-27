#!/usr/bin/env python3
"""
API Key Manager — Command-line tool for managing API key rotation.

Usage:
    python scripts/manage_api_keys.py status           # Show status of all keys
    python scripts/manage_api_keys.py reset gemini     # Reset Gemini keys
    python scripts/manage_api_keys.py check            # Run diagnostics
"""

import os
import sys
import json
import argparse
from pathlib import Path
from typing import Dict, List

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Configure Django for testing
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./smart_tire.db")

# Load .env file
from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

# Import rotator functions
from backend.app.services.api_key_rotator import (
    APIKeyRotator,
    get_gemini_rotator,
    get_weather_rotator,
    get_maps_rotator,
    get_mapillary_rotator,
    initialize_rotators,
)
from backend.app.config import settings


def format_status(status: Dict) -> str:
    """Format API key status for display."""
    lines = []
    lines.append(f"\n🔑 {status['api_type'].upper()} API")
    lines.append(f"   Total Keys: {status['total_keys']} | Active: {status['active_keys']}")
    lines.append(f"   Current Key: {status['current_key'][:16]}..." if status['current_key'] else "   Current Key: NONE")
    lines.append("")
    
    for key_preview, key_status in status['keys'].items():
        status_icon = "✅" if key_status['is_active'] else "❌"
        quota_icon = "⚠️" if key_status['is_quota_exceeded'] else "✓"
        error_indicator = f" ⚡({key_status['consecutive_errors']})" if key_status['consecutive_errors'] > 0 else ""
        
        lines.append(
            f"   {status_icon} {quota_icon} {key_preview} — "
            f"{key_status['requests_today']}/{key_status['daily_quota']} "
            f"({key_status['remaining']} remaining){error_indicator}"
        )
    
    return "\n".join(lines)


def show_status(rotator_name: str = None):
    """Show status of API keys."""
    print("📊 API Key Rotation Status")
    print("=" * 60)
    
    rotators = {
        "gemini": get_gemini_rotator(),
        "weather": get_weather_rotator(),
        "maps": get_maps_rotator(),
        "mapillary": get_mapillary_rotator(),
    }
    
    if rotator_name and rotator_name.lower() in rotators:
        rotators = {rotator_name.lower(): rotators[rotator_name.lower()]}
    
    for name, rotator in rotators.items():
        if rotator:
            status = rotator.get_status()
            print(format_status(status))
        else:
            print(f"\n❌ {name.upper()} rotator not initialized")
    
    print("\n" + "=" * 60)


def reset_keys(rotator_name: str):
    """Reset usage counters for specified API."""
    rotators = {
        "gemini": get_gemini_rotator(),
        "weather": get_weather_rotator(),
        "maps": get_maps_rotator(),
        "mapillary": get_mapillary_rotator(),
    }
    
    if rotator_name.lower() not in rotators:
        print(f"❌ Unknown API: {rotator_name}")
        print(f"   Available: {', '.join(rotators.keys())}")
        return False
    
    rotator = rotators[rotator_name.lower()]
    if rotator:
        rotator.reset_all_keys()
        print(f"✅ Reset all {rotator_name.upper()} API keys")
        show_status(rotator_name)
        return True
    else:
        print(f"❌ {rotator_name.upper()} rotator not initialized")
        return False


def run_diagnostics():
    """Run diagnostics on API keys."""
    print("🔍 Running API Key Diagnostics")
    print("=" * 60)
    
    # Check .env file
    env_file = PROJECT_ROOT / ".env"
    print(f"\n📝 Environment File: {env_file}")
    if env_file.exists():
        print(f"   ✅ .env file found ({env_file.stat().st_size} bytes)")
    else:
        print(f"   ❌ .env file not found — copy from .env.example")
        return False
    
    # Check configuration
    print(f"\n⚙️ Configuration Loaded:")
    gemini_keys = settings.get_gemini_keys()
    weather_keys = settings.get_weather_keys()
    maps_keys = settings.get_maps_keys()
    mapillary_keys = settings.get_mapillary_keys()
    
    print(f"   Gemini Keys: {len(gemini_keys)} configured")
    if len(gemini_keys) == 0:
        print(f"      ⚠️ No Gemini keys found in GEMINI_API_KEYS")
    
    print(f"   Weather Keys: {len(weather_keys)} configured")
    if len(weather_keys) == 0:
        print(f"      ⚠️ No Weather keys found in OPENWEATHER_API_KEYS")
    
    print(f"   Maps Keys: {len(maps_keys)} configured")
    if len(maps_keys) == 0:
        print(f"      ⚠️ No Maps keys found in GOOGLE_MAPS_API_KEYS")
    
    print(f"   Mapillary Keys: {len(mapillary_keys)} configured")
    if len(mapillary_keys) == 0:
        print(f"      ⚠️ No Mapillary keys found in MAPILLARY_API_KEYS")
    
    # Initialize rotators
    print(f"\n🔄 Initializing Rotators...")
    try:
        initialize_rotators(
            gemini_keys=gemini_keys,
            weather_keys=weather_keys,
            maps_keys=maps_keys,
            mapillary_keys=mapillary_keys,
        )
        print(f"   ✅ Rotators initialized successfully")
    except Exception as e:
        print(f"   ❌ Error initializing rotators: {e}")
        return False
    
    # Show status
    print(f"\n📊 Current Status:")
    show_status()
    
    # Summary
    print(f"\n✅ Diagnostics complete!")
    all_keys = len(gemini_keys) + len(weather_keys) + len(maps_keys) + len(mapillary_keys)
    print(f"   Total API Keys: {all_keys}")
    print(f"   Total Daily Capacity: {all_keys * 50} requests (at 50/key)")
    
    return True


def export_status(output_file: str = "api_keys_status.json"):
    """Export API key status to JSON file."""
    print(f"💾 Exporting API Key Status to {output_file}...")
    
    rotators = {
        "gemini": get_gemini_rotator(),
        "weather": get_weather_rotator(),
        "maps": get_maps_rotator(),
        "mapillary": get_mapillary_rotator(),
    }
    
    status = {}
    for name, rotator in rotators.items():
        if rotator:
            status[name] = rotator.get_status()
        else:
            status[name] = {"status": "not_initialized"}
    
    try:
        with open(output_file, "w") as f:
            json.dump(status, f, indent=2, default=str)
        print(f"✅ Status exported to {output_file}")
        return True
    except Exception as e:
        print(f"❌ Error exporting status: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="API Key Manager — Manage API key rotation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/manage_api_keys.py status              # Show all API keys status
  python scripts/manage_api_keys.py status gemini       # Show Gemini keys only
  python scripts/manage_api_keys.py reset weather       # Reset Weather API keys
  python scripts/manage_api_keys.py check               # Run diagnostics
  python scripts/manage_api_keys.py export              # Export status to JSON
        """
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    # Status command
    status_parser = subparsers.add_parser("status", help="Show API key status")
    status_parser.add_argument(
        "api",
        nargs="?",
        choices=["gemini", "weather", "maps", "mapillary"],
        help="Specific API to check (optional)"
    )
    
    # Reset command
    reset_parser = subparsers.add_parser("reset", help="Reset API key usage")
    reset_parser.add_argument(
        "api",
        choices=["gemini", "weather", "maps", "mapillary"],
        help="API to reset"
    )
    
    # Check/diagnostics command
    subparsers.add_parser("check", help="Run diagnostics on API keys")
    
    # Export command
    export_parser = subparsers.add_parser("export", help="Export status to JSON")
    export_parser.add_argument(
        "--output",
        "-o",
        default="api_keys_status.json",
        help="Output file (default: api_keys_status.json)"
    )
    
    args = parser.parse_args()
    
    if args.command == "status":
        initialize_rotators(
            gemini_keys=settings.get_gemini_keys(),
            weather_keys=settings.get_weather_keys(),
            maps_keys=settings.get_maps_keys(),
            mapillary_keys=settings.get_mapillary_keys(),
        )
        show_status(args.api)
    
    elif args.command == "reset":
        initialize_rotators(
            gemini_keys=settings.get_gemini_keys(),
            weather_keys=settings.get_weather_keys(),
            maps_keys=settings.get_maps_keys(),
            mapillary_keys=settings.get_mapillary_keys(),
        )
        reset_keys(args.api)
    
    elif args.command == "check":
        run_diagnostics()
    
    elif args.command == "export":
        initialize_rotators(
            gemini_keys=settings.get_gemini_keys(),
            weather_keys=settings.get_weather_keys(),
            maps_keys=settings.get_maps_keys(),
            mapillary_keys=settings.get_mapillary_keys(),
        )
        export_status(args.output)
    
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
