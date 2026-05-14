"""
Gemini API Client — Direct API wrapper for gemini-2.0-flash (vision + text).
Supports:
  - Text-only prompts  (generate / generate_json)
  - Multimodal prompts (generate_with_image) for sidewall vision analysis
  - API key rotation for handling quota limits and fallback
Separates transport logic from prompt construction.
"""

import base64
import os
import json
import logging
import asyncio
import aiohttp
from typing import Dict, Optional, Any, cast

logger = logging.getLogger(__name__)

GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/models"
DEFAULT_MODEL = "gemini-2.0-flash"
VISION_MODEL = "gemini-2.0-flash"   # same model supports vision


class GeminiClient:
    """
    Low-level Gemini API client with API key rotation support.
    Handles authentication, request formatting, response parsing, and key rotation.
    """

    def __init__(self, api_key: Optional[str] = None, model: str = DEFAULT_MODEL, rotator=None):
        """
        Initialize Gemini client.
        
        Args:
            api_key: Single API key (for backward compatibility)
            model: Model name to use
            rotator: APIKeyRotator instance for multi-key rotation
        """
        self.api_key = api_key or os.getenv("GEMINI_API_KEY", "")
        self.model = model
        self.url = f"{GEMINI_BASE_URL}/{model}:generateContent"
        self.rotator = rotator
        self.enabled = bool(self.api_key or (rotator and rotator.available_keys))

    async def generate(
        self,
        prompt: str,
        temperature: float = 0.2,
        max_tokens: int = 512,
        response_mime_type: str = "application/json",
        timeout: int = 10,
    ) -> Optional[str]:
        """
        Send a text prompt to Gemini and return the response text.
        Automatically rotates to next API key on failure or quota exceeded.

        Args:
            prompt: Text prompt to send
            temperature: Generation temperature (0.0–1.0)
            max_tokens: Maximum output tokens
            response_mime_type: Force JSON response ("application/json")
            timeout: Request timeout in seconds

        Returns:
            Response text string, or None if failed
        """
        if not self.enabled:
            logger.warning("Gemini API key not configured")
            return None

        # Try with rotation if available, otherwise use single key
        if self.rotator:
            return await self._generate_with_rotation(
                prompt, temperature, max_tokens, response_mime_type, timeout
            )
        else:
            return await self._generate_single_key(
                prompt, temperature, max_tokens, response_mime_type, timeout, self.api_key
            )

    async def _generate_with_rotation(
        self,
        prompt: str,
        temperature: float,
        max_tokens: int,
        response_mime_type: str,
        timeout: int,
    ) -> Optional[str]:
        """Try with key rotation."""
        available_keys = self.rotator.available_quota_keys
        if not available_keys:
            logger.error("No Gemini API keys with available quota")
            return None

        # Try each available key
        for attempt, key in enumerate(available_keys):
            result = await self._generate_single_key(
                prompt, temperature, max_tokens, response_mime_type, timeout, key
            )
            if result is not None:
                self.rotator.record_successful_request(key)
                return result
            else:
                self.rotator.record_error(key, "Request failed")
                if attempt < len(available_keys) - 1:
                    logger.warning(f"Retrying with next Gemini API key...")
                    self.rotator.rotate_to_next_key()

        logger.error("All available Gemini API keys failed")
        return None

    async def _generate_single_key(
        self,
        prompt: str,
        temperature: float,
        max_tokens: int,
        response_mime_type: str,
        timeout: int,
        api_key: Optional[str],
    ) -> Optional[str]:
        """Make a single request with given API key."""
        if not api_key:
            logger.error("No API key provided to Gemini client")
            return None
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens,
                "responseMimeType": response_mime_type,
            },
        }
        headers = {"Content-Type": "application/json"}
        url = f"{self.url}?key={api_key}"

        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=timeout)) as session:
                async with session.post(url, json=payload, headers=headers) as resp:
                    resp.raise_for_status()
                    data = cast(Dict[str, Any], await resp.json())
                    # resp.json() is untyped (Any); cast to a dict for static checks
                    candidates: list[Any] = data.get("candidates", []) or []

                    if candidates:
                        try:
                            text_val = candidates[0]["content"]["parts"][0]["text"]
                        except Exception:
                            text_val = None

                        if isinstance(text_val, str):
                            return text_val
                        if text_val is not None:
                            return str(text_val)
                    return None
        except aiohttp.ClientResponseError as e:
            if e.status == 429:
                logger.warning(f"Gemini quota exceeded (429): {e.message}")
            else:
                logger.error(f"Gemini HTTP error {e.status}: {e.message}")
            return None
        except asyncio.TimeoutError:
            logger.warning(f"Gemini request timed out after {timeout}s")
            return None
        except Exception as e:
            logger.error(f"Gemini request failed: {e}")
            return None

    async def generate_json(
        self,
        prompt: str,
        temperature: float = 0.2,
        max_tokens: int = 512,
        timeout: int = 10,
    ) -> Optional[Dict[str, Any]]:
        """
        Generate and parse a JSON response from Gemini.

        Returns:
            Parsed dict, or None if failed / invalid JSON
        """
        text = await self.generate(
            prompt, temperature=temperature,
            max_tokens=max_tokens,
            response_mime_type="application/json",
            timeout=timeout,
        )
        if text is None:
            return None
        try:
            parsed = json.loads(text)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            pass

        # Try to extract JSON block from response text
        import re
        match = re.search(r"\{.*?\}", text, re.DOTALL)
        if match:
            try:
                parsed = json.loads(match.group())
                if isinstance(parsed, dict):
                    return parsed
            except json.JSONDecodeError:
                pass

        logger.error(f"Failed to parse Gemini JSON response: {text[:200]}")
        return None

    async def generate_with_image(
        self,
        prompt: str,
        image_bytes: bytes,
        mime_type: str = "image/jpeg",
        temperature: float = 0.1,
        max_tokens: int = 1024,
        timeout: int = 20,
    ) -> Optional[Dict]:
        """
        Send an image + text prompt to Gemini Vision and return parsed JSON.
        Automatically rotates to next API key on failure or quota exceeded.

        Used for sidewall text extraction — no OCR library required.
        Gemini reads the embossed text directly from the sidewall photograph.

        Args:
            prompt:       Text instructions sent alongside the image.
            image_bytes:  Raw image bytes (JPEG / PNG).
            mime_type:    MIME type of the image (default: 'image/jpeg').
            temperature:  Low value (0.1) keeps extraction deterministic.
            max_tokens:   Max output tokens (1024 covers full JSON response).
            timeout:      Request timeout in seconds.

        Returns:
            Parsed dict with sidewall details, or None if the call failed.
        """
        if not self.enabled:
            logger.warning("Gemini API key not configured — sidewall analysis unavailable")
            return None

        # Try with rotation if available, otherwise use single key
        if self.rotator:
            return await self._generate_with_image_rotation(
                prompt, image_bytes, mime_type, temperature, max_tokens, timeout
            )
        else:
            return await self._generate_with_image_single_key(
                prompt, image_bytes, mime_type, temperature, max_tokens, timeout, self.api_key
            )

    async def _generate_with_image_rotation(
        self,
        prompt: str,
        image_bytes: bytes,
        mime_type: str,
        temperature: float,
        max_tokens: int,
        timeout: int,
    ) -> Optional[Dict]:
        """Try image generation with key rotation."""
        available_keys = self.rotator.available_quota_keys
        if not available_keys:
            logger.error("No Gemini API keys with available quota")
            return None

        # Try each available key
        for attempt, key in enumerate(available_keys):
            result = await self._generate_with_image_single_key(
                prompt, image_bytes, mime_type, temperature, max_tokens, timeout, key
            )
            if result is not None:
                self.rotator.record_successful_request(key)
                return result
            else:
                self.rotator.record_error(key, "Image request failed")
                if attempt < len(available_keys) - 1:
                    logger.warning(f"Retrying image analysis with next Gemini API key...")
                    self.rotator.rotate_to_next_key()

        logger.error("All available Gemini API keys failed for image analysis")
        return None

    async def _generate_with_image_single_key(
        self,
        prompt: str,
        image_bytes: bytes,
        mime_type: str,
        temperature: float,
        max_tokens: int,
        timeout: int,
        api_key: Optional[str],
    ) -> Optional[Dict]:
        """Make a single image request with given API key."""
        if not api_key:
            logger.error("No API key provided to Gemini vision client")
            return None
        # Encode image to base64
        b64_image = base64.b64encode(image_bytes).decode("utf-8")

        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": prompt},
                        {
                            "inline_data": {
                                "mime_type": mime_type,
                                "data": b64_image,
                            }
                        },
                    ]
                }
            ],
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens,
                "responseMimeType": "application/json",
            },
        }
        headers = {"Content-Type": "application/json"}
        # Use vision model endpoint
        vision_url = f"{GEMINI_BASE_URL}/{VISION_MODEL}:generateContent?key={api_key}"

        try:
            async with aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=timeout)
            ) as session:
                    async with session.post(vision_url, json=payload, headers=headers) as resp:
                        resp.raise_for_status()
                        data = cast(Dict[str, Any], await resp.json())
                        # resp.json() is untyped (Any); cast to a dict for static checks
                        candidates: list[Any] = data.get("candidates", []) or []

                        if not candidates:
                            logger.warning("Gemini returned no candidates for image request")
                            return None
                        try:
                            text = candidates[0]["content"]["parts"][0]["text"]
                        except Exception:
                            text = None

                        if not text:
                            logger.error("Gemini vision returned empty text candidate")
                            return None

                        # Parse JSON from the returned text and ensure it's a dict
                        try:
                            parsed = json.loads(text)
                            if isinstance(parsed, dict):
                                return parsed
                        except json.JSONDecodeError:
                            pass

                        import re
                        match = re.search(r"\{.*?\}", text, re.DOTALL)
                        if match:
                            try:
                                parsed = json.loads(match.group())
                                if isinstance(parsed, dict):
                                    return parsed
                            except json.JSONDecodeError:
                                pass

                        logger.error(
                            "Could not parse Gemini vision response as JSON: %s",
                            (text or "")[:300],
                        )
                        return None
        except aiohttp.ClientResponseError as e:
            if e.status == 429:
                logger.warning(f"Gemini quota exceeded (429): {e.message}")
            else:
                logger.error("Gemini vision HTTP error %d: %s", e.status, e.message)
            return None
        except asyncio.TimeoutError:
            logger.warning("Gemini vision request timed out after %ds", timeout)
            return None
        except Exception as e:
            logger.error("Gemini vision request failed: %s", e)
            return None

    def is_available(self) -> bool:
        return self.enabled


# Singleton instance
_client: Optional[GeminiClient] = None

def get_gemini_client(rotator=None) -> GeminiClient:
    """
    Get or create the global Gemini client instance.
    
    Args:
        rotator: Optional APIKeyRotator instance for multi-key rotation
    
    Returns:
        Global GeminiClient instance
    """
    global _client
    if _client is None:
        _client = GeminiClient(rotator=rotator)
    elif rotator and not _client.rotator:
        # Update client with rotator if provided later
        _client.rotator = rotator
        _client.enabled = bool(_client.api_key or (rotator and rotator.available_keys))
    return _client

