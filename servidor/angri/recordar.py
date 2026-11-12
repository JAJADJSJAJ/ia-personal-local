"""Recuperación de recuerdos con tres puntajes (fase B), al estilo de Generative Agents.

- Relevancia: parecido por significado (embeddings) combinado con palabras exactas (FTS5).
- Recencia: decae 0,995 por hora desde la última vez que se usó (o se creó).
- Importancia: la calcula el código, no el modelo (ver CASOS.md sección 4).
Cada puntaje va de 0 a 1 y se suman.
"""
import re
from datetime import datetime

import numpy as np

from . import config, vectores

TIPOS = ("episodio", "nota")


def _texto_indexable(con, tipo, ref_id) -> str | None:
    if tipo == "episodio":
        fila = con.execute("SELECT texto FROM episodios WHERE id=?", (ref_id,)).fetchone()
    else:
        fila = con.execute(
            "SELECT l.titulo || '. ' || n.resumen FROM notas n JOIN lecturas l ON l.id=n.lectura_id WHERE n.id=?",
            (ref_id,),
        ).fetchone()
    return fila[0] if fila else None


def indexar_pendientes(con, tope: int = 64) -> int:
    """Calcula vectores y entradas de búsqueda para lo que todavía no los tiene."""
    pendientes = con.execute(
        "SELECT 'episodio', id FROM episodios WHERE id NOT IN (SELECT ref_id FROM vectores WHERE tipo='episodio') "
        "UNION ALL SELECT 'nota', id FROM notas WHERE estado != 'vencida' "
        "AND id NOT IN (SELECT ref_id FROM vectores WHERE tipo='nota') LIMIT ?",
        (tope,),
    ).fetchall()
    if not pendientes:
        return 0
    textos = [_texto_indexable(con, t, i) or "" for t, i in pendientes]
    matriz = vectores.documentos(textos)
    for (tipo, ref_id), texto, v in zip(pendientes, textos, matriz):
        con.execute("INSERT OR REPLACE INTO vectores (tipo, ref_id, vector) VALUES (?, ?, ?)", (tipo, ref_id, v.tobytes()))
        con.execute("INSERT INTO buscar (texto, tipo, ref_id) VALUES (?, ?, ?)", (texto, tipo, ref_id))
    con.commit()
    return len(pendientes)


def vector_de(con, tipo, ref_id) -> np.ndarray | None:
    fila = con.execute("SELECT vector FROM vectores WHERE tipo=? AND ref_id=?", (tipo, ref_id)).fetchone()
    return np.frombuffer(fila[0], dtype=np.float32) if fila else None


def _importancia(tipo, quien, texto, usos) -> float:
    base = {"fran": 0.6, "nota": 0.4, "angri": 0.3}[quien if tipo == "episodio" else "nota"]
    if re.search(r"\d", texto):
        base += 0.1                                     # fechas, números
    if re.search(r"(?<![.!?¿¡]\s)\b[A-ZÁÉÍÓÚÑ][a-záéíóúñ]{2,}", texto[1:]):
        base += 0.1                                     # nombres propios
    base += min(usos, 3) * 0.1                          # lo que se usa, se refuerza
    return min(base, 1.0)


def _horas_desde(fecha_iso: str) -> float:
    return max((datetime.now() - datetime.fromisoformat(fecha_iso)).total_seconds() / 3600, 0)


def _palabras_clave(consulta: str) -> str:
    palabras = re.findall(r"\w{4,}", consulta.lower())
    return " OR ".join(f'"{p}"' for p in palabras[:8])


