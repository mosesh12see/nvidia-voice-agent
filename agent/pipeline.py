import os
import asyncio
from loguru import logger

from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineParams, PipelineTask
from pipecat.transports.daily.transport import DailyParams, DailyTransport
from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.processors.aggregators.openai_llm_context import OpenAILLMContext
from pipecat.services.openai.llm import OpenAILLMService
from pipecat.services.deepgram.stt import DeepgramSTTService
from pipecat.services.cartesia.tts import CartesiaTTSService
from pipecat.frames.frames import TTSSpeakFrame, EndFrame

from config import CampaignConfig


async def run_agent(room_url: str, campaign: CampaignConfig):
    """Run a Pipecat voice agent in a Daily.co room."""

    transport = DailyTransport(
        room_url,
        token=None,
        bot_name="NvidiaAgent",
        params=DailyParams(
            audio_in_enabled=True,
            audio_in_sample_rate=16000,
            audio_in_channels=1,
            audio_out_enabled=True,
            audio_out_sample_rate=16000,
            transcription_enabled=False,
            vad_enabled=True,
            vad_analyzer=SileroVADAnalyzer(),
        ),
    )

    # Deepgram streaming STT — sub-300ms, explicit 16kHz linear16 mono
    stt = DeepgramSTTService(
        api_key=os.getenv("DEEPGRAM_API_KEY"),
        encoding="linear16",
        sample_rate=16000,
        channels=1,
    )

    # NVIDIA Nemotron LLM via NIM (OpenAI-compatible endpoint)
    llm = OpenAILLMService(
        api_key=os.getenv("NVIDIA_API_KEY"),
        base_url=os.getenv("NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1"),
        model=os.getenv("NVIDIA_LLM_MODEL", "nvidia/llama-3.1-nemotron-70b-instruct"),
    )

    # Cartesia Sonic TTS — ~90ms latency
    tts = CartesiaTTSService(
        api_key=os.getenv("CARTESIA_API_KEY"),
        voice_id=os.getenv("CARTESIA_VOICE_ID", "95856005-0332-41b0-935f-352e296aa0df"),
    )

    messages = [{"role": "system", "content": campaign.system_prompt}]
    context = OpenAILLMContext(messages)
    context_aggregator = llm.create_context_aggregator(context)

    pipeline = Pipeline(
        [
            transport.input(),
            stt,
            context_aggregator.user(),
            llm,
            tts,
            transport.output(),
            context_aggregator.assistant(),
        ]
    )

    task = PipelineTask(pipeline, params=PipelineParams(allow_interruptions=True))

    @transport.event_handler("on_first_participant_joined")
    async def on_first_participant_joined(transport, participant):
        await task.queue_frame(TTSSpeakFrame(campaign.greeting))

    @transport.event_handler("on_participant_left")
    async def on_participant_left(transport, participant, reason):
        await task.queue_frame(EndFrame())

    runner = PipelineRunner()
    await runner.run(task)
