"""
FastAPI launcher — creates Daily.co rooms and spawns Pipecat agents.
Runs on port 4579 (configurable via LAUNCHER_PORT).
"""

import os
import asyncio
import multiprocessing
from contextlib import asynccontextmanager
from typing import Optional

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from loguru import logger

load_dotenv()

from config import load_campaign
from agent.pipeline import run_agent

DAILY_API_KEY = os.getenv("DAILY_API_KEY", "")
DAILY_BASE_URL = os.getenv("DAILY_BASE_URL", "https://api.daily.co/v1")

active_agents: dict[str, multiprocessing.Process] = {}


async def create_daily_room(name: str) -> dict:
    if not DAILY_API_KEY:
        raise HTTPException(status_code=503, detail="DAILY_API_KEY not set")
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{DAILY_BASE_URL}/rooms",
            headers={"Authorization": f"Bearer {DAILY_API_KEY}"},
            json={
                "name": name,
                "properties": {
                    "max_participants": 2,
                    "enable_chat": False,
                    "enable_prejoin_ui": False,
                    "exp": int(asyncio.get_event_loop().time()) + 3600,
                },
            },
        )
        resp.raise_for_status()
        return resp.json()


def _agent_process(room_url: str, campaign_name: str):
    import asyncio
    from dotenv import load_dotenv
    load_dotenv()
    from config import load_campaign
    from agent.pipeline import run_agent
    campaign = load_campaign(campaign_name)
    asyncio.run(run_agent(room_url, campaign))


class StartCallRequest(BaseModel):
    campaign: Optional[str] = "template"
    call_id: Optional[str] = None


class StartCallResponse(BaseModel):
    call_id: str
    room_url: str
    room_name: str


class StopCallRequest(BaseModel):
    call_id: str


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("NVIDIA Voice Agent launcher starting on port {}", os.getenv("LAUNCHER_PORT", "4579"))
    yield
    for call_id, proc in active_agents.items():
        if proc.is_alive():
            proc.terminate()
            logger.info("Terminated agent for call {}", call_id)


app = FastAPI(title="NVIDIA Voice Agent Launcher", lifespan=lifespan)


@app.get("/health")
async def health():
    return {"status": "ok", "active_agents": len(active_agents)}


@app.post("/start-call", response_model=StartCallResponse)
async def start_call(req: StartCallRequest):
    import uuid
    call_id = req.call_id or str(uuid.uuid4())[:8]
    room_name = f"nvidia-agent-{call_id}"

    room = await create_daily_room(room_name)
    room_url = room["url"]

    proc = multiprocessing.Process(
        target=_agent_process,
        args=(room_url, req.campaign or "template"),
        daemon=True,
    )
    proc.start()
    active_agents[call_id] = proc
    logger.info("Started agent call_id={} room={}", call_id, room_url)

    return StartCallResponse(call_id=call_id, room_url=room_url, room_name=room_name)


@app.post("/stop-call")
async def stop_call(req: StopCallRequest):
    proc = active_agents.pop(req.call_id, None)
    if proc and proc.is_alive():
        proc.terminate()
    return {"status": "stopped", "call_id": req.call_id}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "launcher:app",
        host=os.getenv("LAUNCHER_HOST", "127.0.0.1"),
        port=int(os.getenv("LAUNCHER_PORT", "4579")),
        reload=False,
    )
