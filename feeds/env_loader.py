from pathlib import Path

def load_env(path=None):
    if path is None:
        path = Path(__file__).resolve().parent.parent / ".env"
    env = {}
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#') or '=' not in line:
                continue
            k, v = line.split('=', 1)
            env[k.strip()] = v.strip().strip("'\"")
    return env
