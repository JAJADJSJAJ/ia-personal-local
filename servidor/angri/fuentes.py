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


def buscar(consulta: str, ya_leidos: set[str], cantidad: int = 5) -> list[str]:
    """Títulos de artículos de Wikipedia que responden a la búsqueda y no se leyeron."""
    datos = _pedir({
        "action": "query", "format": "json", "formatversion": "2",
        "list": "search", "srsearch": consulta, "srlimit": str(cantidad * 2), "srnamespace": "0",
    })
    titulos = [r["title"] for r in datos.get("query", {}).get("search", [])]
    url = "https://es.wikipedia.org/wiki/"
    return [t for t in titulos if url + t.replace(" ", "_") not in ya_leidos and not t.startswith("Anexo:")][:cantidad]


def articulo(titulo: str) -> dict | None:
    """El artículo completo (sin recortar) de un título."""
    datos = _pedir({
        "action": "query", "format": "json", "formatversion": "2", "titles": titulo,
        "prop": "extracts|info", "explaintext": "1", "inprop": "url", "redirects": "1",
    })
    paginas = datos.get("query", {}).get("pages", [])
    if not paginas or "missing" in paginas[0]:
        return None
    p = paginas[0]
    texto = _limpiar(p.get("extract", ""))
    if len(texto) < config.LARGO_MINIMO // 2:
        return None
    return {"titulo": p.get("title", titulo), "url": p.get("fullurl", ""), "texto": texto}


def parrafos_relevantes(texto: str, vector_pregunta, embeber) -> str:
    """Se queda con los párrafos más relacionados con la pregunta, en su orden original."""
    parrafos = [p.strip() for p in texto.split("\n") if len(p.strip()) > 80]
    if len(parrafos) <= config.PARRAFOS_POR_LECTURA:
        return _recortar("\n\n".join(parrafos))
    m = embeber(parrafos)
    elegidos = sorted(sorted(range(len(parrafos)), key=lambda i: -float(m[i] @ vector_pregunta))
                      [: config.PARRAFOS_POR_LECTURA])
    return _recortar("\n\n".join(parrafos[i] for i in elegidos))


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
