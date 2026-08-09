"""角色卡数据模型。

角色卡用于精确定义某个角色在某一卷中的设定，
章节生成时会注入 Prompt，保证角色言行不偏离定义。
"""

from pydantic import BaseModel, Field


class CharacterCard(BaseModel):
    """单张角色卡。"""

    volume_index: int = Field(default=0, description="所属卷索引（0 起）")
    name: str = Field(default="", description="角色名")
    role: str = Field(default="", description="角色定位（按剧情实际需要，不预设类型）")
    age: str = Field(default="", description="年龄或年龄段")
    appearance: str = Field(default="", description="外貌特征")
    personality: str = Field(default="", description="性格与行为习惯")
    background: str = Field(default="", description="身世背景")
    goals: str = Field(default="", description="目标与动机")
    speech_style: str = Field(default="", description="说话风格与口头禅")
    notes: str = Field(default="", description="备注：与其他角色的关系、成长线等")
