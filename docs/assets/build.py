"""Regenerate the README graphics in docs/assets/.

    python docs/assets/build.py

Stdlib only. The logo is drawn from ``los_bootstrap.logo.LOGO`` as vector
shapes (not <text>), so it renders identically regardless of the viewer's
fonts. The demo transcript is abbreviated real CLI output.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from xml.sax.saxutils import escape

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent.parent / "src"))

from los_bootstrap.logo import LOGO  # noqa: E402

MONO = "ui-monospace, SFMono-Regular, Menlo, Consolas, 'DejaVu Sans Mono', monospace"
SANS = "-apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif"

THEMES = {
    "light": dict(
        accent="#167C80", ink="#1f2328", muted="#8c959f", card="#f6f8fa",
        border="#d0d7de", sub="#59636e", screen="#0d1117",
    ),
    "dark": dict(
        accent="#4DB6AC", ink="#e6edf3", muted="#6e7681", card="#161b22",
        border="#30363d", sub="#9198a1", screen="#010409",
    ),
}


# --------------------------------------------------------------------------
# Logo
# --------------------------------------------------------------------------

CW, CH = 10.0, 20.0
GX, GY, T = 2.4, 3.4, 1.7


def _glyph_paths(ch: str, x: float, y: float) -> list[str]:
    cx, cy = x + CW / 2, y + CH / 2
    l, r, t, b = x, x + CW, y, y + CH
    a, c = cx - GX, cx + GX
    u, d = cy - GY, cy + GY
    table = {
        "═": [f"M{l},{u}H{r}", f"M{l},{d}H{r}"],
        "║": [f"M{a},{t}V{b}", f"M{c},{t}V{b}"],
        "╔": [f"M{r},{u}H{a}V{b}", f"M{r},{d}H{c}V{b}"],
        "╗": [f"M{l},{u}H{c}V{b}", f"M{l},{d}H{a}V{b}"],
        "╚": [f"M{a},{t}V{d}H{r}", f"M{c},{t}V{u}H{r}"],
        "╝": [f"M{c},{t}V{d}H{l}", f"M{a},{t}V{u}H{l}"],
        "╠": [f"M{a},{t}V{b}", f"M{c},{t}V{u}H{r}", f"M{r},{d}H{c}V{b}"],
        "╣": [f"M{c},{t}V{b}", f"M{a},{t}V{u}H{l}", f"M{l},{d}H{a}V{b}"],
        "╦": [f"M{l},{u}H{r}", f"M{l},{d}H{a}V{b}", f"M{r},{d}H{c}V{b}"],
        "╩": [f"M{l},{d}H{r}", f"M{l},{u}H{a}V{t}", f"M{r},{u}H{c}V{t}"],
        "╷": [f"M{cx},{cy}V{b}"],
        "│": [f"M{cx},{t}V{b}"],
        "╵": [f"M{cx},{t}V{cy}"],
    }
    return table.get(ch, [])


def build_logo(theme: str) -> str:
    p = THEMES[theme]
    rows = [row for row in LOGO.strip("\n").split("\n")]
    width = max(len(r) for r in rows)
    split = rows[0].index("╷")
    blocks, shadow, word, rule = [], [], [], []
    for j, row in enumerate(rows):
        i = 0
        while i < len(row):
            ch = row[i]
            x, y = i * CW, j * CH
            if ch == "█":
                k = i
                while k < len(row) and row[k] == "█":
                    k += 1
                blocks.append(f'<rect x="{x}" y="{y}" width="{(k - i) * CW}" height="{CH}"/>')
                i = k
                continue
            paths = _glyph_paths(ch, x, y)
            if i == split:
                rule.extend(paths)
            elif i < split:
                shadow.extend(paths)
            else:
                word.extend(paths)
            i += 1
    pad = 4
    w, h = width * CW + 2 * pad, len(rows) * CH + 2 * pad
    stroke = f'fill="none" stroke-width="{T}" stroke-linecap="square"'
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="{-pad} {-pad} {w} {h}" width="{w * 1.2:.0f}" height="{h * 1.2:.0f}" role="img" aria-label="los-bootstrap">
  <title>los-bootstrap</title>
  <g fill="{p['accent']}">{''.join(blocks)}</g>
  <path d="{''.join(shadow)}" stroke="{p['muted']}" {stroke}/>
  <path d="{''.join(rule)}" stroke="{p['muted']}" {stroke}/>
  <path d="{''.join(word)}" stroke="{p['ink']}" {stroke}/>
</svg>
"""


