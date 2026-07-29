"""Unit tests that do not require an API key."""

from robin_igris.tools import calculator, remember_note, recall_notes, run_tool


def test_calculator_basic():
    assert calculator("2 + 3 * 4") == "14.0"


def test_calculator_sqrt():
    assert calculator("sqrt(144)") == "12.0"


def test_calculator_bad():
    assert calculator("__import__('os')").startswith("Error")


def test_notes_roundtrip():
    remember_note.notes.clear()  # type: ignore[attr-defined]
    run_tool("remember_note", {"note": "ship it"})
    out = recall_notes()
    assert "ship it" in out


def test_unknown_tool():
    assert "Unknown tool" in run_tool("nope", {})
