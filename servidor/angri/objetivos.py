"""Objetivos (fase C): una pregunta propia que vale la pena perseguir, con presupuesto.

Todo lo necesario para seguir está en la fila: pregunta, lo que sabe, próximo paso, lo gastado.
Da igual si pasaron diez minutos o diez días.

Cierre (lo decide el código):
- respondido: alguna lectura respondió (SI) y hay al menos dos notas que lo respaldan
- agotado: dos lecturas seguidas no aportaron nada nuevo, o la búsqueda ya no trae nada
- sin_presupuesto: se usaron todas las lecturas
"""
import random

import numpy as np

from . import config, memoria, modelo, recordar, temas, vectores, verificar

PEDIDO_RESPONDE = """PREGUNTA: {pregunta}

NOTA que acabás de tomar:
{nota}

¿La nota responde la pregunta?
- SI: la nota tiene el dato que pide la pregunta, aunque también diga otras cosas.
- PARCIAL: tiene una parte de la respuesta o algo muy relacionado.
- NO: no dice nada de lo que pide la pregunta.
Respondé solo SI, PARCIAL o NO."""

PEDIDO_RESPUESTA = """PREGUNTA: {pregunta}

Tus notas sobre esto:
{notas}

Respondé la pregunta en 2 a 4 oraciones usando solo lo que dicen las notas. Si las notas no alcanzan, decilo."""

PEDIDO_BUSQUEDA = """PREGUNTA: {pregunta}
{ya_buscado}
Escribí una búsqueda corta (2 a 4 palabras clave, sin signos de pregunta) que ayude a responderla. Solo las palabras."""

PEDIDO_INVESTIGABLE = """PREGUNTA: {pregunta}

¿Esta pregunta se puede responder con datos buscando en una enciclopedia o en internet?
Las preguntas de "por qué" o "cómo" sobre hechos históricos, lugares, personas u obras sí se pueden responder.
Respondé NO solo si es una opinión, si es sobre vos misma, si no dice de qué o de quién habla, o si nadie podría saberlo.
Respondé solo SI o NO."""


def abiertos(con) -> list[tuple]:
    return con.execute(
        "SELECT id, pregunta, gastado, presupuesto, ultima FROM objetivos WHERE estado='abierto' ORDER BY ultima"
    ).fetchall()


def indexar_preguntas(con):
    pendientes = con.execute(
        "SELECT id, texto FROM preguntas WHERE id NOT IN (SELECT ref_id FROM vectores WHERE tipo='pregunta')"
    ).fetchall()
    if pendientes:
        m = vectores.documentos([t for _, t in pendientes])
        for (i, _), v in zip(pendientes, m):
            con.execute("INSERT INTO vectores (tipo, ref_id, vector) VALUES ('pregunta', ?, ?)", (i, v.tobytes()))
        con.commit()


def es_repetida(con, texto: str) -> bool:
    """Una pregunta casi igual a una que ya se hizo (abierta, usada o cerrada) se descarta."""
    filas = con.execute("SELECT vector FROM vectores WHERE tipo='pregunta'").fetchall()
    if not filas:
        return False
    m = np.frombuffer(b"".join(f[0] for f in filas), dtype=np.float32).reshape(len(filas), -1)
    return float((m @ vectores.documentos([texto])[0]).max()) >= config.PREGUNTA_REPETIDA


def crear(con) -> int | None:
    """Convierte una pregunta abierta en objetivo. Sorteo ponderado por el peso de su tema."""
    if len(abiertos(con)) >= config.OBJETIVOS_ABIERTOS_MAX:
        return None
    indexar_preguntas(con)
    preguntas = con.execute(
        "SELECT p.id, p.texto, v.vector FROM preguntas p JOIN vectores v ON v.tipo='pregunta' AND v.ref_id=p.id "
        "WHERE p.estado='abierta'"
    ).fetchall()
    if not preguntas:
        return None
    pesos = []
    for _, _, vec in preguntas:
        _, peso = temas.tema_de_pregunta(con, np.frombuffer(vec, dtype=np.float32))
        pesos.append(0.2 + peso)  # las preguntas sin tema también pueden salir, con menos chance
    pid, texto, _ = random.choices(preguntas, weights=pesos)[0]

    # Antes de invertir lecturas: ¿se puede responder buscando? (código primero, modelo después)
    if not verificar.pregunta_investigable(texto) or not modelo.llamar(
        "investigable", PEDIDO_INVESTIGABLE.format(pregunta=texto)
    ).strip().upper().startswith(("SI", "SÍ")):
        con.execute("UPDATE preguntas SET estado='descartada' WHERE id=?", (pid,))
        memoria.evento(con, "pregunta_no_investigable", texto)
        con.commit()
        return None
    ahora = memoria.ahora()
    oid = con.execute(
        "INSERT INTO objetivos (pregunta_id, pregunta, presupuesto, creado, ultima) VALUES (?, ?, ?, ?, ?)",
        (pid, texto, config.OBJETIVO_PRESUPUESTO, ahora, ahora),
    ).lastrowid
    con.execute("UPDATE preguntas SET estado='en_objetivo' WHERE id=?", (pid,))
    con.commit()
    return oid


def elegir(con) -> tuple | None:
    """El objetivo abierto que hace más tiempo no se toca (para alternar)."""
    lista = abiertos(con)
    return lista[0] if lista else None


