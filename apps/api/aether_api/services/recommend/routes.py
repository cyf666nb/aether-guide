# SCORE-IMPACT: AI-powered personalized route planning.
from __future__ import annotations

import json as _json
import logging
import re
from typing import TYPE_CHECKING

from aether_api.schemas.recommendations import (
    RouteRecommendationDTO,
    RouteRequest,
    RouteStopDTO,
)

if TYPE_CHECKING:
    from aether_api.repository import Repository
    from aether_api.services.ai.client import AIClient

logger = logging.getLogger(__name__)

_INTEREST_LABELS: dict[str, str] = {
    "history": "历史人文",
    "architecture": "古厝建筑",
    "food": "美食小吃",
    "photo": "拍照打卡",
    "culture": "非遗文化",
    "nature": "自然景观",
    "literature": "文学故事",
    "family": "亲子互动",
    "shopping": "文创购物",
    "night": "夜游体验",
}

_PACE_LABELS: dict[str, str] = {
    "relaxed": "轻松休闲（少走路、多休息）",
    "moderate": "适中（正常步行节奏）",
    "active": "活跃（愿意多走多看）",
}

_GROUP_LABELS: dict[str, str] = {
    "solo": "独自游览",
    "couple": "情侣/两人",
    "family": "家庭（有小孩）",
    "friends": "朋友结伴",
    "elder": "长者出行",
}

_GENDER_LABELS: dict[str, str] = {
    "male": "男性",
    "female": "女性",
    "unspecified": "未指定",
}

_AGE_LABELS: dict[str, str] = {
    "kids": "12岁以下儿童",
    "12-17": "青少年（12-17岁）",
    "18-35": "青年（18-35岁）",
    "36-55": "中年（36-55岁）",
    "55+": "长者（55岁以上）",
}


