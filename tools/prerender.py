"""Gera o que o Google precisa ler sem rodar JavaScript, nos três idiomas do site.

- index.html (português, a fonte): escreve os cartões dos trabalhos e a ficha profissional (JSON-LD)
  entre os marcadores PRERENDER;
- en/index.html e es/index.html: copiam o index.html, trocam cada texto que tem data-en/data-es pela
  tradução (guardando o português em data-pt), traduzem o <head> e escrevem os cartões e a ficha
  no idioma da página;
- sitemap.xml: lista as três páginas com os links entre idiomas.

Rodar de novo sem mudar nada não altera os arquivos. Uso: python tools/prerender.py (na pasta do site).
"""

import html
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE = "https://wirbelmov.com"
LANGS = ("pt", "en", "es")
PATH = {"pt": "/", "en": "/en/", "es": "/es/"}

CATS = {
    "anime": {"pt": "Anime & games", "en": "Anime & games", "es": "Anime y juegos"},
    "financas": {"pt": "Finanças", "en": "Finance", "es": "Finanzas"},
    "youtube": {"pt": "YouTube", "en": "YouTube", "es": "YouTube"},
    "shorts": {"pt": "Shorts", "en": "Shorts", "es": "Shorts"},
    "motion": {"pt": "Motion", "en": "Motion", "es": "Motion"},
    "comercial": {"pt": "Comercial", "en": "Commercial", "es": "Comercial"},
}

# <head> of each translated page: Portuguese text -> translation (each must appear exactly once)
HEAD = {
    "en": {
        '<html lang="pt-BR">':
            '<html lang="en">',
        '<link rel="canonical" href="https://wirbelmov.com/">':
            '<link rel="canonical" href="https://wirbelmov.com/en/">',
        '<meta property="og:url" content="https://wirbelmov.com/">':
            '<meta property="og:url" content="https://wirbelmov.com/en/">',
        '<meta property="og:locale" content="pt_BR">\n<meta property="og:locale:alternate" content="en_US">':
            '<meta property="og:locale" content="en_US">\n<meta property="og:locale:alternate" content="pt_BR">',
        '<title>Wirbel · Editor de vídeo freelancer para YouTube e Shorts</title>':
            '<title>Wirbel · Freelance video editor for YouTube and Shorts</title>',
        '<meta name="description" content="Wirbel (Wirbel.mov) é editor de vídeo freelancer e motion designer: edição de vídeos longos para YouTube, canais dark, anime, games e finanças, Shorts e motion graphics.">':
            '<meta name="description" content="Wirbel (Wirbel.mov) is a freelance video editor and motion designer: long-form YouTube video editing, faceless channels, anime, gaming and finance, Shorts and motion graphics.">',
        '<meta property="og:title" content="Wirbel | Editor de vídeo">':
            '<meta property="og:title" content="Wirbel | Video editor">',
        '<meta name="twitter:title" content="Wirbel | Editor de vídeo">':
            '<meta name="twitter:title" content="Wirbel | Video editor">',
        '<meta property="og:description" content="Wirbel, editor de vídeo: edições que prendem o público. Vídeos longos para YouTube, Shorts, motion graphics, cor e som.">':
            '<meta property="og:description" content="Wirbel, video editor: edits that hook the audience. Long-form YouTube videos, Shorts, motion graphics, color and sound.">',
        '<meta name="twitter:description" content="Wirbel, editor de vídeo: edições que prendem o público. Vídeos longos para YouTube, Shorts, motion graphics, cor e som.">':
            '<meta name="twitter:description" content="Wirbel, video editor: edits that hook the audience. Long-form YouTube videos, Shorts, motion graphics, color and sound.">',
        'alt="Avatar do Wirbel, editor de vídeo: personagem de cabelo prateado, gola de pelo escuro e um cajado no ombro"':
            'alt="Avatar of Wirbel, video editor: a silver-haired character with a dark fur collar and a staff on his shoulder"',
    },
    "es": {
        '<html lang="pt-BR">':
            '<html lang="es">',
        '<link rel="canonical" href="https://wirbelmov.com/">':
            '<link rel="canonical" href="https://wirbelmov.com/es/">',
        '<meta property="og:url" content="https://wirbelmov.com/">':
            '<meta property="og:url" content="https://wirbelmov.com/es/">',
        '<meta property="og:locale" content="pt_BR">\n<meta property="og:locale:alternate" content="en_US">\n<meta property="og:locale:alternate" content="es_ES">':
            '<meta property="og:locale" content="es_ES">\n<meta property="og:locale:alternate" content="pt_BR">\n<meta property="og:locale:alternate" content="en_US">',
        '<title>Wirbel · Editor de vídeo freelancer para YouTube e Shorts</title>':
            '<title>Wirbel · Editor de video freelance para YouTube y Shorts</title>',
        '<meta name="description" content="Wirbel (Wirbel.mov) é editor de vídeo freelancer e motion designer: edição de vídeos longos para YouTube, canais dark, anime, games e finanças, Shorts e motion graphics.">':
            '<meta name="description" content="Wirbel (Wirbel.mov) es editor de video freelance y motion designer: edición de videos largos para YouTube, canales dark, anime, videojuegos y finanzas, Shorts y motion graphics.">',
        '<meta property="og:title" content="Wirbel | Editor de vídeo">':
            '<meta property="og:title" content="Wirbel | Editor de video">',
        '<meta name="twitter:title" content="Wirbel | Editor de vídeo">':
            '<meta name="twitter:title" content="Wirbel | Editor de video">',
        '<meta property="og:description" content="Wirbel, editor de vídeo: edições que prendem o público. Vídeos longos para YouTube, Shorts, motion graphics, cor e som.">':
            '<meta property="og:description" content="Wirbel, editor de video: ediciones que atrapan al público. Videos largos para YouTube, Shorts, motion graphics, color y sonido.">',
        '<meta name="twitter:description" content="Wirbel, editor de vídeo: edições que prendem o público. Vídeos longos para YouTube, Shorts, motion graphics, cor e som.">':
            '<meta name="twitter:description" content="Wirbel, editor de video: ediciones que atrapan al público. Videos largos para YouTube, Shorts, motion graphics, color y sonido.">',
        'alt="Avatar do Wirbel, editor de vídeo: personagem de cabelo prateado, gola de pelo escuro e um cajado no ombro"':
            'alt="Avatar de Wirbel, editor de video: personaje de cabello plateado, cuello de piel oscura y un bastón al hombro"',
    },
}

