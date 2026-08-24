"""Regression tests for the external Spectral runtime."""

import subprocess
import textwrap
from pathlib import Path


def test_null_example_does_not_crash_spectral():
    """duplicated-entry-in-enum must not dereference enum on null nodes."""

    ruleset = (
        Path(__file__).parent
        / "resources"
        / "github-cache"
        / "tags"
        / "ruleset-v1.1.0"
        / "spectral"
        / "sdx"
        / "ruleset.yaml"
    )
    openapi_content = textwrap.dedent("""\
        openapi: 3.0.3
        info:
          title: Nullable example regression
          version: 1.0.0
        paths:
          /widgets:
            get:
              operationId: listWidgets
              responses:
                '200':
                  description: Widget list
                  content:
                    application/json:
                      example:
                        nextCursor: null
        """)

    result = subprocess.run(
        ["spectral", "lint", "--ruleset", str(ruleset), "-"],
        input=openapi_content,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )

    assert result.returncode != 2, result.stderr