def consultas_de_busqueda(pregunta: str, ya_buscado: list[str]) -> list[str]:
    """Búsquedas a probar en orden: palabras clave del modelo y, de respaldo, las que saca el código.

    Wikipedia busca todas las palabras juntas, así que una pregunta entera casi nunca encuentra nada.
    """
    previo = ("Ya buscaste: " + "; ".join(ya_buscado) + ". Probá con otras palabras.\n") if ya_buscado else ""
    del_modelo = modelo.llamar("busqueda", PEDIDO_BUSQUEDA.format(pregunta=pregunta, ya_buscado=previo))
    del_modelo = del_modelo.strip().splitlines()[0].strip("\"'*?¿.") if del_modelo.strip() else ""
    del_codigo = verificar.palabras_clave(pregunta)
    corta = " ".join(del_codigo.split()[:2])
    salida = []
    for c in (del_modelo, del_codigo, corta):
        if c and c not in salida and c not in ya_buscado:
            salida.append(c)
    return salida


def registrar_lectura(con, objetivo_id: int, pregunta: str, nota_id: int | None, resumen: str | None) -> str | None:
    """Anota cuánto respondió la lectura y decide si el objetivo se cierra. Devuelve el estado final o None."""
    con.execute("UPDATE objetivos SET gastado=gastado+1, ultima=? WHERE id=?", (memoria.ahora(), objetivo_id))
    if nota_id is not None:
        responde = juzgar(pregunta, resumen)
        con.execute("INSERT OR REPLACE INTO objetivo_nota (objetivo_id, nota_id, responde) VALUES (?, ?, ?)",
                    (objetivo_id, nota_id, responde))
    con.commit()
    return evaluar_cierre(con, objetivo_id)


def _veredicto(r: str) -> str:
    r = r.strip().strip("*").upper()
    return "SI" if r.startswith(("SI", "SÍ")) else "PARCIAL" if "PARCIAL" in r else "NO"


def juzgar(pregunta: str, resumen: str, votos: int = 3) -> str:
    """¿La nota responde? Un modelo chico cambia de opinión con la misma nota: vota varias veces y gana la mayoría.

    Empate: el veredicto más alto. Cerrar como respondido igual pide un SI, dos notas útiles y una respuesta anclada.
    """
    orden = ["NO", "PARCIAL", "SI"]
    vs = [_veredicto(modelo.llamar("responde", PEDIDO_RESPONDE.format(pregunta=pregunta, nota=resumen)))
          for _ in range(votos)]
    return max(orden, key=lambda v: (vs.count(v), orden.index(v)))


def evaluar_cierre(con, objetivo_id: int) -> str | None:
    pregunta, gastado, presupuesto = con.execute(
        "SELECT pregunta, gastado, presupuesto FROM objetivos WHERE id=?", (objetivo_id,)
    ).fetchone()
    notas = con.execute(
        "SELECT n.id, n.resumen, onota.responde FROM objetivo_nota onota JOIN notas n ON n.id=onota.nota_id "
        "WHERE onota.objetivo_id=? ORDER BY n.id", (objetivo_id,)
    ).fetchall()
    utiles = [n for n in notas if n[2] in ("SI", "PARCIAL")]

    estado = None
    if any(n[2] == "SI" for n in notas) and len(utiles) >= 2:
        estado = "respondido"
    elif len(notas) >= 2 and _no_aporta(con, notas[-1][0], [n[0] for n in notas[:-1]]) \
            and _no_aporta(con, notas[-2][0], [n[0] for n in notas[:-2]]):
        estado = "agotado"
    elif gastado >= presupuesto:
        estado = "sin_presupuesto"
    if estado:
        cerrar(con, objetivo_id, estado, pregunta, utiles or notas)
    return estado


def _no_aporta(con, nota_id: int, anteriores: list[int]) -> bool:
    if not anteriores:
        return False
    v = recordar.vector_de(con, "nota", nota_id)
    if v is None:
        return False
    sims = [float(v @ w) for i in anteriores if (w := recordar.vector_de(con, "nota", i)) is not None]
    return bool(sims) and max(sims) >= config.OBJETIVO_AGOTADO


def cerrar(con, objetivo_id: int, estado: str, pregunta: str, notas: list[tuple]):
    respuesta = None
    if notas:
        texto_notas = "\n".join(f"- {' '.join(r.split())}" for _, r, _ in notas)
        respuesta = modelo.llamar("respuesta", PEDIDO_RESPUESTA.format(pregunta=pregunta, notas=texto_notas))
        fuente = " ".join(r for _, r, _ in notas)
        # "Las notas no mencionan X" no es una respuesta sobre el mundo: se sacan esas oraciones y queda el resto
        respuesta = verificar.sin_oraciones_de_la_fuente(respuesta) or None
        if respuesta and (verificar.anclaje(respuesta, fuente) < config.ANCLAJE_MINIMO
                          or verificar.parece_orden(respuesta) or len(respuesta) < 30):
            respuesta = None  # agrega cosas que las notas no dicen, o no queda nada útil: no se guarda
    con.execute("UPDATE objetivos SET estado=?, respuesta=?, ultima=? WHERE id=?",
                (estado, respuesta, memoria.ahora(), objetivo_id))
    pid = con.execute("SELECT pregunta_id FROM objetivos WHERE id=?", (objetivo_id,)).fetchone()[0]
    con.execute("UPDATE preguntas SET estado=? WHERE id=?", ("respondida" if estado == "respondido" else "cerrada", pid))
    con.commit()


def actualizar_sabido(con, objetivo_id: int):
    """'Lo que sé hasta ahora' = las notas útiles del objetivo, cortas. Lo arma el código."""
    filas = con.execute(
        "SELECT n.resumen FROM objetivo_nota onota JOIN notas n ON n.id=onota.nota_id "
        "WHERE onota.objetivo_id=? AND onota.responde != 'NO' ORDER BY n.id", (objetivo_id,)
    ).fetchall()
    sabido = "\n".join(f"- {' '.join(r.split())[:300]}" for (r,) in filas)
    con.execute("UPDATE objetivos SET sabido=? WHERE id=?", (sabido, objetivo_id))
    con.commit()
