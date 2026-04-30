# Token & Context Management Book — PARTY System

## Baseline Measurements (April 17, 2026)

| Config | Tokens | What's in it |
|--------|--------|-------------|
| Claude Code base (no flags) | 19,883 | System prompt + hooks + plugins + MCP + tools |
| Our optimized config | 12,355 | System prompt + 6 tools + AGENT.md |
| Per-turn cost (resume) | ~500 | Previous exchange history |
| Each tool definition | ~700-1000 | Tool name + schema + description |
| Our AGENT.md | ~688 | Agent instructions |

## Context Budget (sonnet[1m] = 1,000,000 tokens)

```
System prompt + tools:     12,355 tokens (1.2%)
Available for work:       987,645 tokens (98.8%)
Each conversation turn:      ~500 tokens
Max turns before limit:    ~1,975 turns
```

Context is NOT the problem for normal conversations. The problem is LARGE FILE READS.

## What Causes "Separator/chunk exceed limit" Errors

1. Agent reads a large file (HANDOFF.md = 20KB = ~5K tokens)
2. Agent reads multiple files in one turn (spec + plan + handoff = 60KB = ~15K tokens)
3. Tool output is huge (git diff, large API response, etc.)
4. Claude Code's auto-compaction fails because a single chunk is larger than the compaction target

## The Solution: Surgical Data Access

### Rule 1: Never read full files — use subagents
Instead of: "Read HANDOFF.md and tell me what to do"
Do: Dispatch a subagent with "Read HANDOFF.md, extract the Klaviyo section only, return 200 words max"

### Rule 2: Limit tool output size
In AGENT.md, instruct agents: "When reading files, use `head -50` or `grep` to get specific sections, not full file reads."

### Rule 3: One file per turn, summarize immediately
If an agent needs to read 3 files, it should read one, summarize the key points, then read the next.

### Rule 4: Subagents for research, main context for decisions
The main agent should only hold: the user's question + the agent's plan + key data points.
All file reading, API calls, and data gathering happen in subagents.

## Optimal CLI Configuration

```
npx @anthropic-ai/claude-code \
  --print \
  --output-format stream-json \
  --verbose \
  --permission-mode bypassPermissions \
  --disable-slash-commands \
  --exclude-dynamic-system-prompt-sections \
  --tools "Bash,Read,Write,Edit,Grep,Glob" \
  --max-turns 30 \
  --model "sonnet[1m]" \
  --effort high \
  --system-prompt-file AGENT.md \
  --name party-{slug} \
  -- "user prompt"
```

This gives:
- OAuth auth (free subscription)
- 1M context window
- 12K base context (leaves 988K for work)
- No skills/plugins bloat
- No MCP server connections
- No dynamic env/git/cwd injection
- Only 6 essential tools

## What NOT to do

- `--bare`: Breaks OAuth, requires API key (costs money)
- `--mcp-config {}`: Breaks auth on some versions
- `CLAUDE_CODE_SIMPLE=1`: Breaks OAuth
- `--append-system-prompt` with large text: Adds to base context permanently
- Reading 10+ files in one turn: Guaranteed context overflow

## Monitoring

The bridge emits `context_analytics` events:
- `init`: Shows tools/MCP/plugins loaded
- `turn`: Per-turn token breakdown (input/output/cache)
- `result`: Total cost, duration, model breakdown
- `rate_limit`: Window status and reset time

Watch for:
- `cache_create` > 50K on a single turn = agent read something huge
- `COMPACTED` flag = context was auto-compacted (history being lost)
- `input_tokens` growing rapidly across turns = accumulation problem
