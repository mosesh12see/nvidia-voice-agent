import os
import yaml
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class CampaignConfig:
    name: str = "Generic Agent"
    system_prompt: str = "You are a helpful voice assistant. Be concise and conversational."
    voice: str = "en-US-1"
    transfer_extension: str = ""
    transfer_keywords: list = field(default_factory=list)
    max_duration_seconds: int = 300
    language: str = "en"
    greeting: str = "Hello, how can I help you today?"


def load_campaign(name: str = None) -> CampaignConfig:
    name = name or os.getenv("DEFAULT_CAMPAIGN", "template")
    path = Path(__file__).parent / "campaigns" / f"{name}.yaml"
    if not path.exists():
        return CampaignConfig()
    with open(path) as f:
        data = yaml.safe_load(f) or {}
    return CampaignConfig(**{k: v for k, v in data.items() if hasattr(CampaignConfig, k)})
