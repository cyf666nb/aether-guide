# SCORE-IMPACT: Digital-human rendering boundary with graceful fallback.
from dataclasses import dataclass


@dataclass(slots=True)
class RenderStatus:
    engine: str
    livekit_ready: bool
    fallback: str


class DigitalHumanClient:
    async def status(self) -> RenderStatus:
        return RenderStatus(engine="MuseTalk stub", livekit_ready=False, fallback="text-card")

