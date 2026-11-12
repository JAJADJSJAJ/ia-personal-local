"""Exposición al azar: un artículo cualquiera de Wikipedia en español. Solo lectura."""
import json
import re
import urllib.parse
import urllib.request

from . import config

API = "https://es.wikipedia.org/w/api.php"


def _pedir(params: dict) -> dict:
    url = API + "?" + urllib.parse.urlencode(params)
    pedido = urllib.request.Request(url, headers={"User-Agent": config.USER_AGENT})
    with urllib.request.urlopen(pedido, timeout=30) as r:
        return json.load(r)


def _limpiar(texto: str) -> str:
    texto = re.sub(r"[​‌‍⁠﻿]", "", texto)  # caracteres invisibles de Wikipedia
    texto = re.sub(r"\n=+[^=\n]+=+\n", "\n", texto)  # títulos de sección
    texto = re.sub(r"\n{2,}", "\n\n", texto)
    return texto.strip()


def _recortar(texto: str) -> str:
    """Corta en el último párrafo completo antes del máximo."""
    if len(texto) <= config.LARGO_MAXIMO:
        return texto
    corte = texto.rfind("\n", 0, config.LARGO_MAXIMO)
    if corte < config.LARGO_MINIMO:
        corte = texto.rfind(". ", 0, config.LARGO_MAXIMO) + 1
    return texto[:corte].strip()


def articulo_al_azar(ya_leidos: set[str], intentos: int = 8) -> dict | None:
    """Devuelve {titulo, url, texto} de un artículo útil y no leído, o None."""
    for _ in range(intentos):
        datos = _pedir({
            "action": "query", "format": "json", "formatversion": "2",
            "generator": "random", "grnnamespace": "0", "grnlimit": "1",
            "prop": "extracts|info", "explaintext": "1", "inprop": "url",
        })
        paginas = datos.get("query", {}).get("pages", [])
        if not paginas:
            continue
        p = paginas[0]
        titulo, url = p.get("title", ""), p.get("fullurl", "")
        texto = _limpiar(p.get("extract", ""))
        if url in ya_leidos or titulo.startswith("Anexo:"):
            continue
        if len(texto) < config.LARGO_MINIMO or "puede referirse a" in texto[:300]:
            continue
        return {"titulo": titulo, "url": url, "texto": _recortar(texto)}
    return None
