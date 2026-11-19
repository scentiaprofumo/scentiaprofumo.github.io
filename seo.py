"""SEO de la web: una página por perfume entero (perfumes/<slug>.html), la lista perfumes/index.html,
sitemap.xml, robots.txt y los datos estructurados (JSON-LD) de la portada.
Uso: python seo.py   (correr cada mes después de enteros.py y fotos_pdf.py)"""
import html
import json
import re
from datetime import date
from pathlib import Path

AQUI = Path(__file__).parent
SITIO = "https://scentiaprofumo.github.io"
WA = "595972166484"
HOY = date.today().isoformat()


def slug(t):
    t = t.lower()
    for a, b in zip("áéíóúüñ’'", "aeiouun  "):
        t = t.replace(a, b)
    return re.sub(r"[^a-z0-9]+", "-", t).strip("-")


def gs(n):
    return "Gs. " + f"{n:,}".replace(",", ".")


def titulo(t):
    """KHAMRAH QAHWA -> Khamrah Qahwa (los nombres vienen en mayúsculas del PDF)."""
    return " ".join(w if any(c.isdigit() for c in w) else w.capitalize() for w in t.split())


ESTILO = """<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Oswald:wght@600;700&family=Inter:wght@400;500;600&display=swap">
<style>
:root{--bg:#0c0b0a;--panel:#151311;--line:#2c2620;--fg:#f2ede4;--muted:#a59c8f;--gold:#d4af6a;color-scheme:dark}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--fg);font-family:Inter,system-ui,sans-serif;line-height:1.55}
.w{max-width:960px;margin:0 auto;padding:28px max(18px,env(safe-area-inset-left)) 60px}
a{color:var(--gold)}nav{font-size:14px;color:var(--muted)}nav a{color:var(--muted)}
h1{font-family:Oswald,"Arial Narrow",sans-serif;text-transform:uppercase;font-size:clamp(30px,6vw,46px);line-height:1;margin:14px 0 6px}
h2{font-family:Oswald,"Arial Narrow",sans-serif;text-transform:uppercase;font-size:24px;margin:34px 0 12px}
.prod{display:grid;grid-template-columns:minmax(0,1.1fr) minmax(0,1fr);gap:28px;align-items:start}
@media(max-width:720px){.prod{grid-template-columns:1fr}}
.prod img{width:100%;height:auto;border-radius:14px;background:#fff;display:block}
.precio{font-family:Oswald,sans-serif;font-size:38px;color:var(--gold)}
.btn{display:inline-block;background:#25d366;color:#05210f;font-weight:600;text-decoration:none;padding:14px 22px;border-radius:99px;margin:14px 0}
.ago{display:inline-block;background:#8c2f39;color:#fff;padding:4px 10px;border-radius:6px;font-size:13px}
ul.l{columns:2;column-gap:28px;padding-left:18px}@media(max-width:600px){ul.l{columns:1}}
ul.l li{margin:4px 0;break-inside:avoid}.m{color:var(--muted)}
footer{margin-top:40px;border-top:1px solid var(--line);padding-top:18px;color:var(--muted);font-size:14px}
</style>"""


def pagina(titulo_, descripcion, url, cuerpo, jsonld, imagen=None):
    og_img = f'<meta property="og:image" content="{imagen}">' if imagen else ""
    return f"""<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(titulo_)}</title>
<meta name="description" content="{html.escape(descripcion)}">
<link rel="canonical" href="{url}">
<meta property="og:type" content="website"><meta property="og:site_name" content="Scentia"><meta property="og:locale" content="es_PY">
<meta property="og:url" content="{url}"><meta property="og:title" content="{html.escape(titulo_)}">
<meta property="og:description" content="{html.escape(descripcion)}">{og_img}
<link rel="icon" href="/img/logo.png">
<script type="application/ld+json">{json.dumps(jsonld, ensure_ascii=False)}</script>
{ESTILO}
</head>
<body><div class="w">
{cuerpo}
<footer>Scentia · Perfumes árabes originales en Paraguay · Delivery y envíos a todo el país ·
WhatsApp <a href="https://wa.me/{WA}">0972 166 484</a> · Instagram <a href="https://instagram.com/scentiaprofumo">@scentiaprofumo</a></footer>
</div></body></html>
"""


