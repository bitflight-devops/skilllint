from __future__ import annotations

from skilllint.cli_help import CompleteHelpFormatter


def test_complete_help_wraps_without_truncating() -> None:
    formatter = CompleteHelpFormatter(width=40)
    text = "This help sentence is deliberately long enough to wrap across multiple terminal-width lines."
    formatter.write_text(text)

    rendered = formatter.getvalue()
    assert text not in rendered
    assert "This help sentence is deliberately long" in rendered.replace("\n", " ")
    assert "terminal-" in rendered
    assert "width lines." in rendered
    assert "..." not in rendered
    assert all(len(line) <= 40 for line in rendered.splitlines())


def test_definition_list_wraps_help_without_losing_words() -> None:
    formatter = CompleteHelpFormatter(width=48)
    description = "Complete option documentation should wrap at terminal width and retain every authored word."
    formatter.write_dl([("--example-option", description)])

    rendered = formatter.getvalue()
    assert "Complete option" in rendered
    assert "documentation should wrap" in rendered
    assert "every authored word." in rendered
    assert "..." not in rendered
    assert all(len(line) <= 48 for line in rendered.splitlines())
