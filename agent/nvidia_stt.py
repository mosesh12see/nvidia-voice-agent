import io
import os
import httpx
from pipecat.services.ai_services import STTService
from pipecat.frames.frames import TranscriptionFrame, ErrorFrame
from pipecat.processors.frame_processor import FrameDirection


class NvidiaParakeetSTT(STTService):
    """NVIDIA Parakeet STT via NIM REST API."""

    def __init__(self, api_key: str = None, model: str = "nvidia/parakeet-ctc-1.1b-asr", **kwargs):
        super().__init__(**kwargs)
        self._api_key = api_key or os.getenv("NVIDIA_API_KEY")
        self._model = model
        self._base_url = os.getenv("NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1")
        self._client = httpx.AsyncClient(timeout=10.0)

    async def run_stt(self, audio: bytes, language: str = "en") -> str:
        headers = {"Authorization": f"Bearer {self._api_key}"}
        files = {"file": ("audio.wav", io.BytesIO(audio), "audio/wav")}
        data = {"model": self._model, "language": language, "response_format": "json"}
        try:
            resp = await self._client.post(
                f"{self._base_url}/audio/transcriptions",
                headers=headers,
                files=files,
                data=data,
            )
            resp.raise_for_status()
            return resp.json().get("text", "").strip()
        except Exception as e:
            await self.push_error(ErrorFrame(f"Parakeet STT error: {e}"))
            return ""

    async def cleanup(self):
        await self._client.aclose()
