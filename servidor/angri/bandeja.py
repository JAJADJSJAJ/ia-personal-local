"""Bandeja de mensajes para Fran (fase D).

Mientras Fran no está, el ciclo deja acá lo que vale la pena contarle (lo decide el código, no el modelo):
  3 · encontró la respuesta a una de sus preguntas
  2 · se dio cuenta de que le interesa un tema nuevo · algo no responde y se tomó un descanso
  1 · dejó una investigación sin respuesta · volvió a andar
Al abrir la charla, Angri saluda contando lo más importante. El modelo solo lo redacta: si agrega
cosas que los mensajes no dicen (anclaje bajo), se usa el texto armado por código.
"""
import re
from datetime import datetime, timedelta

from . import config, memoria, modelo, verificar

ESQUEMA = """
CREATE TABLE IF NOT EXISTS bandeja (
    id INTEGER PRIMARY KEY, fecha TEXT NOT NULL, tipo TEXT NOT NULL, texto TEXT NOT NULL,
    importancia INTEGER NOT NULL, entregado TEXT
);
"""

PEDIDO_SALUDO = """Fran acaba de abrir la charla. Mientras Fran no estaba, VOS (Angri) hiciste esto, contado por vos misma:
{novedades}

Saludá a Fran y contale estas novedades en 2 a 4 oraciones, en primera persona ("me di cuenta", "dejé", "encontré"):
las hiciste vos, no Fran. Usá solo lo que dice la lista: no agregues datos, opiniones ni preguntas."""

# El modelo a veces da vuelta quién hizo qué ("descubriste", "dejaste"): las novedades son de Angri, no de Fran.
_PERSONA_CAMBIADA = re.compile(
    r"\b(dejaste|encontraste|descubriste|buscaste|investigaste|le[ií]ste|tuviste|volviste|abandonaste"
    r"|te diste cuenta|te interes[aó]|te tomaste)\b", re.IGNORECASE)


def _tabla(con):
    con.executescript(ESQUEMA)


def dejar(con, tipo: str, texto: str, importancia: int):
    _tabla(con)
    texto = " ".join(texto.split())
    ya = con.execute("SELECT 1 FROM bandeja WHERE texto=? AND entregado IS NULL", (texto,)).fetchone()
    if not ya:
        con.execute("INSERT INTO bandeja (fecha, tipo, texto, importancia) VALUES (?, ?, ?, ?)",
                    (memoria.ahora(), tipo, texto, importancia))


def pendientes(con) -> list[tuple]:
    """Sin entregar y de los últimos días; lo más importante primero, después lo más nuevo."""
    _tabla(con)
    desde = (datetime.now() - timedelta(days=config.BANDEJA_DIAS)).isoformat(timespec="seconds")
    return con.execute(
        "SELECT id, tipo, texto, importancia FROM bandeja WHERE entregado IS NULL AND fecha>=? "
        "ORDER BY importancia DESC, id DESC", (desde,)).fetchall()


def texto_por_codigo(mensajes: list[tuple], quedan: int) -> str:
    lineas = ["Hola, Fran. Mientras no estabas:"] + [f"- {m[2]}" for m in mensajes]
    if quedan:
        lineas.append(f"(y {quedan} cosa{'s' if quedan > 1 else ''} más, menos importantes)")
    return "\n".join(lineas)


def saludo(con) -> str | None:
    """El primer mensaje de la charla, o None si no hay nada que contar. Marca lo contado como entregado."""
    todos = pendientes(con)
    if not todos:
        return None
    elegidos = todos[: config.BANDEJA_POR_SALUDO]
    quedan = len(todos) - len(elegidos)
    novedades = "\n".join(f"- {m[2]}" for m in elegidos)
    try:
        texto = modelo.llamar("saludo", PEDIDO_SALUDO.format(novedades=novedades)).strip()
        if (verificar.anclaje(texto, novedades) < config.ANCLAJE_MINIMO or verificar.parece_orden(texto)
                or _PERSONA_CAMBIADA.search(texto)):
            texto = texto_por_codigo(elegidos, quedan)
        elif quedan:
            texto += f"\n(Tengo {quedan} cosa{'s' if quedan > 1 else ''} más para contarte si querés.)"
    except OSError:
        texto = texto_por_codigo(elegidos, quedan)
    ahora = memoria.ahora()
    con.executemany("UPDATE bandeja SET entregado=? WHERE id=?", [(ahora, m[0]) for m in elegidos])
    con.commit()
    return texto


def resto(con) -> str | None:
    """Lo que quedó sin contar, armado por código (para cuando Fran pregunta '¿qué más?')."""
    todos = pendientes(con)
    if not todos:
        return None
    ahora = memoria.ahora()
    con.executemany("UPDATE bandeja SET entregado=? WHERE id=?", [(ahora, m[0]) for m in todos])
    con.commit()
    return "\n".join(f"- {m[2]}" for m in todos)
