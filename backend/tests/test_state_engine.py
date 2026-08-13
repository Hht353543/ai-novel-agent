"""人物状态增量应用引擎测试。"""

import pytest

from app.agents.protocol import (
    CharacterState,
    CharacterStateDelta,
    StateChange,
)
from app.agents.state_engine import apply_character_state_deltas


def _state(**kwargs):
    defaults = dict(name="沈惊堂", cultivation="锻体")
    defaults.update(kwargs)
    return CharacterState(**defaults)


def test_apply_scalar_set():
    states = [_state()]
    deltas = [
        CharacterStateDelta(
            character="沈惊堂",
            changes=[
                StateChange(field="cultivation", action="set", new="先天"),
                StateChange(field="current_location", action="set", new="泰岳"),
            ],
        )
    ]
    result = apply_character_state_deltas(states, deltas)
    assert result[0].cultivation == "先天"
    assert result[0].current_location == "泰岳"
    assert states[0].cultivation == "锻体"  # 原列表不被修改


def test_apply_list_add_remove_set():
    states = [_state(possessions=["朴刀"], relationships=["楚云萝"])]
    deltas = [
        CharacterStateDelta(
            character="沈惊堂",
            changes=[
                StateChange(field="possessions", action="add", new="玉佩, 令牌"),
                StateChange(field="relationships", action="remove", new="楚云萝"),
                StateChange(
                    field="known_info",
                    action="set",
                    new="武学熔炉、家族旧案",
                ),
            ],
        )
    ]
    result = apply_character_state_deltas(states, deltas)
    assert result[0].possessions == ["朴刀", "玉佩", "令牌"]
    assert result[0].relationships == []
    assert result[0].known_info == ["武学熔炉", "家族旧案"]


def test_apply_creates_state_for_unknown_character():
    result = apply_character_state_deltas(
        [],
        [
            CharacterStateDelta(
                character="新角色",
                changes=[StateChange(field="cultivation", action="set", new="后天")],
            )
        ],
    )
    assert len(result) == 1
    assert result[0].name == "新角色"
    assert result[0].cultivation == "后天"


def test_apply_unknown_field_raises():
    with pytest.raises(ValueError):
        apply_character_state_deltas(
            [_state()],
            [
                CharacterStateDelta(
                    character="沈惊堂",
                    changes=[StateChange(field="magic_power", action="set", new="x")],
                )
            ],
        )


def test_apply_scalar_add_raises():
    with pytest.raises(ValueError):
        apply_character_state_deltas(
            [_state()],
            [
                CharacterStateDelta(
                    character="沈惊堂",
                    changes=[
                        StateChange(field="cultivation", action="add", new="先天")
                    ],
                )
            ],
        )
