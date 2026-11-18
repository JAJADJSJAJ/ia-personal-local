"""Fuentes de lectura. Solo lectura.

- Al azar: un artículo cualquiera de Wikipedia en español.
- Para investigar, en orden: Wikipedia en español y Wikipedia en inglés. Si la búsqueda no trae nada,
  se prueba con el autocompletado (tolera nombres mal escritos: Zelenoborski -> Zelenoborsky).
- La web general queda lista (pagina_web) pero sin buscador: DuckDuckGo bloquea a los bots y no se esquiva.
  Hace falta una API de búsqueda con clave.
"""
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from html.parser import HTMLParser

from . import config

API = "https://es.wikipedia.org/w/api.php"
APIS = {"es": API, "en": "https://en.wikipedia.org/w/api.php"}


class Espera(Exception):
    """No es una falla: hay que esperar al próximo ciclo."""


class SinRed(Espera):
    pass


class Limite(Espera):
    """Se alcanzó el máximo de pedidos a Wikipedia de esta hora: se espera a la próxima."""


def _contador() -> dict:
    archivo = config.DATOS / "wikipedia.json"
    try:
        return json.loads(archivo.read_text())
    except (OSError, ValueError):
        return {}


def _respetar_ritmo():
    """Cuida a Wikipedia con un contador en vez de un tope diario:
    al menos WIKI_INTERVALO_SEG entre pedidos y como mucho WIKI_PEDIDOS_POR_HORA por hora."""
    from . import memoria
    estado = _contador()
    hora = time.strftime("%Y-%m-%dT%H")
    n = estado.get("n", 0) if estado.get("hora") == hora else 0
    if n >= config.WIKI_PEDIDOS_POR_HORA:
        raise Limite(f"{n} pedidos a Wikipedia en esta hora")
    espera = estado.get("ultimo", 0) + config.WIKI_INTERVALO_SEG - time.time()
    if espera > 0:
        time.sleep(espera)
    memoria.escribir_seguro(config.DATOS / "wikipedia.json",
                            json.dumps({"hora": hora, "n": n + 1, "ultimo": time.time()}))


def _pedir(params: dict, idioma: str = "es") -> dict:
    _respetar_ritmo()
    url = APIS[idioma] + "?" + urllib.parse.urlencode(params)
    pedido = urllib.request.Request(url, headers={"User-Agent": config.USER_AGENT})
    try:
        with urllib.request.urlopen(pedido, timeout=30) as r:
            return json.load(r)
    except urllib.error.HTTPError:
        raise   # Wikipedia respondió con error (429, 503...): eso lo maneja salud
    except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
        # Sin internet en la casa (WiFi, router, DNS): no es culpa de Angri, se reintenta en el próximo ciclo.
        raise SinRed(f"sin internet: {getattr(e, 'reason', e)}") from e


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


def buscar(consulta: str, ya_leidos: set[str], cantidad: int = 5, idioma: str = "es") -> list[str]:
    """Títulos de artículos de Wikipedia que responden a la búsqueda y no se leyeron."""
    datos = _pedir({
        "action": "query", "format": "json", "formatversion": "2",
        "list": "search", "srsearch": consulta, "srlimit": str(cantidad * 2), "srnamespace": "0",
    }, idioma)
    titulos = [r["title"] for r in datos.get("query", {}).get("search", [])]
    if not titulos:   # nada con todas las palabras: autocompletado con la primera parte (tolera errores de escritura)
        palabras = consulta.split()
        for corta in dict.fromkeys([" ".join(palabras[:2]), palabras[0] if palabras else ""]):
            if not corta:
                continue
            datos = _pedir({"action": "opensearch", "format": "json", "search": corta, "limit": str(cantidad * 2),
                            "namespace": "0", "profile": "fuzzy"}, idioma)
            titulos = datos[1] if isinstance(datos, list) and len(datos) > 1 else []
            if titulos:
                break
    url = f"https://{idioma}.wikipedia.org/wiki/"
    return [t for t in titulos if url + t.replace(" ", "_") not in ya_leidos and not t.startswith("Anexo:")][:cantidad]


