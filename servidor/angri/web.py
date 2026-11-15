"""La página de Angri (celular o PC), solo dentro de la red de casa.

Uso: python3 -m angri.web   (lo corre el servicio angri-web en el puerto 8080)
Se entra una vez con http://angri.local:8080/?clave=XXXX; la página guarda la clave (`angri web` la muestra).

Dos partes:
  - El panel: solo LEE. Abrir la página no la interrumpe ni la pausa.
  - La charla: se inicia a propósito (corta lo que esté haciendo, de forma segura), se termina con un
    botón, y se cierra sola si no hay mensajes en 10 minutos o si la página se cierra. Ver ahora.py.

Solo usa la biblioteca estándar. El modelo es uno solo y lento, así que las respuestas van de a una.
"""
import json
import re
import secrets
import subprocess
import threading
import time
import uuid
from datetime import date, datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from . import ahora, bandeja, charla, config, memoria, reflexion, salud, sueno, temas, vigilancia

WEB = Path(__file__).with_name("web")    # index.html + css/ + js/ + vendor/ (three.js va adentro: la página no sale a internet)
PAGINA = WEB / "index.html"
TIPOS = {".css": "text/css; charset=utf-8", ".js": "text/javascript; charset=utf-8"}
_turno = threading.Lock()                 # una respuesta del modelo a la vez
_historiales: dict[str, list] = {}        # sesion -> historial de la charla

NOMBRES = {"azar": "Leyendo algo nuevo", "objetivo": "Investigando una pregunta", "repasar": "Releyendo sus notas",
           "conectar": "Buscando conexiones", "pensar": "Pensando un tema", "descansar": "Descansando",
           "eligiendo": "Decidiendo qué hacer"}


def clave() -> str:
    archivo = config.DATOS / "web-clave"
    if not archivo.exists() or not archivo.read_text().strip():
        memoria.escribir_seguro(archivo, secrets.token_urlsafe(12))
        archivo.chmod(0o600)
    return archivo.read_text().strip()


# ---------------------------------------------------------------- lo que se muestra

def proximo_ciclo() -> str | None:
    try:
        salida = subprocess.run(["systemctl", "show", "-p", "NextElapseUSecRealtime", "--value", "angri-ciclo.timer"],
                                capture_output=True, text=True, timeout=5).stdout
        m = re.search(r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})", salida)
        return m.group(1).replace(" ", "T") if m else None
    except (OSError, subprocess.SubprocessError):
        return None


def situacion(con) -> dict:
    if c := ahora.charla_activa():
        return {"tipo": "charlando", "texto": "Charlando con vos", "restante": ahora.segundos_restantes(c)}
    if config.PAUSA.exists():
        return {"tipo": "pausa", "texto": "En pausa"}
    if sueno.durmiendo():
        return {"tipo": "durmiendo", "texto": "Durmiendo: ordenando su memoria"}
    if e := ahora.en_curso():
        return {"tipo": "activa", "texto": NOMBRES.get(e["actividad"], e["actividad"]), "actividad": e["actividad"],
                "detalle": e.get("detalle", ""), "desde": datetime.fromtimestamp(e["desde"]).isoformat(timespec="seconds")}
    if motivo := salud.descansando(con):
        return {"tipo": "descanso", "texto": "Tomándose un descanso", "detalle": motivo}
    if vigilancia.ajuste(con, "pausa_lectura"):
        return {"tipo": "descanso", "texto": "Pausa de lectura", "detalle": "la vigilancia vio demasiadas notas rechazadas"}
    ultimo = con.execute("SELECT modo, resultado, fecha FROM ciclos WHERE modo != 'falla' ORDER BY id DESC LIMIT 1").fetchone()
    return {"tipo": "esperando", "texto": "Entre una cosa y otra",
            "ultimo": {"actividad": NOMBRES.get(ultimo[0], ultimo[0]), "resultado": ultimo[1], "fecha": ultimo[2]} if ultimo else None}


def reflexiones_de_temas() -> dict:
    carpeta = config.DATOS / "yo" / "temas"
    salida = {}
    for f in sorted(carpeta.glob("*.md")) if carpeta.exists() else []:
        texto = f.read_text(encoding="utf-8")
        titulo = texto.splitlines()[0].lstrip("# ").strip() if texto else f.stem
        entendi = texto.split("## Lo que entendí")[-1].split("##")[0].strip() if "## Lo que entendí" in texto else ""
        salida[titulo] = entendi
    return salida


def diario(dias: int = 2) -> list[dict]:
    lineas = []
    for archivo in sorted(config.DIARIO.glob("*.md"))[-dias:] if config.DIARIO.exists() else []:
        fecha = archivo.stem
        for l in archivo.read_text(encoding="utf-8").splitlines():
            m = re.match(r"- \*\*(\d{2}:\d{2})\*\* · (.*)", l)
            if m:
                lineas.append({"fecha": fecha, "hora": m.group(1), "texto": m.group(2).replace("**", "").replace("*", "")})
    return lineas[-25:][::-1]


