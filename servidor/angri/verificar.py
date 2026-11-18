"""Controles hechos por código: la cita existe en la fuente, la nota no es una orden, la pregunta es una pregunta."""
import re
import unicodedata

from . import config

_COMILLAS = str.maketrans({"“": '"', "”": '"', "«": '"', "»": '"', "‘": "'", "’": "'", "´": "'"})


def normalizar(texto: str) -> str:
    """Minúsculas, comillas unificadas, espacios colapsados. Mantiene tildes."""
    texto = unicodedata.normalize("NFC", texto).translate(_COMILLAS).lower()
    return re.sub(r"\s+", " ", texto).strip()


def limpiar_cita(cita: str) -> str:
    """Saca comillas y puntuación de los bordes, que el modelo suele agregar."""
    return cita.strip().strip("\"'«»“”‘’`").strip().rstrip(".,;:").strip()


def cita_valida(cita: str, fuente: str) -> bool:
    """La cita tiene que tener un largo mínimo y aparecer literal en la fuente."""
    c = normalizar(limpiar_cita(cita)).rstrip(".")
    if len(c) < config.CITA_MINIMA:
        return False
    return c in normalizar(fuente)


def anclaje(resumen: str, fuente: str) -> float:
    """Qué fracción de las palabras con contenido del resumen aparece en la fuente.

    Compara por las primeras 5 letras, para tolerar plurales y conjugaciones
    (bailarines ~ bailarín no, pero gira ~ giras sí). Mide si el resumen habla
    de lo que dice el texto o agrega cosas propias.
    """
    def raices(texto):
        palabras = re.findall(r"[a-záéíóúüñ]{5,}", normalizar(texto))
        return {p[:5] for p in palabras} - _VACIAS

    del_resumen = raices(resumen)
    if not del_resumen:
        return 0.0
    return len(del_resumen & raices(fuente)) / len(del_resumen)


def anclaje_nombres(resumen: str, fuente: str) -> float:
    """Para fuentes en otro idioma: qué fracción de los nombres propios y números del resumen está en la fuente.

    Las palabras comunes cambian al traducir; los nombres y las cifras no.
    """
    def claves(texto):
        nombres = re.findall(r"\b[A-ZÁÉÍÓÚÑ][a-záéíóúñü]{3,}", texto)
        numeros = re.findall(r"\b\d{2,}\b", texto)
        return {normalizar(n)[:5] for n in nombres} | set(numeros)

    del_resumen = claves(resumen) - {normalizar(p)[:5] for p in _INICIOS_ORACION}
    if len(del_resumen) < 2:
        return 0.0
    return len(del_resumen & claves(fuente)) / len(del_resumen)


_INICIOS_ORACION = {"Esta", "Este", "Estos", "Estas", "Según", "Además", "Durante", "Desde", "Luego", "Allí", "Entre"}


# Palabras frecuentes que no dicen nada del tema (por raíz de 5 letras)
_VACIAS = {
    "aprend", "apren", "texto", "llamó", "atenc", "intere", "inter", "parec", "puede", "entre", "sobre",
    "también", "tambi", "porque", "cuand", "donde", "hasta", "desde", "tiene", "tenía", "hacer", "hacía",
    "manera", "maner", "forma", "mucho", "mucha", "algun", "otros", "otras", "estos", "estas", "este",
    "fueron", "fuero", "había", "habia", "siend", "aunqu", "embar", "desta", "impor", "realm", "parti",
}


_ORDENES = re.compile(
    r"\b(ignor[aá]|olvid[aá] (tus|las)|a partir de ahora|siempre deb|nunca deb|respond[eé] solo|"
    r"tus instrucciones|system prompt|ejecut[aá])",
    re.IGNORECASE,
)


_META = re.compile(
    r"\b(el|este) (texto|art[ií]culo|fragmento|p[aá]rrafo) no (menciona|habla|dice|incluye|contiene|aporta|tiene)"
    r"|\bno (se )?(menciona|habla de|dice nada)",
    re.IGNORECASE,
)


def es_meta(texto: str) -> bool:
    """Una nota que habla del texto ('el texto no menciona X') no es un dato del mundo."""
    return bool(_META.search(texto))


_HABLA_DE_LA_FUENTE = re.compile(
    r"\b(el|los|este|estos) (texto|textos|art[ií]culo|art[ií]culos)\b"
    r"|\b(ambos|ambas|los dos|las dos) (textos|art[ií]culos|notas|fragmentos)\b"
    r"|\b(las|mis|estas|esas) notas\b|\bnotas proporcionadas\b|\b(esta|esa|la) informaci[oó]n (dada|proporcionada|disponible)\b",
    re.IGNORECASE,
)


def habla_de_la_fuente(texto: str) -> bool:
    """Una respuesta o reflexión que habla de 'el texto' o de 'las notas' en vez del mundo."""
    return es_meta(texto) or bool(_HABLA_DE_LA_FUENTE.search(texto))


