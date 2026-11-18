"""El sueño de Angri (fase F): una vez por noche ordena su memoria. Lo dispara angri-sueno.timer.

Mientras duerme, el ciclo no corre. Los pasos los decide el código, en este orden:
  1. Copia de seguridad de la memoria (se guardan las últimas 7).
  2. Repasa las notas viejas con los filtros de hoy (las que hoy se rechazarían, vencen).
  3. Junta notas repetidas: si dos lecturas distintas dicen lo mismo, queda una sola y pasa a 'confirmada'.
  4. Olvida preguntas que nunca investigó (viejas, o si hay demasiadas abiertas).
  5. Poda lo que ya no sirve: eventos viejos, log de llamadas muy grande.
  6. Escribe el resumen del día (el modelo redacta; si agrega cosas que no pasaron, no se guarda).
  7. Optimiza la base.
Nunca borra notas ni charlas: vencer es marcar, no borrar.
"""
import gzip
import os
import shutil
import sqlite3
import sys
import traceback
from datetime import date, datetime, timedelta

import numpy as np

from . import bandeja, config, memoria, modelo, recordar, reflexion, verificar, vigilancia

ESQUEMA = """
CREATE TABLE IF NOT EXISTS resumenes (
    fecha TEXT PRIMARY KEY, texto TEXT NOT NULL, creado TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS suenos (
    id INTEGER PRIMARY KEY, fecha TEXT NOT NULL, informe TEXT NOT NULL
);
"""

SISTEMA_RESUMEN = (
    "Sos Angri. Escribís tu diario en español rioplatense, en primera persona y con voseo. "
    "Contás solo lo que pasó según la lista, sin agregar datos, opiniones ni moralejas. Texto simple, sin asteriscos."
)

PEDIDO_RESUMEN = """Esto es lo que pasó en las últimas 24 horas:
{hechos}

Escribí el resumen de tu día en 3 a 5 oraciones, en primera persona: qué leíste, qué investigaste y qué te quedó.
Usá solo lo que dice la lista."""


def _hace(**kw) -> str:
    return (datetime.now() - timedelta(**kw)).isoformat(timespec="seconds")


def durmiendo() -> bool:
    """Para el ciclo y la charla: si el sueño está corriendo (y no quedó colgado hace horas)."""
    if not config.DURMIENDO.exists():
        return False
    horas = (datetime.now().timestamp() - config.DURMIENDO.stat().st_mtime) / 3600
    return horas < 2


# ---------------------------------------------------------------- 1. copia de seguridad

def copia(con) -> str:
    carpeta = config.DATOS / "copias"
    carpeta.mkdir(exist_ok=True)
    destino = carpeta / f"memoria-{date.today():%Y-%m-%d}.db"
    temporal = destino.with_name(f".{destino.name}.tmp")
    temporal.unlink(missing_ok=True)
    dst = sqlite3.connect(temporal)
    with dst:
        con.backup(dst)   # copia consistente aunque haya WAL
    dst.close()
    os.replace(temporal, destino)   # si se corta la luz a mitad de la copia, no queda una copia rota con nombre válido
    viejas = sorted(carpeta.glob("memoria-*.db"))[: -config.SUENO_COPIAS]
    for v in viejas:
        v.unlink()
    return f"copia {destino.name} ({destino.stat().st_size // 1024} KB)"


# ---------------------------------------------------------------- 2. repasar notas viejas

def repasar(con) -> int:
    vencidas = 0
    for nid, resumen in con.execute("SELECT id, resumen FROM notas WHERE estado != 'vencida'").fetchall():
        if verificar.es_meta(resumen) or verificar.parece_orden(resumen):
            con.execute("UPDATE notas SET estado='vencida' WHERE id=?", (nid,))
            vencidas += 1
    return vencidas


# ---------------------------------------------------------------- 3. juntar repetidas

