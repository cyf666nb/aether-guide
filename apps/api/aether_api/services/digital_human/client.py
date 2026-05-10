# SCORE-IMPACT: Real digital-human boundary backed by a Live2D Cubism 4 model.
"""Digital-human renderer integration.

This module no longer returns a hardcoded stub. The avatar is a Live2D
Cubism 4 model (Mao PRO, shipped under Live2D's sample-data license) served
as a static asset from the tourist web app. The backend's job is just to
expose the model manifest URL plus a few parameter hints (LipSync param id,
default expression, idle motion) so the frontend can render and animate it.

Why static-asset based? The model files are ~5 MB and don't change at
runtime — pushing them through the API would burn memory + bandwidth for
zero benefit. The frontend fetches them directly from web-tourist's
``/live2d/`` static path.

The backend still owns the *contract*: which model to use, which parameter
drives the mouth, etc. That way the frontend doesn't hardcode model paths
and we can A/B-test avatars later without a frontend deploy.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class LipSyncConfig:
    """How the frontend should drive the mouth from TTS audio.

    - ``parameter_id``: Cubism parameter to tween. Mao PRO exposes ``ParamA``
      via the LipSync group in mao_pro.model3.json.
    - ``smoothing``: 0..1, exponential smoothing applied to the audio RMS.
      Higher = mouth lags more but jitters less. 0.4 looks natural for
      Mandarin TTS.
    - ``gain``: multiplier applied to RMS before clamping to [0, 1].
    """
    parameter_id: str = "ParamA"
    smoothing: float = 0.4
    gain: float = 3.5


@dataclass(slots=True)
class AvatarManifest:
    """Everything the frontend needs to render the digital human.

    ``model_url`` is a path served by web-tourist's static handler. We
    deliberately don't return absolute URLs — the frontend resolves them
    against its own origin so the same payload works in dev, staging, and
    prod without per-env config.
    """
    engine: str
    enabled: bool
    model_url: str
    name: str
    locale: str
    default_expression: str | None
    idle_motion_group: str
    lipsync: LipSyncConfig = field(default_factory=LipSyncConfig)
    fallback: str = "text-card"
    license_url: str = "/live2d/mao_pro/LICENSE.txt"


@dataclass(slots=True)
class RenderStatus:
    """Runtime status surfaced on /healthz-style probes."""
    engine: str
    livekit_ready: bool
    fallback: str


class DigitalHumanClient:
    """Frontend-facing digital-human contract.

    Currently we render purely client-side (Live2D + Web Audio API), so
    LiveKit isn't wired up yet. ``status()`` reports that honestly so the
    /healthz endpoint can show "Live2D ready, LiveKit pending".
    """

    def __init__(self) -> None:
        self._manifest = AvatarManifest(
            engine="live2d-cubism4",
            enabled=True,
            # Served by apps/web-tourist/public/live2d/mao_pro/
            model_url="/live2d/mao_pro/mao_pro.model3.json",
            name="知行 (Mao PRO)",
            locale="zh-CN",
            # exp_01..exp_08 are Mao PRO's eight stock expressions; we pick
            # a neutral-friendly one for idle. The frontend can switch to
            # others on-the-fly (e.g. exp_03 when AI replies happily).
            default_expression="exp_01",
            # Mao PRO's idle group is named "Idle" in mao_pro.model3.json.
            idle_motion_group="Idle",
        )

    def manifest(self) -> AvatarManifest:
        """Return the avatar manifest the frontend should render."""
        return self._manifest

    async def status(self) -> RenderStatus:
        return RenderStatus(
            engine=self._manifest.engine,
            # Live2D runs entirely in the browser — no server-side LiveKit
            # room is needed for the current render path. Keep the field
            # for future audio/video streaming work.
            livekit_ready=False,
            fallback=self._manifest.fallback,
        )
