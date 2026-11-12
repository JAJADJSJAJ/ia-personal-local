"""Las dudas que Angri le hace a Fran, y las respuestas de Fran vinculadas a ellas.

Cuando Fran escribe en la charla, el código se fija si el mensaje responde una duda reciente:
  - si la duda era lo último que dijo Angri (en el saludo o en la charla), alcanza con un parecido bajo;
  - si no, el mensaje tiene que parecerse bastante a la pregunta.
La respuesta queda guardada como "lo que me contó Fran": no es un dato verificado del mundo, y se cuenta así.
"""
import re
from datetime import datetime, timedelta

from . import bandeja, config, memoria, vectores

ESQUEMA = """
CREATE TABLE IF NOT EXISTS respuestas_fran (
    id INTEGER PRIMARY KEY, fecha TEXT NOT NULL, bandeja_id INTEGER, pregunta TEXT NOT NULL, respuesta TEXT NOT NULL
);
"""


def pregunta_de(texto: str) -> str | None:
    m = re.search(r"«(.+?)»", texto)
    return m.group(1) if m else None


def pendientes(con) -> list[tuple]:
    """Dudas de las últimas semanas que Fran todavía no respondió: (bandeja_id, pregunta, texto)."""
    con.executescript(ESQUEMA)
    bandeja._tabla(con)
    desde = (datetime.now() - timedelta(days=config.DUDA_DIAS)).isoformat(timespec="seconds")
    filas = con.execute("SELECT id, texto FROM bandeja WHERE tipo='duda' AND fecha >= ? "
                        "AND id NOT IN (SELECT bandeja_id FROM respuestas_fran WHERE bandeja_id IS NOT NULL)",
                        (desde,)).fetchall()
    return [(i, p, t) for i, t in filas if (p := pregunta_de(t))]


def vincular(con, mensaje: str, ultimo_de_angri: str = "") -> str | None:
    """Si el mensaje de Fran responde una duda pendiente, lo guarda y devuelve la pregunta respondida."""
    dudas = pendientes(con)
    if not dudas or len(mensaje.split()) < 2:
        return None
    m = vectores.consulta(mensaje)
    preguntas = vectores.documentos([p for _, p, _ in dudas])
    sims = preguntas @ m
    mejor = int(sims.argmax())
    bid, pregunta, _ = dudas[mejor]
    recien_preguntada = pregunta in ultimo_de_angri
    umbral = config.DUDA_SIMILITUD_CONTEXTO if recien_preguntada else config.DUDA_SIMILITUD
    if float(sims[mejor]) < umbral:
        return None
    con.execute("INSERT INTO respuestas_fran (fecha, bandeja_id, pregunta, respuesta) VALUES (?, ?, ?, ?)",
                (memoria.ahora(), bid, pregunta, mensaje))
    con.execute("UPDATE bandeja SET entregado=COALESCE(entregado, ?) WHERE id=?", (memoria.ahora(), bid))
    memoria.evento(con, "duda_respondida", pregunta[:200])
    con.commit()
    from .ciclo import escribir_diario
    escribir_diario(f"Fran me contó sobre *{pregunta}*: «{' '.join(mensaje.split())[:300]}»")
    return pregunta


def respondidas(con, desde: str | None = None) -> list[tuple]:
    con.executescript(ESQUEMA)
    if desde:
        return con.execute("SELECT pregunta, respuesta FROM respuestas_fran WHERE fecha >= ? ORDER BY id", (desde,)).fetchall()
    return con.execute("SELECT pregunta, respuesta FROM respuestas_fran ORDER BY id").fetchall()