# --------------------------------------------------------------------------
# Terminal demo
# --------------------------------------------------------------------------

# Each scene is a list of (command, output-lines). Output markup:
# {g}…{/} green, {y}…{/} yellow, {c}…{/} cyan, {d}…{/} dim, {b}…{/} bold.
SCENES: list[list[tuple[str, list[str]]]] = [
    [
        ("los-bootstrap devices", ["  38141FDJH004QN           device"]),
        ("los-bootstrap audit", [
            "{b}Device{/}",
            "  Model           : Pixel 7 (panther)",
            "  Security patch  : 2025-09-05",
            "  ROM             : LineageOS 21.0-20250915-NIGHTLY-panther",
            "",
            "{b}Audit findings{/}",
            "  {y}!{/}  Private DNS is off",
            "     DNS lookups go to whatever the network hands you, in cleartext.",
            "     {c}→ How to fix:{/} Settings > Network > Private DNS > dns.quad9.net",
            "  {g}✓{/}  No common Google client packages installed",
            "  {g}✓{/}  ADB-over-network is not enabled",
            "  {g}✓{/}  Screen lock appears enabled",
            "  {d}·  microG installed (free-software GMS replacement){/}",
        ]),
    ],
    [
        ("los-bootstrap harden", [
            "{b}Hardening checks{/}",
            "  {y}!{/}  Developer options enabled",
            "  {y}!{/}  USB debugging (ADB) enabled",
            "  {y}!{/}  Verified boot: orange (bootloader unlocked)",
            "  {y}!{/}  Lockdown in power menu not enabled",
            "     The Lockdown option instantly disables fingerprint and face",
            "     unlock — useful at a border crossing or after theft.",
            "     {c}→ Fix:{/} adb shell settings put secure lockdown_in_power_menu 1",
            "     {y}⚠  Tradeoff:{/} None. Lockdown does not wipe the device.",
            "  {g}✓{/}  Screen lock appears enabled",
            "  {g}✓{/}  Storage is encrypted",
            "  {g}✓{/}  Unknown sources (global) not enabled",
            "  4 issues need attention.",
        ]),
    ],
    [
        ("los-bootstrap plan --profile privacy-default", [
            "{b}Profile: privacy-default{/}",
            "  Sideloads F-Droid, queues replacement apps, switches on encrypted DNS.",
            "",
            "{b}Steps{/}",
            "   1 {d}[=] skip{/}           org.fdroid.fdroid already installed",
            "   2 {c}[↓] install_apk{/}    com.aurora.store from F-Droid",
            "   3 {c}[↓] install_apk{/}    net.osmand.plus from F-Droid",
            "   4 {c}[↓] install_apk{/}    org.thunderdog.challegram from F-Droid",
            "   5 {y}[~] set_setting{/}    global.private_dns_mode = 'hostname'",
            "",
            "Summary: 6 to run, 0 manual, 2 already satisfied.",
        ]),
    ],
    [
        ("los-bootstrap flash check", [
            "{b}First-Boot Verification{/}",
            "  {g}✓{/}  LineageOS detected",
            "  {g}✓{/}  Verified Boot state acceptable",
            "  {g}✓{/}  microG is installed (not real Play Services)",
            "  {d}·  A/B slot active: _a{/}",
            "",
            "  {g}Clean first boot — the install looks good.{/}",
        ]),
        ("los-bootstrap integrity doctor", [
            "{b}Device integrity doctor{/}",
            "  {y}!{/}  Bootloader unlocked",
            "  {y}!{/}  Developer options enabled",
            "  {d}·  Build signed with release-keys{/}",
            "  {d}·  microG present (no real Play Integrity verdict){/}",
        ]),
    ],
]

TERM_COLORS = dict(
    fg="#c9d1d9", g="#3fb950", y="#d29922", c="#39c5cf", d="#8b949e",
    b="#f0f6fc", prompt="#4DB6AC", bg="#0d1117", bar="#161b22",
)

FONT = 13.5
CHAR = 8.13  # advance width at FONT for ~0.6em monospace fonts
LINE = 19
PAD_X = 20
TOP = 52
ROWS = 18
TW = 860
TH = TOP + ROWS * LINE + 8

TYPE_CPS = 22.0
PRE_TYPE = 0.5
POST_TYPE = 0.35
LINE_STEP = 0.07
HOLD = 2.8
END_HOLD = 1.2

