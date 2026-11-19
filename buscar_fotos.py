"""Busca 3 fotos candidatas por perfume entero (Firecrawl, búsqueda de imágenes) y las baja.
Uso: python buscar_fotos.py 30      -> los primeros 30 de la lista de prioridad
Escribe _candidatas/<id>_<n>.jpg y _candidatas/candidatas.json. La clave sale de la config de Claude Code."""
import io
import json
import os
import sys
import urllib.parse
from pathlib import Path
import requests
from PIL import Image

AQUI = Path(__file__).parent
DEST = AQUI / "_candidatas"
DECANTS = ["TROPICAL VIBE", "CLUB DE NUIT URBAN ELXIR", "SUMMIT ELIXIR", "SABAH AL WARD", "QAED AL FURSAN", "ECLAIRE PISTACHE"]
POPULARES = ["KHAMRAH", "ASAD", "CLUB DE NUIT INTENSE", "9PM", "HAWAS", "YARA", "ODYSSEY", "BADEE", "FAKHAR", "AMEER AL ARAB", "JEAN LOWE"]
# sitios que dan miniaturas, collages o capturas en vez de la foto del producto
EVITAR = ("ebay.", "amazon.", "pinterest.", "instagram.", "tiktok.", "youtube.", "facebook.", "fimgs.net", "fragrantica", "reddit.", "aliexpress.")
OFICIALES = ("lattafa", "maisonalhambra", "armaf", "alwataniah", "rayhaan", "afnan", "rasasi", "alharamain", "fragranceworld")


def clave():
    d = json.loads((Path.home() / ".claude.json").read_text(encoding="utf-8"))
    return d["mcpServers"]["firecrawl"]["env"]["FIRECRAWL_API_KEY"]


def prioridad(todos, n):
    libres = [p for p in todos if not p["agotado"]]
    elegidos = [p for k in DECANTS for p in libres if p["nombre"] == k]
    elegidos += [p for p in libres if p["oferta"] and p not in elegidos]
    for k in POPULARES:
        elegidos += [p for p in libres if p["nombre"].startswith(k) and p not in elegidos][:2]
    return elegidos[:n]


def buscar(q, key):
    r = requests.post("https://api.firecrawl.dev/v2/search", headers={"Authorization": f"Bearer {key}"},
                      json={"query": q, "sources": ["images"], "limit": 10}, timeout=60)
    r.raise_for_status()
    return r.json().get("data", {}).get("images", [])


def puntaje(img):
    host = urllib.parse.urlparse(img.get("url", "")).netloc + urllib.parse.urlparse(img["imageUrl"]).netloc
    w, h = img.get("imageWidth") or 0, img.get("imageHeight") or 0
    if any(e in host for e in EVITAR) or min(w, h) < 600 or not 0.6 < w / max(h, 1) < 1.6:
        return None
    return (any(o in host for o in OFICIALES), w * h)


def main(n, ids=()):
    DEST.mkdir(exist_ok=True)
    key = clave()
    todos = json.loads((AQUI / "enteros/enteros.json").read_text(encoding="utf-8"))
    salida = []
    for p in ([p for p in todos if p["id"] in ids] if ids else prioridad(todos, n)):
        q = f'{p["nombre"]} {p["ml"] or 100}ml perfume bottle box'
        imgs = sorted((i for i in buscar(q, key) if puntaje(i)), key=puntaje, reverse=True)
        fotos = []
        for img in imgs:
            if len(fotos) == 3:
                break
            try:
                r = requests.get(img["imageUrl"], timeout=30, headers={"User-Agent": "Mozilla/5.0"})
                im = Image.open(io.BytesIO(r.content)).convert("RGB")
            except Exception:
                continue
            im.thumbnail((1200, 1200))
            f = DEST / f'{p["id"]}_{len(fotos) + 1}.jpg'
            im.save(f, quality=90)
            fotos.append(dict(archivo=f.name, origen=img.get("url"), imagen=img["imageUrl"]))
        salida.append(dict(id=p["id"], nombre=p["nombre"], ml=p["ml"], genero=p["genero"], actual=p["foto"], fotos=fotos))
        print(p["id"], p["nombre"], len(fotos), "fotos")
    (DEST / "candidatas.json").write_text(json.dumps(salida, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    # python buscar_fotos.py 30   |   python buscar_fotos.py ids d135 c084 ...
    main(0, sys.argv[2:]) if sys.argv[1] == "ids" else main(int(sys.argv[1]))
