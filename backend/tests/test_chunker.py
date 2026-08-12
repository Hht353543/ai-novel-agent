"""知识分块器测试。"""

from app.rag.chunker import chunk_text


def test_short_text_single_chunk():
    assert chunk_text("short", 100) == ["short"]


def test_empty_text():
    assert chunk_text("", 100) == []


def test_paragraph_packing_with_overlap():
    p1 = "A" * 200
    p2 = "B" * 200
    p3 = "C" * 200
    p4 = "D" * 200
    chunks = chunk_text("\n\n".join([p1, p2, p3, p4]), 500, overlap=200)
    assert all(len(c) <= 500 for c in chunks)
    assert chunks[0].startswith("A")
    assert chunks[-1].endswith("D")
    assert chunks[1].startswith(chunks[0][-200:])
    assert chunks[2].startswith(chunks[1][-200:])


def test_hard_split_covers_all_chars():
    huge = "X" * 500
    pieces = chunk_text(huge, 200, overlap=50)
    expected_starts = []
    start = 0
    while True:
        expected_starts.append(start)
        if start + 200 >= 500:
            break
        start += 150
    assert len(pieces) == len(expected_starts)
    for piece, s in zip(pieces, expected_starts):
        assert piece == huge[s : s + 200]
