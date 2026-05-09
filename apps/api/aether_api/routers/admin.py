# SCORE-IMPACT: Admin knowledge operations, A/B prompts, and analytics.
from fastapi import APIRouter

from aether_api.dependencies import RepositoryDep
from aether_api.schemas.admin import (
    DashboardOverviewDTO,
    DocumentDTO,
    IndexProgressDTO,
    PersonaDTO,
    PersonaRequest,
    PromptExperimentDTO,
    PromptExperimentRequest,
    SessionReplayDTO,
    TurnLabelDTO,
    TurnLabelRequest,
    UploadDocumentRequest,
)
from aether_api.schemas.common import BaseResponse
from aether_api.tracing import current_trace_id

router = APIRouter(tags=["admin"])


@router.post("/documents", response_model=BaseResponse[DocumentDTO])
async def upload_document(
    payload: UploadDocumentRequest,
    repository: RepositoryDep,
) -> BaseResponse[DocumentDTO]:
    document = await repository.create_document(
        scenic_id=payload.scenic_id,
        title=payload.title,
        source_uri=payload.source_uri,
        version=payload.version,
    )
    return BaseResponse(data=document, trace_id=current_trace_id())


@router.get("/documents/{document_id}/progress", response_model=BaseResponse[IndexProgressDTO])
async def document_progress(
    document_id: str,
    repository: RepositoryDep,
) -> BaseResponse[IndexProgressDTO]:
    progress = await repository.document_progress(document_id)
    return BaseResponse(data=progress, trace_id=current_trace_id())


@router.post("/personas", response_model=BaseResponse[PersonaDTO])
async def upsert_persona(
    payload: PersonaRequest,
    repository: RepositoryDep,
) -> BaseResponse[PersonaDTO]:
    persona = await repository.upsert_persona(
        scenic_id=payload.scenic_id,
        name=payload.name,
        voice_id=payload.voice_id,
        avatar_id=payload.avatar_id,
        version=payload.version,
        status=payload.status,
    )
    return BaseResponse(data=persona, trace_id=current_trace_id())


@router.post("/prompts/experiments", response_model=BaseResponse[PromptExperimentDTO])
async def create_prompt_experiment(
    payload: PromptExperimentRequest,
    repository: RepositoryDep,
) -> BaseResponse[PromptExperimentDTO]:
    experiment = await repository.create_prompt_experiment(
        name=payload.name,
        traffic_split=payload.traffic_split,
        metric=payload.metric,
    )
    return BaseResponse(data=experiment, trace_id=current_trace_id())


@router.get("/dashboard/overview", response_model=BaseResponse[DashboardOverviewDTO])
async def dashboard_overview(repository: RepositoryDep) -> BaseResponse[DashboardOverviewDTO]:
    overview = await repository.dashboard_overview()
    return BaseResponse(data=overview, trace_id=current_trace_id())


@router.get("/sessions/{session_id}/replay", response_model=BaseResponse[SessionReplayDTO])
async def session_replay(
    session_id: str,
    repository: RepositoryDep,
) -> BaseResponse[SessionReplayDTO]:
    replay = await repository.session_replay(session_id)
    return BaseResponse(data=replay, trace_id=current_trace_id())


@router.post("/turns/{turn_id}/label", response_model=BaseResponse[TurnLabelDTO])
async def label_turn(
    turn_id: str,
    _payload: TurnLabelRequest,
    repository: RepositoryDep,
) -> BaseResponse[TurnLabelDTO]:
    label = await repository.label_turn(turn_id)
    return BaseResponse(data=label, trace_id=current_trace_id())