def juntar_repetidas(con) -> int:
    filas = con.execute(
        "SELECT n.id, n.lectura_id, v.vector FROM notas n JOIN vectores v ON v.tipo='nota' AND v.ref_id=n.id "
        "WHERE n.estado != 'vencida' ORDER BY n.id").fetchall()
    if len(filas) < 2:
        return 0
    m = np.stack([np.frombuffer(f[2], dtype=np.float32) for f in filas])
    sims = m @ m.T
    juntadas, vencida = 0, set()
    for i in range(len(filas)):
        if i in vencida:
            continue
        for j in range(i + 1, len(filas)):
            if j in vencida or sims[i, j] < config.SUENO_REPETIDA:
                continue
            if filas[i][1] == filas[j][1]:
                continue   # misma lectura: no es una confirmación independiente
            # Queda la más vieja; que otra fuente diga lo mismo la confirma.
            con.execute("UPDATE notas SET estado='confirmada' WHERE id=?", (filas[i][0],))
            con.execute("UPDATE notas SET estado='vencida' WHERE id=?", (filas[j][0],))
            vencida.add(j)
            juntadas += 1
    return juntadas


# ---------------------------------------------------------------- 4. olvidar preguntas

def olvidar_preguntas(con) -> int:
    olvidadas = con.execute("UPDATE preguntas SET estado='olvidada' WHERE estado='abierta' AND fecha < ?",
                            (_hace(days=config.SUENO_PREGUNTA_DIAS),)).rowcount
    sobran = con.execute("SELECT id FROM preguntas WHERE estado='abierta' ORDER BY fecha DESC LIMIT -1 OFFSET ?",
                         (config.SUENO_PREGUNTAS_MAX,)).fetchall()
    for (pid,) in sobran:
        con.execute("UPDATE preguntas SET estado='olvidada' WHERE id=?", (pid,))
    return olvidadas + len(sobran)


# ---------------------------------------------------------------- 5. podar

def podar(con) -> str:
    eventos = con.execute("DELETE FROM eventos WHERE fecha < ?", (_hace(days=config.SUENO_EVENTOS_DIAS),)).rowcount
    log = config.LOGS / "llamadas.jsonl"
    rotado = ""
    if log.exists() and log.stat().st_size > config.SUENO_LOG_MAXIMO:
        destino = config.LOGS / f"llamadas-{date.today():%Y-%m-%d}.jsonl.gz"
        with open(log, "rb") as f, gzip.open(destino, "wb") as g:
            shutil.copyfileobj(f, g)
        log.write_text("")
        for viejo in sorted(config.LOGS.glob("llamadas-*.jsonl.gz"))[: -config.SUENO_COPIAS]:
            viejo.unlink()
        rotado = f", log rotado a {destino.name}"
    return f"{eventos} eventos viejos borrados{rotado}"


# ---------------------------------------------------------------- 6. resumen del día

def hechos_del_dia(con) -> list[str]:
    desde = _hace(hours=24)
    hechos = [f"Leí «{t}»: {' '.join(r.split())}" for t, r in con.execute(
        "SELECT l.titulo, n.resumen FROM notas n JOIN lecturas l ON l.id=n.lectura_id "
        "WHERE n.fecha >= ? AND n.estado != 'vencida' ORDER BY n.id", (desde,))]
    for p, e, r in con.execute("SELECT pregunta, estado, respuesta FROM objetivos WHERE estado != 'abierto' AND ultima >= ?",
                               (desde,)):
        hechos.append(f"Encontré respuesta a «{p}»: {r}" if e == "respondido" and r
                      else f"Dejé de investigar «{p}» sin una respuesta clara.")
    for (p,) in con.execute("SELECT pregunta FROM objetivos WHERE creado >= ?", (desde,)):
        hechos.append(f"Empecé a investigar «{p}».")
    from . import dudas
    for p, r in dudas.respondidas(con, desde):
        hechos.append(f"Le pregunté a Fran «{p}» y me contó: {' '.join(r.split())[:200]}")
    return hechos[: config.SUENO_HECHOS_MAX]


