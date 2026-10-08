"""Build sanitizer-safe title cards and inject them into dashboard JSON.

Grafana (with HTML sanitizing ON) strips <style>, <svg>, <script>, web-font links and most
positioning/animation CSS from text panels. It does keep:
  - inline styles for layout/colour (flex, gap, padding, margin, border, radius, shadows, backgrounds)
  - <img> and CSS background images with data:image/svg+xml URIs
SVG images run their own internal <style>/@keyframes/SMIL animations, so every animated or
font-dependent part of a card lives in an SVG, inlined here as a data URI. Variable text
(${host} etc.) must stay in the HTML, because Grafana does not interpolate inside images.

Card folder layout (title-cards/<name>/):
  card.json      {"dashboard": "dashboards/x.json", "panelId": 100}
  card.html      HTML using inline styles; {{SVG:<file>}} is replaced by a data URI of <file>.svg
  *.svg          may contain {{FONT:<Family>}} (base64 woff2) and {{KEYFRAMES}} (from timeline.json)
  timeline.json  optional bat/ghost keyframe tables

Usage:
  python title-cards/build_cards.py spooky            # rebuild card, update dashboard JSON
  python title-cards/build_cards.py spooky --push     # ...and save the dashboard to Grafana
"""
import argparse
import base64
import json
import re
import sys
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CARDS = ROOT / "title-cards"
FONT_CACHE = CARDS / ".fonts"  # gitignored; fonts are SIL OFL from Google Fonts
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36"


def font_b64(family):
    path = FONT_CACHE / f"{family}.woff2"
    if not path.exists():
        FONT_CACHE.mkdir(exist_ok=True)
        css_url = "https://fonts.googleapis.com/css2?family=" + urllib.parse.quote(family) + "&display=swap"
        css = urllib.request.urlopen(urllib.request.Request(css_url, headers={"User-Agent": UA})).read().decode()
        woff2 = re.findall(r"url\((https://fonts\.gstatic\.com/[^)]+\.woff2)\)", css)[-1]
        path.write_bytes(urllib.request.urlopen(woff2).read())
    return base64.b64encode(path.read_bytes()).decode()


def kf(name, rows):
    return "@keyframes %s{%s}" % (name, "".join("%s%%{%s}" % (t, v) for t, v in rows))


def timeline_keyframes(card_dir):
    path = card_dir / "timeline.json"
    if not path.exists():
        return ""
    tl = json.loads(path.read_text())
    out = []
    if "bat" in tl:
        keys = tl["bat"]["keys"]
        out.append(kf("batPath", [(k["t"], "transform:translate(%spx,%spx)" % (k["x"], k["y"])) for k in keys]))
        out.append(kf("batSpin", [(k["t"], "transform:scale(%s) rotate(%sdeg)" % (k["s"], k["deg"])) for k in keys]))
    if "ghost" in tl:
        keys = tl["ghost"]["keys"]
        out.append(kf("gPath", [(k["t"], "transform:translate(%spx,%spx)" % (k["x"], k["y"])) for k in keys]))
        out.append(kf("gSize", [(k["t"], "transform:scale(%s,%s)" % (k["s"], abs(k["s"]))) for k in keys]))
        out.append(kf("gFade", [(k["t"], "opacity:%s" % k["o"]) for k in keys]))
    return "\n    ".join(out)


def svg_data_uri(card_dir, name, keyframes):
    svg = (card_dir / f"{name}.svg").read_text(encoding="utf-8")
    svg = re.sub(r"<!--.*?-->", "", svg, flags=re.S)
    svg = re.sub(r"\{\{FONT:(\w+)\}\}", lambda m: font_b64(m.group(1)), svg)
    svg = svg.replace("{{KEYFRAMES}}", keyframes)
    svg = re.sub(r">\s+<", "><", svg).strip()
    svg = re.sub(r"\s{2,}", " ", svg)
    # Percent-encode everything risky in an HTML attribute or to Grafana's variable syntax ($, [, ]).
    return "data:image/svg+xml;charset=utf-8," + urllib.parse.quote(svg, safe=" /:;,=+()!*.-_~")


def build(name):
    card_dir = CARDS / name
    cfg = json.loads((card_dir / "card.json").read_text())
    keyframes = timeline_keyframes(card_dir)
    html = (card_dir / "card.html").read_text(encoding="utf-8")
    html = re.sub(r"\{\{SVG:(\w+)\}\}", lambda m: svg_data_uri(card_dir, m.group(1), keyframes), html)
    if re.search(r"<(style|svg|script|link|iframe)\b", html):
        sys.exit("card.html contains tags Grafana's sanitizer will strip")
    dash_path = ROOT / cfg["dashboard"]
    dash = json.loads(dash_path.read_text(encoding="utf-8"))
    panel = next(p for p in dash["panels"] if p["id"] == cfg["panelId"])
    panel["options"]["mode"] = "html"
    panel["options"]["content"] = html
    dash_path.write_text(json.dumps(dash, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    print(f"{name}: {len(html) // 1024} KB card -> {cfg['dashboard']} panel {cfg['panelId']}")
    return dash, cfg


def push(dash, cfg):
    conf = Path.home() / ".config" / "grafana" / "claude.yaml"
    text = conf.read_text()
    url = re.search(r"url:\s*(\S+)", text).group(1)
    token = re.search(r"token:\s*(\S+)", text).group(1)
    body = {"dashboard": dict(dash, id=None, version=None), "overwrite": True, "message": "title card rebuild"}
    if cfg.get("folderUid"):
        body["folderUid"] = cfg["folderUid"]
    req = urllib.request.Request(url.rstrip("/") + "/api/dashboards/db", data=json.dumps(body).encode(),
                                 headers={"Authorization": "Bearer " + token, "Content-Type": "application/json"})
    print(urllib.request.urlopen(req).read().decode())


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("card")
    ap.add_argument("--push", action="store_true", help="save the dashboard to Grafana (uses ~/.config/grafana/claude.yaml)")
    a = ap.parse_args()
    d, c = build(a.card)
    if a.push:
        push(d, c)
