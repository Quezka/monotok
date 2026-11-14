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

- **Claude Code plugin (everywhere):**

  ```
  /plugin install monotok --marketplace Quezka/monotok
  ```

  On older Claude Code: `/plugin marketplace add Quezka/monotok`, then
  `/plugin install monotok@monotok`. A `SessionStart` hook loads `AGENTS.md` at the
  start of every session and again after `/clear` or compaction.
- **One repo:** copy `AGENTS.md` to the repo root. Codex, Cursor, Copilot, Gemini CLI,
  opencode and others read it. `CLAUDE.md` here imports it for Claude Code.
- **Everywhere, without the plugin:** add `@/path/to/monotok/AGENTS.md` to `~/.claude/CLAUDE.md`.
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

## Track

`tools/track.py` measures what Monotok saves in real Claude Code sessions.

```
python3 tools/track.py              # by mode, then by day
python3 tools/track.py --days 7 --by session
python3 tools/track.py files ~/Documents/Repos/quire   # comments + agent docs in a repo
```

- Reads transcripts from `~/.claude/projects/**/*.jsonl` and keeps one line per reply in
  `~/.local/share/monotok/history.jsonl`, so history survives Claude Code's 30-day cleanup.
  A `SessionEnd` hook running `track.py update` keeps it current.
- `out` and `think` are exact, from the API usage of each reply. `text` is the visible
  reply, counted with `o200k_base` (Claude's tokenizer is not public).
- Each reply is classified as `monotok`, `prose`, `wenyan` or `short`. Monotok replies
  are mostly alphabet glyphs (>= 50%) and have almost no articles or pronouns (< 5%).
- `saved~` is an estimate: Monotok text tokens x `ratio / (1 - ratio)`, with `ratio`
  (default 0.48) taken from the `examples/` totals. Change it with `--ratio`.
- `files` counts comment lines in code and agent-only docs, and estimates what
  rewriting the prose ones would save on every agent read.
- Thinking tokens are not controlled by `AGENTS.md`; they are shown separately.

Needs `tiktoken` (`pip3 install --target ~/.local/share/monotok/pylib tiktoken` works
without root; the script looks there).

## License

MIT
