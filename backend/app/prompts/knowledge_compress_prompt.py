"""知识库原文压缩 Prompt 模板。

把长篇小说原文分块压缩成高密度摘要，让注入 Prompt 的预算内
能承载更多小说信息（人名、地名、势力、能力、事件线、伏笔）。
"""

from app.config import settings


SYSTEM_ROLE = """你是一名资深网络小说编辑，擅长把长篇原文压缩成高信息密度的要点摘要，只保留关键信息，不遗漏专有名词。"""


# 不同板块的压缩侧重
CATEGORY_COMPRESS_GUIDE = {
    "世界观": "重点保留：世界格局、力量/境界体系、地理地名、势力组织及其关系、时代背景。",
    "剧情大纲": "重点保留：完整事件线、章节推进、冲突与反转、爽点与悬念、伏笔、节奏结构。",
    "人物角色卡": "重点保留：人物姓名、身份、性格、外貌、背景、人物关系、成长变化、说话风格。",
    "other": "重点保留：所有专有名词与核心设定，去除重复与客套。",
}


def build_compress_prompt(
    category: str,
    chunk_index: int,
    chunk_total: int,
    chunk: str,
) -> str:
    """构建单个原文分块的压缩 Prompt。"""
    guide = CATEGORY_COMPRESS_GUIDE.get(
        category, CATEGORY_COMPRESS_GUIDE["other"]
    )
    target = settings.knowledge_compress_summary_max
    return f"""请把下面的小说原文压缩成一段高密度中文摘要。

## 板块
{category}

## 压缩侧重
{guide}

## 原文（第 {chunk_index + 1} 段，共 {chunk_total} 段）
{chunk}

## 输出要求
只输出一个合法的 JSON 对象，不要包含任何解释文字、不要使用代码块标记：
{{"summary": "压缩后的摘要"}}

## 要求
1. 摘要约 {target} 字，信息密度优先，宁要名词不要形容词；
2. 所有人物名、地名、势力名、功法/境界名必须原样保留，不得改写或省略；
3. 按时间/事件顺序压缩，保留关键转折与伏笔；
4. 忽略网站广告、重复章节标题、客套话与无关内容。"""
