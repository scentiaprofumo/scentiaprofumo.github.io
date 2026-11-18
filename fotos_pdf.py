"""Foto Scentia desde la foto del propio PDF: se recorta el frasco y la caja (sin las barritas de notas,
el círculo de "Inspiración" ni el fondo) y se pone sobre el mármol negro.
Uso: python fotos_pdf.py "<pdf dama>" "<pdf caballero>" [id id ...]   (sin ids = todos menos los agotados)
Escribe enteros/fotos_pdf/<id>.jpg y apunta enteros.json a esas fotos. Cada mes: primero enteros.py, después este."""
import json
import sys
from pathlib import Path
import numpy as np
import pymupdf
from PIL import Image
from playwright.sync_api import sync_playwright

AQUI = Path(__file__).parent
sys.path.insert(0, str(AQUI.parent / "posts"))
import bienvenida as B  # noqa: E402
from prototipo_fotos import png_uri, ESCENA  # noqa: E402
import enteros as E  # noqa: E402

OUT = AQUI / "enteros/fotos_pdf"
# el recorte no los separa bien de las barritas o del círculo de "Inspiración": quedan con la foto del PDF
NO_RECORTAR = {"KHAMRAH QAHWA", "CHANTS TENDERINA", "ASAD ELIXIR", "JEAN LOWE VIBE", "FAKHAR BLACK", "VICTORIOSO",
               "HAYAATI GOLD ELIXIR", "ODYSSEY ARTISTO", "HONOR AND GLORY", "AJMAL EHSAAS"}


def solo_producto(im, rgba):
    """Deja la mancha más grande (caja + frasco suelen tocarse) y las casi tan grandes; saca barritas y círculos.
    Productos blancos sobre fondo blanco: rembg los deja agujereados, así que dentro del contorno del producto
    vuelve opaco todo lo que no sea el fondo blanco que llega desde los bordes."""
    from scipy import ndimage
    from scipy.spatial import ConvexHull
    from PIL import ImageDraw
    alfa = np.asarray(rgba.getchannel("A")).copy()
    etiquetas, n = ndimage.label(alfa > 60)
    if n == 0:
        return rgba
    # se queda con la pieza más grande y las piezas firmes (alfa alto) pegadas a ella: el frasco al lado de la caja.
    # Las barritas de notas salen con alfa bajo; el círculo de "Inspiración" y el frasco de referencia, separados.
    cajas = ndimage.find_objects(etiquetas)
    areas = ndimage.sum(alfa > 60, etiquetas, range(1, n + 1))
    firmes = ndimage.mean(alfa, etiquetas, range(1, n + 1))
    quedan = [int(np.argmax(areas))]
    cambio = True
    while cambio:
        cambio = False
        for i, c in enumerate(cajas):
            if i in quedan or areas[i] < 0.15 * areas.max() or firmes[i] < 200:
                continue
            for j in quedan:
                k = cajas[j]
                gap = max(c[1].start - k[1].stop, k[1].start - c[1].stop)
                if gap <= 30 and c[0].start < k[0].stop and k[0].start < c[0].stop:
                    quedan.append(i)
                    cambio = True
                    break
    mascara = np.isin(etiquetas, [i + 1 for i in quedan])
    # contorno (envolvente convexa) del producto
    ys, xs = np.nonzero(mascara)
    pts = np.c_[xs, ys][:: max(1, len(xs) // 4000)]
    casco = Image.new("L", im.size, 0)
    ImageDraw.Draw(casco).polygon([tuple(pts[i]) for i in ConvexHull(pts).vertices], fill=255)
    # fondo: blanco casi puro conectado con los bordes
    marca = im.copy()
    w, h = im.size
    for xy in [(0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1)]:
        ImageDraw.floodfill(marca, xy, (255, 0, 255), thresh=12)
    fondo = np.all(np.asarray(marca) == (255, 0, 255), axis=2)
    alfa[(np.asarray(casco) > 0) & ~fondo] = 255
    alfa[~ndimage.binary_dilation(np.asarray(casco) > 0, iterations=2)] = 0
    out = im.convert("RGBA")
    out.putalpha(Image.fromarray(alfa))
    return out.crop(Image.fromarray(((alfa > 60) * 255).astype(np.uint8)).getbbox())


def main(pdfs, ids):
    from rembg import new_session, remove
    sesion = new_session("isnet-general-use")
    OUT.mkdir(parents=True, exist_ok=True)
    datos = json.loads((AQUI / "enteros/enteros.json").read_text(encoding="utf-8"))
    por_pagina = {}
    for p in datos:
        if ((p["id"] in ids) if ids else not p["agotado"]) and p["nombre"].upper() not in NO_RECORTAR:
            por_pagina.setdefault((p["genero"], p["pagina"]), []).append(p)
    docs = {("Dama" if "dama" in Path(f).name.lower() else "Caballero"): pymupdf.open(f) for f in pdfs}
    B.OUT = AQUI.parent / "posts/bienvenida"
    B.LOGO = B.uri(B.FLY / "logo-scentia.png")
    fondo = B.uri(AQUI.parent / "posts/prototipo/_marmol_sq.png")
    B.OUT = OUT
    hechos = 0
    with sync_playwright() as pw:
        for (genero, pagina), lista in por_pagina.items():
            pg = docs[genero][pagina - 1]
            perfumes, _ = E.perfumes_de(pg)
            for p in lista:
                # la celda de este perfume en la página: misma etiqueta de nombre y precio
                cel = next((q["celda"] for q in perfumes if q["precio"] == p["precio"]
                            and E.limpiar(q["nombre"])[0] == p["nombre"]), None)
                if cel is None:
                    continue
                pix = pg.get_pixmap(clip=cel, dpi=220)
                im = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
                foto = solo_producto(im, remove(im, session=sesion))
                html = B.pagina(800, 670, fondo, ESCENA.format(pb=70, gy=40, gw=620, foto=png_uri(foto), mw=640, mh=520, bw=420, lw=520))
                B.render(pw, p["id"], 800, 670, html)
                png = OUT / f'{p["id"]}.png'
                Image.open(png).convert("RGB").save(OUT / f'{p["id"]}.jpg', quality=86, optimize=True)
                png.unlink()
                p["foto"] = f'enteros/fotos_pdf/{p["id"]}.jpg'
                hechos += 1
    (AQUI / "enteros/enteros.json").write_text(json.dumps(datos, ensure_ascii=False, indent=0), encoding="utf-8")
    print(hechos, "fotos")


if __name__ == "__main__":
    main(sys.argv[1:3], set(sys.argv[3:]))
