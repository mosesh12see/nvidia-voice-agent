import os
import asyncio
from loguru import logger

from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineParams, PipelineTask
from pipecat.transports.services.daily import DailyParams, DailyTransport
from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.processors.aggregators.openai_llm_context import OpenAILLMContext
from pipecat.services.openai import OpenAILLMService
from openai import AsyncOpenAI

from agent.nvidia_stt import NvidiaParakeetSTT
from agent.nvidia_tts import build_tts_service
from config import CampaignConfig


async def run_agent(room_url: str, campaign: CampaignConfig):
    """Run a Pipecat voice agent in a Daily.co room."""

    transport = DailyTransport(
        room_url,
        token=None,
        bot_name="NvidiaAgent",
        params=DailyParams(
            audio_in_enabled=True,
            audio_out_enabled=True,
            transcription_enabled=False,
            vad_enabled=True,
            vad_analyzer=SileroVADAnalyzer(),
        ),
    )

    stt = NvidiaParakeetSTT()

    llm_client = AsyncOpenAI(
        api_key=os.getenv("NVIDIA_API_KEY"),
        base_url=os.getenv("NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1"),
    )
    llm = OpenAILLMService(
        client=llm_client,
        model=os.getenv("NVIDIA_LLM_MODEL", "nvidia/llama-3.1-nemotron-70b-instruct"),
    )

    tts = build_tts_service()

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

    task = PipelineTask(pipeline, PipelineParams(allow_interruptions=True))

    @transport.event_handler("on_first_participant_joined")
    async def on_first_participant_joined(transport, participant):
        await transport.capture_participant_transcription(participant["id"])
        await task.queue_frames([context_aggregator.user().get_context_frame()])

    @transport.event_handler("on_participant_left")
    async def on_participant_left(transport, participant, reason):
        await task.cancel()

    runner = PipelineRunner()
    await runner.run(task)
