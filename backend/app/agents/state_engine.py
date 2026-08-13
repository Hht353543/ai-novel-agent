"""人物状态更新引擎：规则化应用 CharacterStateDelta（纯函数，可单测）。"""

from app.agents.protocol import CharacterState, CharacterStateDelta, StateChange

SCALAR_FIELDS = {
    "current_location",
    "current_faction",
    "current_identity",
    "cultivation",
    "plot_status",
}
LIST_FIELDS = {"possessions", "known_info", "relationships"}


def _split_list(value: str) -> list[str]:
    return [
        part.strip()
        for part in value.replace("，", ",").replace("、", ",").split(",")
        if part.strip()
    ]


def _apply_change(state: CharacterState, change: StateChange) -> None:
    field = change.field
    if field in SCALAR_FIELDS:
        if change.action != "set":
            raise ValueError(f"标量字段 {field} 只支持 set 操作")
        setattr(state, field, change.new)
        return
    if field in LIST_FIELDS:
        current = list(getattr(state, field))
        if change.action == "set":
            setattr(state, field, _split_list(change.new))
        elif change.action == "add":
            for item in _split_list(change.new):
                if item not in current:
                    current.append(item)
            setattr(state, field, current)
        elif change.action == "remove":
            remove = set(_split_list(change.new))
            setattr(state, field, [i for i in current if i not in remove])
        else:
            raise ValueError(f"未知列表操作: {change.action}")
        return
    raise ValueError(f"未知状态字段: {field}")


def apply_character_state_deltas(
    states: list[CharacterState],
    deltas: list[CharacterStateDelta],
) -> list[CharacterState]:
    """把增量应用到人物状态列表，返回深拷贝后的新列表。"""
    result = [s.copy(deep=True) for s in states]
    index = {s.name: i for i, s in enumerate(result)}
    for delta in deltas:
        idx = index.get(delta.character)
        if idx is None:
            result.append(CharacterState(name=delta.character))
            index[delta.character] = len(result) - 1
            idx = index[delta.character]
        state = result[idx]
        for change in delta.changes:
            _apply_change(state, change)
    return result
