"""Temas que se forman solos (fase C).

Nadie declara un tema: cada nota nueva se compara con el centro de los temas existentes.
Si se parece lo suficiente a uno, se suma y lo mueve; si no, arranca un tema nuevo.
Cuando un tema junta TEMA_MINIMO_PARA_NOMBRE notas, el modelo le pone nombre.

El peso de un tema sube con la novedad en campana (lo parecido a lo conocido pero algo distinto)
y baja con el tiempo si no se alimenta.
"""
import math
from datetime import datetime

import numpy as np

from . import config, memoria, modelo

PEDIDO_NOMBRE = """Estas son notas que tomaste sobre un mismo tema:
{notas}

Nombrá el tema que tienen en común en 1 a 4 palabras, en español. Solo el nombre."""


def campana(novedad: float) -> float:
    """1 en la novedad ideal, cae hacia lo repetido (0) y hacia lo que no tiene relación con nada (1)."""
    return math.exp(-(((novedad - config.NOVEDAD_IDEAL) / config.NOVEDAD_ANCHO) ** 2))


def peso_actual(peso: float, actualizado: str) -> float:
    dias = (datetime.now() - datetime.fromisoformat(actualizado)).total_seconds() / 86400
    return peso * config.TEMA_OLVIDO_POR_DIA ** max(dias, 0)


def novedad(con, nota_id: int, vector: np.ndarray) -> float:
    """1 - similitud con la nota más parecida que ya tenía. Sin notas previas, la novedad es la ideal."""
    filas = con.execute("SELECT vector FROM vectores WHERE tipo='nota' AND ref_id != ?", (nota_id,)).fetchall()
    if not filas:
        return config.NOVEDAD_IDEAL
    m = np.frombuffer(b"".join(f[0] for f in filas), dtype=np.float32).reshape(len(filas), -1)
    return float(1 - (m @ vector).max())


def asignar(con, nota_id: int, vector: np.ndarray, titulo: str, refuerzo: float = 0.0) -> dict:
    """Ubica la nota en un tema (o crea uno), actualiza el peso y, si corresponde, le pone nombre."""
    nov = novedad(con, nota_id, vector)
    temas = con.execute("SELECT id, centro, n, peso, actualizado, nombre FROM temas").fetchall()
    mejor, sim_mejor = None, -1.0
    for t in temas:
        sim = float(np.frombuffer(t[1], dtype=np.float32) @ vector)
        if sim > sim_mejor:
            mejor, sim_mejor = t, sim
    ahora = memoria.ahora()
    ganancia = campana(nov) + refuerzo

    if mejor is not None and sim_mejor >= config.TEMA_SIMILITUD:
        tema_id, centro, n, peso, actualizado, nombre = mejor
        c = np.frombuffer(centro, dtype=np.float32) * n + vector
        c = (c / np.linalg.norm(c)).astype(np.float32)
        n += 1
        peso = peso_actual(peso, actualizado) + ganancia
        con.execute("UPDATE temas SET centro=?, n=?, peso=?, actualizado=? WHERE id=?",
                    (c.tobytes(), n, peso, ahora, tema_id))
    else:
        nombre, n = None, 1
        tema_id = con.execute(
            "INSERT INTO temas (centro, peso, n, creado, actualizado) VALUES (?, ?, 1, ?, ?)",
            (vector.astype(np.float32).tobytes(), ganancia, ahora, ahora),
        ).lastrowid
    con.execute("INSERT OR REPLACE INTO nota_tema (nota_id, tema_id, novedad) VALUES (?, ?, ?)",
                (nota_id, tema_id, nov))
    con.commit()

    recien = False
    if nombre is None and n >= config.TEMA_MINIMO_PARA_NOMBRE:
        nombre = nombrar(con, tema_id)
        recien = nombre is not None
    return {"tema_id": tema_id, "nombre": nombre, "novedad": nov, "nuevo": n == 1, "recien_nombrado": recien}


def nombrar(con, tema_id: int) -> str | None:
    filas = con.execute(
        "SELECT l.titulo, n.resumen FROM nota_tema nt JOIN notas n ON n.id=nt.nota_id "
        "JOIN lecturas l ON l.id=n.lectura_id WHERE nt.tema_id=? ORDER BY n.id DESC LIMIT 6", (tema_id,)
    ).fetchall()
    notas = "\n".join(f"- {t}: {' '.join(r.split())[:200]}" for t, r in filas)
    nombre = modelo.llamar("nombre_tema", PEDIDO_NOMBRE.format(notas=notas)).strip().strip("\"'*.«»").splitlines()[0]
    if not nombre or len(nombre) > 60:
        return None
    con.execute("UPDATE temas SET nombre=? WHERE id=?", (nombre, tema_id))
    con.commit()
    return nombre


def ranking(con, cantidad: int = 10) -> list[tuple]:
    """(id, nombre, peso actual, notas) de los temas con nombre, del más pesado al más liviano."""
    filas = con.execute("SELECT id, nombre, peso, actualizado, n FROM temas WHERE nombre IS NOT NULL").fetchall()
    return sorted(((i, nom, peso_actual(p, a), n) for i, nom, p, a, n in filas), key=lambda t: -t[2])[:cantidad]


def tema_de_pregunta(con, vector: np.ndarray) -> tuple[int | None, float]:
    """El tema más cercano a una pregunta, y su peso actual."""
    mejor, sim_mejor, peso = None, -1.0, 0.0
    for i, centro, p, a in con.execute("SELECT id, centro, peso, actualizado FROM temas"):
        sim = float(np.frombuffer(centro, dtype=np.float32) @ vector)
        if sim > sim_mejor:
            mejor, sim_mejor, peso = i, sim, peso_actual(p, a)
    if sim_mejor < config.TEMA_SIMILITUD:
        return None, 0.0
    return mejor, peso
