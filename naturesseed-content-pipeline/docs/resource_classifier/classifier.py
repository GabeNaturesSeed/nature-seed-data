import json
import subprocess

from docs.resource_classifier.prompt import build_prompt


class ClassifierError(Exception):
    pass


def parse_response(raw: str) -> list[dict]:
    text = raw.strip()
    # Strip markdown fences if claude wraps output
    if text.startswith("```"):
        lines = text.splitlines()
        text = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        raise ClassifierError(f"JSON parse failed: {e}\nRaw: {raw[:200]}") from e
    if not isinstance(data, list):
        raise ClassifierError(f"Expected JSON array, got {type(data).__name__}: {raw[:200]}")
    return data


def call_claude(batch: list[dict], timeout: int = 120) -> list[dict]:
    prompt = build_prompt(batch)
    result = subprocess.run(
        ["claude", "-p", prompt, "--output-format", "json"],
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    if result.returncode != 0:
        raise ClassifierError(f"claude exited {result.returncode}: {result.stderr[:300]}")
    # claude --output-format json wraps in {"type":"result","result":...} — unwrap if present
    raw = result.stdout.strip()
    try:
        wrapper = json.loads(raw)
        if isinstance(wrapper, dict) and "result" in wrapper:
            raw = wrapper["result"]
            if isinstance(raw, str):
                pass  # parse below
            elif isinstance(raw, list):
                return raw
    except json.JSONDecodeError:
        pass
    return parse_response(raw if isinstance(raw, str) else json.dumps(raw))
