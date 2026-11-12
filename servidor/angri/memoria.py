"""La memoria de Angri en SQLite. Fase A: lecturas, notas, preguntas y contadores."""
import sqlite3
from datetime import date, datetime

from . import config

ESQUEMA = """
CREATE TABLE IF NOT EXISTS lecturas (
    id INTEGER PRIMARY KEY, fecha TEXT NOT NULL, titulo TEXT, url TEXT UNIQUE NOT NULL
);
CREATE TABLE IF NOT EXISTS notas (
    id INTEGER PRIMARY KEY, fecha TEXT NOT NULL, lectura_id INTEGER REFERENCES lecturas(id),
    resumen TEXT NOT NULL, cita TEXT NOT NULL,
    estado TEXT NOT NULL DEFAULT 'provisoria'   -- provisoria | confirmada | vencida
);
CREATE TABLE IF NOT EXISTS preguntas (
    id INTEGER PRIMARY KEY, fecha TEXT NOT NULL, lectura_id INTEGER REFERENCES lecturas(id),
    texto TEXT NOT NULL, estado TEXT NOT NULL DEFAULT 'abierta'
);
CREATE TABLE IF NOT EXISTS eventos (
    id INTEGER PRIMARY KEY, fecha TEXT NOT NULL, tipo TEXT NOT NULL, detalle TEXT
);
-- Fase B
CREATE TABLE IF NOT EXISTS episodios (
    id INTEGER PRIMARY KEY, fecha TEXT NOT NULL, sesion TEXT NOT NULL,
    quien TEXT NOT NULL,          -- fran | angri
    texto TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS vectores (
    tipo TEXT NOT NULL, ref_id INTEGER NOT NULL, vector BLOB NOT NULL, PRIMARY KEY (tipo, ref_id)
);
CREATE TABLE IF NOT EXISTS accesos (
    tipo TEXT NOT NULL, ref_id INTEGER NOT NULL, ultimo TEXT NOT NULL, usos INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (tipo, ref_id)
);
CREATE VIRTUAL TABLE IF NOT EXISTS buscar USING fts5(texto, tipo UNINDEXED, ref_id UNINDEXED);
-- Fase C
CREATE TABLE IF NOT EXISTS temas (
    id INTEGER PRIMARY KEY, nombre TEXT, centro BLOB NOT NULL,
    peso REAL NOT NULL DEFAULT 0, n INTEGER NOT NULL DEFAULT 0,
    creado TEXT NOT NULL, actualizado TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS nota_tema (
    nota_id INTEGER PRIMARY KEY REFERENCES notas(id), tema_id INTEGER NOT NULL REFERENCES temas(id),
    novedad REAL
);
CREATE TABLE IF NOT EXISTS objetivos (
    id INTEGER PRIMARY KEY, pregunta_id INTEGER REFERENCES preguntas(id), pregunta TEXT NOT NULL,
    estado TEXT NOT NULL DEFAULT 'abierto',   -- abierto | respondido | agotado | sin_presupuesto
    sabido TEXT NOT NULL DEFAULT '', proximo TEXT, gastado INTEGER NOT NULL DEFAULT 0,
    presupuesto INTEGER NOT NULL, respuesta TEXT, creado TEXT NOT NULL, ultima TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS objetivo_nota (
    objetivo_id INTEGER NOT NULL REFERENCES objetivos(id), nota_id INTEGER NOT NULL REFERENCES notas(id),
    responde TEXT NOT NULL, PRIMARY KEY (objetivo_id, nota_id)  -- SI | PARCIAL | NO
);
CREATE TABLE IF NOT EXISTS busquedas (
    id INTEGER PRIMARY KEY, objetivo_id INTEGER REFERENCES objetivos(id), fecha TEXT NOT NULL,
    consulta TEXT NOT NULL, resultados INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS ciclos (
    id INTEGER PRIMARY KEY, fecha TEXT NOT NULL, modo TEXT NOT NULL, tema_id INTEGER, resultado TEXT
);
"""


def abrir() -> sqlite3.Connection:
    config.DATOS.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(config.BASE)
    # Seguro ante cortes de luz (ver INVESTIGACION.md, sección 9)
    con.execute("PRAGMA journal_mode=WAL")
    con.execute("PRAGMA synchronous=FULL")
    con.execute("PRAGMA foreign_keys=ON")
    con.executescript(ESQUEMA)
    return con


def ahora() -> str:
    return datetime.now().isoformat(timespec="seconds")


def urls_leidas(con) -> set[str]:
    return {fila[0] for fila in con.execute("SELECT url FROM lecturas")}


def lecturas_hoy(con) -> int:
    return con.execute("SELECT COUNT(*) FROM lecturas WHERE fecha >= ?", (date.today().isoformat(),)).fetchone()[0]


def guardar_lectura(con, titulo, url) -> int:
    cur = con.execute("INSERT INTO lecturas (fecha, titulo, url) VALUES (?, ?, ?)", (ahora(), titulo, url))
    return cur.lastrowid


def guardar_nota(con, lectura_id, resumen, cita) -> int:
    cur = con.execute(
        "INSERT INTO notas (fecha, lectura_id, resumen, cita) VALUES (?, ?, ?, ?)",
        (ahora(), lectura_id, resumen, cita),
    )
    return cur.lastrowid


def guardar_pregunta(con, lectura_id, texto) -> int:
    cur = con.execute(
        "INSERT INTO preguntas (fecha, lectura_id, texto) VALUES (?, ?, ?)", (ahora(), lectura_id, texto)
    )
    return cur.lastrowid


def guardar_episodio(con, sesion, quien, texto) -> int:
    """Cada mensaje de la charla se guarda tal cual, al instante, sin llamar al modelo."""
    cur = con.execute(
        "INSERT INTO episodios (fecha, sesion, quien, texto) VALUES (?, ?, ?, ?)", (ahora(), sesion, quien, texto)
    )
    con.commit()
    return cur.lastrowid


def evento(con, tipo, detalle=""):
    """Contadores para la vigilancia: nota_ok, nota_rechazada, pregunta_descartada, error..."""
    con.execute("INSERT INTO eventos (fecha, tipo, detalle) VALUES (?, ?, ?)", (ahora(), tipo, detalle))
