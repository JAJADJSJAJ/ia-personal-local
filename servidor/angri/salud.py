"""Qué hacer cuando algo falla (Wikipedia, el wifi, el modelo).

- Cada falla queda en la tabla ciclos con modo 'falla' y de qué parte vino.
- Después de varias fallas seguidas se toma un descanso que crece (1 h, 2 h, 4 h, hasta 6 h)
  en vez de reintentar cada 20 minutos para siempre. Un ciclo que sale bien vuelve al ritmo normal.
- Si la misma investigación hace fallar el ciclo varias veces, se abandona como 'fallido'.
- Lo que pasa queda en el diario, para que Fran lo vea sin revisar logs.
"""
import traceback
from datetime import datetime, timedelta

from . import bandeja, config, memoria

PARTES = {"fuentes.py": "internet (Wikipedia)", "modelo.py": "el modelo",
          "vectores.py": "los embeddings", "recordar.py": "los embeddings"}


def de_donde(exc: BaseException) -> str:
    """La parte del código más profunda que reconocemos en el traceback."""
    parte = "el código"
    for frame in traceback.extract_tb(exc.__traceback__):
        for archivo, nombre in PARTES.items():
            if frame.filename.endswith(archivo):
                parte = nombre
    return parte


def fallas_seguidas(con) -> list[tuple]:
    """Fallas desde el último ciclo que salió bien, la más reciente primero: (fecha, resultado)."""
    filas = []
    for fecha, modo, resultado in con.execute("SELECT fecha, modo, resultado FROM ciclos ORDER BY id DESC LIMIT 50"):
        if modo != "falla":
            break
        filas.append((fecha, resultado or ""))
    return filas


def espera_minutos(n_fallas: int) -> int:
    if n_fallas < config.FALLAS_ANTES_DE_ESPERAR:
        return 0
    return min(config.ESPERA_INICIAL_MIN * 2 ** (n_fallas - config.FALLAS_ANTES_DE_ESPERAR), config.ESPERA_MAXIMA_MIN)


def descansando(con) -> str | None:
    fallas = fallas_seguidas(con)
    minutos = espera_minutos(len(fallas))
    if fallas and any(c in fallas[0][1] for c in ("HTTP Error 429", "HTTP Error 503")):
        # Wikipedia pidió que bajemos el ritmo: se respeta desde la primera vez.
        minutos = max(minutos, config.ESPERA_INICIAL_MIN)
    if not minutos:
        return None
    hasta = datetime.fromisoformat(fallas[0][0]) + timedelta(minutes=minutos)
    if datetime.now() < hasta:
        return f"descansando tras {len(fallas)} fallas seguidas, hasta las {hasta:%H:%M}"
    return None


def registrar_falla(con, exc: BaseException, objetivo_id: int | None, escribir_diario) -> None:
    parte = de_donde(exc)
    detalle = f"{parte}: {type(exc).__name__}: {exc}"[:300]
    marca = f" [objetivo {objetivo_id}]" if objetivo_id else ""
    con.execute("INSERT INTO ciclos (fecha, modo, tema_id, resultado) VALUES (?, 'falla', NULL, ?)",
                (memoria.ahora(), detalle + marca))
    memoria.evento(con, "error", detalle + marca)

    # Si se cayó internet o el modelo, la investigación no tiene la culpa: solo cuenta si rompió el código.
    if objetivo_id and parte == "el código":
        desde = (datetime.now() - timedelta(days=1)).isoformat(timespec="seconds")
        veces = con.execute("SELECT COUNT(*) FROM ciclos WHERE modo='falla' AND fecha>=? AND resultado LIKE ?",
                            (desde, f"%[objetivo {objetivo_id}]")).fetchone()[0]
        fila = con.execute("SELECT pregunta FROM objetivos WHERE id=? AND estado='abierto'", (objetivo_id,)).fetchone()
        if fila and veces >= config.FALLAS_POR_OBJETIVO:
            con.execute("UPDATE objetivos SET estado='fallido', ultima=? WHERE id=?", (memoria.ahora(), objetivo_id))
            con.execute("UPDATE preguntas SET estado='cerrada' WHERE id=(SELECT pregunta_id FROM objetivos WHERE id=?)",
                        (objetivo_id,))
            escribir_diario(f"Dejé *{fila[0]}*: cada vez que la intento algo se rompe.")
            bandeja.dejar(con, "fallido", f"Dejé «{fila[0]}»: cada vez que la intentaba algo se rompía.", 1)

    n = len(fallas_seguidas(con))
    if n == config.FALLAS_ANTES_DE_ESPERAR:
        escribir_diario(f"Algo no responde ({parte}). Me tomo un descanso y vuelvo a probar más tarde.")
        bandeja.dejar(con, "falla", f"Tuve problemas: no respondía {parte}, así que me tomé un descanso.", 2)
    con.commit()


def anotar_recuperacion(con, fallas_previas: int, escribir_diario) -> None:
    if fallas_previas >= config.FALLAS_ANTES_DE_ESPERAR:
        escribir_diario(f"Volví a andar después de {fallas_previas} intentos fallidos.")
        bandeja.dejar(con, "recuperada", f"Ya volví a andar después de {fallas_previas} intentos fallidos.", 1)
        con.commit()
