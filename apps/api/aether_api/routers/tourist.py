# SCORE-IMPACT: First runnable tourist loop and multimodal API surface.
from fastapi import APIRouter, Depends, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import Response

from aether_api.auth.dependencies import authenticate_websocket, require_role
from aether_api.dependencies import AIClientDep, EmbeddingDep, RepositoryDep, VectorStoreDep
from aether_api.errors import AppError, ErrorCode
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
from aether_api.services.ai.client import AIContextChunk, AIRequest
from aether_api.services.common.image import validate_image_base64
from aether_api.services.location.vps import VisualPositioningService
from aether_api.services.rag.retriever import RAGRetriever
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
    request: Request,
    session_id: str,
    payload: PhotoSceneRequest,
    repository: RepositoryDep,
) -> BaseResponse[PhotoSceneResponse]:
    validate_image_base64(payload.image_base64)
    await repository.get_session(session_id)
    settings = request.app.state.settings
    service = VisualPositioningService(repository, settings=settings)
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
    narration = result.follow_up or "已识别到景点"
    response = PhotoSceneResponse(
        status=result.status,
        landmark_id=result.landmark_id,
        landmark_name=landmark_name,
        confidence=result.confidence,
        narration=narration,
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


@router.post(
    "/tts",
    dependencies=_tourist_dep,
)
async def text_to_speech(
    request: Request,
) -> Response:
    body = await request.json()
    text = body.get("text", "")
    if not text:
        raise AppError(ErrorCode.bad_request, "text is required", status_code=400)

    settings = request.app.state.settings
    from aether_api.services.tts.client import TTSClient

    tts = TTSClient(settings)
    audio = await tts.synthesize(text)
    if audio is None:
        raise AppError(
            ErrorCode.ai_provider_unavailable,
            "TTS synthesis failed",
            status_code=503,
        )
    return Response(content=audio, media_type="audio/wav")


# WebSocket: can't use HTTP Depends for auth — browsers don't send Authorization
# on the upgrade handshake. Validate the JWT from `?token=` instead.
@router.websocket("/sessions/{session_id}/stream")
async def stream_session(
    websocket: WebSocket,
    session_id: str,
    repository: RepositoryDep,
    ai_client: AIClientDep,
    vectorstore: VectorStoreDep,
    embedding: EmbeddingDep,
) -> None:
    principal = await authenticate_websocket(websocket, required_role="tourist")
    if principal is None:
        return
    # Echo back the accepted subprotocol so the handshake completes per RFC 6455
    # when the client used Sec-WebSocket-Protocol: bearer.<jwt>.
    accepted = getattr(websocket.state, "accepted_subprotocol", None)
    await websocket.accept(subprotocol=accepted) if accepted else await websocket.accept()
    session = await repository.get_session(session_id)
    persona_prompt: str | None = None
    try:
        persona = await repository.get_persona(session.persona_id)
        persona_prompt = persona.system_prompt
    except AppError as exc:
        if exc.code != ErrorCode.not_found:
            raise
    try:
        while True:
            set_trace_id(new_trace_id())
            raw_message = await websocket.receive_json()
            message = StreamMessage.model_validate(raw_message)
            retrieved = await RAGRetriever(
                repository,
                vectorstore=vectorstore,
                embedding=embedding,
            ).retrieve(
                message.text,
                session.scenic_id,
            )
            ai_request = AIRequest(
                session_id=session.id,
                scenic_id=session.scenic_id,
                prompt=message.text,
                locale=message.locale,
                system_prompt=persona_prompt,
                context=[
                    AIContextChunk(
                        source_id=chunk.source_id,
                        text=chunk.text,
                        score=chunk.score,
                    )
                    for chunk in retrieved
                ],
            )
            full_content = ""
            async for token in ai_client.generate_reply_stream(ai_request):
                full_content += token
                await websocket.send_json(
                    {
                        "type": "stream_chunk",
                        "data": {"content": token},
                    }
                )
            assistant = AssistantMessage(
                session_id=session.id,
                content=full_content,
                citations=[chunk.source_id for chunk in retrieved] or ["seed:intro"],
                cost_usd=0.0,
                cache_hit=False,
            )
            await websocket.send_json(
                {
                    "type": "stream_end",
                    "trace_id": current_trace_id(),
                    "data": assistant.model_dump(mode="json"),
                    "code": "OK",
                    "message": "ok",
                }
            )
    except WebSocketDisconnect:
        return