def estado(con) -> dict:
    from . import actividades, dudas
    con.executescript(actividades.ESQUEMA + dudas.ESQUEMA + sueno.ESQUEMA)

    def todos(sql, *a):
        return con.execute(sql, a).fetchall()

    hoy = date.today().isoformat()
    primera = con.execute("SELECT MIN(fecha) FROM lecturas").fetchone()[0]
    reflex = reflexiones_de_temas()
    g = reflexion.genero(con)
    ult_resumen = sueno.ultimo_resumen(con)
    return {
        "situacion": situacion(con),
        "proximo": proximo_ciclo(),
        "cifras": {
            "dias": (date.today() - date.fromisoformat(primera[:10])).days + 1 if primera else 0,
            "lecturas": con.execute("SELECT COUNT(*) FROM lecturas").fetchone()[0],
            "lecturas_hoy": con.execute("SELECT COUNT(*) FROM lecturas WHERE fecha >= ?", (hoy,)).fetchone()[0],
            "notas": con.execute("SELECT COUNT(*) FROM notas WHERE estado != 'vencida'").fetchone()[0],
            "preguntas": con.execute("SELECT COUNT(*) FROM preguntas WHERE estado IN ('abierta','en_objetivo')").fetchone()[0],
        },
        "actividades_hoy": dict(todos("SELECT modo, COUNT(*) FROM ciclos WHERE fecha >= ? GROUP BY modo", hoy)),
        "quien_soy": (reflexion.leer("quien-soy.md") or "").split("## Datos")[0].replace("# Quién soy", "").strip(),
        "genero": {"valor": g[0], "motivo": g[1]} if g else None,
        "resumen": {"fecha": ult_resumen[0], "texto": ult_resumen[1]} if ult_resumen else None,
        "temas": [{"nombre": n, "peso": round(p, 2), "notas": k, "entendi": reflex.get(n, "")}
                  for _, n, p, k in temas.ranking(con, 8)],
        "investigando": [{"pregunta": p, "gastado": gg, "presupuesto": t} for p, gg, t in todos(
            "SELECT pregunta, gastado, presupuesto FROM objetivos WHERE estado='abierto' ORDER BY ultima DESC")],
        "preguntas": [{"texto": t, "fecha": f} for t, f in todos(
            "SELECT texto, fecha FROM preguntas WHERE estado='abierta' ORDER BY id DESC LIMIT 12")],
        "cerradas": [{"pregunta": p, "estado": e, "respuesta": r} for p, e, r in todos(
            "SELECT pregunta, estado, respuesta FROM objetivos WHERE estado != 'abierto' ORDER BY ultima DESC LIMIT 8")],
        "notas": [{"titulo": t, "url": u, "resumen": r, "cita": c, "fecha": f, "estado": e} for t, u, r, c, f, e in todos(
            "SELECT l.titulo, l.url, n.resumen, n.cita, n.fecha, n.estado FROM notas n JOIN lecturas l ON l.id=n.lectura_id "
            "WHERE n.estado != 'vencida' ORDER BY n.id DESC LIMIT 15")],
        "conexiones": [{"a": a, "b": b, "texto": t, "fecha": f} for a, b, t, f in todos(
            "SELECT la.titulo, lb.titulo, c.texto, c.fecha FROM conexiones c "
            "JOIN notas na ON na.id=c.nota_a JOIN lecturas la ON la.id=na.lectura_id "
            "JOIN notas nb ON nb.id=c.nota_b JOIN lecturas lb ON lb.id=nb.lectura_id "
            "WHERE c.valida=1 ORDER BY c.id DESC LIMIT 6")],
        "de_fran": [{"pregunta": p, "respuesta": r, "fecha": f} for p, r, f in todos(
            "SELECT pregunta, respuesta, fecha FROM respuestas_fran ORDER BY id DESC LIMIT 6")],
        "diario": diario(),
        "vigilancia": [{"clave": c, "hasta": h, "motivo": m} for c, _, h, m in vigilancia.vigentes(con)],
        "mensajes_sin_leer": len(bandeja.pendientes(con)),
    }


# ---------------------------------------------------------------- servidor

