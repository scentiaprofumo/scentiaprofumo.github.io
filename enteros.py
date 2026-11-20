"""Saca los perfumes enteros de los PDF mensuales (Dama / Caballero) para la web.
Uso: python enteros.py "<pdf dama>" "<pdf caballero>"
Escribe enteros/enteros.json y una foto por perfume en enteros/img/.
Cada página trae hasta 6 perfumes (2 columnas x 3 filas): nombre y precio debajo de la foto."""
import json
import re
import sys
from pathlib import Path
import pymupdf

AQUI = Path(__file__).parent
OUT = AQUI / "enteros"
# "150.000 Gs", "150. 000", "125.000Gs oferta", "205.000 de 60ml"
PRECIO = re.compile(r"(\d{2,3})\.{0,2}\s?(\d{3})\s*(?:G\s*S)?\s*(OFERTA)?\s*(?:DE\s*(\d{2,3})\s*ML)?\s*$", re.I)
valor = lambda m: int(m.group(1) + m.group(2))
ML = re.compile(r"(\d{2,3})\s*ML\b", re.I)


# precio de venta: el PDF trae el precio del proveedor; al usuario le cobran DESCUENTO menos (ej. Kit Radio:
# catálogo 175.000, pagó 160.000). Venta = (catálogo - DESCUENTO) x MARGEN, redondeado para arriba a 5.000.
# El costo no se guarda en la web (es pública).
# Desde CARO de catálogo el margen baja a MARGEN_CARO (para competir), pero nunca por debajo de PISO_CARO:
# así un perfume caro no queda más barato que uno que cuesta menos.
# Premium (decants a otro precio): catálogo desde PREMIUM.
DESCUENTO, MARGEN, REDONDEO = 15000, 1.5, 5000
CARO, MARGEN_CARO, PISO_CARO = 200000, 1.4, 280000
PREMIUM = 220000


