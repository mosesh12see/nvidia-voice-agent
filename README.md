# NVIDIA Voice Agent

Generic reusable voice agent template using:
- **STT**: NVIDIA Parakeet (via NIM API)
- **LLM**: NVIDIA Nemotron (via NIM API, OpenAI-compatible)
- **TTS**: NVIDIA Magpie (preview) or Cartesia Sonic (fallback)
- **Transport**: Daily.co WebRTC via Pipecat
- **Telephony**: Asterisk PJSIP, new isolated context

**Cost**: ~$0.015-0.027/min vs $0.12-0.15/min for Vapi/Retell

## Quick Start

### 1. Local setup
```bash
cp env.example .env
# Fill in: NVIDIA_API_KEY, DAILY_API_KEY, CARTESIA_API_KEY
pip3 install -r requirements.txt
python3 launcher.py
```

### 2. Deploy to Asterisk server
```bash
bash deploy.sh
```

### 3. Configure on server
Edit `/opt/nvidia-voice-agent/.env`:
```
NVIDIA_API_KEY=nvapi-...
DAILY_API_KEY=f8950b5428f78ff0a01cd0cd4816227c20badf26aade8c26e8463bae818eb159
CARTESIA_API_KEY=sk_car_...
TTS_PROVIDER=cartesia
```

Add to `/etc/asterisk/extensions.conf`:
```
#include "includes/nvidia-agent.conf"
```

Start the service:
```bash
systemctl start nvidia-agent
asterisk -rx 'dialplan reload'
```

Test by calling extension **8400**.

## Adding a New Campaign

1. Copy `campaigns/template.yaml` to `campaigns/my-campaign.yaml`
2. Edit the system prompt, voice, transfer extension
3. Add a new extension to `dialplan/nvidia-agent.conf`:
   ```
   exten => 8401,1,NoOp(My campaign)
    same => n,Answer()
    same => n,AGI(/opt/nvidia-voice-agent/agi/nvidia_agent.agi,my-campaign)
    ...
   ```

## Switching TTS Provider

In `.env`:
```
TTS_PROVIDER=cartesia   # default, proven
TTS_PROVIDER=magpie     # NVIDIA preview
```

## API Keys Needed

| Key | Where | Notes |
|-----|-------|-------|
| `NVIDIA_API_KEY` | build.nvidia.com | NIM API — STT + LLM + Magpie TTS |
| `DAILY_API_KEY` | Pipecat Cloud dashboard | Already saved in MASTER_SECRETS |
| `CARTESIA_API_KEY` | cartesia.ai | TTS fallback (already in Api Info) |
