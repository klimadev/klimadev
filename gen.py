"""
gen.py — assets do README do klimadev.

Arquitetura: markdown nativo é o substrato do README. SVG só onde a
ilustração carrega informação que o texto não carrega:

  1. wordmark dark/light  -> gradiente do nome (o unico lugar onde cor
                              precisa ser precisa, e texto puro nao
                              faz gradiente)
  2. badges de status     -> selo de "morreu / fechei / no ar / em obra"

Todo o resto (secoes, tabelas, linha do tempo, post-mortems, botoes,
stack) e markdown/HTML nativo do GitHub: legivel, buscavel, copiável,
adaptativo ao tema e sem manutencao.

Como editar: muda a string aqui e roda `python gen.py`.
"""
import base64
import hashlib
import pathlib
import re
import subprocess
import urllib.request

ROOT = pathlib.Path(__file__).parent
OUT = ROOT / "banners"
CACHE = ROOT / ".fontcache.b64"
FONT_URL = ("https://raw.githubusercontent.com/JetBrains/JetBrainsMono/"
            "master/fonts/ttf/JetBrainsMono-Bold.ttf")

W = 880
BG, LINE, FG, MUTED = "#0d1117", "#30363d", "#e6edf3", "#8b949e"

B64 = ""


# ---------------------------------------------------------------- infra
def font_b64(chars):
    """Subset OFL da JetBrains Mono Bold embutido como data-URI.

    So os glifos realmente usados sao embutidos: "Lima" sao 4 letras.
    O subset ASCII inteiro (95 glifos) pesava 32 KB por arquivo; com os
    glifos certos, o wordmark fica em ~2 KB.
    """
    key = "".join(sorted(set(chars)))
    cache = ROOT / f".fontcache-{key}.b64"
    if cache.exists():
        return cache.read_text()
    ttf = ROOT / ".jbm.ttf"
    if not ttf.exists():
        urllib.request.urlretrieve(FONT_URL, ttf)
    woff2 = ROOT / ".jbm.woff2"
    subprocess.run(["pyftsubset", str(ttf), f"--text={key}",
                    "--flavor=woff2", f"--output-file={woff2}"], check=True)
    data = base64.b64encode(woff2.read_bytes()).decode()
    for p in (ttf, woff2):
        if p.exists():
            p.unlink()
    cache.write_text(data)
    return data


AMP = chr(38)


def esc(s):
    return (s.replace(AMP, AMP + "amp;")
            .replace("<", AMP + "lt;")
            .replace(">", AMP + "gt;"))


def svg_open(w, h, aria, b64, c0, c1, c2):
    return [f'<svg width="{w}" height="{h}" viewBox="0 0 {w} {h}" '
            'xmlns="http://www.w3.org/2000/svg" role="img" '
            f'aria-label="{esc(aria)}">',
            "  <style>",
            "    @font-face { font-family: 'JBM';",
            f"      src: url(data:font/woff2;base64,{b64}) format('woff2');",
            "      font-weight: 700; }",
            "  </style>",
            "  <defs>",
            '    <linearGradient id="g" x1="0" y1="0" x2="1" y2="0">',
            f'      <stop offset="0" stop-color="{c0}"/>',
            f'      <stop offset="0.55" stop-color="{c1}"/>',
            f'      <stop offset="1" stop-color="{c2}"/>',
            "    </linearGradient>",
            "  </defs>"]


def text(x, y, body, size=15, fill=FG):
    return (f'  <text x="{x}" y="{y}" font-family="JBM, monospace" '
            f'font-size="{size}" font-weight="700" fill="{fill}">'
            f'{esc(body)}</text>')


# ---------------------------------------------------------------- wordmark
# O gradiente precisa contrastar com o fundo do tema. Dark usa tons
# claros (12.8:1 sobre #0d1117); light usa tons escuros (7.5:1 sobre
# #ffffff). Texto corrido exige 4.5:1 -> todos passam.
WORDMARK = {
    "dark": ("#5eead4", "#38bdf8", "#f472b6"),
    "light": ("#0f766e", "#1d4ed8", "#be185d"),
}


