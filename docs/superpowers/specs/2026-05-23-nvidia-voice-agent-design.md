# NVIDIA Voice Agent — Design Spec
Date: 2026-05-23

## Goal
Generic reusable voice agent template using NVIDIA NIM API (Parakeet STT + Nemotron LLM + Magpie TTS) + Pipecat, wired into Moses's Asterisk box (157.230.13.249) without touching any existing campaign dialplans.

## Architecture

```
Caller → Asterisk [nvidia-agent] context
  → Python AGI script (agi/nvidia_agent.agi)
    → records audio
    → POST /turn to FastAPI launcher (port 4579)
      → NvidiaParakeetSTT: audio → transcript
      → NvidiaNemotronLLM: transcript + history → response text
      → NvidiaMagpieTTS: response text → audio bytes
    ← returns {audio, action: continue|transfer|hangup}
  → plays audio to caller
  → if transfer: Dial() to configured extension
  → loop
```

## Components

- `launcher.py` — FastAPI server on port 4579, handles /turn and /health
- `agent/pipeline.py` — Pipecat pipeline, one instance per call
- `agent/nvidia_stt.py` — Custom STTService wrapping NVIDIA Parakeet REST API
- `agent/nvidia_tts.py` — Custom TTSService wrapping NVIDIA Magpie (fallback: Cartesia)
- `agent/nvidia_llm.py` — OpenAI-compatible client pointing at NVIDIA NIM
- `agi/nvidia_agent.agi` — Asterisk AGI script, records audio, calls launcher, plays response
- `campaigns/template.yaml` — Generic campaign config (system prompt, voice, transfer ext)
- `dialplan/nvidia-agent.conf` — New [nvidia-agent] context only, safe to include
- `systemd/nvidia-agent.service` — Isolated systemd service, separate from all existing services

## Isolation Guarantees
- New context [nvidia-agent] — zero overlap with solar-exits, solexes, cap-energy, etc.
- New port 4579 — no conflict with existing services
- New systemd service `nvidia-agent.service`
- No pjsip_gradient.conf changes

## API Keys
- NVIDIA NIM: `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`
- Cartesia TTS fallback: `sk_car_sJxvJcFBo8rap9m4YGZmcW`
- Daily.co: placeholder (user to add after signup)

## Cost Estimate
~$0.015–$0.027/min all-in vs $0.12–$0.15/min for Vapi/Retell
