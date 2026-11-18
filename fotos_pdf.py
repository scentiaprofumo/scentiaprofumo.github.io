"""Foto de cada perfume entero desde la foto del propio PDF: queda solo el frasco y la caja sobre blanco,
sin las barritas de notas ni el círculo de "Inspiración" (decisión del usuario: nada más que el perfume).
Uso: python fotos_pdf.py "<pdf dama>" "<pdf caballero>" [id id ...]   (sin ids = todos menos los agotados)
Escribe enteros/fotos_pdf/<id>.jpg y apunta enteros.json a esas fotos. Cada mes: primero enteros.py, después este."""
import json
import sys
from pathlib import Path
import numpy as np
import pymupdf
from PIL import Image

AQUI = Path(__file__).parent
import enteros as E  # noqa: E402

OUT = AQUI / "enteros/fotos_pdf"
# el recorte no los separa bien de las barritas o del círculo de "Inspiración": quedan con la foto del PDF
NO_RECORTAR = set()
# sets con varios frascos en fila: la IA marca solo uno y el corte de la derecha se llevaría los demás
SIN_CORTE_DERECHA = {"KIT YARA"}
# las barritas o el círculo están pegados al producto: se pinta de blanco lo que queda fuera de (izquierda, derecha),
# en fracción del ancho de la foto, antes de recortar
FRANJA = {"HONOR AND GLORY": (0, .61), "CHANTS TENDERINA": (0, .70), "KHAMRAH QAHWA": (0, .55),
          "ASAD ELIXIR": (0, .655), "JEAN LOWE VIBE": (0, .655), "FAKHAR BLACK": (.03, .68), "VICTORIOSO": (0, .65),
          "HAYAATI GOLD ELIXIR": (0, .72), "ODYSSEY ARTISTO": (0, .735), "MOHRA": (0, .65)}


def solo_producto(im, rgba, corte_derecha=True):
    """La IA (isnet) solo decide QUÉ piezas son el producto (caja + frasco) y descarta barritas y círculos.
    El recorte en sí es borrar el fondo blanco que llega desde los bordes: nunca se come partes del producto."""
    from scipy import ndimage
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
    # fondo: blanco casi puro conectado con los bordes de la foto
    marca = im.copy()
    w, h = im.size
    for xy in [(0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1)]:
        ImageDraw.floodfill(marca, xy, (255, 0, 255), thresh=8)
    fondo = np.all(np.asarray(marca) == (255, 0, 255), axis=2)
    # queda todo lo que no es fondo y toca alguna pieza elegida: la caja y el frasco salen con su forma real,
    # aunque la IA no haya visto una parte clara; lo separado por blanco (barritas, círculo) se va
    # (antes se cortan los hilos finos de píxeles grises que a veces unen las barritas con la caja)
    solido = ndimage.binary_opening(~fondo, iterations=3)
    trozos, _ = ndimage.label(solido)
    elegidos = np.unique(trozos[mascara & solido])
    quedan = ndimage.binary_dilation(np.isin(trozos, elegidos[elegidos > 0]), iterations=4) & ~fondo
    # las barritas y el círculo de "Inspiración" siempre están a la derecha: se corta lo que sobresale a la derecha
    # de lo que la IA marcó como producto (a la izquierda no se toca: ahí suelen estar las cajas que no ve entera)
    if corte_derecha:
        quedan[:, np.nonzero(mascara)[1].max() + 6:] = False
    alfa = quedan.astype(np.uint8) * 255
    out = im.convert("RGBA")
    out.putalpha(Image.fromarray(alfa))
    return out.crop(Image.fromarray(((alfa > 60) * 255).astype(np.uint8)).getbbox())


def en_blanco(foto):
    """El perfume solo, sobre blanco, centrado en un lienzo 6:5 (el de las tarjetas de la web) con aire alrededor."""
    w, h = foto.size
    m = int(0.08 * max(w, h))
    cw, ch = w + 2 * m, h + 2 * m
    cw, ch = max(cw, int(ch * 1.2)), max(ch, int(cw / 1.2))
    lienzo = Image.new("RGBA", (cw, ch), (255, 255, 255, 255))
    lienzo.alpha_composite(foto, ((cw - w) // 2, (ch - h) // 2))
    return lienzo.convert("RGB")


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
    hechos = 0
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
            if p["nombre"].upper() in FRANJA:
                izq, der = FRANJA[p["nombre"].upper()]
                arr = np.asarray(im).copy()
                arr[:, :int(izq * im.width)] = 255
                arr[:, int(der * im.width):] = 255
                im = Image.fromarray(arr)
            foto = solo_producto(im, remove(im, session=sesion), p["nombre"].upper() not in SIN_CORTE_DERECHA)
            en_blanco(foto).save(OUT / f'{p["id"]}.jpg', quality=90, optimize=True)
            p["foto"] = f'enteros/fotos_pdf/{p["id"]}.jpg'
            hechos += 1
    (AQUI / "enteros/enteros.json").write_text(json.dumps(datos, ensure_ascii=False, indent=0), encoding="utf-8")
    print(hechos, "fotos")


if __name__ == "__main__":
    main(sys.argv[1:3], set(sys.argv[3:]))