PERSON = {
    "pt": ("Editor de vídeo freelancer e motion designer",
           "Wirbel é editor de vídeo freelancer: edição de vídeos longos narrados para YouTube, canais dark, anime, games e finanças, Shorts e motion graphics.",
           ["Edição de vídeos longos para YouTube", "Edição de Shorts e Reels", "Motion graphics para YouTube", "Cor e som para vídeo"],
           "Edição de vídeo", "Wirbel · Editor de vídeo"),
    "en": ("Freelance video editor and motion designer",
           "Wirbel is a freelance video editor: long narrated YouTube videos, faceless channels, anime, gaming and finance, Shorts and motion graphics.",
           ["Long-form YouTube video editing", "Shorts and Reels editing", "Motion graphics for YouTube", "Color and sound for video"],
           "Video editing", "Wirbel · Video editor"),
    "es": ("Editor de video freelance y motion designer",
           "Wirbel es editor de video freelance: edición de videos largos narrados para YouTube, canales dark, anime, videojuegos y finanzas, Shorts y motion graphics.",
           ["Edición de videos largos para YouTube", "Edición de Shorts y Reels", "Motion graphics para YouTube", "Color y sonido para video"],
           "Edición de video", "Wirbel · Editor de video"),
}
INLANG = {"pt": "pt-BR", "en": "en", "es": "es"}


def esc(s):
    return html.escape(str(s or ""), quote=True)


def tr(v, lang):
    if isinstance(v, dict):
        return v.get(lang) or v.get("pt") or v.get("en") or ""
    return v or ""


