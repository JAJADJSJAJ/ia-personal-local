"""Vigilancia automática (fase C2): como nadie la revisa a diario, el código mira y actúa solo.

Mide cosas contables, sin preguntarle nada al modelo, y si algo se pasa del umbral pone un AJUSTE
con fecha de vencimiento (después todo vuelve a lo normal):

  Medida                                          Ajuste
  un solo tema se queda con casi todo              más lectura al azar (unos días)
  muchas preguntas descartadas por repetidas       solo azar por un día (cambio de tema)
  muchas notas rechazadas por los controles        pausa de lectura unas horas + mensaje a Fran
  quien-soy.md casi igual noche tras noche         pausa de reflexiones unos días
  base o disco demasiado grandes                   mensaje a Fran

Lo rápido (notas rechazadas) se mira en cada ciclo; todo lo demás, una vez por noche durante el sueño.
Cada noche escribe /var/lib/angri/salud.md con los números, para mirar cuando se quiera.
"""
import shutil
from datetime import datetime, timedelta

from . import bandeja, config, memoria

ESQUEMA = """
CREATE TABLE IF NOT EXISTS ajustes (
    clave TEXT PRIMARY KEY, valor REAL NOT NULL, hasta TEXT NOT NULL, motivo TEXT NOT NULL, desde TEXT NOT NULL
);
"""

MOTIVOS = {
    "prob_objetivo": "un solo tema se estaba quedando con casi todo",
    "solo_azar": "muchas preguntas repetidas",
    "pausa_lectura": "los controles rechazaron demasiadas notas",
    "pausa_reflexion": "lo que escribe sobre sí casi no cambia",
}


def _hace(**kw) -> str:
    return (datetime.now() - timedelta(**kw)).isoformat(timespec="seconds")


# ---------------------------------------------------------------- ajustes

def ajuste(con, clave: str) -> float | None:
    """El valor del ajuste si está vigente; si no, None."""
    con.executescript(ESQUEMA)
    fila = con.execute("SELECT valor, hasta FROM ajustes WHERE clave=?", (clave,)).fetchone()
    if fila and fila[1] > memoria.ahora():
        return fila[0]
    return None


def poner(con, clave: str, valor: float, horas: float, detalle: str) -> bool:
    """Pone un ajuste. Devuelve True si es nuevo (para avisar una sola vez)."""
    con.executescript(ESQUEMA)
    nuevo = ajuste(con, clave) is None
    hasta = (datetime.now() + timedelta(hours=horas)).isoformat(timespec="seconds")
    con.execute("INSERT OR REPLACE INTO ajustes (clave, valor, hasta, motivo, desde) VALUES (?, ?, ?, ?, ?)",
                (clave, valor, hasta, detalle, memoria.ahora()))
    if nuevo:
        memoria.evento(con, "vigilancia", f"{clave}: {detalle}")
    return nuevo


def vigentes(con) -> list[tuple]:
    con.executescript(ESQUEMA)
    return con.execute("SELECT clave, valor, hasta, motivo FROM ajustes WHERE hasta > ? ORDER BY clave",
                       (memoria.ahora(),)).fetchall()


# ---------------------------------------------------------------- medidas

def _contar(con, tipo: str, desde: str) -> int:
    return con.execute("SELECT COUNT(*) FROM eventos WHERE tipo=? AND fecha >= ?", (tipo, desde)).fetchone()[0]


def medir_notas(con) -> dict:
    desde = _hace(hours=config.VIG_NOTAS_HORAS)
    ok, mal = _contar(con, "nota_ok", desde), _contar(con, "nota_rechazada", desde)
    total = ok + mal
    return {"aceptadas": ok, "rechazadas": mal, "tasa_rechazo": mal / total if total else 0.0, "total": total}


