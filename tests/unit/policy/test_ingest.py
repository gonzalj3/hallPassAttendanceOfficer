import pytest

from hpao.policy import chunk_text


class TestChunkText:
    def test_empty_input_yields_no_chunks(self) -> None:
        assert chunk_text("") == []

    def test_whitespace_only_input_yields_no_chunks(self) -> None:
        assert chunk_text("   \n\n   \n\n   ") == []

    def test_single_paragraph_returned_intact(self) -> None:
        para = "A student must attend at least 90% of the days the course is offered."
        assert chunk_text(para) == [para]

    def test_paragraph_boundaries_are_preserved(self) -> None:
        text = "First paragraph.\n\nSecond paragraph.\n\nThird paragraph."
        assert chunk_text(text) == ["First paragraph.", "Second paragraph.", "Third paragraph."]

    def test_long_paragraph_is_window_split(self) -> None:
        para = "x" * 3000
        chunks = chunk_text(para, max_chars=1000)
        assert len(chunks) == 3
        assert all(len(c) == 1000 for c in chunks)
        assert "".join(chunks) == para

    def test_invalid_max_chars_rejected(self) -> None:
        with pytest.raises(ValueError, match="positive"):
            chunk_text("anything", max_chars=0)

    def test_strips_surrounding_whitespace_per_paragraph(self) -> None:
        text = "  hello  \n\n  world  "
        assert chunk_text(text) == ["hello", "world"]
