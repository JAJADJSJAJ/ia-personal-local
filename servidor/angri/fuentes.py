"""Fuentes de lectura. Solo lectura.

- Al azar: un artículo cualquiera de Wikipedia en español.
- Para investigar, en orden: Wikipedia en español, en inglés, Wikidata (datos sueltos: fechas, lugares,
  población) y Wikipedia en italiano, francés, portugués y alemán. Si la búsqueda no trae nada,
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
APIS = {"es": API} | {i: f"https://{i}.wikipedia.org/w/api.php" for i in ("en", "it", "fr", "pt", "de")}


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


# ---------------------------------------------------------------- Wikidata

WIKIDATA = "https://www.wikidata.org/w/api.php"
_WD_MAX_DATOS = 40   # datos por entidad que se pasan a texto


def _wd(params: dict) -> dict:
    _respetar_ritmo()
    url = WIKIDATA + "?" + urllib.parse.urlencode({"format": "json", **params})
    pedido = urllib.request.Request(url, headers={"User-Agent": config.USER_AGENT})
    try:
        with urllib.request.urlopen(pedido, timeout=30) as r:
            return json.load(r)
    except urllib.error.HTTPError:
        raise
    except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
        raise SinRed(f"sin internet: {getattr(e, 'reason', e)}") from e


def wikidata_buscar(consulta: str, ya_leidos: set[str], cantidad: int = 3) -> list[str]:
    """Ids (Q...) de entidades de Wikidata para una búsqueda. Prueba con todo y, si no, con la primera palabra."""
    palabras = consulta.split()
    for q in dict.fromkeys([consulta, " ".join(palabras[:2]), palabras[0] if palabras else ""]):
        if not q:
            continue
        datos = _wd({"action": "wbsearchentities", "search": q, "language": "es", "uselang": "es",
                     "limit": str(cantidad * 2), "type": "item"})
        ids = [r["id"] for r in datos.get("search", [])
               if f"https://www.wikidata.org/wiki/{r['id']}" not in ya_leidos]
        if ids:
            return ids[:cantidad]
    return []


def _etiqueta(entidad: dict) -> str:
    e = entidad.get("labels", {})
    return (e.get("es") or e.get("en") or next(iter(e.values()), {})).get("value", "")


def _valor(dv: dict, etiquetas: dict) -> str | None:
    """Un valor de Wikidata como texto en español, o None si no se puede leer."""
    tipo, v = dv.get("type"), dv.get("value")
    if tipo == "wikibase-entityid":
        return etiquetas.get(v.get("id")) or None
    if tipo == "time":
        t, precision = v["time"], v.get("precision", 11)
        anio = t[1:5].lstrip("0") or "0"
        anio = anio + (" a. C." if t.startswith("-") else "")
        if precision >= 11:
            return f"{int(t[9:11])}/{int(t[6:8])}/{anio}"
        return anio
    if tipo == "quantity":
        n = v["amount"].lstrip("+")
        return n[:-2] if n.endswith(".0") else n
    if tipo == "monolingualtext":
        return v.get("text")
    if tipo == "string":
        return v if len(v) < 120 and not v.startswith("http") else None
    return None


def wikidata_articulo(qid: str) -> dict | None:
    """Los datos de una entidad de Wikidata escritos como texto: «Fecha de nacimiento: 1322.»"""
    datos = _wd({"action": "wbgetentities", "ids": qid, "languages": "es|en",
                 "props": "labels|descriptions|claims"})
    ent = datos.get("entities", {}).get(qid)
    if not ent or "missing" in ent:
        return None
    nombre = _etiqueta(ent)
    afirmaciones = []
    for prop, lista in ent.get("claims", {}).items():
        for c in lista:
            snak = c.get("mainsnak", {})
            dv = snak.get("datavalue")
            # Identificadores de catálogos, imágenes y links no dicen nada del mundo
            if snak.get("datatype") in ("external-id", "commonsMedia", "url", "globe-coordinate", "geo-shape"):
                continue
            if dv and c.get("rank") != "deprecated":
                cuando = c.get("qualifiers", {}).get("P585", [{}])[0].get("datavalue")   # "en tal fecha"
                afirmaciones.append((prop, dv, cuando))
    # Primero se juntan todos los ids a traducir (propiedades y valores) y se piden de una vez
    ids = {p for p, _, _ in afirmaciones}
    ids |= {dv["value"]["id"] for _, dv, _ in afirmaciones if dv.get("type") == "wikibase-entityid"}
    etiquetas = {}
    ids = sorted(ids)
    for i in range(0, min(len(ids), 150), 50):
        r = _wd({"action": "wbgetentities", "ids": "|".join(ids[i:i + 50]), "languages": "es|en", "props": "labels"})
        etiquetas |= {k: _etiqueta(e) for k, e in r.get("entities", {}).items()}
    lineas, vistas = [], set()
    for prop, dv, cuando in afirmaciones:
        nombre_prop, valor = etiquetas.get(prop), _valor(dv, etiquetas)
        if not nombre_prop or not valor:
            continue
        extra = f" (en {_valor(cuando, etiquetas)})" if cuando else ""
        linea = f"{nombre} — {nombre_prop}: {valor}{extra}."
        if linea not in vistas:
            vistas.add(linea)
            lineas.append(linea)
        if len(lineas) >= _WD_MAX_DATOS:
            break
    desc = ent.get("descriptions", {}).get("es", ent.get("descriptions", {}).get("en", {})).get("value", "")
    texto = (f"{nombre}: {desc}.\n" if desc else "") + "\n".join(lineas)
    if not nombre or len(texto) < config.LARGO_MINIMO // 2:
        return None
    return {"titulo": nombre, "url": f"https://www.wikidata.org/wiki/{qid}", "texto": texto,
            "fuente": "Wikidata", "idioma": "es"}