def medir_preguntas(con) -> dict:
    desde = _hace(days=2)
    rep = _contar(con, "pregunta_repetida", desde)
    nuevas = con.execute("SELECT COUNT(*) FROM preguntas WHERE fecha >= ?", (desde,)).fetchone()[0]
    total = rep + nuevas
    return {"repetidas": rep, "nuevas": nuevas, "tasa_repetidas": rep / total if total else 0.0, "total": total}


def medir_temas(con) -> dict:
    filas = con.execute("SELECT tema_id, COUNT(*) FROM ciclos WHERE fecha >= ? AND tema_id IS NOT NULL "
                        "GROUP BY tema_id ORDER BY 2 DESC", (_hace(days=7),)).fetchall()
    total = sum(n for _, n in filas)
    return {"temas_distintos": len(filas), "ciclos_con_tema": total,
            "cuota_del_mayor": filas[0][1] / total if total else 0.0}


def medir_reflexion() -> dict:
    """Parecido entre las últimas versiones de quien-soy.md (la actual y las del historial)."""
    carpeta = config.DATOS / "yo"
    actual = carpeta / "quien-soy.md"
    viejas = sorted((carpeta / "historial").glob("quien-soy-*.md"))[-(config.VIG_REFLEXION_NOCHES - 1):] \
        if (carpeta / "historial").exists() else []
    textos = [v.read_text(encoding="utf-8") for v in viejas] + ([actual.read_text(encoding="utf-8")] if actual.exists() else [])
    textos = [t.split("## Datos")[0] for t in textos]
    if len(textos) < config.VIG_REFLEXION_NOCHES:
        return {"versiones": len(textos), "parecido_minimo": None}
    from . import vectores
    m = vectores.documentos(textos)
    sims = [float(m[i] @ m[i + 1]) for i in range(len(textos) - 1)]
    return {"versiones": len(textos), "parecido_minimo": min(sims)}


def medir_espacio() -> dict:
    base_mb = config.BASE.stat().st_size / 1e6 if config.BASE.exists() else 0.0
    libre_gb = shutil.disk_usage(config.DATOS).free / 1e9
    return {"base_mb": base_mb, "disco_libre_gb": libre_gb}


# ---------------------------------------------------------------- vigilar

def vigilar_rapido(con) -> list[str]:
    """En cada ciclo: solo lo que conviene frenar enseguida."""
    acciones = []
    n = medir_notas(con)
    if n["total"] >= config.VIG_NOTAS_MINIMO and n["tasa_rechazo"] > config.VIG_RECHAZO_MAXIMO:
        if poner(con, "pausa_lectura", 1, config.VIG_PAUSA_LECTURA_HORAS,
                 f"{n['rechazadas']} de {n['total']} notas rechazadas en {config.VIG_NOTAS_HORAS} h"):
            bandeja.dejar(con, "vigilancia", "Paré de leer un rato: casi todo lo que anotaba no pasaba los controles. "
                                             "Vuelvo a probar en unas horas.", 2)
            acciones.append("pausa de lectura")
    con.commit()
    return acciones


