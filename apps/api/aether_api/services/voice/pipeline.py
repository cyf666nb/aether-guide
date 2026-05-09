# SCORE-IMPACT: Streaming voice pipeline contract for W2 expansion.
from dataclasses import dataclass


@dataclass(slots=True)
class VoicePipelineStatus:
    vad: str = "stubbed"
    asr: str = "stubbed"
    tts: str = "stubbed"
    fallback: str = "text"


class VoicePipeline:
    async def status(self) -> VoicePipelineStatus:
        return VoicePipelineStatus()

