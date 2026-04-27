"""LLM client that routes through the Claude Code CLI (`claude -p`)
instead of the Anthropic API.

Why: the user has a Claude Code Max subscription. Calls made via the CLI
use the logged-in OAuth session and bill against the Max plan, while
direct `anthropic.Anthropic()` calls bill against API credits separately.
For interactive ad-hoc inference inside an audit script, the CLI route
is far cheaper.

The class shape matches `anthropic.Anthropic` just enough that callers
which used `client.messages.create(...)` keep working without changes
to rules or tests.
"""

import shutil
import subprocess
from dataclasses import dataclass


@dataclass
class _CliResponseContent:
    text: str


@dataclass
class _CliResponse:
    content: list[_CliResponseContent]


class _CliMessages:
    def __init__(self, default_model: str | None = None, timeout: float = 180.0) -> None:
        self._default_model = default_model
        self._timeout = timeout

    def create(self, model: str | None = None, max_tokens: int | None = None,
               messages: list[dict] | None = None, **_ignored) -> _CliResponse:
        if not messages:
            raise ValueError("messages is required")
        # Concatenate every user/system content block into a single prompt.
        # Claude Code's `-p` mode accepts a single prompt string.
        parts: list[str] = []
        for m in messages:
            content = m.get("content", "")
            if isinstance(content, list):
                # anthropic-style content blocks
                content = "".join(b.get("text", "") for b in content
                                   if isinstance(b, dict) and b.get("type") == "text")
            parts.append(str(content))
        prompt = "\n\n".join(parts).strip()

        cmd = ["claude", "-p"]
        chosen_model = model or self._default_model
        if chosen_model:
            cmd.extend(["--model", chosen_model])

        result = subprocess.run(
            cmd, input=prompt,
            capture_output=True, text=True, timeout=self._timeout,
        )
        if result.returncode != 0:
            raise RuntimeError(
                f"claude CLI failed (exit {result.returncode}): "
                f"{result.stderr.strip()[:300]}"
            )
        return _CliResponse(content=[_CliResponseContent(text=result.stdout)])


class CliClaudeClient:
    """Drop-in replacement for `anthropic.Anthropic()` that routes through
    the Claude Code CLI. Only `client.messages.create(...)` is implemented —
    that is the only surface our audit rules use.

    Requires `claude` to be on PATH and the CLI to be logged in (`claude login`).
    """

    def __init__(self, default_model: str | None = None, timeout: float = 180.0) -> None:
        if shutil.which("claude") is None:
            raise RuntimeError(
                "`claude` CLI not found on PATH. Install Claude Code and run "
                "`claude login`, or set ANTHROPIC_API_KEY and use the API client."
            )
        self.messages = _CliMessages(default_model=default_model, timeout=timeout)
