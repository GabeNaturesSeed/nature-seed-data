import os
import tempfile
from feeds.env_loader import load_env

def test_load_env_parses_spaces_and_quotes():
    content = "WC_CK = 'ck_abc123'\nWC_CS = \"cs_def456\"\n"
    with tempfile.NamedTemporaryFile(mode='w', suffix='.env', delete=False) as f:
        f.write(content)
        path = f.name
    env = load_env(path)
    assert env['WC_CK'] == 'ck_abc123'
    assert env['WC_CS'] == 'cs_def456'

def test_load_env_ignores_comments_and_blanks():
    content = "# comment\n\nFOO = 'bar'\n"
    with tempfile.NamedTemporaryFile(mode='w', suffix='.env', delete=False) as f:
        f.write(content)
        path = f.name
    env = load_env(path)
    assert 'FOO' in env
    assert len(env) == 1
