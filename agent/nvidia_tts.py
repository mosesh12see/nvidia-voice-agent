import os
import httpx
from typing import AsyncGenerator
from pipecat.services.tts_service import TTSService
from pipecat.frames.frames import AudioRawFrame, ErrorFrame


class NvidiaMagpieTTS(TTSService):
    """NVIDIA Magpie TTS via NIM REST API (preview). Falls back to Cartesia if unavailable."""

    def __init__(self, api_key: str = None, voice: str = None, **kwargs):
        super().__init__(**kwargs)
        self._api_key = api_key or os.getenv("NVIDIA_API_KEY")
        self._voice = voice or os.getenv("MAGPIE_VOICE", "en-US-1")
        self._base_url = os.getenv("NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1")
        self._client = httpx.AsyncClient(timeout=15.0)

    async def run_tts(self, text: str) -> AsyncGenerator[bytes, None]:
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": "magpie-tts-multilingual",
            "input": text,
            "voice": self._voice,
            "response_format": "wav",
        }
        try:
            resp = await self._client.post(
                f"{self._base_url}/audio/speech",
                headers=headers,
                json=payload,
            )
            resp.raise_for_status()
            yield resp.content
        except Exception as e:
            await self.push_error(ErrorFrame(f"Magpie TTS error: {e}"))

    async def cleanup(self):
        await self._client.aclose()


class CartesiaTTSFallback(TTSService):
    """Cartesia Sonic TTS — primary fallback when Magpie is unavailable."""

    def __init__(self, api_key: str = None, voice_id: str = None, **kwargs):
        super().__init__(**kwargs)
        self._api_key = api_key or os.getenv("CARTESIA_API_KEY")
        self._voice_id = voice_id or os.getenv(
            "CARTESIA_VOICE_ID", "95856005-0332-41b0-935f-352e296aa0df"
        )
        self._client = httpx.AsyncClient(timeout=15.0)

    async def run_tts(self, text: str) -> AsyncGenerator[bytes, None]:
        headers = {
            "X-API-Key": self._api_key,
            "Cartesia-Version": "2024-06-10",
            "Content-Type": "application/json",
        }
        payload = {
            "transcript": text,
            "model_id": "sonic-english",
            "voice": {"mode": "id", "id": self._voice_id},
            "output_format": {"container": "raw", "encoding": "pcm_s16le", "sample_rate": 16000},
        }
        try:
            resp = await self._client.post(
                "https://api.cartesia.ai/tts/bytes",
                headers=headers,
                json=payload,
            )
            resp.raise_for_status()
            yield resp.content
        except Exception as e:
            await self.push_error(ErrorFrame(f"Cartesia TTS error: {e}"))

    async def cleanup(self):
        await self._client.aclose()


def build_tts_service(**kwargs):
    provider = os.getenv("TTS_PROVIDER", "cartesia").lower()
    if provider == "magpie":
        return NvidiaMagpieTTS(**kwargs)
    return CartesiaTTSFallback(**kwargs)