_MARK = re.compile(r"\{(\w)\}(.*?)\{/\}")


def _tspans(markup: str) -> str:
    out, pos = [], 0
    for m in _MARK.finditer(markup):
        if m.start() > pos:
            out.append(escape(markup[pos:m.start()]))
        key, body = m.group(1), escape(m.group(2))
        weight = ' font-weight="700"' if key == "b" else ""
        out.append(f'<tspan fill="{TERM_COLORS[key]}"{weight}>{body}</tspan>')
        pos = m.end()
    out.append(escape(markup[pos:]))
    return "".join(out)


def build_demo() -> str:
    timeline: list[tuple[float, float, list[str]]] = []
    anims: list[str] = []
    t = 0.0
    n = 0

    def pct(sec: float, total: float) -> str:
        return f"{100 * sec / total:.3f}%"

    scene_specs = []
    for scene in SCENES:
        start = t
        items = []
        row = 0
        for cmd, lines in scene:
            type_start = t + PRE_TYPE
            type_end = type_start + len(cmd) / TYPE_CPS
            out_start = type_end + POST_TYPE
            line_times = [out_start + k * LINE_STEP for k in range(len(lines))]
            items.append((row, cmd, type_start, type_end, lines, line_times))
            row += 1 + len(lines) + 1
            t = (line_times[-1] if line_times else out_start) + 0.6
        t += HOLD
        scene_specs.append((start, t, items))
    total = t + END_HOLD

    body: list[str] = []
    for s_start, s_end, items in scene_specs:
        n += 1
        sid = f"s{n}"
        anims.append(
            f"@keyframes {sid}{{0%{{opacity:0}}{pct(s_start, total)}{{opacity:1}}"
            f"{pct(s_end, total)}{{opacity:0}}100%{{opacity:0}}}}"
            f".{sid}{{opacity:0;animation:{sid} {total:.2f}s step-end infinite}}"
        )
        parts = [f'<g class="{sid}">']
        for idx, (row, cmd, ts, te, lines, line_times) in enumerate(items):
            y = TOP + row * LINE
            x_cmd = PAD_X + 2 * CHAR
            width = len(cmd) * CHAR
            cid = f"{sid}c{idx}"
            cursor_off = te + POST_TYPE
            parts.append(
                f'<text x="{PAD_X}" y="{y}" fill="{TERM_COLORS["prompt"]}" font-weight="700">$</text>'
                f'<text x="{x_cmd}" y="{y}" textLength="{width:.1f}" lengthAdjust="spacing">{escape(cmd)}</text>'
            )
            anims.append(
                f"@keyframes {cid}{{0%{{transform:translateX(0)}}"
                f"{pct(ts, total)}{{transform:translateX(0);animation-timing-function:steps({len(cmd)},end)}}"
                f"{pct(te, total)}{{transform:translateX({width:.1f}px)}}"
                f"100%{{transform:translateX({width:.1f}px)}}}}"
                f".{cid}{{animation:{cid} {total:.2f}s linear infinite}}"
                f"@keyframes {cid}k{{0%{{opacity:0}}{pct(s_start if idx == 0 else ts - PRE_TYPE, total)}{{opacity:1}}"
                f"{pct(cursor_off, total)}{{opacity:0}}100%{{opacity:0}}}}"
                f".{cid}k{{opacity:0;animation:{cid}k {total:.2f}s step-end infinite}}"
            )
            parts.append(
                f'<g class="{cid}">'
                f'<rect x="{x_cmd}" y="{y - LINE + 5}" width="{width + CHAR + 2:.1f}" height="{LINE}" fill="{TERM_COLORS["bg"]}"/>'
                f'<g class="{cid}k"><rect class="blink" x="{x_cmd}" y="{y - LINE + 6}" width="{CHAR:.1f}" height="{LINE - 3}" fill="{TERM_COLORS["fg"]}"/></g>'
                f"</g>"
            )
            for k, (line, lt) in enumerate(zip(lines, line_times)):
                if not line:
                    continue
                lid = f"{cid}l{k}"
                anims.append(
                    f"@keyframes {lid}{{0%{{opacity:0}}{pct(lt, total)}{{opacity:1}}100%{{opacity:1}}}}"
                    f".{lid}{{opacity:0;animation:{lid} {total:.2f}s step-end infinite}}"
                )
                ly = y + (k + 1) * LINE
                parts.append(f'<text class="{lid}" x="{PAD_X}" y="{ly}" xml:space="preserve">{_tspans(line)}</text>')
        parts.append("</g>")
        body.append("".join(parts))

    c = TERM_COLORS
    style = (
        "@keyframes blink{0%{opacity:1}50%{opacity:0}100%{opacity:1}}"
        ".blink{animation:blink 1s step-end infinite}"
        "@media (prefers-reduced-motion: reduce){*{animation-duration:0s!important}}"
        + "".join(anims)
    )
    dots = "".join(
        f'<circle cx="{20 + 18 * i}" cy="16" r="5.5" fill="{col}"/>'
        for i, col in enumerate(("#ff5f57", "#febc2e", "#28c840"))
    )
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {TW} {TH}" width="{TW}" height="{TH}" role="img" aria-label="Animated terminal demo of los-bootstrap: devices, audit, harden, plan, flash check and integrity doctor">
  <title>los-bootstrap terminal demo</title>
  <style>{style}</style>
  <rect width="{TW}" height="{TH}" rx="10" fill="{c['bg']}"/>
  <path d="M0,10a10,10 0 0 1 10,-10H{TW - 10}a10,10 0 0 1 10,10V32H0Z" fill="{c['bar']}"/>
  {dots}
  <text x="{TW / 2}" y="20" text-anchor="middle" font-family="{SANS}" font-size="12" fill="{c['d']}">los-bootstrap — USB: Pixel 7 (LineageOS 21)</text>
  <g font-family="{MONO}" font-size="{FONT}" fill="{c['fg']}">
    {''.join(body)}
  </g>