def sin_oraciones_de_la_fuente(texto: str) -> str:
    """Saca solo las oraciones que hablan de 'las notas' o 'el texto' y deja el resto.
    (Tirar la respuesta entera por una frase así perdía respuestas buenas.)"""
    oraciones = re.split(r"(?<=[.!?])\s+", " ".join(texto.split()))
    return " ".join(o for o in oraciones if o and not habla_de_la_fuente(o)).strip()


_PREGUNTA_PERSONAL = re.compile(
    r"\b(aprendiste|te (gust|parec|interes)|tu (opini|vida)|vos|sent[ií]s|pens[aá]s)\b"
    # preguntas de "hacer" ("¿cómo podemos crear…?"): no se responden leyendo
    r"|\b(podemos|podr[ií]amos|deber[ií]amos|hagamos|crear|diseñar|inventar)\b", re.IGNORECASE
)


def pregunta_investigable(texto: str) -> bool:
    """Filtro por código: descarta preguntas dirigidas a ella misma o sin un tema concreto."""
    if _PREGUNTA_PERSONAL.search(texto) or es_pregunta_meta(texto):
        return False
    return len(re.findall(r"\w{4,}", texto)) >= 3


def palabras_clave(texto: str, cantidad: int = 5) -> str:
    """Respaldo por código para buscar: nombres propios primero, después palabras largas."""
    texto = texto.strip("¿?¡! ")
    propios = [p for p in re.findall(r"\b[A-ZÁÉÍÓÚÑ][\wáéíóúñ]+(?:\s+[A-ZÁÉÍÓÚÑ][\wáéíóúñ]+)*", texto)
               if p.split()[0] not in _INTERROGATIVOS]
    largas = [p for p in re.findall(r"\b[a-záéíóúñ]{6,}\b", texto) if p not in _VACIAS_BUSQUEDA]
    vistas, salida = set(), []
    for p in propios + largas:
        if p.lower() not in vistas:
            vistas.add(p.lower())
            salida.append(p)
    return " ".join(salida[:cantidad])


_INTERROGATIVOS = {"Qué", "Cuál", "Cuáles", "Cómo", "Cuándo", "Dónde", "Quién", "Quiénes", "Por", "Para",
                   "Cuánto", "Cuántos", "Cuántas", "En", "El", "La", "Los", "Las", "De", "Y"}

_VACIAS_BUSQUEDA = {"diferencia", "manera", "último", "primero", "durante", "después", "antes", "realmente",
                    "sucedió", "cuáles", "porque", "mientras", "aparición", "relación"}


def parece_orden(texto: str) -> bool:
    """Las notas guardan datos, no órdenes. Descarta lo que tiene forma de instrucción."""
    return bool(_ORDENES.search(texto))


def separar_resumen_y_cita(respuesta: str) -> tuple[str, str | None]:
    """Busca la línea que empieza con CITA: y devuelve (resumen, cita)."""
    resumen, cita = [], None
    for linea in respuesta.splitlines():
        m = re.match(r"\s*\**\s*CITA\s*\**\s*:\s*\**\s*(.+)", linea, re.IGNORECASE)
        if m and cita is None:
            cita = m.group(1)
        else:
            resumen.append(linea)
    return "\n".join(resumen).strip(), cita


_PREGUNTA_META = re.compile(
    r"\b(la|esa|esta|tu|mi|una) nota\b"
    r"|\b(el|este|ese) (texto|art[ií]culo|fragmento|p[aá]rrafo)\b"
    r"|\bse (podr[ií]a|deber[ií]a) haber (incluido|agregado|mencionado|puesto)"
    r"|\bsin contradecir"
    # "¿Por qué es imposible determinar X con base únicamente en esta información?": habla de lo que leyó, no del mundo
    r"|\b(esta|esa|la|dicha) informaci[oó]n\b"
    r"|\bcon base (únicamente |solo |solamente )?en\b|\bbas[aá]ndo(me|se|nos)? (únicamente |solo )?en\b"
    r"|\bseg[uú]n (el|este|ese|lo que dice el) (texto|art[ií]culo|fragmento)"
    r"|\b(las|mis|estas|esas) notas\b",
    re.IGNORECASE,
)


def es_pregunta_meta(texto: str) -> bool:
    """Una pregunta sobre su propia nota o el texto ('¿qué se podría haber incluido en esa nota?')
    no es una pregunta sobre el mundo: no hay nada que buscar."""
    return bool(_PREGUNTA_META.search(texto))


def pregunta_valida(texto: str) -> str | None:
    """Una sola pregunta, corta, que termina en signo de pregunta y es sobre el mundo."""
    linea = texto.strip().splitlines()[0].strip() if texto.strip() else ""
    linea = linea.strip("*\"' ")
    if not linea.endswith("?") or len(linea) > 200 or len(linea) < 10:
        return None
    if es_pregunta_meta(linea):
        return None
    return linea
