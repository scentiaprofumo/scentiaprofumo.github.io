"""Con la elección de la página "Elegir fotos" arma la foto Scentia de cada perfume entero.
Uso: python fotos_finales.py "FOTOS c180:3 c141:1 ..."   (0 = ninguna: queda la foto del PDF)
Guarda enteros/fotos/<clave>.jpg y las anota en fotos_elegidas.json (por nombre, no por id:
los id cambian cada mes, los nombres no). enteros.py las vuelve a aplicar al actualizar el mes."""
import json
import re
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright

AQUI = Path(__file__).parent
sys.path.insert(0, str(AQUI.parent / "posts"))
import bienvenida as B  # noqa: E402
from prototipo_fotos import sin_fondo, png_uri, ESCENA  # noqa: E402

ELEGIDAS = AQUI / "fotos_elegidas.json"


def clave(p):
    return f'{p["genero"]}|{p["nombre"].upper()}|{p["ml"]}'


def aplicar(enteros):
    """Pone la foto Scentia a los perfumes que ya la tienen."""
    elegidas = json.loads(ELEGIDAS.read_text(encoding="utf-8")) if ELEGIDAS.exists() else {}
    for p in enteros:
        if clave(p) in elegidas:
            p["foto"] = elegidas[clave(p)]
    return enteros


def main(texto):
    cands = {c["id"]: c for c in json.loads((AQUI / "_candidatas/candidatas.json").read_text(encoding="utf-8"))}
    elegidas = json.loads(ELEGIDAS.read_text(encoding="utf-8")) if ELEGIDAS.exists() else {}
    (AQUI / "enteros/fotos").mkdir(parents=True, exist_ok=True)
    B.OUT = AQUI.parent / "posts/bienvenida"
    B.LOGO = B.uri(B.FLY / "logo-scentia.png")
    fondo = AQUI.parent / "posts/prototipo/_marmol_sq.png"
    B.OUT = AQUI / "_candidatas"  # B.render guarda acá el PNG
    revisar = []
    with sync_playwright() as pw:
        for pid, n in re.findall(r"([cd]\d{3}):(\d)", texto):
            c, n = cands[pid], int(n)
            if n == 0:
                continue
            foto = sin_fondo(AQUI / "_candidatas" / c["fotos"][n - 1]["archivo"])
            # si casi no se borró nada, el fondo no era liso: la foto entra con su fondo y conviene mirarla
            alfa = foto.getchannel("A").histogram()
            if alfa[0] / sum(alfa) < 0.03:
                revisar.append(c["nombre"])
            slug = re.sub(r"[^a-z0-9]+", "-", f'{c["genero"]}-{c["nombre"]}-{c["ml"]}'.lower()).strip("-")
            html = B.pagina(800, 670, B.uri(fondo), ESCENA.format(pb=70, gy=40, gw=620, foto=png_uri(foto), mw=640, mh=520, bw=420, lw=520))
            B.render(pw, slug, 800, 670, html)
            png = AQUI / "_candidatas" / f"{slug}.png"
            from PIL import Image
            Image.open(png).convert("RGB").save(AQUI / "enteros/fotos" / f"{slug}.jpg", quality=86, optimize=True)
            png.unlink()
            elegidas[clave(c)] = f"enteros/fotos/{slug}.jpg"
    ELEGIDAS.write_text(json.dumps(elegidas, ensure_ascii=False, indent=1), encoding="utf-8")
    datos = json.loads((AQUI / "enteros/enteros.json").read_text(encoding="utf-8"))
    (AQUI / "enteros/enteros.json").write_text(json.dumps(aplicar(datos), ensure_ascii=False, indent=0), encoding="utf-8")
    print(len(elegidas), "perfumes con foto Scentia")
    for r in revisar:
        print("REVISAR (fondo no liso):", r)


if __name__ == "__main__":
    main(sys.argv[1])