def vigilar(con) -> list[str]:
    """Una vez por noche: todas las medidas, los ajustes y salud.md."""
    acciones = vigilar_rapido(con)
    p, t, e = medir_preguntas(con), medir_temas(con), medir_espacio()
    try:
        r = medir_reflexion()
    except OSError:
        r = {"versiones": 0, "parecido_minimo": None}

    if p["total"] >= config.VIG_PREGUNTAS_MINIMO and p["tasa_repetidas"] > config.VIG_REPETIDAS_MAXIMO:
        if poner(con, "solo_azar", 1, 24, f"{p['repetidas']} de {p['total']} preguntas repetidas en 2 días"):
            acciones.append("un día solo de lecturas al azar")
    if t["ciclos_con_tema"] >= config.VIG_TEMAS_MINIMO and t["cuota_del_mayor"] > config.VIG_CUOTA_MAXIMA:
        if poner(con, "prob_objetivo", config.VIG_PROB_OBJETIVO_BAJA, 72,
                 f"un tema se quedó con el {t['cuota_del_mayor']:.0%} de los ciclos de la semana"):
            acciones.append("más lectura al azar por 3 días")
    if r["parecido_minimo"] is not None and r["parecido_minimo"] > config.VIG_REFLEXION_PARECIDO:
        if poner(con, "pausa_reflexion", 1, 72, f"quien-soy.md casi igual {r['versiones']} noches seguidas"):
            acciones.append("pausa de reflexiones por 3 días")
    if e["base_mb"] > config.VIG_BASE_MAXIMA_MB or e["disco_libre_gb"] < config.VIG_DISCO_MINIMO_GB:
        bandeja.dejar(con, "vigilancia", f"Me estoy quedando sin lugar: la memoria ocupa {e['base_mb']:.0f} MB y "
                                         f"quedan {e['disco_libre_gb']:.0f} GB libres.", 2)
        acciones.append("aviso de espacio")
    con.commit()
    escribir_salud(con, medir_notas(con), p, t, r, e, acciones)
    return acciones


def escribir_salud(con, n, p, t, r, e, acciones):
    def marca(malo: bool) -> str:
        return "⚠️" if malo else "✓"
    parecido = f"{r['parecido_minimo']:.2f}" if r["parecido_minimo"] is not None else "todavía no hay suficientes versiones"
    lineas = [
        f"# Salud de Angri — {datetime.now():%d/%m/%Y %H:%M}", "",
        "Lo mide el código, sin preguntarle nada al modelo.", "",
        "| Medida | Valor | Umbral |", "|---|---|---|",
        f"| {marca(n['tasa_rechazo'] > config.VIG_RECHAZO_MAXIMO)} Notas rechazadas ({config.VIG_NOTAS_HORAS} h) | "
        f"{n['rechazadas']} de {n['total']} ({n['tasa_rechazo']:.0%}) | más de {config.VIG_RECHAZO_MAXIMO:.0%} |",
        f"| {marca(p['tasa_repetidas'] > config.VIG_REPETIDAS_MAXIMO)} Preguntas repetidas (2 días) | "
        f"{p['repetidas']} de {p['total']} ({p['tasa_repetidas']:.0%}) | más de {config.VIG_REPETIDAS_MAXIMO:.0%} |",
        f"| {marca(t['cuota_del_mayor'] > config.VIG_CUOTA_MAXIMA)} Ciclos del tema más visitado (7 días) | "
        f"{t['cuota_del_mayor']:.0%} de {t['ciclos_con_tema']}, {t['temas_distintos']} temas distintos | "
        f"más de {config.VIG_CUOTA_MAXIMA:.0%} |",
        f"| {marca(r['parecido_minimo'] is not None and r['parecido_minimo'] > config.VIG_REFLEXION_PARECIDO)} "
        f"Parecido entre sus últimas reflexiones | {parecido} | más de {config.VIG_REFLEXION_PARECIDO} |",
        f"| {marca(e['base_mb'] > config.VIG_BASE_MAXIMA_MB)} Tamaño de la memoria | {e['base_mb']:.1f} MB | "
        f"más de {config.VIG_BASE_MAXIMA_MB} MB |",
        f"| {marca(e['disco_libre_gb'] < config.VIG_DISCO_MINIMO_GB)} Disco libre | {e['disco_libre_gb']:.0f} GB | "
        f"menos de {config.VIG_DISCO_MINIMO_GB} GB |",
        "", "## Ajustes activos", "",
    ]
    vig = vigentes(con)
    lineas += [f"- **{c}** hasta {h[:16].replace('T', ' ')}: {m}" for c, _, h, m in vig] or ["- Ninguno: todo normal."]
    if acciones:
        lineas += ["", "## Lo que hizo esta vez", ""] + [f"- {a}" for a in acciones]
    (config.DATOS / "salud.md").write_text("\n".join(lineas) + "\n", encoding="utf-8")
