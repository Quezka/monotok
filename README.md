# Monotok

An alphabet for AI agents in which **every glyph costs exactly one token**.
Drop `AGENTS.md` into a repo (or import it globally) and the agent writes only in Monotok:
chat replies, code comments, and docs that only agents read.

Output tokens are paid once. Comments and agent docs are paid again every time an
agent reads the file, so compressing them saves tokens on every future session.
Human-facing text (README, changelog, commits, PRs, UI strings) stays normal.

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
| chat: bugfix  | 81 | 36 | 56% |
| chat: deps    | 73 | 33 | 55% |
| chat: status  | 75 | 41 | 45% |
| code comment  | 52 | 30 | 42% |
| agent doc     | 59 | 38 | 36% |
| total         | 340 | 178 | 48% |

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
