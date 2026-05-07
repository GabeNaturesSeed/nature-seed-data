import json
from pathlib import Path


def load_checkpoint(path: Path) -> set[int]:
    if not path.exists():
        return set()
    data = json.loads(path.read_text())
    return set(data["completed_batches"])


def save_checkpoint(path: Path, completed: set[int]) -> None:
    path.write_text(json.dumps({"completed_batches": sorted(completed)}))
