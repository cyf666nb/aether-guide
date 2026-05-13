# SCORE-IMPACT: Photo-based VPS with VLM-powered landmark recognition.
from __future__ import annotations

import asyncio
import json
import logging
import re
from dataclasses import dataclass
from typing import TYPE_CHECKING

import httpx

from aether_api.repository import Repository
from aether_api.schemas.common import GeoPoint
from aether_api.schemas.landmarks import LandmarkDTO
from aether_api.schemas.location import LocationResult

if TYPE_CHECKING:
    from aether_api.config import Settings

logger = logging.getLogger(__name__)

_shared_vlm_client: httpx.AsyncClient | None = None
_shared_vlm_client_lock = asyncio.Lock()


async def _get_shared_vlm_client() -> httpx.AsyncClient:
    global _shared_vlm_client
    if _shared_vlm_client is not None:
        return _shared_vlm_client
    async with _shared_vlm_client_lock:
        if _shared_vlm_client is None:
            _shared_vlm_client = httpx.AsyncClient(
                timeout=httpx.Timeout(15.0),
                limits=httpx.Limits(
                    max_keepalive_connections=10,
                    max_connections=20,
                    keepalive_expiry=30.0,
                ),
            )
        return _shared_vlm_client


async def aclose_shared_client() -> None:
    global _shared_vlm_client
    if _shared_vlm_client is not None:
        try:
            await _shared_vlm_client.aclose()
        finally:
            _shared_vlm_client = None


@dataclass(frozen=True, slots=True)
class VisualCandidate:
    id: str
    name: str
    summary: str
    aliases: tuple[str, ...] = ()
    point: GeoPoint | None = None


