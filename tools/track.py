#!/usr/bin/env python3
"""
track token use + monotok economy

    python3 tools/track.py                  report: by mode, then by day
    python3 tools/track.py --days 7         report: last 7 days
    python3 tools/track.py --by session     report: by session
    python3 tools/track.py update           add new turns -> history; no out
    python3 tools/track.py files PATH       comments + agent docs @ PATH: tokens, mode

src: claude code transcripts @ `~/.claude/projects/**/*.jsonl`
history @ `~/.local/share/monotok/history.jsonl` <- transcripts rm after ~30 days
`out` + `think` = exact (api usage); `text` = tiktoken `o200k_base` (claude tokenizer = no public)
`saved` = estimate: text monotok * ratio / (1 - ratio); ratio <- `examples/` (`--ratio`)
"""
import argparse
import collections
import datetime as dt
import json
import os
import pathlib
import re
import subprocess
import sys

# tiktoken @ local lib if no system install
sys.path.insert(0, str(pathlib.Path.home() / ".local/share/monotok/pylib"))
try:
    import tiktoken
except ImportError:
    sys.exit("need tiktoken: pip3 install --target ~/.local/share/monotok/pylib tiktoken")

ROOT = pathlib.Path(__file__).resolve().parent.parent
PROJECTS = pathlib.Path.home() / ".claude/projects"
HISTORY = pathlib.Path(os.environ.get("MONOTOK_HISTORY",
                       pathlib.Path.home() / ".local/share/monotok/history.jsonl"))
ENC = tiktoken.get_encoding("o200k_base")
RATIO = 0.48  # <- `tools/count.py` total @ examples

# prose word = no glyph + banned by grammar rule 4 (articles, pronouns, filler)
PROSE = set("""the a an is are was were be been being i i'm i'll i've we we'll you're
it it's its this that these those there here will would should could can let let's
of to for and but so which what because however just really actually basically
sure please hope happy simply also very""".split())

FENCE = re.compile(r"```.*?```", re.S)
INLINE = re.compile(r"`[^`\n]*`")
# token = word | op glyph (`->` `=` `?` ...)
WORD = re.compile(r"[A-Za-z][A-Za-z']*|[-=<>!]+|[?~@#|;*+:]")
CJK = re.compile(r"[㐀-鿿豈-﫿]")


def alphabet():
    text = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
    block = re.search(r"```monotok-alphabet\n(.*?)```", text, re.S)
    return {l.split("\t", 1)[0] for l in block.group(1).splitlines() if l.strip()}


GLYPHS = alphabet()


def classify(text):
    """mode of text: monotok | prose | wenyan | short; + glyph share"""
    bare = INLINE.sub(" ", FENCE.sub(" ", text))
    solid = re.sub(r"\s", "", bare)
    if solid and len(CJK.findall(solid)) / len(solid) > 0.2:
        return "wenyan", 0.0
    words = [w.lower() for w in WORD.findall(bare)]
    if len(words) < 4:
        return "short", 0.0
    glyph = sum(w in GLYPHS for w in words) / len(words)
    prose = sum(w in PROSE for w in words) / len(words)
    # examples: monotok glyph >= `0.82`, prose `0`; plain glyph <= `0.27`, prose >= `0.28`
    # prose limit `0.05` <- rule 8 allow some english
    return ("monotok" if glyph >= 0.5 and prose < 0.05 else "prose"), glyph


def turns(path):
    """1 record per assistant message id; text = all text blocks"""
    msgs = collections.OrderedDict()
    try:
        lines = path.open(encoding="utf-8")
    except OSError:
        return []
    for line in lines:
        try:
            d = json.loads(line)
        except ValueError:
            continue
        if d.get("type") != "assistant":
            continue
        m = d.get("message") or {}
        mid = m.get("id")
        if not mid or m.get("model") == "<synthetic>":
            continue
        r = msgs.setdefault(mid, {"id": mid, "ts": d.get("timestamp", ""),
                                  "session": d.get("sessionId", path.stem),
                                  "project": path.parent.name, "model": m.get("model"),
                                  "sub": bool(d.get("isSidechain")), "text": []})
        for c in m.get("content") or []:
            if c.get("type") == "text":
                r["text"].append(c.get("text", ""))
        u = m.get("usage") or {}
        r["out"] = u.get("output_tokens", 0)
        r["think"] = (u.get("output_tokens_details") or {}).get("thinking_tokens", 0)
    out = []
    for r in msgs.values():
        text = "\n".join(r.pop("text"))
        r["text_tok"] = len(ENC.encode(text)) if text else 0
        r["mode"], r["glyph"] = classify(text) if text else ("tool", 0.0)
        r["glyph"] = round(r["glyph"], 3)
        out.append(r)
    return out


def update():
    """new turns -> history; ret count added"""
    seen = set()
    if HISTORY.exists():
        for line in HISTORY.open(encoding="utf-8"):
            try:
                seen.add(json.loads(line)["id"])
            except (ValueError, KeyError):
                pass
    new = []
    now = dt.datetime.now().timestamp()
    for path in sorted(PROJECTS.glob("**/*.jsonl")):
        rows = turns(path)
        # file write < `300 s` ago -> session live -> last message maybe partial; add later run
        if rows and now - path.stat().st_mtime < 300:
            rows = rows[:-1]
        new += [r for r in rows if r["id"] not in seen]
    if new:
        HISTORY.parent.mkdir(parents=True, exist_ok=True)
        with HISTORY.open("a", encoding="utf-8") as f:
            for r in sorted(new, key=lambda r: r["ts"]):
                seen.add(r["id"])
                f.write(json.dumps(r) + "\n")
    return len(new)


