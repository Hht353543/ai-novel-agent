"""Writer Agent：根据上下文、人物状态与 RAG 生成章节正文。"""

import logging

from app.agents.base import AgentError, BaseAgent
from app.agents.context import AgentContext
from app.agents.protocol import ChapterResult, CharacterSystem, NovelPlan
from app.agents.prompts import build_writer_prompt
from app.schemas.novel import ChapterGenerateRequest
from app.services.chapter_service import (
    clean_chapter_output,
    demo_chapter,
    join_text,
)

logger = logging.getLogger(__name__)

SYSTEM_ROLE = (
    "你是一名拥有20年经验的网络小说白金作者，擅长在严格遵循设定与大纲的前提下"
    "写出节奏明快、人物不 OOC 的章节正文。"
)


def _writer_query(ctx: AgentContext) -> str:
    outline = ctx.chapter_outline
    return " ".join(
        part
        for part in [
            ctx.plan.title if ctx.plan else "",
            outline.title if outline else "",
            outline.goal if outline else "",
            ctx.extra_requirements,
        ]
        if part
    )


class WriterAgent(BaseAgent[ChapterResult]):
    """章节写作 Agent：输出章节正文。"""

    name = "writer"
    role = "章节写作 Agent"

    def validate_input(self, ctx: AgentContext) -> None:
        if ctx.plan is None:
            raise AgentError(
                self.name,
                "validate_input",
                "validation",
                "缺少小说规划",
                run_id=ctx.run_id,
            )

    def validate_output(self, ctx: AgentContext, result: ChapterResult) -> None:
        if not result.content.strip():
            raise AgentError(
                self.name,
                "validate_output",
                "validation",
                "章节正文为空",
                run_id=ctx.run_id,
            )

    async def _run(self, ctx: AgentContext) -> ChapterResult:
        if ctx.plan is None:
            raise AgentError(
                self.name,
                "_run",
                "validation",
                "缺少小说规划",
                run_id=ctx.run_id,
            )
        plan = ctx.plan
        if not self.llm.available:
            logger.warning("未配置 DEEPSEEK_API_KEY，Writer 返回演示正文")
            return self._demo(ctx, plan)
        context = await self._retrieve(ctx, _writer_query(ctx))
        ctx.retrieved_context = context
        arc = (
            plan.arcs[ctx.current_arc]
            if 0 <= ctx.current_arc < len(plan.arcs)
            else None
        )
        prompt = build_writer_prompt(
            plan=plan,
            arc=arc,
            chapter_outline=ctx.chapter_outline,
            characters=CharacterSystem(
                profiles=ctx.characters,
                states=ctx.character_states,
                relationships=ctx.relationships,
            ),
            memory=ctx.memory,
            context_text=ctx.context_text,
            previous_chapter_text=ctx.previous_chapter_text,
            rag_context=context,
            extra_requirements=ctx.extra_requirements,
            attachment_name=ctx.attachment_name,
            attachment_text=ctx.attachment_text,
            target_length=ctx.target_length,
            revision_instructions=ctx.revision_instructions,
            memory_facts=ctx.memory_facts,
            timeline=ctx.timeline,
            previous_draft=ctx.previous_draft,
            base_version=ctx.base_version,
        )
        raw = await self._llm_text(ctx, prompt, SYSTEM_ROLE)
        content = clean_chapter_output(raw)
        attempt = int(ctx.metadata.get("attempt", 1) or 1)
        return ChapterResult(
            attempt=attempt,
            base_version=ctx.base_version,
            content=content,
            full_text=join_text(ctx.context_text, content),
            memory=ctx.memory,
        )

    def _demo(self, ctx: AgentContext, plan: NovelPlan) -> ChapterResult:
        title = (
            ctx.chapter_outline.title
            if ctx.chapter_outline is not None
            else f"第{ctx.current_chapter + 1}章"
        )
        request = ChapterGenerateRequest(
            outline=plan.to_outline(),
            volume_index=ctx.current_arc,
            chapter_index=ctx.current_chapter,
            chapter_title=title,
            context_text=ctx.context_text,
            previous_chapter_text=ctx.previous_chapter_text,
            mode="generate",
            target_length=ctx.target_length,
            character_cards=[],
            extra_requirements=ctx.extra_requirements,
            attachment_name=ctx.attachment_name,
            attachment_text=ctx.attachment_text,
            memory=ctx.memory,
        )
        content = demo_chapter(request)
        attempt = int(ctx.metadata.get("attempt", 1) or 1)
        return ChapterResult(
            attempt=attempt,
            base_version=ctx.base_version,
            content=content,
            full_text=join_text(ctx.context_text, content),
            memory=ctx.memory,
        )
