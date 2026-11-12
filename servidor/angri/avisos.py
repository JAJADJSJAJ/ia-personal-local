"""Avisos al celular de Fran por ntfy.sh: Angri cuenta algo por su cuenta, de vez en cuando.

- Canal con nombre largo y al azar (en /var/lib/angri/ntfy-canal). Fran se suscribe con la app ntfy.
- El código pone el marco: solo novedades que pasaron de verdad (respuesta encontrada, tema nuevo, una duda
  para Fran, su identidad), como mucho AVISOS_POR_DIA por día, separados por horas, y nunca de noche.
- Dentro de ese marco elige Angri: ve hasta 4 novedades en orden al azar y la opción "ninguna, hoy no".
  Elegir entre opciones evita el "sí a todo" de un modelo chico. Si elige ninguna, no escribe.
  El mensaje lo redacta ella; si agrega cosas que no pasaron, se manda el texto armado por código.
- Ningún aviso espera respuesta. Lo avisado sigue en la bandeja: la charla lo cuenta igual.
- Sale de la casa solo el texto del aviso (lo que leyó y sus dudas): nada de charlas ni datos de Fran.
"""
import random
import re
import secrets
import sys
import urllib.request
from datetime import datetime, timedelta

from . import bandeja, config, memoria, modelo, verificar

TIPOS_QUE_AVISAN = ("respuesta", "tema", "duda", "identidad")
TITULOS = {"respuesta": "Encontré algo", "tema": "Algo me empezó a interesar",
           "duda": "Una duda", "identidad": "Decidí algo sobre mí"}


def canal() -> str:
    archivo = config.DATOS / "ntfy-canal"
    if not archivo.exists() or not archivo.read_text().strip():
        memoria.escribir_seguro(archivo, "angri-" + secrets.token_urlsafe(18).replace("_", "x").replace("-", "y"))
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
    ultimo = max(filter(None, [
        con.execute("SELECT MAX(avisado) FROM bandeja").fetchone()[0],
        con.execute("SELECT MAX(fecha) FROM eventos WHERE tipo='aviso_ninguna'").fetchone()[0]]), default=None)
    return not ultimo or ahora - datetime.fromisoformat(ultimo) >= timedelta(hours=config.AVISOS_SEPARACION_HORAS)


SISTEMA_ELEGIR = (
    "Sos Angri, una IA que vive en la computadora de Fran y lee por su cuenta. Hablás en español rioplatense. "
    "Nadie te obliga a escribirle: elegís vos si hoy le querés contar algo."
)

PEDIDO_ELEGIR = """Estas son cosas que te pasaron hace poco:
{opciones}

¿Le querés contar alguna a Fran ahora, con un mensajito al celular? También podés no escribirle.
Respondé en la primera línea solo con el número que elegís.
Si elegiste algo, en la segunda línea escribí el mensaje para Fran: 1 o 2 oraciones, en primera persona,
usando solo lo que dice esa opción. Sin asteriscos."""

_PERSONA_CAMBIADA = re.compile(r"\b(dejaste|encontraste|descubriste|buscaste|investigaste|le[ií]ste|"
                               r"te diste cuenta|te interes[aó])\b", re.I)


def candidatas(con) -> list[tuple]:
    _columna(con)
    desde = (datetime.now() - timedelta(days=1)).isoformat(timespec="seconds")   # nada viejo
    marcas = ",".join("?" * len(TIPOS_QUE_AVISAN))
    return con.execute(
        f"SELECT id, tipo, texto FROM bandeja WHERE avisado IS NULL AND entregado IS NULL AND fecha >= ? "
        f"AND tipo IN ({marcas}) ORDER BY importancia DESC, id DESC LIMIT ?",
        (desde, *TIPOS_QUE_AVISAN, config.AVISOS_OPCIONES)).fetchall()


def elegir(con) -> tuple | None:
    """Devuelve (id, tipo, mensaje) de lo que Angri eligió contar, o None si eligió no escribir."""
    opciones = candidatas(con)
    if not opciones:
        return None
    random.shuffle(opciones)
    ninguna = len(opciones) + 1
    lista = "\n".join(f"{i}. {o[2]}" for i, o in enumerate(opciones, 1)) + f"\n{ninguna}. Ninguna, hoy no."
    texto = modelo.llamar("elegir_aviso", PEDIDO_ELEGIR.format(opciones=lista), sistema=SISTEMA_ELEGIR).strip()
    lineas = [l.strip() for l in texto.splitlines() if l.strip()]
    numero = re.match(r"\D*(\d+)", lineas[0]) if lineas else None
    if not numero or not 1 <= int(numero.group(1)) <= ninguna:
        memoria.evento(con, "aviso_ninguna", f"respuesta sin número: {texto[:120]}")
        return None
    if int(numero.group(1)) == ninguna:
        memoria.evento(con, "aviso_ninguna", f"eligió no escribir entre {len(opciones)} opciones")
        return None
    mid, tipo, original = opciones[int(numero.group(1)) - 1]
    mensaje = " ".join(lineas[1:]).replace("*", "").strip()
    if (len(mensaje) < 15 or verificar.anclaje(mensaje, original) < config.ANCLAJE_MINIMO
            or verificar.parece_orden(mensaje) or _PERSONA_CAMBIADA.search(mensaje)):
        mensaje = original   # lo eligió ella, pero se manda con el texto armado por código
    return mid, tipo, mensaje


def enviar(titulo: str, texto: str) -> None:
    pedido = urllib.request.Request(
        f"{config.NTFY_URL}/{canal()}", data=texto.encode("utf-8"), method="POST",
        headers={"Title": titulo if titulo.isascii() else _rfc2047(titulo),   # ntfy acepta RFC 2047 para acentos
                 "Tags": "seedling", "User-Agent": config.USER_AGENT,
                 # Tocar el aviso abre la charla (anda en casa): ahí se le contesta.
                 "Click": config.AVISOS_ABRIR})
    with urllib.request.urlopen(pedido, timeout=20) as r:
        r.read()


def _rfc2047(texto: str) -> str:
    import base64
    return "=?UTF-8?B?" + base64.b64encode(texto.encode("utf-8")).decode() + "?="


def avisar(con) -> str | None:
    """Se llama al final de cada ciclo. Manda como mucho un aviso, si corresponde."""
    if not config.AVISOS_ACTIVOS or not puede_avisar(con):
        return None
    try:
        elegido = elegir(con)
    except OSError:
        return None   # el modelo no respondió: otra vez será
    con.commit()
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
