# Monotok

An alphabet for AI agents in which **every glyph costs exactly one token**.
Drop `AGENTS.md` into a repo (or import it globally) and the agent replies only in Monotok.

```
test login = fail <- `auth.ts`@`42` use `<` | need `<=`
fix: `<` -> `<=`
next: run `npm test`
```

## Why not a brand-new script?

Tokenizers are trained on ordinary text. Symbols they rarely saw are split into
several byte tokens, so an invented alphabet costs *more*, not less:

| glyph | tokens (`o200k_base`) |
|-------|-----------------------|
| `->`, `=>`, `!=`, `fix`, `bug` | 1 |
| `∴`, `≠`, `✗` | 2 |
| `ꙮ` | 3 |

So Monotok keeps only units that are already one token: ASCII operators and short
lowercase English words. Meaning comes from a tight grammar (`subject op object`,
one fact per line), not from new characters.

## Savings

`python3 tools/count.py` on the pairs in `examples/`:

| example | plain | Monotok | saved |
|---------|-------|---------|-------|
| bugfix  | 81 | 36 | 56% |
| deps    | 73 | 33 | 55% |
| status  | 75 | 41 | 45% |
| total   | 229 | 110 | 52% |

Counts use `o200k_base`; `cl100k_base` gives the same picture. Claude's tokenizer
is not public, so its exact numbers may differ.

## Use

- **One repo:** copy `AGENTS.md` to the repo root. Codex, Cursor, Copilot, Gemini CLI,
  opencode and others read it. `CLAUDE.md` here imports it for Claude Code.
- **Everywhere (Claude Code):** add `@/path/to/monotok/AGENTS.md` to `~/.claude/CLAUDE.md`.
- **Turn off:** write `monotok off`.

Payload stays verbatim (code, paths, errors, numbers). Security warnings and
confirmations for irreversible actions are written in plain language.

## Check

```
pip install tiktoken
python3 tools/count.py --check   # every glyph is 1 token, no duplicates
python3 tools/count.py           # savings on examples/
```

CI runs both on every push. To add a glyph, add a line to the
`monotok-alphabet` block in `AGENTS.md` and run `--check`.

## License

MIT
