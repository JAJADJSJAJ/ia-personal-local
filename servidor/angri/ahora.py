"""Qué está haciendo Angri en este momento, y la charla por la web (con inicio, fin y corte seguro).

EN_CICLO      {pid, actividad, detalle, desde}  mientras corre un ciclo (lo escribe ciclo.py)
CHARLA_WEB    {sesion, inicio, latido, mensaje}  mientras Fran charla desde la página

La charla por la web tiene inicio y fin explícitos (no un "charlando" que vence solo):
  - Al iniciarla se corta lo que esté haciendo (ciclo o sueño) para dejarle el modelo libre.
    Cortar es seguro: la base guarda todo o nada, y el próximo ciclo arranca de cero.
  - Mientras dura, no corre ningún ciclo.
  - Se termina con el botón, o sola si la página deja de dar señales (se cerró el celular)
    o si pasan CHARLA_WEB_INACTIVIDAD_MIN minutos sin mensajes. Así nunca queda trabada esperando.
"""
import json
import os
import signal
import time

from . import config, memoria


def _leer(archivo) -> dict | None:
    try:
        return json.loads(archivo.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


# ---------------------------------------------------------------- qué está haciendo

def marcar(actividad: str, detalle: str = ""):
    previo = _leer(config.EN_CICLO) or {}
    desde = previo.get("desde") if previo.get("actividad") == actividad else time.time()
    memoria.escribir_seguro(config.EN_CICLO, json.dumps(
        {"pid": os.getpid(), "actividad": actividad, "detalle": detalle[:200], "desde": desde or time.time()},
        ensure_ascii=False))


def limpiar():
    config.EN_CICLO.unlink(missing_ok=True)


def proceso_vivo(pid: int, modulo: str) -> bool:
    """El pid existe y es de verdad el proceso de Angri que esperamos (no otro que reusó el número)."""
    try:
        cmd = open(f"/proc/{pid}/cmdline", "rb").read().replace(b"\0", b" ").decode(errors="ignore")
    except OSError:
        return False
    return modulo in cmd


def en_curso() -> dict | None:
    """Lo que está haciendo ahora, si hay un ciclo corriendo de verdad."""
    estado = _leer(config.EN_CICLO)
    if estado and proceso_vivo(estado.get("pid", 0), "angri.ciclo"):
        return estado
    return None


# ---------------------------------------------------------------- charla por la web

def charla_activa() -> dict | None:
    c = _leer(config.CHARLA_WEB)
    if not c:
        return None
    ahora = time.time()
    if (ahora - c.get("latido", 0) > config.CHARLA_WEB_LATIDO_SEG
            or ahora - c.get("mensaje", 0) > config.CHARLA_WEB_INACTIVIDAD_MIN * 60):
        terminar_charla()   # se fue sin despedirse: se cierra sola para que Angri siga con lo suyo
        return None
    return c


def segundos_restantes(c: dict) -> int:
    return max(0, int(config.CHARLA_WEB_INACTIVIDAD_MIN * 60 - (time.time() - c.get("mensaje", 0))))


def _cortar(archivo, modulo: str) -> str | None:
    estado = _leer(archivo)
    pid = (estado or {}).get("pid")
    if pid and proceso_vivo(pid, modulo):
        try:
            os.kill(pid, signal.SIGTERM)
        except OSError:
            return None
        for _ in range(50):   # hasta 5 s para que termine
            if not proceso_vivo(pid, modulo):
                break
            time.sleep(0.1)
        archivo.unlink(missing_ok=True)
        return (estado or {}).get("actividad") or modulo
    return None


def iniciar_charla(sesion: str) -> str | None:
    """Toma el turno: corta lo que esté haciendo y deja la marca. Devuelve qué cortó, si cortó algo."""
    ahora = time.time()
    memoria.escribir_seguro(config.CHARLA_WEB, json.dumps(
        {"sesion": sesion, "inicio": ahora, "latido": ahora, "mensaje": ahora}))
    cortado = _cortar(config.EN_CICLO, "angri.ciclo")
    if _cortar(config.DURMIENDO, "angri.sueno"):
        cortado = "dormir"
    return cortado


def latido(sesion: str, mensaje: bool = False) -> dict | None:
    c = charla_activa()
    if not c or c.get("sesion") != sesion:
        return None
    c["latido"] = time.time()
    if mensaje:
        c["mensaje"] = time.time()
    memoria.escribir_seguro(config.CHARLA_WEB, json.dumps(c))
    return c


def terminar_charla():
    config.CHARLA_WEB.unlink(missing_ok=True)
