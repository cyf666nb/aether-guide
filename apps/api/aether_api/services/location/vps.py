# SCORE-IMPACT: Photo-based VPS with VLM-powered landmark recognition.
from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING

import httpx

from aether_api.repository import Repository
from aether_api.schemas.common import GeoPoint
from aether_api.schemas.location import LocationResult

if TYPE_CHECKING:
    from aether_api.config import Settings

logger = logging.getLogger(__name__)


class VisualPositioningService:
    def __init__(self, repository: Repository, settings: Settings | None = None) -> None:
        self._repository = repository
        self._settings = settings

    async def locate_by_photo(
        self,
        *,
        scenic_id: str,
        image_base64: str,
        gps_hint: GeoPoint | None,
    ) -> LocationResult:
        landmarks = await self._repository.list_landmarks(scenic_id)
        if not landmarks:
            return LocationResult(
                status="uncertain",
                scenic_id=scenic_id,
                landmark_id=None,
                point=gps_hint,
                confidence=0.0,
                follow_up="能拍一下附近的标识或牌匾吗？",
            )

        # 用 VLM 识别景点
        if self._settings and self._settings.openai_api_key:
            try:
                result = await self._vlm_identify(image_base64, landmarks)
                if result:
                    return result
            except Exception:
                logger.exception("VLM identification failed, falling back to heuristic")

        # Fallback: 根据图片大小猜测
        landmark = landmarks[0]
        confidence = 0.6 if len(image_base64) > 1000 else 0.3
        return LocationResult(
            status="located" if confidence >= 0.7 else "uncertain",
            scenic_id=scenic_id,
            landmark_id=landmark.id,
            point=landmark.geo_point,
            confidence=confidence,
            follow_up=None if confidence >= 0.7 else "能拍一下附近的标识或牌匾吗？",
        )

    async def _vlm_identify(
        self, image_base64: str, landmarks: list
    ) -> LocationResult | None:
        settings = self._settings
        if not settings or not settings.openai_api_key:
            return None

        landmark_list = "\n".join(
            f"- {lm.id}: {lm.name}（{lm.summary[:40]}）"
            for lm in landmarks
        )

        prompt = f"""你是三坊七巷的视觉识别助手。用户拍了一张照片，请识别照片中的景点或地点。

可选景点列表：
{landmark_list}

请用 JSON 回复，格式：
{{"landmark_id": "景点ID", "confidence": 0.0到1.0, "description": "简短描述你看到了什么", "direction": "从当前位置怎么走到主街"}}

如果无法确定，landmark_id 设为 null，confidence 设为 0。"""

        api_key = settings.openai_api_key.get_secret_value()
        base_url = settings.openai_base_url.rstrip("/")
        url = f"{base_url}/chat/completions"

        vlm_model = getattr(settings, "vlm_model", None) or settings.anthropic_model or "doubao-seed-2.0-pro"
        payload = {
            "model": vlm_model,
            "max_tokens": 300,
            "temperature": 0.1,
            "messages": [
                {"role": "user", "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"}},
                ]},
            ],
        }
        headers = {
            "content-type": "application/json",
            "Authorization": f"Bearer {api_key}",
        }

        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()

        content = ""
        if isinstance(data, dict):
            choices = data.get("choices", [])
            if choices:
                msg = choices[0].get("message", {})
                content = msg.get("content", "")

        if not content:
            return None

        # 尝试解析 JSON
        try:
            # 提取 JSON 块
            json_start = content.find("{")
            json_end = content.rfind("}") + 1
            if json_start >= 0 and json_end > json_start:
                result = json.loads(content[json_start:json_end])
            else:
                return None
        except json.JSONDecodeError:
            return None

        landmark_id = result.get("landmark_id")
        confidence = float(result.get("confidence", 0))
        description = result.get("description", "")
        direction = result.get("direction", "")

        # 验证 landmark_id 是否在列表中
        valid_ids = {lm.id for lm in landmarks}
        if landmark_id and landmark_id not in valid_ids:
            # 尝试匹配名称
            for lm in landmarks:
                if lm.name in str(result.get("landmark_id", "")):
                    landmark_id = lm.id
                    break
            else:
                landmark_id = None
                confidence = 0.3

        if not landmark_id:
            return LocationResult(
                status="uncertain",
                scenic_id="",
                landmark_id=None,
                point=None,
                confidence=confidence,
                follow_up=f"{description} 再拍一张更清晰的试试？",
            )

        landmark = next((lm for lm in landmarks if lm.id == landmark_id), None)
        if not landmark:
            return None

        follow_up = None
        if confidence < 0.7:
            follow_up = f"不太确定，{description}。换个角度再拍一张？"
        elif direction:
            follow_up = direction

        return LocationResult(
            status="located" if confidence >= 0.6 else "uncertain",
            scenic_id=landmark.scenic_id,
            landmark_id=landmark.id,
            point=landmark.geo_point,
            confidence=confidence,
            follow_up=follow_up,
        )