def card(p, lang):
    title, desc = tr(p.get("title"), lang), tr(p.get("desc"), lang)
    short = desc.split(". ")[0]
    if short and not short.endswith("."):
        short += "."
    thumb = (f'<img src="/{esc(str(p["thumb"]).lstrip("/"))}" alt="{esc(title)}" loading="lazy">' if p.get("thumb")
             else '<div class="swirl"></div>')
    dur = f'<span class="dur">{esc(p["dur"])}</span>' if p.get("dur") else ""
    cat = CATS.get(p.get("cat"), {}).get(lang, p.get("cat"))
    return (f'<button type="button" class="card"><div class="thumb">{thumb}'
            f'<span class="badge">{esc(cat)}</span>{dur}</div>'
            f'<div class="meta"><h3>{esc(title)}</h3>{f"<p>{esc(short)}</p>" if short else ""}</div></button>')


def iso_duration(dur):
    parts = [int(x) for x in str(dur or "").split(":") if x.isdigit()]
    if not parts:
        return None
    while len(parts) < 3:
        parts.insert(0, 0)
    h, m, s = parts[-3:]
    return "PT" + (f"{h}H" if h else "") + (f"{m}M" if m else "") + f"{s}S"


def yt_id(url):
    m = re.search(r"(?:youtu\.be/|[?&]v=)([\w-]{11})", url or "")
    return m.group(1) if m else ""


def jsonld(d, lang):
    job, desc, offers, stype, page_name = PERSON[lang]
    url = SITE + PATH[lang]
    person = {
        "@type": "Person", "@id": f"{SITE}/#wirbel", "name": "Wirbel",
        "alternateName": ["Wirbel.mov", "wirbelmov", "Wirbel Mov"], "jobTitle": job, "description": desc,
        "url": f"{SITE}/", "image": f"{SITE}/assets/icon-512.png",
        # the same skills named the way people search for them in each language
        "knowsAbout": ["Edição de vídeo", "Editor de vídeo para YouTube", "Edição de vídeo freelancer",
                       "Video editing", "YouTube video editor", "Freelance video editing",
                       "Edición de video", "Editor de video para YouTube", "Edición de video freelance",
                       "Motion graphics", "Shorts", "Reels", "Canais dark", "Faceless YouTube channels",
                       "Canales dark", "Color grading", "Audio mixing", "Adobe Premiere Pro", "Adobe After Effects"],
        "knowsLanguage": ["pt-BR", "en", "es"],
        "sameAs": [s["url"] for s in (d.get("contact") or {}).get("socials", []) if s.get("url")],
        "makesOffer": [{"@type": "Offer", "itemOffered": {"@type": "Service", "name": n, "serviceType": stype}}
                       for n in offers],
    }
    videos = []
    for p in d.get("projects", []):
        vid = yt_id(p.get("url"))
        if not vid:
            continue
        v = {"@type": "VideoObject", "name": tr(p.get("title"), lang), "description": tr(p.get("desc"), lang),
             "thumbnailUrl": f"{SITE}/{str(p['thumb']).lstrip('/')}" if p.get("thumb") else f"https://i.ytimg.com/vi/{vid}/hqdefault.jpg",
             "embedUrl": f"https://www.youtube.com/embed/{vid}", "url": p["url"], "inLanguage": "pt-BR",
             "contributor": {"@id": f"{SITE}/#wirbel"}}
        if p.get("date"):
            v["uploadDate"] = p["date"]
        if iso_duration(p.get("dur")):
            v["duration"] = iso_duration(p.get("dur"))
        videos.append(v)
    graph = [
        {"@type": "WebSite", "@id": f"{SITE}/#site", "url": f"{SITE}/", "name": "Wirbel.mov", "alternateName": "Wirbel",
         "inLanguage": ["pt-BR", "en", "es"], "publisher": {"@id": f"{SITE}/#wirbel"}},
        {"@type": "ProfilePage", "@id": f"{url}#page", "url": url, "name": page_name, "inLanguage": INLANG[lang],
         "mainEntity": {"@id": f"{SITE}/#wirbel"}, "isPartOf": {"@id": f"{SITE}/#site"}},
        person, *videos,
    ]
    body = json.dumps({"@context": "https://schema.org", "@graph": graph}, ensure_ascii=False, indent=1)
    return '<script type="application/ld+json">\n' + body.replace("</", "<\\/") + "\n</script>"