def articulo(titulo: str, idioma: str = "es") -> dict | None:
    """El artículo completo (sin recortar) de un título."""
    datos = _pedir({
        "action": "query", "format": "json", "formatversion": "2", "titles": titulo,
        "prop": "extracts|info", "explaintext": "1", "inprop": "url", "redirects": "1",
    }, idioma)
    paginas = datos.get("query", {}).get("pages", [])
    if not paginas or "missing" in paginas[0]:
        return None
    p = paginas[0]
    texto = _limpiar(p.get("extract", ""))
    if len(texto) < config.LARGO_MINIMO // 2:
        return None
    fuente = "Wikipedia" if idioma == "es" else f"Wikipedia ({idioma})"
    return {"titulo": p.get("title", titulo), "url": p.get("fullurl", ""), "texto": texto, "fuente": fuente, "idioma": idioma}


# ---------------------------------------------------------------- web general

# Sitios que no sirven como fuente: redes, videos, tiendas, foros, y Wikipedia (se busca aparte).
_WEB_DESCARTADOS = ("wikipedia.org", "youtube.", "facebook.", "instagram.", "tiktok.", "twitter.", "://x.com",
                    "pinterest.", "amazon.", "mercadolibre.", "linkedin.", "reddit.", "quora.", "duckduckgo.")


def _web_pedir(url: str, datos: dict | None = None) -> str:
    _respetar_ritmo()
    cuerpo = urllib.parse.urlencode(datos).encode() if datos else None
    pedido = urllib.request.Request(url, data=cuerpo, headers={"User-Agent": config.USER_AGENT})
    try:
        with urllib.request.urlopen(pedido, timeout=30) as r:
            if "html" not in r.headers.get("Content-Type", "html"):
                return ""
            return r.read(2_000_000).decode(r.headers.get_content_charset() or "utf-8", "replace")
    except urllib.error.HTTPError:
        raise
    except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
        raise SinRed(f"sin internet: {getattr(e, 'reason', e)}") from e


class _Texto(HTMLParser):
    """Texto de una página, sin menús, scripts ni pie."""
    _SALTAR = {"script", "style", "nav", "header", "footer", "aside", "form", "noscript", "svg"}
    _BLOQUES = {"p", "li", "h1", "h2", "h3", "blockquote", "td", "div", "br"}

    def __init__(self):
        super().__init__()
        self.partes, self._saltar = [], 0

    def handle_starttag(self, tag, attrs):
        if tag in self._SALTAR:
            self._saltar += 1
        elif tag in self._BLOQUES:
            self.partes.append("\n")

    def handle_endtag(self, tag):
        if tag in self._SALTAR and self._saltar:
            self._saltar -= 1
        elif tag in self._BLOQUES:
            self.partes.append("\n")

    def handle_data(self, data):
        if not self._saltar:
            self.partes.append(data)


def texto_de_html(html: str) -> str:
    t = _Texto()
    t.feed(html)
    lineas = [" ".join(l.split()) for l in "".join(t.partes).split("\n")]
    return "\n".join(l for l in lineas if len(l) > 60)


def pagina_web(titulo: str, url: str) -> dict | None:
    """El texto de una página web, o None si no tiene bastante para leer."""
    try:
        texto = texto_de_html(_web_pedir(url))
    except urllib.error.HTTPError:
        return None   # una página caída no es una falla de Angri
    if len(texto) < config.LARGO_MINIMO // 2:
        return None
    sitio = urllib.parse.urlparse(url).netloc.removeprefix("www.")
    return {"titulo": titulo or sitio, "url": url, "texto": _limpiar(texto), "fuente": sitio}


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
        return {"titulo": titulo, "url": url, "texto": _recortar(texto), "fuente": "Wikipedia"}
    return None
