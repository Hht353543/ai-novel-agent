"""模型 JSON 容错解析测试。"""

import pytest

from app.llm.json_parser import parse_json_array_response, parse_json_response


def test_parse_json_response_direct():
    assert parse_json_response('{"a":1}') == {"a": 1}


def test_parse_json_response_fenced():
    assert parse_json_response('```json\n{"a":1}\n```') == {"a": 1}


def test_parse_json_response_prefix_suffix():
    assert parse_json_response('说明 {"a":1} 结尾') == {"a": 1}


def test_parse_json_response_loose_quotes():
    assert parse_json_response("{'a':'1'}") == {"a": "1"}


def test_parse_json_response_trailing_comma():
    assert parse_json_response('{"a":1,}') == {"a": 1}


def test_parse_json_response_truncated():
    assert parse_json_response('{"a":"x","b":["1","2"') == {
        "a": "x",
        "b": ["1", "2"],
    }


def test_parse_json_response_invalid_raises():
    with pytest.raises(ValueError):
        parse_json_response("hello")


def test_parse_json_array_top_level():
    assert parse_json_array_response('["t1","t2"]') == ["t1", "t2"]


def test_parse_json_array_object_titles():
    assert parse_json_array_response('{"titles":["a","b"]}') == ["a", "b"]


def test_parse_json_array_single_title():
    assert parse_json_array_response('{"title":"abc"}') == ["abc"]


def test_parse_json_array_fenced():
    assert parse_json_array_response('```json\n["a"]\n```') == ["a"]


def test_parse_json_array_invalid_raises():
    with pytest.raises(ValueError):
        parse_json_array_response("nope")
