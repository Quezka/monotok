#!/usr/bin/env python3
"""Check the Monotok alphabet and measure token savings.

    python3 tools/count.py --check      every glyph must be 1 token
    python3 tools/count.py              compare examples/*.plain.txt with *.monotok.txt

Needs `pip install tiktoken`. Claude's tokenizer is not public, so the
counts use OpenAI's cl100k_base and o200k_base as a stand-in.
"""
import pathlib
import re
import sys

import tiktoken

ROOT = pathlib.Path(__file__).resolve().parent.parent
ENCODINGS = ["cl100k_base", "o200k_base"]


def alphabet():
    text = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
    block = re.search(r"```monotok-alphabet\n(.*?)```", text, re.S)
    if not block:
        sys.exit("AGENTS.md: no monotok-alphabet block")
    return [line.split("\t", 1)[0] for line in block.group(1).splitlines() if line.strip()]


def check():
    glyphs = alphabet()
    bad = []
    for name in ENCODINGS:
        enc = tiktoken.get_encoding(name)
        for g in glyphs:
            # A glyph appears both at line start and after a space.
            for form in (g, " " + g):
                n = len(enc.encode(form))
                if n != 1:
                    bad.append(f"{name}: {form!r} = {n} tokens")
    for g in sorted({g for g in glyphs if glyphs.count(g) > 1}):
        bad.append(f"duplicate glyph {g!r}")
    for line in bad:
        print(line)
    print(f"{len(glyphs)} glyphs, {len(bad)} problems")
    return 1 if bad else 0


def pct(x, y):
    return f"{x}->{y} (-{round(100 * (x - y) / x)}%)"


def compare():
    encs = [tiktoken.get_encoding(n) for n in ENCODINGS]
    totals = [[0, 0] for _ in encs]
    for plain in sorted((ROOT / "examples").glob("*.plain.txt")):
        mono = plain.with_name(plain.name.replace(".plain.", ".monotok."))
        a, b = plain.read_text(encoding="utf-8"), mono.read_text(encoding="utf-8")
        cells = []
        for i, enc in enumerate(encs):
            x, y = len(enc.encode(a)), len(enc.encode(b))
            totals[i][0] += x
            totals[i][1] += y
            cells.append(f"{ENCODINGS[i]} {pct(x, y)}")
        print(f"{plain.name.split('.')[0]:<8} " + "  ".join(cells))
    print("total    " + "  ".join(f"{ENCODINGS[i]} {pct(x, y)}" for i, (x, y) in enumerate(totals)))
    return 0


if __name__ == "__main__":
    sys.exit(check() if "--check" in sys.argv else compare())
