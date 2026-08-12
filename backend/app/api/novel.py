"""小说生成相关 API 路由。"""

import asyncio
import json

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from app.config import settings
from app.schemas.novel import (
    ChapterReviewRequest,
    ChapterReviewResponse,
    CharacterCardsGenerateRequest,
    CharacterCardsGenerateResponse,
    ChapterGenerateRequest,
    ChapterGenerateResponse,
    NovelGenerateRequest,
    NovelGenerateResponse,
    RetrieveResponse,
    ReviewIssue,
    TitlesGenerateRequest,
    TitlesGenerateResponse,
)
from app.services.character_card_service import CharacterCardService
from app.services.chapter_service import ChapterService
from app.services.title_service import TitleService
from app.services.review_service import review_chapter
from app.services.knowledge_compress import default_categories
from app.services.novel_service import NovelService, novel_retrieval_query
from app.rag.retriever import get_retriever

router = APIRouter(prefix="/api/novel", tags=["novel"])

# 业务编排服务（模块级单例）
novel_service = NovelService()
chapter_service = ChapterService()
character_card_service = CharacterCardService()
title_service = TitleService()
# RAG 检索器（进程级单例，与生成服务保持一致）
_retriever = get_retriever()


@router.post("/generate", response_model=NovelGenerateResponse)
async def generate_novel(request: NovelGenerateRequest) -> NovelGenerateResponse:
    """根据用户创意需求，检索知识库并调用 DeepSeek 生成小说大纲。"""
    return await novel_service.generate(request)


@router.post("/retrieve", response_model=RetrieveResponse)
async def retrieve_context(request: NovelGenerateRequest) -> RetrieveResponse:
    """按板块读取并压缩知识库参考原文（用于调试 / 验证知识库）。"""
    context = await asyncio.to_thread(
        _retriever.retrieve,
        novel_retrieval_query(request),
        default_categories(),
    )
    return RetrieveResponse(context=context)


@router.post("/chapter/generate", response_model=ChapterGenerateResponse)
async def generate_chapter(
    request: ChapterGenerateRequest,
) -> ChapterGenerateResponse:
    """根据大纲生成章节正文；支持首次生成、以编辑后内容续写、从修改处重写。"""
    return await chapter_service.generate(request)


@router.post("/chapter/stream")
async def stream_chapter(request: ChapterGenerateRequest) -> StreamingResponse:
    """流式生成章节正文（SSE）；旧的非流式接口保持不变。"""

    async def event_source():
        async for event in chapter_service.generate_stream(request):
            yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"

    return StreamingResponse(event_source(), media_type="text/event-stream")


@router.post("/chapter/review", response_model=ChapterReviewResponse)
async def review_chapter_endpoint(
    request: ChapterReviewRequest,
) -> ChapterReviewResponse:
    """审校章节（一致性/爽点/错字/设定冲突），默认关闭。"""
    if not settings.review_enabled:
        return ChapterReviewResponse(
            success=False,
            status="disabled",
            message="审校功能未开启（设置 REVIEW_ENABLED=true 后重启生效）。",
        )
    if not request.chapter_text.strip():
        return ChapterReviewResponse(
            success=False,
            status="error",
            message="正文为空，无法审校。",
        )
    if not chapter_service.llm.available:
        return ChapterReviewResponse(
            success=True,
            status="demo",
            message="未配置 DEEPSEEK_API_KEY，跳过审校。",
        )
    issues = await review_chapter(
        chapter_service.llm,
        request.outline,
        request.chapter_title,
        request.chapter_text,
        request.memory,
    )
    return ChapterReviewResponse(
        success=True,
        status="success",
        issues=[
            ReviewIssue(
                type=str(item.get("type", "")),
                severity=str(item.get("severity", "")),
                description=str(item.get("description", "")),
                suggestion=str(item.get("suggestion", "")),
            )
            for item in issues
        ],
    )


@router.post("/character-cards/generate", response_model=CharacterCardsGenerateResponse)
async def generate_character_cards(
    request: CharacterCardsGenerateRequest,
) -> CharacterCardsGenerateResponse:
    """根据大纲与指定卷生成该卷主要人物的角色卡。"""
    return await character_card_service.generate(request)


@router.post("/titles/generate", response_model=TitlesGenerateResponse)
async def generate_titles(
    request: TitlesGenerateRequest,
) -> TitlesGenerateResponse:
    """生成章节标题：volume=按卷生成前10章标题 / chapter=根据正文生成单章标题。"""
    return await title_service.generate(request)