class RoutePlanner:
    def __init__(self, repository: Repository) -> None:
        self._repository = repository

    async def recommend(
        self,
        profile: RouteRequest,
        ai_client: AIClient | None = None,
    ) -> RouteRecommendationDTO:
        landmarks = await self._repository.list_landmarks(profile.scenic_id)

        if not landmarks:
            return RouteRecommendationDTO(
                scenic_id=profile.scenic_id,
                total_walk_minutes=0,
                intro="暂无可用景点数据。",
                stops=[],
            )

        if ai_client is None:
            return self._fallback_route(profile, landmarks)

        # Filter: keep only landmarks whose tags overlap with user interests.
        interest_set = set(profile.interests)
        scored = [
            (
                len(interest_set & {t.lower() for t in (lm.tags or [])}),
                lm,
            )
            for lm in landmarks
        ]
        # Sort by tag overlap (desc), then keep top 25 + always-include core landmarks.
        scored.sort(key=lambda x: x[0], reverse=True)
        core_ids = {"nanhou-street", "linjuemin-bingxin", "yanfu-former-residence"}
        selected = [lm for _, lm in scored if lm.id in core_ids or _ > 0]
        # Pad with top-scoring landmarks if too few.
        if len(selected) < 5:
            selected = [lm for _, lm in scored[:15]]
        # Hard cap at 15 to keep the prompt small and fast.
        selected = selected[:15]
        landmark_catalog = [
            {
                "id": lm.id,
                "name": lm.name,
                "summary": lm.summary,
                "tags": lm.tags or [],
                "avg_duration_min": lm.avg_duration_min or 15,
            }
            for lm in selected
        ]

        prompt = self._build_prompt(profile, landmark_catalog)
        try:
            from aether_api.services.ai.client import AIRequest

            response = await ai_client.generate_reply(
                AIRequest(
                    session_id="route-planner",
                    scenic_id=profile.scenic_id,
                    prompt=prompt,
                    locale="zh-CN",
                    system_prompt=(
                        "你是三坊七巷的路线规划专家。根据游客的个人资料和景点信息，"
                        "生成一条个性化的游览路线。只输出 JSON，不要输出其他内容。"
                    ),
                )
            )
            parsed = self._parse_response(response.content, landmarks)
            total_walk = sum(s.walk_minutes_from_previous for s in parsed)
            total_dur = sum(s.duration_min for s in parsed)
            return RouteRecommendationDTO(
                scenic_id=profile.scenic_id,
                total_walk_minutes=total_walk,
                total_duration_min=total_dur,
                intro=self._build_intro(profile, len(parsed)),
                stops=parsed,
            )
        except Exception:
            logger.exception("AI route generation failed, using fallback")
            return self._fallback_route(profile, landmarks)

    def _build_prompt(self, profile: RouteRequest, catalog: list[dict]) -> str:
        interests_str = "、".join(
            _INTEREST_LABELS.get(i, i) for i in profile.interests
        )
        return (
            f"请为以下游客规划一条三坊七巷游览路线，输出严格 JSON 格式：\n\n"
            f"游客信息：\n"
            f"- 性别：{_GENDER_LABELS.get(profile.gender, profile.gender)}\n"
            f"- 年龄段：{_AGE_LABELS.get(profile.age_range, profile.age_range)}\n"
            f"- 兴趣偏好：{interests_str}\n"
            f"- 游览节奏：{_PACE_LABELS.get(profile.pace, profile.pace)}\n"
            f"- 同行类型：{_GROUP_LABELS.get(profile.group_type, profile.group_type)}\n"
            f"- 计划时长：约 {profile.duration_minutes} 分钟\n\n"
            f"可选景点（必须从中选择，使用对应的 id）：\n"
            + "\n".join(
                f"- {lm['id']} | {lm['name']} | {','.join(lm['tags'][:3])} | ~{lm['avg_duration_min']}min"
                for lm in catalog
            )
            + "\n\n"
            "规划要求：\n"
            "1. 根据游客偏好筛选 3-6 个合适的景点\n"
            "2. 按步行动线合理排列，标注每段步行时间（分钟）\n"
            "3. 总时长尽量接近游客计划的时长\n"
            "4. 考虑游客的年龄和节奏来调整步行距离和景点数量\n"
            "5. 给每个站点写一句个性化推荐理由\n"
            "6. 全家出游多选亲子友好景点和休息点，长者减少步行和台阶\n\n"
            '请输出 JSON（不要markdown代码块标记）：\n'
            '{"stops":[{"landmark_id":"...","name":"...","walk_minutes_from_previous":0,"reason":"...","duration_min":20,"highlight":"一句话亮点"},...]}'
        )

    def _parse_response(
        self, content: str, landmarks: list
    ) -> list[RouteStopDTO]:
        landmark_by_id = {lm.id: lm for lm in landmarks}
        # Strip markdown code fences if the model included them.
        clean = content.strip()
        clean = re.sub(r"^```(?:json)?\s*", "", clean)
        clean = re.sub(r"\s*```$", "", clean)
        try:
            data = _json.loads(clean)
        except _json.JSONDecodeError:
            # Try to find a JSON object anywhere in the text.
            match = re.search(r"\{[\s\S]*\}", clean)
            if match:
                try:
                    data = _json.loads(match.group())
                except _json.JSONDecodeError:
                    return []
            else:
                return []

        stops_data = data.get("stops", [])
        if not isinstance(stops_data, list):
            return []

        stops: list[RouteStopDTO] = []
        for stop in stops_data:
            lid = stop.get("landmark_id", "")
            lm = landmark_by_id.get(lid)
            if lm is None:
                continue
            stops.append(
                RouteStopDTO(
                    landmark_id=lid,
                    name=lm.name,
                    walk_minutes_from_previous=max(0, int(stop.get("walk_minutes_from_previous", 0))),
                    reason=str(stop.get("reason", lm.summary)),
                    duration_min=max(5, int(stop.get("duration_min", lm.avg_duration_min or 15))),
                    highlight=str(stop.get("highlight", "")),
                )
            )
        return stops

    def _build_intro(self, profile: RouteRequest, stop_count: int) -> str:
        pace_text = _PACE_LABELS.get(profile.pace, "适中节奏")
        group_text = _GROUP_LABELS.get(profile.group_type, "游客")
        duration = profile.duration_minutes
        return (
            f"为{group_text}设计了一条约 {duration} 分钟的{pace_text}路线，"
            f"共 {stop_count} 站，兼顾步行距离和游览体验。"
        )

    def _fallback_route(
        self, profile: RouteRequest, landmarks: list
    ) -> RouteRecommendationDTO:
        preferred = [
            "nanhou-street",
            "linjuemin-bingxin",
            "yanfu-former-residence",
            "xiaohuanglou",
            "shuixie-stage",
        ]
        landmark_by_id = {lm.id: lm for lm in landmarks}
        stops: list[RouteStopDTO] = []
        for idx, lid in enumerate(preferred):
            lm = landmark_by_id.get(lid)
            if lm is None:
                continue
            stops.append(
                RouteStopDTO(
                    landmark_id=lid,
                    name=lm.name,
                    walk_minutes_from_previous=0 if idx == 0 else 8,
                    reason=_fallback_reason(lid),
                    duration_min=lm.avg_duration_min or 15,
                )
            )
        total_walk = sum(s.walk_minutes_from_previous for s in stops)
        total_dur = sum(s.duration_min for s in stops)
        return RouteRecommendationDTO(
            scenic_id=profile.scenic_id,
            total_walk_minutes=total_walk,
            total_duration_min=total_dur,
            intro="（离线模式）为你推荐的经典路线：",
            stops=stops,
        )


def _fallback_reason(lid: str) -> str:
    reasons = {
        "nanhou-street": "先在中轴步行街建立方位感，顺便补给小吃和饮水。",
        "linjuemin-bingxin": "用《与妻书》和冰心文学记忆打开名人故居线。",
        "yanfu-former-residence": "承接近代思想与教育主题。",
        "xiaohuanglou": "从人物故事转入古厝建筑，观察马鞍墙和天井。",
        "shuixie-stage": "以非遗演艺和夜游体验收束路线。",
    }
    return reasons.get(lid, "经典步行路线推荐站点。")