def resumen_del_dia(con) -> str | None:
    hechos = hechos_del_dia(con)
    if not hechos:
        return None
    lista = "\n".join(f"- {h}" for h in hechos)
    texto = modelo.llamar("resumen", PEDIDO_RESUMEN.format(hechos=lista), sistema=SISTEMA_RESUMEN).strip()
    if verificar.anclaje(texto, lista) < config.ANCLAJE_MINIMO or verificar.parece_orden(texto):
        memoria.evento(con, "resumen_rechazado", texto[:200])
        return None
    dia = (datetime.now() - timedelta(hours=12)).date().isoformat()   # a las 4 de la mañana, el día es el de ayer
    # La charla lo recibe como contexto (charla.actualidad): sirve para "¿qué hiciste ayer?".
    con.execute("INSERT OR REPLACE INTO resumenes (fecha, texto, creado) VALUES (?, ?, ?)", (dia, texto, memoria.ahora()))
    return texto


def ultimo_resumen(con) -> tuple[str, str] | None:
    con.executescript(ESQUEMA)
    return con.execute("SELECT fecha, texto FROM resumenes ORDER BY fecha DESC LIMIT 1").fetchone()


# ---------------------------------------------------------------- principal

def escribir_diario(linea: str):
    from .ciclo import escribir_diario as escribir
    escribir(linea)


def dormir() -> str:
    if config.PAUSA.exists():
        return "en pausa: no duermo"
    import json
    memoria.escribir_seguro(config.DURMIENDO, json.dumps({"pid": os.getpid(), "actividad": "dormir"}))
    con = memoria.abrir()
    con.executescript(ESQUEMA)
    informe = []
    try:
        informe.append(copia(con))
        informe.append(f"{repasar(con)} notas vencidas al repasarlas")
        con.commit()
        recordar.indexar_pendientes(con)
        informe.append(f"{juntar_repetidas(con)} notas repetidas juntadas")
        informe.append(f"{olvidar_preguntas(con)} preguntas olvidadas")
        informe.append(podar(con))
        con.commit()
        try:
            resumen = resumen_del_dia(con)
        except OSError:
            resumen = None
            informe.append("sin resumen: el modelo no respondió")
        if resumen:
            escribir_diario(f"Antes de dormir: {resumen}")
            bandeja.dejar(con, "resumen", f"Resumen de mi día: {resumen}", 1)
            informe.append("resumen escrito")
        con.commit()
        # Fase E: reflexión. Cada paso por separado: si el modelo falla en uno, los otros siguen.
        # Si la vigilancia vio que lo que escribe sobre sí ya casi no cambia, descansa de reflexionar unos días.
        # El género no se le pregunta: si algún día lo trae, que salga de ella (Fran, 13/11).
        # La pausa frena solo quién soy: los temas sí cambian con lo que lee.
        pasos = [reflexion.reflexionar_tema]
        if vigilancia.ajuste(con, "pausa_reflexion"):
            informe.append("sin quién soy: pausa puesta por la vigilancia")
        else:
            pasos.append(reflexion.reflexionar_quien_soy)
        for paso in pasos:
            try:
                if r := paso(con):
                    informe.append(r)
            except OSError:
                informe.append(f"{paso.__name__}: el modelo no respondió")
        con.commit()
        # Vigilancia: al final, para que mida también la reflexión de esta noche. Escribe salud.md.
        try:
            acciones = vigilancia.vigilar(con)
            informe.append("vigilancia: " + (", ".join(acciones) if acciones else "todo normal"))
        except OSError:
            informe.append("vigilancia: no pudo medir todo (embeddings)")
        con.execute("PRAGMA optimize")
        if date.today().weekday() == 6:   # domingo: compactar
            con.execute("VACUUM")
        texto = "; ".join(informe)
        con.execute("INSERT INTO suenos (fecha, informe) VALUES (?, ?)", (memoria.ahora(), texto))
        con.commit()
        return texto
    finally:
        con.close()
        config.DURMIENDO.unlink(missing_ok=True)


def main():
    # Si Fran inicia una charla, la web corta este proceso (SIGTERM): se sale prolijo, corriendo los finally
    # (borra EN_CICLO, cierra la base). La base guarda todo o nada, así que cortar es seguro.
    import signal
    signal.signal(signal.SIGTERM, lambda *_: sys.exit(0))
    try:
        print(dormir())
    except Exception as e:
        try:
            con = memoria.abrir()
            memoria.evento(con, "error", f"sueño: {type(e).__name__}: {e}")
            con.commit()
            con.close()
        finally:
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
