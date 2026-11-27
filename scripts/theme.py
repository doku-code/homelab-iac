#!/usr/bin/env python3
"""Charcoal Titanium: writes every form of the shared design tokens from services/_shared/theme/tokens.json.

  scripts/theme.py          rewrite the generated files
  scripts/theme.py --check  fail when a generated file differs from what this script writes (tests, CI)

Generated:
  services/_shared/theme/tokens.css    the tokens as CSS custom properties (the preview links it)
  the block between "tokens:start" and "tokens:end" at the top of each adapter stylesheet
  the typeface (Geist, SIL Open Font License) between "font:start" and "font:end" where a stylesheet must carry it
  the stylesheet embedded in a deployment file where an application only takes CSS as a setting

An adapter is the application's own stylesheet: it maps the application's native variables to the tokens. It lives
beside the application's deployment files (Kustomize cannot read outside its directory), so the tokens are copied
into it by this script instead of being imported at run time. Standard library only.
"""
import base64
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
THEME = ROOT / "services/_shared/theme"
START, END = "/* tokens:start (written by scripts/theme.py from services/_shared/theme/tokens.json) */", "/* tokens:end */"

# Stylesheets that carry a copy of the tokens.
ADAPTERS = [
    "services/homepage/config/custom.css",
    "services/authentik/theme.css",
    "services/argocd/theme.css",
    "services/forgejo/theme-charcoal-titanium.css",
]
# Stylesheets that carry the typeface itself, where the application serves no file of ours: (stylesheet, font file, family).
FONT_START, FONT_END = "/* font:start (written by scripts/theme.py from services/_shared/theme/fonts) */", "/* font:end */"
FONTS = [("services/homepage/config/custom.css", "fonts/Geist-Variable.woff2", "Geist")]
# Deployment files that carry a whole stylesheet as a setting: (file, stylesheet, start marker, end marker, indent).
EMBEDDED = [
    ("services/authentik/blueprints/homelab-brand.yaml", "services/authentik/theme.css", "        /* theme:start (scripts/theme.py) */", "        /* theme:end */", 8),
    ("services/argocd/values.yaml", "services/argocd/theme.css", "    /* theme:start (scripts/theme.py) */", "    /* theme:end */", 4),
]


def tokens():
    return json.loads((THEME / "tokens.json").read_text())


def properties(data):
    """(name, value) of every custom property, in the file's order."""
    rows = []
    for group in ("color", "series", "radius", "space", "font", "pattern", "motion"):
        for key, value in data[group].items():
            name = {"color": f"--ct-{key}", "series": f"--ct-series-{key}", "radius": f"--ct-radius-{key}", "space": f"--ct-space-{key}",
                    "font": f"--ct-font-{key}", "pattern": f"--ct-{key}", "motion": f"--ct-motion-{key}"}[group]
            rows.append((name, value))
    return rows


def block(data, selector=":root"):
    lines = [START, f"{selector} {{"] + [f"  {name}: {value};" for name, value in properties(data)] + ["}", END]
    return "\n".join(lines)


def tokens_css(data):
    return (f"/* {data['name']}: the shared design tokens as CSS custom properties.\n"
            "   Written by scripts/theme.py from tokens.json; do not edit. */\n" + block(data) + "\n")


def with_block(text, data, path):
    if START not in text or END not in text:
        sys.exit(f"{path}: no tokens block (a line '{START}' and a line '{END}')")
    selector = re.search(re.escape(START) + r"\n(.+?) \{", text)
    head, rest = text.split(START, 1)
    return head + block(data, selector.group(1) if selector else ":root") + rest.split(END, 1)[1]


def embedded(text, css, start, end, indent, path):
    if start not in text or end not in text:
        sys.exit(f"{path}: no '{start.strip()}' / '{end.strip()}' markers")
    head, rest = text.split(start, 1)
    body = "\n".join((" " * indent + line) if line else "" for line in css.rstrip("\n").split("\n"))
    return head + start + "\n" + body + "\n" + end + rest.split(end, 1)[1]


def with_font(text, font, family, path):
    if FONT_START not in text or FONT_END not in text:
        sys.exit(f"{path}: no font block (a line '{FONT_START}' and a line '{FONT_END}')")
    data = base64.b64encode((THEME / font).read_bytes()).decode()
    face = (f"@font-face {{\n  font-family: \"{family}\";\n  font-weight: 100 900;\n  font-style: normal;\n  font-display: swap;\n"
            f"  src: url(\"data:font/woff2;base64,{data}\") format(\"woff2\");\n}}")
    head, rest = text.split(FONT_START, 1)
    return head + FONT_START + "\n" + face + "\n" + FONT_END + rest.split(FONT_END, 1)[1]


def outputs():
    data = tokens()
    result = {THEME / "tokens.css": tokens_css(data)}
    for name in ADAPTERS:
        path = ROOT / name
        result[path] = with_block(path.read_text(), data, name)
    for name, font, family in FONTS:
        result[ROOT / name] = with_font(result[ROOT / name], font, family, name)
    for name, source, start, end, indent in EMBEDDED:
        path = ROOT / name
        result[path] = embedded(path.read_text(), result[ROOT / source], start, end, indent, name)
    return result


def main():
    stale = []
    for path, text in outputs().items():
        if "--check" in sys.argv:
            if not path.exists() or path.read_text() != text:
                stale.append(str(path.relative_to(ROOT)))
        elif not path.exists() or path.read_text() != text:
            path.write_text(text)
            print(f"written: {path.relative_to(ROOT)}")
    if stale:
        sys.exit("stale theme files, run scripts/theme.py: " + ", ".join(stale))


if __name__ == "__main__":
    main()