class Manejador(BaseHTTPRequestHandler):
    server_version = "Angri"

    def log_message(self, *args):
        pass

    def _responder(self, codigo: int, cuerpo: bytes, tipo="application/json; charset=utf-8", cache="no-store"):
        self.send_response(codigo)
        self.send_header("Content-Type", tipo)
        self.send_header("Content-Length", str(len(cuerpo)))
        self.send_header("Cache-Control", cache)
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Security-Policy",
                         "default-src 'self'; style-src 'self' 'unsafe-inline'; script-src 'self' 'unsafe-inline'; img-src 'self' data:")
        self.end_headers()
        self.wfile.write(cuerpo)

    def _json(self, datos, codigo=200):
        self._responder(codigo, json.dumps(datos, ensure_ascii=False).encode("utf-8"))

    def _autorizado(self, datos: dict | None = None) -> bool:
        dada = self.headers.get("X-Clave", "") or (datos or {}).get("clave", "")
        return secrets.compare_digest(str(dada), clave())

    def _estatico(self, ruta: str):
        """Sirve css/js de la carpeta web/. Solo nombres simples y extensiones conocidas: nada sale de esa carpeta."""
        partes = ruta.removeprefix("/static/").split("/")
        archivo = WEB.joinpath(*partes)
        if (not all(re.fullmatch(r"[\w][\w.-]*", p) for p in partes) or archivo.suffix not in TIPOS
                or not archivo.is_file()):
            return self._json({"error": "no existe"}, 404)
        # three.js no cambia nunca: se guarda una semana. Lo propio se pide siempre de nuevo.
        cache = "max-age=604800, immutable" if partes[0] == "vendor" else "no-store"
        self._responder(200, archivo.read_bytes(), TIPOS[archivo.suffix], cache)

    def do_GET(self):
        ruta = urlparse(self.path).path
        if ruta == "/":
            return self._responder(200, PAGINA.read_bytes(), "text/html; charset=utf-8")
        if ruta.startswith("/static/"):
            return self._estatico(ruta)
        if ruta == "/api/estado":
            if not self._autorizado():
                return self._json({"error": "clave"}, 401)
            con = memoria.abrir()
            try:
                return self._json(estado(con))
            finally:
                con.close()
        self._json({"error": "no existe"}, 404)

    def do_POST(self):
        largo = min(int(self.headers.get("Content-Length", 0)), 20_000)
        try:
            datos = json.loads(self.rfile.read(largo) or b"{}")
        except ValueError:
            return self._json({"error": "json"}, 400)
        if not self._autorizado(datos):
            return self._json({"error": "clave"}, 401)
        ruta = urlparse(self.path).path
        sesion = str(datos.get("sesion", ""))

        if ruta == "/api/charla/iniciar":
            if (c := ahora.charla_activa()) and c.get("sesion") != sesion:
                # Otra pestaña o dispositivo tenía la charla abierta: se la toma esta.
                _historiales.pop(c.get("sesion"), None)
            sesion = uuid.uuid4().hex[:8]
            cortado = ahora.iniciar_charla(sesion)
            _historiales[sesion] = []
            con = memoria.abrir()
            try:
                with _turno:
                    try:
                        hola = bandeja.saludo(con)
                    except OSError:
                        hola = None
                if hola:
                    memoria.guardar_episodio(con, sesion, "angri", hola)
                    _historiales[sesion].append({"role": "assistant", "content": hola})
            finally:
                con.close()
            return self._json({"sesion": sesion, "texto": hola, "cortado": cortado,
                               "restante": config.CHARLA_WEB_INACTIVIDAD_MIN * 60})

        if ruta == "/api/charla/terminar":
            c = ahora.charla_activa()
            if c and c.get("sesion") == sesion:
                ahora.terminar_charla()
                _historiales.pop(sesion, None)
            return self._json({"ok": True})

        # Lo que sigue necesita una charla abierta y que sea la de esta página
        c = ahora.latido(sesion, mensaje=(ruta == "/api/mensaje"))
        if not c:
            return self._json({"error": "La charla se cerró. Iniciá otra cuando quieras."}, 409)

        if ruta == "/api/charla/latido":
            return self._json({"restante": ahora.segundos_restantes(c)})

        con = memoria.abrir()
        try:
            historial = _historiales.setdefault(sesion, [])
            if ruta == "/api/novedades":
                resto = bandeja.resto(con)
                if resto:
                    historial.append({"role": "assistant", "content": resto})
                return self._json({"texto": resto or "Nada más por ahora.", "restante": ahora.segundos_restantes(c)})
            if ruta == "/api/mensaje":
                texto = str(datos.get("texto", "")).strip()[:2000]
                if not texto:
                    return self._json({"error": "vacío"}, 400)
                with _turno:
                    respuesta, _ = charla.responder(con, sesion, historial, texto)
                c = ahora.latido(sesion, mensaje=True) or c
                return self._json({"texto": respuesta, "restante": ahora.segundos_restantes(c)})
            return self._json({"error": "no existe"}, 404)
        except OSError:
            return self._json({"error": "El modelo no responde ahora. Probá en un rato."}, 503)
        finally:
            con.close()


def main():
    clave()
    servidor = ThreadingHTTPServer(("0.0.0.0", config.WEB_PUERTO), Manejador)
    print(f"Angri web en el puerto {config.WEB_PUERTO}")
    servidor.serve_forever()


if __name__ == "__main__":
    main()