</svg>
"""


# --------------------------------------------------------------------------
# Getting-started graphic
# --------------------------------------------------------------------------

STEPS = [
    ("Install on your computer",
     ["One command installs", "los-bootstrap and adb.", "Linux, macOS or Windows."]),
    ("Turn on USB debugging",
     ["Tap Build number 7× to", "unlock Developer options,", "then switch on USB debugging."]),
    ("Plug in and tap Allow",
     ["Connect a USB cable. The", "phone asks to trust this", "computer — tap Allow."]),
    ("Run los-bootstrap",
     ["The wizard finds your", "phone and walks you", "through every step."]),
]


def _laptop(x: float, y: float, p: dict, screen: str) -> str:
    return (
        f'<rect x="{x}" y="{y}" width="120" height="76" rx="6" fill="{p["ink"]}"/>'
        f'<rect x="{x + 5}" y="{y + 5}" width="110" height="64" rx="2" fill="{p["screen"]}"/>'
        f'<path d="M{x - 14},{y + 80}H{x + 134}L{x + 126},{y + 88}H{x - 6}Z" fill="{p["ink"]}"/>'
        + screen
    )


def _phone(x: float, y: float, p: dict, inner: str) -> str:
    return (
        f'<rect x="{x}" y="{y}" width="62" height="112" rx="9" fill="{p["ink"]}"/>'
        f'<rect x="{x + 4}" y="{y + 8}" width="54" height="96" rx="3" fill="{p["card"]}"/>'
        f'<rect x="{x + 24}" y="{y + 3}" width="14" height="2.5" rx="1.2" fill="{p["muted"]}"/>'
        + inner
    )


def _illustrations(p: dict) -> list[str]:
    mono = f'font-family="{MONO}"'
    t = TERM_COLORS
    one = _laptop(52, 24, p,
        f'<text x="62" y="46" {mono} font-size="9" fill="{t["prompt"]}">$ <tspan fill="{t["fg"]}">curl … | sh</tspan></text>'
        f'<text x="62" y="60" {mono} font-size="8" fill="{t["g"]}">✓ adb</text>'
        f'<text x="62" y="72" {mono} font-size="8" fill="{t["g"]}">✓ los-bootstrap</text>')
    two = _phone(80, 12, p,
        f'<text x="88" y="34" font-family="{SANS}" font-size="7" fill="{p["sub"]}">About phone</text>'
        f'<rect x="87" y="40" width="48" height="16" rx="2" fill="{p["accent"]}" opacity="0.18"/>'
        f'<text x="90" y="51" font-family="{SANS}" font-size="7" font-weight="700" fill="{p["ink"]}">Build number</text>'
        f'<text x="111" y="70" font-family="{SANS}" font-size="13" font-weight="700" fill="{p["accent"]}" text-anchor="middle">×7</text>'
        f'<text x="88" y="88" font-family="{SANS}" font-size="6.5" fill="{p["ink"]}">USB debugging</text>'
        f'<rect x="88" y="92" width="18" height="8" rx="4" fill="{p["accent"]}"/>'
        f'<circle cx="102" cy="96" r="3" fill="#fff"/>')
    three = (
        f'<path d="M58,118 C58,134 108,132 112,104" fill="none" stroke="{p["muted"]}" stroke-width="3" stroke-linecap="round"/>'
        f'<rect x="10" y="66" width="56" height="44" rx="4" fill="{p["ink"]}"/>'
        f'<rect x="14" y="70" width="48" height="34" rx="1.5" fill="{p["screen"]}"/>'
        f'<rect x="54" y="112" width="8" height="8" rx="1" fill="{p["muted"]}"/>'
        + _phone(112, 4, p,
            f'<rect x="118" y="34" width="50" height="46" rx="4" fill="{p["border"]}"/>'
            f'<text x="121" y="46" font-family="{SANS}" font-size="6" font-weight="700" fill="{p["ink"]}">Allow USB</text>'
            f'<text x="121" y="54" font-family="{SANS}" font-size="6" font-weight="700" fill="{p["ink"]}">debugging?</text>'
            f'<rect x="138" y="64" width="26" height="11" rx="5.5" fill="{p["accent"]}"/>'
            f'<text x="151" y="72" font-family="{SANS}" font-size="6" font-weight="700" fill="#fff" text-anchor="middle">Allow</text>')
    )
    four = _laptop(52, 24, p,
        f'<text x="62" y="42" {mono} font-size="9" fill="{t["prompt"]}">$ <tspan fill="{t["fg"]}">los-bootstrap</tspan></text>'
        f'<text x="62" y="54" {mono} font-size="7.5" fill="{t["c"]}">› Audit</text>'
        f'<text x="62" y="63" {mono} font-size="7.5" fill="{t["d"]}">  Harden</text>'
        f'<text x="62" y="72" {mono} font-size="7.5" fill="{t["d"]}">  Bootstrap …</text>')
    return [one, two, three, four]


def build_steps(theme: str) -> str:
    p = THEMES[theme]
    cw, gap, ch = 224, 28, 300
    w = 4 * cw + 3 * gap
    ill = _illustrations(p)
    cards = []
    for i, ((title, desc), art) in enumerate(zip(STEPS, ill)):
        x = i * (cw + gap)
        lines = "".join(
            f'<text x="{cw / 2}" y="{236 + 18 * k}" text-anchor="middle" font-size="13" fill="{p["sub"]}">{escape(s)}</text>'
            for k, s in enumerate(desc)
        )
        cards.append(
            f'<g transform="translate({x},0)">'
            f'<rect x="0.5" y="0.5" width="{cw - 1}" height="{ch - 1}" rx="12" fill="{p["card"]}" stroke="{p["border"]}"/>'
            f'<g transform="translate(0,22)">{art}</g>'
            f'<circle cx="{cw / 2}" cy="174" r="12" fill="{p["accent"]}"/>'
            f'<text x="{cw / 2}" y="178.5" text-anchor="middle" font-size="13" font-weight="700" fill="#fff">{i + 1}</text>'
            f'<text x="{cw / 2}" y="210" text-anchor="middle" font-size="15" font-weight="700" fill="{p["ink"]}">{escape(title)}</text>'
            f"{lines}</g>"
        )
        if i < 3:
            ax = x + cw + 4
            cards.append(
                f'<path d="M{ax},150h{gap - 10}m-6,-6l6,6l-6,6" fill="none" stroke="{p["muted"]}" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>'
            )
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {ch}" width="{w}" height="{ch}" role="img" aria-label="Getting started in four steps: install on your computer, turn on USB debugging, plug in and tap Allow, run los-bootstrap">
  <title>Getting started with los-bootstrap</title>
  <g font-family="{SANS}">{''.join(cards)}</g>
</svg>
"""


def main() -> None:
    outputs = {"demo.svg": build_demo()}
    for theme in THEMES:
        outputs[f"logo-{theme}.svg"] = build_logo(theme)
        outputs[f"getting-started-{theme}.svg"] = build_steps(theme)
    for name, svg in outputs.items():
        (HERE / name).write_text(svg, encoding="utf-8")
        print(f"wrote docs/assets/{name} ({len(svg.encode()) // 1024} KiB)")


if __name__ == "__main__":
    main()
