import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
TEMPLATES = sorted(
    p
    for katalog in ("flexible_reports", "demo")
    for p in (ROOT / katalog).rglob("templates/**/*.html")
)


@pytest.mark.parametrize("path", TEMPLATES, ids=lambda p: str(p.relative_to(ROOT)))
def test_comments_are_single_line(path):
    # ``{# ... #}`` is single-line only: after a newline Django stops treating
    # it as a comment and the text leaks into the rendered page. Multi-line
    # comments need ``{% comment %}``.
    for number, line in enumerate(path.read_text().splitlines(), start=1):
        for opening in re.finditer(r"\{#", line):
            assert "#}" in line[opening.end() :], (
                f"{path.name}:{number}: unterminated {{# comment"
            )


def test_templates_found():
    assert any(p.name == "change_form_with_clone.html" for p in TEMPLATES)