def main():
    datos = json.loads((AQUI / "enteros/enteros.json").read_text(encoding="utf-8"))
    usados = {}
    for p in datos:
        s = slug(f'{p["nombre"]} {p["ml"] or ""}ml')
        if s in usados:
            s = slug(f'{p["nombre"]} {p["ml"] or ""}ml {p["genero"]}')
        n = usados[s] = usados.get(s, 0) + 1
        p["slug"] = s if n == 1 else f"{s}-{n}"
    (AQUI / "enteros/enteros.json").write_text(json.dumps(datos, ensure_ascii=False, indent=0), encoding="utf-8")

    out = AQUI / "perfumes"
    out.mkdir(exist_ok=True)
    for f in out.glob("*.html"):
        f.unlink()
    for p in datos:
        nombre = titulo(p["nombre"])
        ml = f' {p["ml"]} ml' if p["ml"] else ""
        url = f"{SITIO}/perfumes/{p['slug']}.html"
        img = f"{SITIO}/{p['foto']}"
        disp = "Agotado por ahora" if p["agotado"] else "Disponible"
        t = f"{nombre}{ml} precio en Paraguay | Scentia"
        d = (f"{nombre}{ml} original para {p['genero'].lower()} a {gs(p['precio'])} en Paraguay. "
             f"{'Agotado por ahora: consultá reposición. ' if p['agotado'] else ''}Delivery y envíos a todo el país. Pedilo por WhatsApp.")
        msg = f"Hola Scentia! Quiero el perfume entero {nombre}{ml} ({gs(p['precio'])})."
        boton = (f'<span class="ago">Agotado</span><p><a class="btn" href="https://wa.me/{WA}?text='
                 f'{html.escape(re.sub(" ", "%20", "Hola Scentia! ¿Cuándo vuelve " + nombre + ml + "?"))}">Avisame cuando vuelva</a></p>'
                 if p["agotado"] else
                 f'<p><a class="btn" href="https://wa.me/{WA}?text={html.escape(msg.replace(" ", "%20"))}">Pedir por WhatsApp</a></p>')
        mismos = [q for q in datos if q["genero"] == p["genero"] and not q["agotado"] and q is not p]
        i = datos.index(p)
        otros = (mismos[i % max(1, len(mismos)):] + mismos)[:8]
        relacionados = "".join(f'<li><a href="{q["slug"]}.html">{html.escape(titulo(q["nombre"]))}</a> <span class="m">{gs(q["precio"])}</span></li>' for q in otros)
        cuerpo = f"""<nav><a href="/">Scentia</a> › <a href="/perfumes/">Perfumes {p['genero'].lower()}</a> › {html.escape(nombre)}</nav>
<div class="prod"><img src="/{p['foto']}" alt="{html.escape(nombre + ml)}, perfume original para {p['genero'].lower()}, frasco y caja" width="800" height="667">
<div><h1>{html.escape(nombre)}{ml}</h1>
<p class="m">Perfume original · {p['genero']} · {disp}</p>
<div class="precio">{gs(p['precio'])}</div>{boton}
<p>Frasco entero de {html.escape(nombre)}{ml}, 100% original. Hacemos delivery y envíos a todo Paraguay: el costo depende del destino y lo coordinamos por WhatsApp.</p>
<p>¿Querés probarlo antes? Mirá nuestros <a href="/#decants">decants de 5 y 10 ml</a>.</p></div></div>
<h2>Otros perfumes para {p['genero'].lower()}</h2><ul class="l">{relacionados}</ul>"""
        jsonld = [{
            "@context": "https://schema.org", "@type": "Product", "name": f"{nombre}{ml}", "image": img,
            "description": f"Perfume original {nombre}{ml} para {p['genero'].lower()}.", "url": url,
            "offers": {"@type": "Offer", "price": p["precio"], "priceCurrency": "PYG", "url": url,
                       "availability": "https://schema.org/OutOfStock" if p["agotado"] else "https://schema.org/InStock",
                       "itemCondition": "https://schema.org/NewCondition", "seller": {"@type": "Organization", "name": "Scentia"},
                       "shippingDetails": {"@type": "OfferShippingDetails", "shippingDestination": {"@type": "DefinedRegion", "addressCountry": "PY"}}}},
            {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
                {"@type": "ListItem", "position": 1, "name": "Scentia", "item": SITIO + "/"},
                {"@type": "ListItem", "position": 2, "name": "Perfumes", "item": SITIO + "/perfumes/"},
                {"@type": "ListItem", "position": 3, "name": f"{nombre}{ml}", "item": url}]}]
        (out / f"{p['slug']}.html").write_text(pagina(t, d, url, cuerpo, jsonld, img), encoding="utf-8")

    # lista completa: lo que Google lee para descubrir las páginas
    def lista(g):
        return "".join(f'<li><a href="{p["slug"]}.html">{html.escape(titulo(p["nombre"]))}{" " + str(p["ml"]) + " ml" if p["ml"] else ""}</a>'
                       f' <span class="m">{gs(p["precio"])}{" · agotado" if p["agotado"] else ""}</span></li>'
                       for p in sorted(datos, key=lambda x: x["nombre"]) if p["genero"] == g)
    cuerpo = f"""<nav><a href="/">Scentia</a> › Perfumes</nav>
<h1>Perfumes árabes originales en Paraguay</h1>
<p>Lista completa de frascos enteros con su precio en guaraníes. Delivery y envíos a todo Paraguay. Para probar antes de comprar el frasco, mirá nuestros <a href="/#decants">decants de 5 y 10 ml</a>.</p>
<h2>Perfumes para dama</h2><ul class="l">{lista("Dama")}</ul>
<h2>Perfumes para caballero</h2><ul class="l">{lista("Caballero")}</ul>"""
    (out / "index.html").write_text(pagina("Lista de perfumes árabes originales y precios en Paraguay | Scentia",
        f"{len(datos)} perfumes árabes originales para dama y caballero con su precio en Paraguay: Lattafa, Armaf, Maison Alhambra, Afnan y más. Delivery y envíos a todo el país.",
        SITIO + "/perfumes/", cuerpo, {"@context": "https://schema.org", "@type": "CollectionPage", "name": "Perfumes árabes originales", "url": SITIO + "/perfumes/"}),
        encoding="utf-8")

    # portada: negocio, decants con precio y preguntas frecuentes
    idx = (AQUI / "index.html").read_text(encoding="utf-8")
    precios = dict(re.findall(r'"(\d+ ml)": (\d+)', re.search(r"const PRECIO = \{[^}]*\}", idx).group(0)))
    decants = re.findall(r'\{img:"([^"]+)", nombre:"([^"]+)", marca:"([^"]+)"', idx)
    portada = [
        {"@context": "https://schema.org", "@type": "OnlineStore", "name": "Scentia", "url": SITIO + "/",
         "logo": SITIO + "/img/logo.png", "description": "Perfumes árabes originales, decants de 5 y 10 ml y frascos enteros en Paraguay.",
         "telephone": "+595972166484", "areaServed": {"@type": "Country", "name": "Paraguay"}, "currenciesAccepted": "PYG",
         "sameAs": ["https://www.instagram.com/scentiaprofumo/"]},
        {"@context": "https://schema.org", "@type": "ItemList", "name": "Decants de perfumes árabes", "itemListElement": [
            {"@type": "ListItem", "position": i + 1, "item": {
                "@type": "Product", "name": f"Decant {n} de {m}", "brand": {"@type": "Brand", "name": m}, "image": f"{SITIO}/img/{img}.jpg",
                "offers": {"@type": "AggregateOffer", "priceCurrency": "PYG", "lowPrice": min(map(int, precios.values())),
                           "highPrice": max(map(int, precios.values())), "offerCount": len(precios)}}}
            for i, (img, n, m) in enumerate(decants)]},
        {"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
            {"@type": "Question", "name": "¿Qué es un decant?", "acceptedAnswer": {"@type": "Answer", "text": "Es perfume original sacado del frasco y pasado a un atomizador chico de 5 o 10 ml, para probarlo antes de comprar el frasco entero."}},
            {"@type": "Question", "name": "¿Los perfumes son originales?", "acceptedAnswer": {"@type": "Answer", "text": "Sí. Cada decant sale del frasco original; no vendemos imitaciones."}},
            {"@type": "Question", "name": "¿Para cuánto alcanza un decant?", "acceptedAnswer": {"@type": "Answer", "text": "5 ml rinden de 70 a 80 atomizaciones y 10 ml de 130 a 160."}},
            {"@type": "Question", "name": "¿Hacen envíos?", "acceptedAnswer": {"@type": "Answer", "text": "Sí, contamos con delivery y hacemos envíos a todo Paraguay. El costo depende del destino."}}]}]
    idx = re.sub(r'(<script type="application/ld\+json">).*?(</script>)',
                 lambda m: m.group(1) + json.dumps(portada, ensure_ascii=False) + m.group(2), idx, count=1, flags=re.S)
    (AQUI / "index.html").write_text(idx, encoding="utf-8")

    urls = [(SITIO + "/", "1.0"), (SITIO + "/perfumes/", "0.8")] + [(f"{SITIO}/perfumes/{p['slug']}.html", "0.6") for p in datos]
    (AQUI / "sitemap.xml").write_text('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + "".join(f"<url><loc>{u}</loc><lastmod>{HOY}</lastmod><priority>{pr}</priority></url>\n" for u, pr in urls) + "</urlset>\n", encoding="utf-8")
    (AQUI / "robots.txt").write_text(f"User-agent: *\nAllow: /\nDisallow: /_candidatas/\n\nSitemap: {SITIO}/sitemap.xml\n", encoding="utf-8")
    print(len(datos), "páginas de perfume +", len(urls), "URLs en el sitemap")


if __name__ == "__main__":
    main()
