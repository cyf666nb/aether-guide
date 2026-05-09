# SCORE-IMPACT: First runnable tourist loop and multimodal API surface.
from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect

from aether_api.auth.dependencies import authenticate_websocket, require_role
from aether_api.dependencies import AIClientDep, RepositoryDep
from aether_api.schemas.common import BaseResponse
from aether_api.schemas.feedback import FeedbackDTO, FeedbackRequest
from aether_api.schemas.landmarks import LandmarkListDTO
from aether_api.schemas.sessions import (
    AssistantMessage,
    CreateSessionRequest,
    PhotoSceneRequest,
    PhotoSceneResponse,
    SessionDTO,
    StreamMessage,
)
from aether_api.services.ai.client import AIRequest
from aether_api.services.location.vps import VisualPositioningService
from aether_api.tracing import current_trace_id, new_trace_id, set_trace_id

router = APIRouter(tags=["tourist"])
_tourist_dep = [Depends(require_role("tourist"))]


@router.post(
    "/sessions",
    response_model=BaseResponse[SessionDTO],
    dependencies=_tourist_dep,
)
async def create_session(
    payload: CreateSessionRequest,
    repository: RepositoryDep,
) -> BaseResponse[SessionDTO]:
    session = await repository.create_session(
        scenic_id=payload.scenic_id,
        user_id=payload.user_id,
        persona_id=payload.persona_id,
    )
    return BaseResponse(data=session, trace_id=current_trace_id())


@router.post(
    "/sessions/{session_id}/photo",
    response_model=BaseResponse[PhotoSceneResponse],
    dependencies=_tourist_dep,
)
async def identify_photo(
    session_id: str,
    payload: PhotoSceneRequest,
    repository: RepositoryDep,
) -> BaseResponse[PhotoSceneResponse]:
    await repository.get_session(session_id)
    service = VisualPositioningService(repository)
    result = await service.locate_by_photo(
        scenic_id=payload.scenic_id,
        image_base64=payload.image_base64,
        gps_hint=payload.gps_hint,
    )
    landmark_name = None
    if result.landmark_id:
        landmarks = await repository.list_landmarks(payload.scenic_id)
        landmark_name = next(
            (landmark.name for landmark in landmarks if landmark.id == result.landmark_id),
            None,
        )
    response = PhotoSceneResponse(
        status=result.status,
        landmark_id=result.landmark_id,
        landmark_name=landmark_name,
        confidence=result.confidence,
        narration="This is a demo VPS identification result.",
        follow_up=result.follow_up,
    )
    return BaseResponse(data=response, trace_id=current_trace_id())


@router.get(
    "/landmarks",
    response_model=BaseResponse[LandmarkListDTO],
    dependencies=_tourist_dep,
)
async def list_landmarks(
    scenic_id: str,
    repository: RepositoryDep,
) -> BaseResponse[LandmarkListDTO]:
    landmarks = await repository.list_landmarks(scenic_id)
    return BaseResponse(
        data=LandmarkListDTO(scenic_id=scenic_id, landmarks=landmarks),
        trace_id=current_trace_id(),
    )


@router.post(
    "/feedback",
    response_model=BaseResponse[FeedbackDTO],
    dependencies=_tourist_dep,
)
async def submit_feedback(
    payload: FeedbackRequest,
    repository: RepositoryDep,
) -> BaseResponse[FeedbackDTO]:
    feedback = await repository.save_feedback(payload)
    return BaseResponse(data=feedback, trace_id=current_trace_id())


# WebSocket: can't use HTTP Depends for auth — browsers don't send Authorization
# on the upgrade handshake. Validate the JWT from `?token=` instead.
@router.websocket("/sessions/{session_id}/stream")
async def stream_session(
    websocket: WebSocket,
    session_id: str,
    repository: RepositoryDep,
    ai_client: AIClientDep,
) -> None:
    principal = await authenticate_websocket(websocket, required_role="tourist")
    if principal is None:
        return
    await websocket.accept()
    session = await repository.get_session(session_id)
    try:
        while True:
            set_trace_id(new_trace_id())
            raw_message = await websocket.receive_json()
            message = StreamMessage.model_validate(raw_message)
            ai_response = await ai_client.generate_reply(
                AIRequest(
                    session_id=session.id,
                    scenic_id=session.scenic_id,
                    prompt=message.text,
                    locale=message.locale,
                )
            )
            assistant = AssistantMessage(
                session_id=session.id,
                content=ai_response.content,
                citations=ai_response.citations,
                cost_usd=ai_response.cost_usd,
                cache_hit=ai_response.cache_hit,
            )
            await websocket.send_json(
                {
                    "trace_id": current_trace_id(),
                    "data": assistant.model_dump(mode="json"),
                    "code": "OK",
                    "message": "ok",
                }
            )
    except WebSocketDisconnect:
        return