VISUAL_RECOGNITION_CATALOG: tuple[VisualCandidate, ...] = (
    VisualCandidate(
        "nanhou-street",
        "南后街",
        "三坊七巷南北向中轴步行街，常见街牌、商铺、石板路和入口人流。",
        ("南后街主街", "南后街步行街"),
        GeoPoint(lat=26.0835, lng=119.2967, accuracy_m=25),
    ),
    VisualCandidate(
        "nanhou-street-north-archway",
        "南后街北口牌坊",
        "北侧入口牌坊，刻有南后街字样，是高频打卡入口。",
        ("北口牌坊", "南后街牌坊"),
        GeoPoint(lat=26.0856, lng=119.2966, accuracy_m=25),
    ),
    VisualCandidate(
        "nanhou-street-south-archway",
        "南后街南口牌坊",
        "南侧入口牌坊，靠近澳门路和林则徐纪念馆延伸方向。",
        ("南口牌坊",),
        GeoPoint(lat=26.0812, lng=119.2967, accuracy_m=25),
    ),
    VisualCandidate("yijin-lane", "衣锦坊", "西侧三坊之一，仕宦荣归文化意象。", ("衣锦坊巷",)),
    VisualCandidate(
        "wenru-lane", "文儒坊", "西侧三坊之一，文教、儒学和名人故里线索。", ("文儒坊巷",)
    ),
    VisualCandidate(
        "guanglu-lane", "光禄坊", "西侧三坊之一，相对安静，适合古厝观察。", ("光禄坊巷",)
    ),
    VisualCandidate(
        "yangqiao-alley", "杨桥巷", "七巷中偏北的一条，靠近杨桥路入口。", ("杨桥路口",)
    ),
    VisualCandidate(
        "langguan-alley", "郎官巷", "七巷之一，仕宦文化相关，严复故居位于此处。", ("郎官巷20号",)
    ),
    VisualCandidate(
        "ta-alley", "塔巷", "七巷之一，适合识别巷名牌、窄巷和门楼尺度。", ("塔巷巷口",)
    ),
    VisualCandidate(
        "huang-alley",
        "黄巷",
        "七巷之一，古厝细部、马鞍墙、天井和建筑摄影常见。",
        ("黄巷巷口",),
        GeoPoint(lat=26.08347, lng=119.29692, accuracy_m=20),
    ),
    VisualCandidate(
        "anmin-alley", "安民巷", "七巷之一，人流相对缓和，适合街巷过渡。", ("安民巷巷口",)
    ),
    VisualCandidate(
        "gong-alley",
        "宫巷",
        "七巷之一，传统宅院空间和沈葆桢故居线索。",
        ("宫巷巷口",),
        GeoPoint(lat=26.08205, lng=119.2969, accuracy_m=20),
    ),
    VisualCandidate(
        "jipi-alley", "吉庇巷", "七巷南侧收束点，可衔接澳门路和林则徐纪念馆。", ("吉庇巷巷口",)
    ),
    VisualCandidate(
        "linjuemin-bingxin",
        "林觉民·冰心故居",
        "名人故居，常见门匾、故居牌识和院落空间。",
        ("林觉民故居", "冰心故居", "林觉民冰心故居"),
        GeoPoint(lat=26.0817, lng=119.2968, accuracy_m=20),
    ),
    VisualCandidate(
        "yanfu-former-residence",
        "严复故居",
        "近代思想家严复相关故居，常见严复故居牌匾。",
        ("严复旧居",),
        GeoPoint(lat=26.08478, lng=119.29638, accuracy_m=20),
    ),
    VisualCandidate(
        "shenbaozhen-former-residence",
        "沈葆桢故居",
        "船政、海防和近代化主题故居。",
        ("沈葆桢旧居",),
        GeoPoint(lat=26.08205, lng=119.2969, accuracy_m=20),
    ),
    VisualCandidate(
        "ermei-study", "二梅书屋", "书香气质文化空间，适合识别书屋牌识。", ("二梅书屋旧址",)
    ),
    VisualCandidate(
        "xiaohuanglou",
        "小黄楼",
        "代表性古厝与院落体验空间，适合识别黄墙、天井、园林和木构。",
        ("小黄楼景区",),
        GeoPoint(lat=26.08325, lng=119.29615, accuracy_m=20),
    ),
    VisualCandidate(
        "shuixie-stage",
        "水榭戏台",
        "代表性演艺空间，常见戏台、水榭、演出和夜游场景。",
        ("水榭戏臺", "闽剧戏台"),
        GeoPoint(lat=26.08188, lng=119.29672, accuracy_m=20),
    ),
    VisualCandidate(
        "ouyang-family-house",
        "欧阳氏民居",
        "传统民居院落，可识别宅院、门楼和家族居住空间。",
        ("欧阳氏古厝",),
        GeoPoint(lat=26.08262, lng=119.29608, accuracy_m=20),
    ),
    VisualCandidate(
        "fuzhou-intangible-heritage",
        "福州非遗展示点",
        "油纸伞、软木画、脱胎漆器、闽剧等非遗展示和手作场景。",
        ("非遗展示点", "非遗手作体验区", "油纸伞铺"),
        GeoPoint(lat=26.0839, lng=119.2968, accuracy_m=30),
    ),
    VisualCandidate(
        "tea-culture-zone",
        "茉莉花茶文化区",
        "茉莉花茶、茶席、茶馆和福州茶文化场景。",
        ("茉莉花茶馆", "茶文化区"),
        GeoPoint(lat=26.0844, lng=119.2967, accuracy_m=30),
    ),
    VisualCandidate(
        "min-cuisine-area",
        "闽菜美食区",
        "福州小吃、闽菜正餐和南后街南端餐饮片区。",
        ("闽菜馆", "福州小吃", "美食区"),
        GeoPoint(lat=26.0815, lng=119.2965, accuracy_m=35),
    ),
    VisualCandidate(
        "linzexu-memorial-nearby",
        "林则徐纪念馆",
        "三坊七巷南侧邻近延伸点，常见林则徐纪念馆牌识。",
        ("林则徐纪念馆（邻近延伸）", "林文忠公祠"),
        GeoPoint(lat=26.07955, lng=119.2957, accuracy_m=30),
    ),
    VisualCandidate(
        "horse-head-wall",
        "马鞍墙观景点",
        "福州古厝外部特征，墙体起伏形似马鞍。",
        ("马鞍墙", "封火墙"),
        GeoPoint(lat=26.0837, lng=119.2972, accuracy_m=30),
    ),
    VisualCandidate(
        "sky-well-spot", "天井观景点", "福州古厝天井空间，可见院落采光和层层递进结构。", ("天井",)
    ),
    VisualCandidate(
        "moon-gate", "月门", "古厝与园林中的圆形门洞，适合框景拍摄。", ("月洞门", "圆门")
    ),
    VisualCandidate(
        "heart-tree",
        "爱心树",
        "三坊七巷高辨识度网红打卡树，情侣合影常见。",
        ("心形树", "夫妻树"),
        GeoPoint(lat=26.0815, lng=119.29703, accuracy_m=15),
    ),
    VisualCandidate(
        "night-nanhou",
        "夜游南后街",
        "灯笼、暖光、夜景、人流和南后街夜游氛围。",
        ("夜景灯笼街", "南后街夜景"),
        GeoPoint(lat=26.0837, lng=119.2966, accuracy_m=25),
    ),
)


