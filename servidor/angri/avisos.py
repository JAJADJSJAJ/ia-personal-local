"""Avisos al celular de Fran por ntfy.sh: Angri cuenta algo por su cuenta, de vez en cuando.

- Canal con nombre largo y al azar (en /var/lib/angri/ntfy-canal). Fran se suscribe con la app ntfy.
- Lo decide el código: solo novedades que valen (respuesta encontrada, tema nuevo, una duda para Fran,
  su género), como mucho AVISOS_POR_DIA por día, separados por horas, y nunca de noche.
- Ningún aviso espera respuesta. Lo avisado sigue en la bandeja: la charla lo cuenta igual.
- Sale de la casa solo el texto del aviso (lo que leyó y sus dudas): nada de charlas ni datos de Fran.
"""
import secrets
import sys
import urllib.request
from datetime import datetime, timedelta

from . import bandeja, config, memoria

TIPOS_QUE_AVISAN = ("respuesta", "tema", "duda", "identidad")
TITULOS = {"respuesta": "Encontré algo", "tema": "Algo me empezó a interesar",
           "duda": "Una duda", "identidad": "Decidí algo sobre mí"}


def canal() -> str:
    archivo = config.DATOS / "ntfy-canal"
    if not archivo.exists():
        archivo.write_text("angri-" + secrets.token_urlsafe(18).replace("_", "x").replace("-", "y"))
        archivo.chmod(0o600)
    return archivo.read_text().strip()


def _columna(con):
    bandeja._tabla(con)
    columnas = [c[1] for c in con.execute("PRAGMA table_info(bandeja)")]
    if "avisado" not in columnas:
        con.execute("ALTER TABLE bandeja ADD COLUMN avisado TEXT")


def puede_avisar(con, ahora: datetime | None = None) -> bool:
    ahora = ahora or datetime.now()
    if not (config.AVISOS_DESDE_HORA <= ahora.hour < config.AVISOS_HASTA_HORA):
        return False
    _columna(con)
    hoy = ahora.date().isoformat()
    n_hoy = con.execute("SELECT COUNT(*) FROM bandeja WHERE avisado >= ?", (hoy,)).fetchone()[0]
    if n_hoy >= config.AVISOS_POR_DIA:
        return False
    ultimo = con.execute("SELECT MAX(avisado) FROM bandeja").fetchone()[0]
    return not ultimo or ahora - datetime.fromisoformat(ultimo) >= timedelta(hours=config.AVISOS_SEPARACION_HORAS)


def elegir(con) -> tuple | None:
    _columna(con)
    desde = (datetime.now() - timedelta(days=1)).isoformat(timespec="seconds")   # nada viejo
    marcas = ",".join("?" * len(TIPOS_QUE_AVISAN))
    return con.execute(
        f"SELECT id, tipo, texto FROM bandeja WHERE avisado IS NULL AND entregado IS NULL AND fecha >= ? "
        f"AND tipo IN ({marcas}) ORDER BY importancia DESC, id DESC LIMIT 1", (desde, *TIPOS_QUE_AVISAN)).fetchone()


def enviar(titulo: str, texto: str) -> None:
    pedido = urllib.request.Request(
        f"{config.NTFY_URL}/{canal()}", data=texto.encode("utf-8"), method="POST",
        headers={"Title": titulo if titulo.isascii() else _rfc2047(titulo),   # ntfy acepta RFC 2047 para acentos
                 "Tags": "seedling", "User-Agent": config.USER_AGENT})
    with urllib.request.urlopen(pedido, timeout=20) as r:
        r.read()


def _rfc2047(texto: str) -> str:
    import base64
    return "=?UTF-8?B?" + base64.b64encode(texto.encode("utf-8")).decode() + "?="


def avisar(con) -> str | None:
    """Se llama al final de cada ciclo. Manda como mucho un aviso, si corresponde."""
    if not config.AVISOS_ACTIVOS or not puede_avisar(con):
        return None
    elegido = elegir(con)
    if not elegido:
        return None
    mid, tipo, texto = elegido
    try:
        enviar(TITULOS.get(tipo, "Angri"), texto)
    except OSError as e:
        memoria.evento(con, "aviso_fallido", f"{type(e).__name__}: {e}")
        con.commit()
        return None
    con.execute("UPDATE bandeja SET avisado=? WHERE id=?", (memoria.ahora(), mid))
    memoria.evento(con, "aviso", texto[:200])
    con.commit()
    return texto


def main():
    """angri avisos [probar]: muestra cómo suscribirse, o manda un aviso de prueba."""
    con = memoria.abrir()
    c = canal()
    if len(sys.argv) > 1 and sys.argv[1] == "probar":
        enviar("Angri", "Hola, Fran. Así te van a llegar mis avisos: pocos, y solo cuando tenga algo para contarte.")
        print("Aviso de prueba enviado.")
    else:
        print("Para recibir los avisos de Angri en el celular:")
        print("  1. Instalá la app ntfy (Play Store o App Store).")
        print("  2. Tocá + (suscribirse) y escribí este canal, con el servidor ntfy.sh por defecto:")
        print(f"       {c}")
        print("  3. Probalo con: angri avisos probar")
    con.close()


if __name__ == "__main__":
    main()
