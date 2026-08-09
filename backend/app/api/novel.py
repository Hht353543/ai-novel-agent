"""小说生成相关 API 路由。"""

import asyncio

from fastapi import APIRouter

from app.schemas.novel import (
    CharacterCardsGenerateRequest,
    CharacterCardsGenerateResponse,
    ChapterGenerateRequest,
    ChapterGenerateResponse,
    NovelGenerateRequest,
    NovelGenerateResponse,
    RetrieveResponse,
    TitlesGenerateRequest,
    TitlesGenerateResponse,
)
from app.services.character_card_service import CharacterCardService
from app.services.chapter_service import ChapterService
from app.services.novel_service import NovelService
from app.services.title_service import TitleService
from app.services.knowledge_compress import (
    default_categories,
    load_compressed_category_context,
)

router = APIRouter(prefix="/api/novel", tags=["novel"])

# 业务编排服务（模块级单例）
novel_service = NovelService()
chapter_service = ChapterService()
character_card_service = CharacterCardService()
title_service = TitleService()


@router.post("/generate", response_model=NovelGenerateResponse)
async def generate_novel(request: NovelGenerateRequest) -> NovelGenerateResponse:
    """根据用户创意需求，检索知识库并调用 DeepSeek 生成小说大纲。"""
    return await novel_service.generate(request)


@router.post("/retrieve", response_model=RetrieveResponse)
async def retrieve_context(request: NovelGenerateRequest) -> RetrieveResponse:
    """按板块读取并压缩知识库参考原文（用于调试 / 验证知识库）。"""
    context = await asyncio.to_thread(
        load_compressed_category_context,
        default_categories(),
    )
    return RetrieveResponse(context=context)


@router.post("/chapter/generate", response_model=ChapterGenerateResponse)
async def generate_chapter(
    request: ChapterGenerateRequest,
) -> ChapterGenerateResponse:
    """根据大纲生成章节正文；支持首次生成、以编辑后内容续写、从修改处重写。"""
    return await chapter_service.generate(request)


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
