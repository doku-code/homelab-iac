#!/usr/bin/env python3
"""Offline tests for the Charcoal Titanium design system (TASK-039): one source of tokens, generated copies that
match it, adapters that only touch appearance, and a preview that asks the network for nothing."""
import colorsys
import importlib.util
import json
import re
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
THEME = ROOT / "services/_shared/theme"


def rgb(value):
    return tuple(int(value[i:i + 2], 16) for i in (1, 3, 5))


def luminance(value):
    channels = [c / 255 for c in rgb(value)]
    linear = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in channels]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


def contrast(a, b):
    high, low = sorted((luminance(a), luminance(b)), reverse=True)
    return (high + 0.05) / (low + 0.05)


def main():
    tokens = json.loads((THEME / "tokens.json").read_text())
    color = tokens["color"]

    # The palette of the brief, and nothing blue in the chrome: every surface, line and text colour is neutral or
    # slightly warm (red >= blue) and barely saturated. States and data series are the only colours.
    assert (color["canvas"], color["surface"], color["fg"], color["action"], color["action-fg"]) == ("#10100F", "#1B1B19", "#EDECE9", "#E6E5E1", "#10100F")
    chrome = [k for k in color if k not in ("success", "warning", "error")]
    for name in chrome:
        r, g, b = rgb(color[name])
        assert r >= b and colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)[1] <= 0.08, f"{name} {color[name]} is not a neutral, warm tone"
    # Text can be read: body text on every surface, the dark label on the off-white button, muted text on the page.
    for surface in ("canvas", "sidebar", "surface", "surface-elevated", "surface-hover", "surface-active"):
        assert contrast(color["fg"], color[surface]) >= 7, surface
        assert contrast(color["fg-secondary"], color[surface]) >= 4.5, surface
    assert contrast(color["action-fg"], color["action"]) >= 7 and contrast(color["fg-muted"], color["surface"]) >= 4.5
    assert all(contrast(color[state], color["surface"]) >= 4.5 for state in ("success", "warning", "error"))
    # The data series can be told apart: no two share a hue.
    hues = sorted(colorsys.rgb_to_hsv(*[c / 255 for c in rgb(v)])[0] * 360 for k, v in tokens["series"].items() if k != "5")
    assert all(b - a >= 20 for a, b in zip(hues, hues[1:])), hues
    assert tokens["radius"] == {"sm": "4px", "md": "6px", "lg": "8px", "dialog": "12px"}
    assert all(int(v[:-2]) % 4 == 0 for v in tokens["space"].values()), "spacing on a 4 px scale"
    assert 120 <= int(tokens["motion"]["duration"][:-2]) <= 180
    assert "http" not in json.dumps(tokens["font"]), "no font is fetched from anywhere"
    assert (THEME / "fonts/Geist-Variable.woff2").read_bytes()[:4] == b"wOF2" and "SIL Open Font License" in (THEME / "fonts/Geist-OFL.txt").read_text()

    # One source: every generated copy is what scripts/theme.py writes from tokens.json today.
    check = subprocess.run([sys.executable, str(ROOT / "scripts/theme.py"), "--check"], capture_output=True, text=True)
    assert check.returncode == 0, check.stderr
    css = (THEME / "tokens.css").read_text()
    assert all(f"--ct-{name}: {value};" in css for name, value in color.items())

    # Adapters take their colours from the tokens: outside the generated block, no colour is written by hand
    # (Forgejo's theme needs literal values for its ramp steps and transparencies, all of them neutral).
    loader = importlib.util.spec_from_file_location("theme", ROOT / "scripts/theme.py")
    generator = importlib.util.module_from_spec(loader)
    loader.loader.exec_module(generator)
    assert len(generator.ADAPTERS) == 5 and all((ROOT / name).exists() for name in generator.ADAPTERS)
    for name in generator.ADAPTERS:
        text = (ROOT / name).read_text()
        own = text.split("/* tokens:end */", 1)[1]
        # Gradients are the tokens of the group "pattern" (backdrop, metal, panel sheen), used by name; Homepage alone
        # writes one more: the light under the cursor (operator, 2026-11-27 and 28). No blur, no glow.
        assert own.count("gradient(") == ("homepage" in name) and "backdrop-filter: blur" not in own and "text-shadow" not in own, name
        assert not re.search(r"https?://", re.sub(r"/\*.*?\*/", "", text, flags=re.S)), f"{name}: no request to another site"
        literals = re.findall(r"#[0-9a-fA-F]{6}(?:[0-9a-fA-F]{2})?\b", own)
        if "forgejo" in name:
            for value in literals:
                r, g, b = rgb(value[:7])
                assert r >= b and max(r, g, b) - min(r, g, b) <= 12, f"{name}: {value} is not neutral"
        else:
            assert not literals and "rgba(" not in own, f"{name}: colours come from the tokens, found {literals[:3]}"

    # Homepage: the selectors custom.js relies on are still styled, and the page has no image unless a visitor picks one.
    homepage = (ROOT / "services/homepage/config/custom.css").read_text()
    script = (ROOT / "services/homepage/config/custom.js").read_text()
    styled = set(re.findall(r"\.(nith-[a-z-]+)", homepage))
    assert len(styled) >= 40, "the widgets' rules are all still there"
    for cls in styled:
        assert cls in script, f"custom.css styles .{cls}, which custom.js never creates"
    for attribute in ("data-nith-card", "data-nith-state", "data-remote-state", "data-healthy", "data-online"):
        assert attribute in homepage and attribute.replace("data-", "") in script.replace("-", "").lower() or attribute in script, attribute
    settings = yaml.safe_load((ROOT / "services/homepage/config/settings.yaml").read_text())
    assert "background" not in settings and settings["theme"] == "dark" and settings["color"] == "neutral"
    assert "ackground" not in script and "#background" not in homepage and "prefers-reduced-motion" in homepage, "no background image, no switcher"
    assert 'font-family: "Geist";' in homepage and "data:font/woff2;base64," in homepage and "--mx" in script, "the typeface ships with the page"

    # Authentik: appearance of the default brand only. The stylesheet sets variables on the document and on
    # components' own roots; it never reaches into a component, and the blueprint names no flow, policy or provider.
    brand = yaml.safe_load((ROOT / "services/authentik/blueprints/homelab-brand.yaml").read_text())
    (entry,) = brand["entries"]
    assert entry["model"] == "authentik_brands.brand" and entry["identifiers"] == {"domain": "authentik-default"} and entry["state"] == "present"
    assert set(entry["attrs"]) == {"attributes", "branding_custom_css"} and entry["attrs"]["attributes"] == {"settings": {"theme": {"base": "dark"}}}
    authentik = re.sub(r"/\*.*?\*/", "", (ROOT / "services/authentik/theme.css").read_text(), flags=re.S)
    selectors = {s.strip() for block in re.findall(r"([^{}]+)\{", authentik) for s in block.split(",")} - {"@media (prefers-reduced-motion: reduce)"}
    # Variables on the document and on components' roots, then rules on PatternFly's own classes only: nothing is
    # hidden, moved or given content, so no step of a sign-in can disappear behind the theme.
    allowed = re.compile(r"^(:root|:host|html|body|html\[data-theme=\"dark\"\]|:host\(\[theme=\"dark\"\]\)|a:focus-visible|(\.pf-c-[a-z_-]+)(\.pf-m-[a-z]+)?( \.pf-c-[a-z_-]+)?(:hover|:focus|:focus-visible|::after|::placeholder)?)$")
    assert all(allowed.match(s) for s in selectors), sorted(s for s in selectors if not allowed.match(s))
    for forbidden in ("display:", "visibility", "content:", "position:", "pointer-events", "opacity", "url(", "@import"):
        assert forbidden not in authentik, f"Authentik's theme must not use {forbidden}"
    assert authentik.count("!important") <= 6, "important only where Authentik sets the same thing later"
    assert entry["attrs"]["branding_custom_css"].count("--pf-c-button--m-primary--BackgroundColor: var(--ct-action);") == 1

    # Argo CD: the chart's own setting for a custom stylesheet; health and sync colours are not mentioned.
    values = yaml.safe_load((ROOT / "services/argocd/values.yaml").read_text())
    styles = values["configs"]["styles"]
    assert ".sidebar" in styles and "--ct-canvas: #10100F;" in styles and "ui.cssurl" not in values["configs"].get("cm", {}), "the chart sets ui.cssurl itself"
    assert not re.search(r"health|sync-status|degraded|progressing|out-of-sync", re.sub(r"/\*.*?\*/", "", styles, flags=re.S), re.I)

    # Forgejo: only variables the installed version's dark theme defines (or the font hook of its base stylesheet).
    upstream = set((ROOT / "services/forgejo/forgejo-17.0.1-dark-variables.txt").read_text().split())
    forgejo = (ROOT / "services/forgejo/theme-charcoal-titanium.css").read_text()
    assert '@import "./theme-forgejo-dark.css";' in forgejo
    ours = set(re.findall(r"^  (--(?!ct-)[a-z0-9-]+):", forgejo.split("/* tokens:end */", 1)[1], re.M))
    assert ours - upstream == {"--fonts-override"} and len(ours) >= 50, sorted(ours - upstream)
    assert not re.search(r"--color-(diff|red|green|syntax|console|ansi)", forgejo.split("/* tokens:end */", 1)[1]), "diff, state and syntax colours stay Forgejo's"

    # AdGuard Home: its own dark mode, a setting of its configuration file.
    assert re.search(r"^theme: dark$", (ROOT / "ansible/roles/adguard_home/templates/AdGuardHome.yaml.j2").read_text(), re.M)

    # The preview is one local file: the tokens, no script, nothing fetched.
    preview = (THEME / "preview/index.html").read_text()
    assert '<link rel="stylesheet" href="../tokens.css">' in preview and "<script" not in preview
    assert not re.findall(r'(?:src|href)="https?://', preview) and "@import" not in preview and "url(http" not in preview
    assert not re.findall(r"#[0-9a-fA-F]{6}\b", re.sub(r"url\(\"data:[^)]*\)", "", preview.split("<style>")[1].split("</style>")[0])), "the preview's colours are the tokens"
    for part in ('class="side"', "<table>", "btn primary", "btn second", "btn ghost", "btn danger", 'type="checkbox"', "<select>", 'class="toggle',
                 'role="dialog"', 'role="menu"', "note warn", 'class="cards"', "<svg", "<pre>", 'class="auth"', "prefers-reduced-motion", ":focus-visible"):
        assert part in preview, f"the preview shows no {part}"

    print("PASS: one source of tokens and generated copies that match it; neutral warm chrome with readable contrast; adapters without hand-written "
          "colours or requests to other sites; Homepage's widget selectors kept; Authentik and Argo CD through their own settings; Forgejo within "
          "the installed version's variables; a self-contained preview")


if __name__ == "__main__":
    main()