def put(page, name, content):
    pat = re.compile(rf"(<!--PRERENDER:{name}-->).*?(<!--/PRERENDER:{name}-->)", re.S)
    if not pat.search(page):
        raise SystemExit(f"marcador PRERENDER:{name} não encontrado")
    return pat.sub(lambda m: m.group(1) + content + m.group(2), page, count=1)


def fill(page, d, lang):
    ps = d.get("projects", [])
    page = put(page, "feat", "".join(card(p, lang) for p in ps if p.get("featured")))
    page = put(page, "rest", "".join(card(p, lang) for p in ps if not p.get("featured")))
    return put(page, "jsonld", jsonld(d, lang))


ELEM = re.compile(r'<(\w+)((?:\s[^<>]*?)?)\sdata-en="([^"]*)"\sdata-es="([^"]*)"([^<>]*)>(.*?)</\1>', re.S)


def translate_body(page, lang):
    """Swap the text of every data-en/data-es element and keep the Portuguese in data-pt."""
    head, body = page.split("<body>", 1)
    body, script = body.split("<script>", 1)  # the page script holds no translatable markup

    def swap(m):
        tag, before, en, es, after, inner = m.groups()
        if f"<{tag}" in inner:  # nested element of the same tag: the regex cannot pair it safely
            raise SystemExit(f"elemento <{tag}> aninhado não suportado: {inner[:60]}")
        new = html.unescape(en if lang == "en" else es)
        return (f'<{tag}{before} data-en="{en}" data-es="{es}" data-pt="{esc(inner)}"{after}>{new}</{tag}>')

    body, n = ELEM.subn(swap, body)
    if n < 30:  # the page has 38 today; far fewer means the markup changed and the pattern stopped matching
        raise SystemExit(f"só {n} textos traduzidos; esperado perto de 38 (a página mudou?)")
    return head + "<body>" + body + "<script>" + script, n


def translate_head(page, lang):
    for old, new in HEAD[lang].items():
        if page.count(old) != 1:
            raise SystemExit(f"[{lang}] trecho do cabeçalho não encontrado (ou repetido): {old[:70]}")
        page = page.replace(old, new)
    return page


def sitemap():
    alts = "".join(f'\n    <xhtml:link rel="alternate" hreflang="{h}" href="{SITE}{PATH[l]}"/>'
                   for h, l in (("pt", "pt"), ("en", "en"), ("es", "es"), ("x-default", "pt")))
    urls = "".join(f"\n  <url>\n    <loc>{SITE}{PATH[l]}</loc>{alts}\n  </url>" for l in LANGS)
    return ('<?xml version="1.0" encoding="UTF-8"?>\n'
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:xhtml="http://www.w3.org/1999/xhtml">'
            f"{urls}\n</urlset>\n")


def write_if_changed(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists() or path.read_text(encoding="utf-8") != text:
        path.write_text(text, encoding="utf-8", newline="\n")
        return True
    return False


def main():
    d = json.loads((ROOT / "projects.json").read_text(encoding="utf-8"))
    src = (ROOT / "index.html").read_text(encoding="utf-8")
    pt_page = fill(src, d, "pt")
    report = [f"index.html {'atualizado' if write_if_changed(ROOT / 'index.html', pt_page) else 'igual'}"]
    for lang in ("en", "es"):
        page, n = translate_body(translate_head(pt_page, lang), lang)
        page = fill(page, d, lang)
        changed = write_if_changed(ROOT / lang / "index.html", page)
        report.append(f"{lang}/index.html {'atualizado' if changed else 'igual'} ({n} textos)")
    report.append(f"sitemap.xml {'atualizado' if write_if_changed(ROOT / 'sitemap.xml', sitemap()) else 'igual'}")
    print(" · ".join(report))


if __name__ == "__main__":
    main()