def load(days):
    since = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=days)).isoformat() if days else ""
    rows = []
    for line in HISTORY.open(encoding="utf-8"):
        r = json.loads(line)
        if r["ts"] >= since:
            rows.append(r)
    return rows


def table(head, rows):
    w = [max(len(str(x)) for x in col) for col in zip(head, *rows)]
    for row in [head] + rows:
        print("  ".join(str(x).rjust(n) if i else str(x).ljust(n) for i, (x, n) in enumerate(zip(row, w))))


def saved(rows, ratio):
    t = sum(r["text_tok"] for r in rows if r["mode"] == "monotok")
    return round(t * ratio / (1 - ratio))


def report(args):
    update()
    rows = load(args.days)
    if not rows:
        print("no turns")
        return 0
    replies = [r for r in rows if r["mode"] not in ("tool",)]

    print(f"## by mode  (o200k text; ratio {args.ratio})")
    groups = collections.defaultdict(list)
    for r in replies:
        groups[r["mode"]].append(r)
    table(["mode", "replies", "text", "avg/reply", "glyph%"],
          [[m, len(g), sum(r["text_tok"] for r in g), round(sum(r["text_tok"] for r in g) / len(g)),
            round(100 * sum(r["glyph"] for r in g) / len(g))]
           for m, g in sorted(groups.items(), key=lambda kv: -len(kv[1]))])

    print(f"\n## by {args.by}")
    key = {"day": lambda r: r["ts"][:10], "session": lambda r: r["session"][:8],
           "project": lambda r: r["project"][-28:]}[args.by]
    groups = collections.defaultdict(list)
    for r in rows:
        groups[key(r)].append(r)
    body = []
    for k, g in sorted(groups.items(), key=lambda kv: min(r["ts"] for r in kv[1])):
        rep = [r for r in g if r["mode"] != "tool"]
        mono = sum(r["mode"] == "monotok" for r in rep)
        talk = sum(r["mode"] in ("monotok", "prose", "wenyan") for r in rep)
        body.append([k, len(g), sum(r["out"] for r in g), sum(r["think"] for r in g),
                     sum(r["text_tok"] for r in rep),
                     f"{round(100 * mono / talk)}%" if talk else "-", saved(g, args.ratio)])
    table([args.by, "turns", "out", "think", "text", "monotok", "saved~"], body)

    out = sum(r["out"] for r in rows)
    think = sum(r["think"] for r in rows)
    print(f"\ntotal: out `{out}` (think `{think}`, rest `{out - think}`); "
          f"saved~ `{saved(rows, args.ratio)}` text tokens")
    return 0


CODE = {".py": "#", ".sh": "#", ".rb": "#", ".yml": "#", ".yaml": "#", ".toml": "#",
        ".js": "//", ".ts": "//", ".tsx": "//", ".jsx": "//", ".rs": "//", ".go": "//",
        ".c": "//", ".h": "//", ".cpp": "//", ".java": "//", ".kt": "//", ".dart": "//",
        ".swift": "//", ".cs": "//", ".gd": "#", ".lua": "--", ".sql": "--"}
AGENT_DOCS = re.compile(r"(^|/)(AGENTS|CLAUDE|GEMINI)\.md$|(^|/)\.cursor/rules/|(^|/)docs/agents/|(^|/)\.clinerules")


def comment_text(path, mark):
    """comment lines only; block comment `/* */` + `*` line = count too"""
    out = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        s = line.strip()
        if s.startswith(mark) and not s.startswith("#!"):
            out.append(s[len(mark):])
        elif mark == "//" and (s.startswith("/*") or s.startswith("* ") or s == "*"):
            out.append(s.lstrip("/*"))
    return "\n".join(out)


def files(args):
    base = pathlib.Path(args.path).resolve()
    try:
        names = subprocess.run(["git", "-C", str(base), "ls-files"], capture_output=True,
                               text=True, check=True).stdout.split("\n")
    except (subprocess.CalledProcessError, FileNotFoundError):
        names = [str(p.relative_to(base)) for p in base.rglob("*") if p.is_file()]
    rows = []
    for name in filter(None, names):
        p = base / name
        if not p.is_file():
            continue
        if AGENT_DOCS.search(name):
            kind, text = "doc", p.read_text(encoding="utf-8", errors="replace")
        elif p.suffix in CODE:
            kind, text = "comment", comment_text(p, CODE[p.suffix])
        else:
            continue
        if not text.strip():
            continue
        mode, glyph = classify(text)
        rows.append([name[-48:], kind, len(ENC.encode(text)), mode, f"{round(100 * glyph)}%"])
    if not rows:
        print("no comments | agent docs")
        return 0
    rows.sort(key=lambda r: -r[2])
    table(["file", "kind", "tokens", "mode", "glyph%"], rows[:args.top])
    prose = sum(r[2] for r in rows if r[3] == "prose")
    print(f"\ntotal: `{sum(r[2] for r in rows)}` tokens @ `{len(rows)}` files; "
          f"prose `{prose}` -> monotok saved~ `{round(prose * args.ratio)}` per agent read")
    return 0


def main():
    ap = argparse.ArgumentParser(description="track monotok token economy")
    ap.add_argument("cmd", nargs="?", default="report", choices=["report", "update", "files"])
    ap.add_argument("path", nargs="?", default=".")
    ap.add_argument("--days", type=int, default=0, help="only last N days (0 = all)")
    ap.add_argument("--by", choices=["day", "session", "project"], default="day")
    ap.add_argument("--ratio", type=float, default=RATIO, help="monotok saving vs prose")
    ap.add_argument("--top", type=int, default=25, help="files: rows to show")
    args = ap.parse_args()
    if args.cmd == "update":
        update()
        return 0
    return files(args) if args.cmd == "files" else report(args)


if __name__ == "__main__":
    sys.exit(main())
