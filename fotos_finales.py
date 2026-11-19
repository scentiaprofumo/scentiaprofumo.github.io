"""Con la elección de la página "Elegir fotos" pone una foto de internet a los perfumes enteros cuya foto del PDF
sale mal: solo el perfume sobre blanco, igual que las del PDF.
Uso: python fotos_finales.py "FOTOS c180:3 c141:1 ..."   (0 = ninguna: queda la foto del PDF;
"d156:1s" = recorte simple de fondo blanco, para cuando rembg se come parte de la caja)
Guarda enteros/fotos/<clave>.jpg y las anota en fotos_elegidas.json (por nombre, no por id:
los id cambian cada mes, los nombres no). enteros.py las vuelve a aplicar y fotos_pdf.py no las pisa."""
import json
import re
import sys
from pathlib import Path

AQUI = Path(__file__).parent
sys.path.insert(0, str(AQUI.parent / "posts"))
from prototipo_fotos import sin_fondo, sin_fondo_simple  # noqa: E402
from fotos_pdf import en_blanco  # noqa: E402

ELEGIDAS = AQUI / "fotos_elegidas.json"


def clave(p):
    return f'{p["genero"]}|{p["nombre"].upper()}|{p["ml"]}'


def aplicar(enteros):
    elegidas = json.loads(ELEGIDAS.read_text(encoding="utf-8")) if ELEGIDAS.exists() else {}
    for p in enteros:
        if clave(p) in elegidas:
            p["foto"] = elegidas[clave(p)]
    return enteros


def main(texto):
    cands = {c["id"]: c for c in json.loads((AQUI / "_candidatas/candidatas.json").read_text(encoding="utf-8"))}
    elegidas = json.loads(ELEGIDAS.read_text(encoding="utf-8")) if ELEGIDAS.exists() else {}
    (AQUI / "enteros/fotos").mkdir(parents=True, exist_ok=True)
    for pid, n, simple in re.findall(r"([cd]\d{3}):(\d)(s?)", texto):
        c, n = cands[pid], int(n)
        if n == 0:
            continue
        foto = (sin_fondo_simple if simple else sin_fondo)(AQUI / "_candidatas" / c["fotos"][n - 1]["archivo"])
        slug = re.sub(r"[^a-z0-9]+", "-", f'{c["genero"]}-{c["nombre"]}-{c["ml"]}'.lower()).strip("-")
        en_blanco(foto).save(AQUI / "enteros/fotos" / f"{slug}.jpg", quality=90, optimize=True)
        elegidas[clave(c)] = f"enteros/fotos/{slug}.jpg"
    ELEGIDAS.write_text(json.dumps(elegidas, ensure_ascii=False, indent=1), encoding="utf-8")
    datos = json.loads((AQUI / "enteros/enteros.json").read_text(encoding="utf-8"))
    (AQUI / "enteros/enteros.json").write_text(json.dumps(aplicar(datos), ensure_ascii=False, indent=0), encoding="utf-8")
    print(len(elegidas), "perfumes con foto de internet")


if __name__ == "__main__":
    main(sys.argv[1])