def wordmark_svg(variant):
    """Nome + barra de gradiente, centralizados.

    O canvas e justo ao conteudo (nao 880px): exibido com width="100%"
    ele escala como um bloco, e centralizar evita a palavra grudada na
    esquerda. A barra mede a largura da palavra, nao a do canvas.
    """
    c0, c1, c2 = WORDMARK[variant]
    w, h = 460, 132
    b64 = font_b64("Lima")
    p = svg_open(w, h, "Lima", b64, c0, c1, c2)
    p.append(f'  <text x="{w//2}" y="92" font-family="JBM, monospace" '
             'font-size="92" font-weight="700" fill="url(#g)" '
             'text-anchor="middle" textLength="232" '
             'lengthAdjust="spacingAndGlyphs">Lima</text>')
    p.append(f'  <rect x="{(w-232)//2}" y="108" width="232" height="5" '
             'rx="2.5" fill="url(#g)"/>')
    p.append("</svg>")
    return "\n".join(p)


# ---------------------------------------------------------------- badges
# Selos de estado. Cores identicas as do wordmark dark (mesma familia),
# escolhidas para passar 4.5:1 sobre #0d1117 e sobre #ffffff.
BADGES = {
    "morreu": ("b91c1c", "morreu"),
    "fechei": ("a16207", "fechei"),
    "no-ar": ("15803d", "no ar"),
    "em-obra": ("1d4ed8", "em obra"),
    "produto": ("0e7490", "produto"),
    "apps": ("9d174d", "apps"),
    "infra": ("6d28d9", "infra"),
    "gestor": ("4338ca", "gestor"),
}


def badge_svg(name):
    """Selo de estado: fundo solido, sem fonte embutida.

    O selo e pequeno (13px) e usa a fonte do sistema, entao a largura
    exata do texto varia entre maquinas. Em vez de confiar em medicao
    (textLength nao e respeitado por todo renderizador), o texto e
    centralizado numa zona larga com folga: sobra espaco dos dois
    lados, e a pílula nunca corta o rotulo. Resultado: ~700 bytes em
    vez de 33 KB por selo.
    """
    color, label = BADGES[name]
    tw = len(label) * 9.4          # estimativa generosa (Verdana bold)
    zone_x, zone_w = 30, tw + 8    # zona do texto, com folga dos dois lados
    w = round(zone_x + zone_w + 12)
    h = 30
    p = [f'<svg width="{w}" height="{h}" viewBox="0 0 {w} {h}" '
         'xmlns="http://www.w3.org/2000/svg" role="img" '
         f'aria-label="{esc(label)}">',
         f'  <rect x="1" y="1" width="{w-2}" height="{h-2}" rx="15" '
         f'fill="#{color}"/>',
         f'  <circle cx="16" cy="15" r="5" fill="#ffffff"/>',
         f'  <text x="{round(zone_x + zone_w/2)}" y="20" '
         'font-family="Verdana,Geneva,DejaVu Sans,sans-serif" '
         'font-size="13" font-weight="700" fill="#ffffff" '
         'text-anchor="middle">'
         f'{esc(label)}</text>',
         "</svg>"]
    return "\n".join(p)


# ---------------------------------------------------------------- cache
def sync_versions(hashes):
    """Sincroniza ?v=<hash> das referencias locais no README.

    O camo do GitHub cacheia por URL: sem mudar a query, um SVG novo
    continua servindo o antigo. A versao e o hash do conteudo, entao:
      - mudou o asset -> URL muda -> cache invalidado;
      - asset igual   -> URL igual -> cache preservado.

    Contador incremental resolveria o primeiro caso, mas quebraria o
    segundo a cada build.
    """
    readme = ROOT / "README.md"
    if not readme.exists():
        return
    src = readme.read_text(encoding="utf-8")

    def repl(m):
        name = m.group(2)
        h = hashes.get(name)
        return f"{m.group(1)}{h}" if h else m.group(0)

    new = re.sub(r"(banners/([a-z0-9\-]+\.svg)\?v=)([a-z0-9]+)", repl, src)
    if new != src:
        readme.write_text(new, encoding="utf-8")
        print("README: versoes de cache sincronizadas")


# ---------------------------------------------------------------- main
def main():
    OUT.mkdir(exist_ok=True)
    hashes = {}

    def emit(filename, content):
        path = OUT / filename
        path.write_text(content, encoding="utf-8")
        digest = hashlib.sha1(content.encode("utf-8")).hexdigest()[:8]
        hashes[filename] = digest
        print(f"{filename} {path.stat().st_size} bytes  v={digest}")

    for variant in ("dark", "light"):
        emit(f"wordmark-{variant}.svg", wordmark_svg(variant))

    for name in BADGES:
        emit(f"badge-{name}.svg", badge_svg(name))

    sync_versions(hashes)


if __name__ == "__main__":
    main()