def _normalize_text(value: object) -> str:
    text = str(value or "").casefold()
    text = re.sub(r"[\\s·•,，.。:：;；()（）\\[\\]【】'\"“”‘’/\\\\-]", "", text)
    return text


def _extract_json_object(content: str) -> dict[str, object] | None:
    json_start = content.find("{")
    json_end = content.rfind("}") + 1
    if json_start < 0 or json_end <= json_start:
        return None
    try:
        parsed = json.loads(content[json_start:json_end])
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict) else None


def _coerce_confidence(value: object) -> float:
    if not isinstance(value, (int, float, str)):
        return 0.0
    try:
        confidence = float(value)
    except (TypeError, ValueError):
        return 0.0
    return max(0.0, min(1.0, confidence))


def _catalog_prompt() -> str:
    lines: list[str] = []
    for candidate in VISUAL_RECOGNITION_CATALOG:
        aliases = f"（别名：{'、'.join(candidate.aliases)}）" if candidate.aliases else ""
        lines.append(f"- {candidate.id}: {candidate.name}{aliases}；{candidate.summary}")
    return "\n".join(lines)


def _match_visual_candidate(
    raw_id: object,
    place_name: object,
    landmarks: list[LandmarkDTO],
) -> tuple[LandmarkDTO | None, VisualCandidate | None, str | None]:
    raw_id_text = str(raw_id or "").strip()
    place_text = str(place_name or "").strip()
    normalized_place = _normalize_text(place_text)

    landmark_by_id = {lm.id: lm for lm in landmarks}
    if raw_id_text in landmark_by_id:
        landmark = landmark_by_id[raw_id_text]
        return landmark, None, landmark.name

    for candidate in VISUAL_RECOGNITION_CATALOG:
        if raw_id_text == candidate.id:
            matched_landmark = landmark_by_id.get(candidate.id)
            return (
                matched_landmark,
                candidate,
                matched_landmark.name if matched_landmark else candidate.name,
            )

    search_values = [normalized_place, _normalize_text(raw_id_text)]
    for lm in landmarks:
        normalized_name = _normalize_text(lm.name)
        if normalized_name and any(
            value and (normalized_name in value or value in normalized_name)
            for value in search_values
        ):
            return lm, None, lm.name

    for candidate in VISUAL_RECOGNITION_CATALOG:
        names = (candidate.name, *candidate.aliases)
        normalized_names = [_normalize_text(name) for name in names]
        if any(
            name and value and (name in value or value in name)
            for name in normalized_names
            for value in search_values
        ):
            matched_landmark = landmark_by_id.get(candidate.id)
            return (
                matched_landmark,
                candidate,
                matched_landmark.name if matched_landmark else candidate.name,
            )

    return None, None, place_text or None


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
        if self._settings and self._settings.openai_api_key:
            try:
                result = await self._vlm_identify(image_base64, scenic_id, landmarks)
                if result:
                    return result
            except Exception:
                logger.exception("VLM identification failed, falling back to heuristic")

        return LocationResult(
            status="uncertain",
            scenic_id=scenic_id,
            landmark_id=None,
            landmark_name=None,
            point=gps_hint,
            confidence=0.0,
            follow_up="能拍一下附近的牌匾、巷名或建筑正面吗？",
        )

    async def _vlm_identify(
        self,
        image_base64: str,
        scenic_id: str,
        landmarks: list[LandmarkDTO],
    ) -> LocationResult | None:
        settings = self._settings
        if not settings or not settings.openai_api_key:
            return None

        curated_ids = {lm.id for lm in landmarks}

        prompt = f"""你是三坊七巷的视觉识别助手。用户拍了一张照片，请识别照片中的景点或地点。

识别要求：
1. 优先根据画面中的牌匾、巷名、门楼、建筑形态、店招、展陈文字判断真实地点。
2. 下面是视觉参考库，不是唯一答案；如果照片明显是三坊七巷内其它地点，
   也要输出你识别到的 place_name。
3. landmark_id 只在能和参考库 ID 明确对应时填写；如果只知道地点名称但
   没有精确 ID，landmark_id 填 null。
4. 不要为了匹配列表而硬猜最近的精选景点。看不清就返回低置信度。

游客页精选景点 ID（这些可以直接返回 landmark_id）：
{", ".join(sorted(curated_ids)) or "无"}

视觉参考库：
{_catalog_prompt()}

请用 JSON 回复，字段为：
- place_name：识别到的地点名称，无法确定时为 null
- landmark_id：参考库 ID，无法精确对应时为 null
- confidence：0.0 到 1.0
- description：简短描述你看到了什么
- direction：从当前位置怎么走到主街或下一步建议

如果无法确定，place_name 和 landmark_id 设为 null，confidence 设为 0。只回复 JSON。"""

        api_key = settings.openai_api_key.get_secret_value()
        base_url = settings.openai_base_url.rstrip("/")
        url = f"{base_url}/chat/completions"

        vlm_model = (
            getattr(settings, "vlm_model", None)
            or settings.anthropic_model
            or "doubao-seed-2.0-pro"
        )
        payload = {
            "model": vlm_model,
            "max_tokens": 300,
            "temperature": 0.1,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"},
                        },
                    ],
                },
            ],
        }
        headers = {
            "content-type": "application/json",
            "Authorization": f"Bearer {api_key}",
        }

        client = await _get_shared_vlm_client()
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

        result = _extract_json_object(content)
        if result is None:
            return None

        return self._location_from_vlm_payload(result, scenic_id, landmarks)

    def _location_from_vlm_payload(
        self,
        result: dict[str, object],
        scenic_id: str,
        landmarks: list[LandmarkDTO],
    ) -> LocationResult:
        landmark_id = result.get("landmark_id")
        place_name = result.get("place_name") or result.get("landmark_name") or landmark_id
        confidence = _coerce_confidence(result.get("confidence", 0))
        description = str(result.get("description") or "").strip()
        direction = str(result.get("direction") or "").strip()
        landmark, candidate, resolved_name = _match_visual_candidate(
            landmark_id, place_name, landmarks
        )

        if not resolved_name:
            return LocationResult(
                status="uncertain",
                scenic_id=scenic_id,
                landmark_id=None,
                landmark_name=None,
                point=None,
                confidence=confidence,
                follow_up=f"{description} 再拍一张更清晰的牌匾或巷名试试？".strip(),
            )

        follow_up = None
        if confidence < 0.7:
            follow_up = (
                f"不太确定，{description}。换个角度再拍一张？"
                if description
                else "不太确定，换个角度再拍一张？"
            )
        elif direction:
            follow_up = direction
        elif description:
            follow_up = description

        result_landmark_id = landmark.id if landmark is not None else None
        point = (
            landmark.geo_point if landmark is not None else candidate.point if candidate else None
        )
        return LocationResult(
            status="located" if confidence >= 0.6 else "uncertain",
            scenic_id=landmark.scenic_id if landmark is not None else scenic_id,
            landmark_id=result_landmark_id,
            landmark_name=resolved_name,
            point=point,
            confidence=confidence,
            follow_up=follow_up,
        )