def precio_venta(catalogo):
    redondear = lambda x: -(-int(x) // REDONDEO) * REDONDEO
    if catalogo >= CARO:
        return max(redondear((catalogo - DESCUENTO) * MARGEN_CARO), PISO_CARO)
    return redondear((catalogo - DESCUENTO) * MARGEN)


assert precio_venta(175000) == 240000 and precio_venta(195000) == 270000
assert precio_venta(200000) == 280000 and precio_venta(220000) == 290000 and precio_venta(300000) == 400000
assert all(precio_venta(c) <= precio_venta(c + 1000) for c in range(100000, 600000, 1000))


def lineas(pagina):
    for b in pagina.get_text("dict")["blocks"]:
        for l in b.get("lines", []):
            t = " ".join("".join(s["text"] for s in l["spans"]).split())
            if t:
                yield t, pymupdf.Rect(l["bbox"])


def perfumes_de(pagina):
    mitad = pagina.rect.width / 2
    ls = list(lineas(pagina))
    agotados = [r for t, r in ls if "AGOTADO" in t.upper()]
    textos = [(t, r) for t, r in ls if "AGOTADO" not in t.upper() and t.upper() not in ("OFERTA", "OFERTAS")]
    columna = lambda r: 0 if (r.x0 + r.x1) / 2 < mitad else 1
    es_precio = lambda t: (m := PRECIO.search(t)) and valor(m) >= 30000
    # "KHASHABI 100 ML 195.000" con "130.000 Gs" abajo: es el nombre con el precio anterior, no un perfume aparte
    def debajo(r, t=""):
        con_nombre = re.search(r"[A-Z]{3}", ML.sub("", PRECIO.sub("", t)).upper())  # "100 ML 185.000" es otro tamaño, no un precio viejo
        return con_nombre and [rr for tt, rr in textos if es_precio(tt) and columna(rr) == columna(r) and 0 < rr.y0 - r.y0 < 30]
    viejos = sum(1 for t, r in textos if es_precio(t) and debajo(r, t))
    textos = [(PRECIO.sub("", t).strip() if es_precio(t) and debajo(r, t) else t, r) for t, r in textos]
    salida = []
    for t, r in textos:
        m = PRECIO.search(t)
        if not es_precio(t):
            continue
        col = columna(r)
        # el nombre: lo que hay antes del precio en esta línea + la línea de arriba en la misma columna
        resto = t[:m.start()].strip()
        arriba = [(tt, rr) for tt, rr in textos if rr.y0 < r.y0 - 4 and rr.y1 <= r.y0 + 8 and r.y0 - rr.y1 < 45
                  and columna(rr) == col and not es_precio(tt) and re.search(r"[A-Z]{3}", tt.upper())]
        nombre_r = max(arriba, key=lambda x: x[1].y1) if arriba else None
        nombre = " ".join(x for x in [nombre_r[0] if nombre_r else "", resto, f"{m.group(4)} ML" if m.group(4) else ""] if x)
        top_label = nombre_r[1].y0 if nombre_r else r.y0
        salida.append(dict(nombre=nombre, precio=valor(m), oferta=bool(m.group(3)), col=col, y_label=top_label, y_fin=r.y1))
    # la foto de cada perfume es lo que hay entre la etiqueta anterior de su columna y la suya
    for p in salida:
        anteriores = [q["y_fin"] for q in salida if q["col"] == p["col"] and q["y_fin"] < p["y_label"]]
        top = max(anteriores) + 2 if anteriores else 20
        x0 = 0 if p["col"] == 0 else mitad
        p["celda"] = pymupdf.Rect(x0, top, x0 + mitad, p["y_label"] - 1)
    # otro tamaño del mismo perfume ("150 ML 220.000 Gs" debajo de "100 ML 185.000 Gs"): mismo nombre y misma foto
    for p in sorted(salida, key=lambda p: p["y_label"]):
        if not re.search(r"[A-Z]{3}", ML.sub("", p["nombre"]).upper()) or p["celda"].height < 40:
            q = max((q for q in salida if q is not p and q["col"] == p["col"] and q["y_fin"] <= p["y_label"] + 2),
                    key=lambda q: q["y_fin"], default=None)
            if q:
                p["nombre"] = ML.sub("", q["nombre"]).strip() + " " + (ML.findall(p["nombre"])[-1:] or [""])[0] + " ML"
                p["celda"] = q["celda"]
    for p in salida:
        p["agotado"] = any(p["celda"].contains(pymupdf.Point((a.x0 + a.x1) / 2, (a.y0 + a.y1) / 2)) for a in agotados)
    return salida, viejos


def limpiar(nombre):
    tam = ML.findall(nombre)  # "9PM LATTAFA 100 ML 150 ML": vale el último
    ml = int(tam[-1]) if tam else None
    n = " ".join(ML.sub("", nombre).split()).strip(" -·|")
    n = re.sub(r"\s+GS$", "", n, flags=re.I)
    return n, ml


def main(pdfs):
    (OUT / "img").mkdir(parents=True, exist_ok=True)
    for f in (OUT / "img").glob("*.jpg"):
        f.unlink()
    todos = []
    for pdf in pdfs:
        genero = "Dama" if "dama" in Path(pdf).name.lower() else "Caballero"
        doc = pymupdf.open(pdf)
        esperados = sum(1 for pg in doc for t, _ in lineas(pg)
                        if (m := PRECIO.search(t)) and valor(m) >= 30000)
        # control aparte: todos los números con forma de precio que haya en el PDF
        a_ojo = sum(len(re.findall(r"\d{2,3}\.\s?\d{3}(?!\d)", t)) for pg in doc for t, _ in lineas(pg))
        n_gen = viejos_total = 0
        for i, pg in enumerate(doc):
            perfumes, viejos = perfumes_de(pg)
            viejos_total += viejos
            for p in perfumes:
                nombre, ml = limpiar(p["nombre"])
                n_gen += 1
                foto = f"{genero[0].lower()}{n_gen:03d}.jpg"
                pix = pg.get_pixmap(clip=p["celda"], dpi=110)
                pix.save(OUT / "img" / foto, jpg_quality=78)
                todos.append(dict(id=foto[:-4], genero=genero, nombre=nombre, ml=ml, precio=precio_venta(p["precio"]), premium=p["precio"] >= PREMIUM,
                                  agotado=p["agotado"], oferta=p["oferta"], foto=f"enteros/img/{foto}", pagina=i + 1))
        assert n_gen + viejos_total == esperados, f"{genero}: saqué {n_gen} de {esperados} precios"
        if a_ojo != esperados:
            print(f"OJO {genero}: hay {a_ojo} números con forma de precio y reconocí {esperados}")
        print(genero, n_gen, "perfumes,", sum(t["agotado"] for t in todos if t["genero"] == genero), "agotados")
    # el PDF repite algunos perfumes en dos páginas: queda el primero
    vistos = set()
    todos = [t for t in todos if (k := (t["genero"], t["nombre"], t["ml"], t["precio"])) not in vistos and not vistos.add(k)]
    raros = [t for t in todos if len(t["nombre"]) < 3 or t["precio"] > 600000]
    for r in raros:
        print("REVISAR", r)
    # las fotos Scentia ya elegidas (fotos_finales.py) siguen valiendo el mes que viene
    elegidas = AQUI / "fotos_elegidas.json"
    elegidas = json.loads(elegidas.read_text(encoding="utf-8")) if elegidas.exists() else {}
    for t in todos:
        # recorte ya hecho por fotos_pdf.py (mismo PDF = mismo id): se reusa; un PDF nuevo pide correr fotos_pdf.py
        if (AQUI / f'enteros/fotos_pdf/{t["id"]}.jpg').exists() and not t["agotado"]:
            t["foto"] = f'enteros/fotos_pdf/{t["id"]}.jpg'
        t["foto"] = elegidas.get(f'{t["genero"]}|{t["nombre"].upper()}|{t["ml"]}', t["foto"])
    (OUT / "enteros.json").write_text(json.dumps(todos, ensure_ascii=False, indent=0), encoding="utf-8")


if __name__ == "__main__":
    main(sys.argv[1:])