def recuperar(con, consulta: str, k: int | None = None, excluir_sesion: str | None = None) -> list[dict]:
    """Devuelve los k recuerdos con mayor puntaje total, con su procedencia."""
    k = k or config.RECUERDOS_POR_TURNO
    filas = con.execute("SELECT tipo, ref_id, vector FROM vectores WHERE tipo IN ('episodio', 'nota')").fetchall()
    if not filas:
        return []

    # Relevancia por significado
    matriz = np.frombuffer(b"".join(f[2] for f in filas), dtype=np.float32).reshape(len(filas), -1)
    sim = matriz @ vectores.consulta(consulta)
    relevancia = {(f[0], f[1]): float(s) for f, s in zip(filas, sim)}

    # Relevancia por palabras exactas: un empujón a lo que comparte términos con la consulta
    clave = _palabras_clave(consulta)
    if clave:
        for tipo, ref_id in con.execute("SELECT tipo, ref_id FROM buscar WHERE buscar MATCH ? LIMIT 20", (clave,)):
            if (tipo, ref_id) in relevancia:
                relevancia[(tipo, ref_id)] += 0.1

    # Primero se filtran los que se pueden traer; recién después se normaliza la relevancia
    # entre ellos (si no, el propio mensaje actual, que se parece 100% a sí mismo, hunde a todos).
    elegibles = []
    for (tipo, ref_id), rel in relevancia.items():
        if rel < config.SIMILITUD_MINIMA:
            continue  # parecido absoluto demasiado bajo: no tiene que ver, aunque sea el "mejor" que hay
        if tipo == "episodio":
            f = con.execute("SELECT fecha, quien, texto, sesion FROM episodios WHERE id=?", (ref_id,)).fetchone()
            if not f or (excluir_sesion and f[3] == excluir_sesion):
                continue  # los turnos de la charla actual ya van aparte
            if f[1] == "angri":
                continue  # lo que dijo Angri no es evidencia: si inventó algo, no puede volver como recuerdo
            if f[2].rstrip().endswith("?"):
                continue  # una pregunta de Fran no es un dato que recordar
            fecha, quien, texto = f[0], f[1], f[2]
            origen = "Fran me dijo" if quien == "fran" else "Le dije a Fran"
        else:
            f = con.execute(
                "SELECT n.fecha, l.titulo, n.resumen, n.estado FROM notas n JOIN lecturas l ON l.id=n.lectura_id WHERE n.id=?",
                (ref_id,),
            ).fetchone()
            if not f or f[3] == "vencida":
                continue
            fecha, quien, texto = f[0], "nota", f[2]
            origen = f"Leí en Wikipedia («{f[1]}»)" + (", sin confirmar" if f[3] == "provisoria" else "")
        elegibles.append((tipo, ref_id, rel, fecha, quien, texto, origen))
    if not elegibles:
        return []

    valores = np.array([e[2] for e in elegibles])
    lo, hi = valores.min(), valores.max()
    rango = (hi - lo) or 1.0

    candidatos = []
    for tipo, ref_id, rel, fecha, quien, texto, origen in elegibles:
        rel_norm = (rel - lo) / rango if len(elegibles) > 1 else 1.0
        if rel_norm < config.RELEVANCIA_MINIMA:
            continue  # sin relación con lo que se está hablando: no se trae aunque sea reciente
        acc = con.execute("SELECT ultimo, usos FROM accesos WHERE tipo=? AND ref_id=?", (tipo, ref_id)).fetchone()
        ultimo, usos = (acc[0], acc[1]) if acc else (fecha, 0)
        puntaje = (
            rel_norm
            + config.RECENCIA_POR_HORA ** _horas_desde(ultimo)
            + _importancia(tipo, quien, texto, usos)
        )
        candidatos.append({"tipo": tipo, "ref_id": ref_id, "fecha": fecha, "origen": origen,
                           "texto": texto, "puntaje": puntaje, "similitud": rel})

    candidatos.sort(key=lambda c: c["puntaje"], reverse=True)
    elegidos, usados = [], 0
    for c in candidatos:
        if len(elegidos) >= k or usados + len(c["texto"]) > config.PRESUPUESTO_RECUERDOS:
            break
        elegidos.append(c)
        usados += len(c["texto"])

    ahora = datetime.now().isoformat(timespec="seconds")
    for c in elegidos:
        con.execute(
            "INSERT INTO accesos (tipo, ref_id, ultimo, usos) VALUES (?, ?, ?, 1) "
            "ON CONFLICT(tipo, ref_id) DO UPDATE SET ultimo=excluded.ultimo, usos=usos+1",
            (c["tipo"], c["ref_id"], ahora),
        )
    con.commit()
    return elegidos


def como_texto(recuerdos: list[dict]) -> str:
    """Formato para el prompt: cada recuerdo con su procedencia y fecha."""
    if not recuerdos:
        return "(ninguno)"
    return "\n".join(f"- [{r['origen']}, {r['fecha'][:10]}] {' '.join(r['texto'].split())}" for r in recuerdos)
