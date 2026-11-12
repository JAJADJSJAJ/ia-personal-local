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


def evento(con, tipo, detalle=""):
    """Contadores para la vigilancia: nota_ok, nota_rechazada, pregunta_descartada, error..."""
    con.execute("INSERT INTO eventos (fecha, tipo, detalle) VALUES (?, ?, ?)", (ahora(), tipo, detalle))
