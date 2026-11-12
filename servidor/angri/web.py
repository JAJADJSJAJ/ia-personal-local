"""Charla con Angri desde el navegador (celular o PC), solo dentro de la red de casa.

Uso: python3 -m angri.web   (lo corre el servicio angri-web en el puerto 8080)
Se entra una vez con http://angri.local:8080/?clave=XXXX; la página guarda la clave y después alcanza con
http://angri.local:8080. La clave está en /var/lib/angri/web-clave (`angri web` la muestra).

Solo usa la biblioteca estándar. El modelo es uno solo y lento, así que las respuestas van de a una.
"""
import json
import secrets
import threading
import time
import uuid
from datetime import date
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from . import bandeja, charla, config, memoria, reflexion, salud, temas

PAGINA = Path(__file__).with_name("web.html")
_turno = threading.Lock()                 # una respuesta del modelo a la vez
_sesiones: dict[str, dict] = {}           # sesion -> {"historial": [...], "ultimo": timestamp}
SESION_VENCE = 3600


def clave() -> str:
    archivo = config.DATOS / "web-clave"
    if not archivo.exists() or not archivo.read_text().strip():
        memoria.escribir_seguro(archivo, secrets.token_urlsafe(12))
        archivo.chmod(0o600)
    return archivo.read_text().strip()


def _sesion(sid: str | None) -> tuple[str, list]:
    ahora = time.time()
    for s in [s for s, v in _sesiones.items() if ahora - v["ultimo"] > SESION_VENCE]:
        del _sesiones[s]
    if not sid or sid not in _sesiones:
        sid = uuid.uuid4().hex[:8]
        _sesiones[sid] = {"historial": [], "ultimo": ahora}
    _sesiones[sid]["ultimo"] = ahora
    return sid, _sesiones[sid]["historial"]


def estado(con) -> dict:
    hoy = date.today().isoformat()
    diario = config.DIARIO / f"{hoy}.md"
    lineas = [l[2:] for l in diario.read_text(encoding="utf-8").splitlines() if l.startswith("- ")] if diario.exists() else []
    return {
        "situacion": "en pausa" if config.PAUSA.exists() else (salud.descansando(con) or "despierta"),
        "lecturas_hoy": con.execute("SELECT COUNT(*) FROM lecturas WHERE fecha >= ?", (hoy,)).fetchone()[0],
        "notas_total": con.execute("SELECT COUNT(*) FROM notas").fetchone()[0],
        "temas": [{"nombre": n, "peso": round(p, 1), "notas": k} for _, n, p, k in temas.ranking(con, 5)],
        "investigando": [{"pregunta": p, "gastado": g, "presupuesto": t} for p, g, t in con.execute(
            "SELECT pregunta, gastado, presupuesto FROM objetivos WHERE estado='abierto' ORDER BY ultima DESC")],
        "cerradas": [{"pregunta": p, "estado": e, "respuesta": r} for p, e, r in con.execute(
            "SELECT pregunta, estado, respuesta FROM objetivos WHERE estado != 'abierto' ORDER BY ultima DESC LIMIT 5")],
        "mensajes_sin_leer": len(bandeja.pendientes(con)),
        "diario": lineas[-12:][::-1],
        "quien_soy": (reflexion.leer("quien-soy.md") or "").split("## Datos")[0].replace("# Quién soy", "").strip(),
    }


class Manejador(BaseHTTPRequestHandler):
    server_version = "Angri"

    def log_message(self, *args):  # sin ruido en el journal por cada pedido
        pass

    def _responder(self, codigo: int, cuerpo: bytes, tipo="application/json; charset=utf-8"):
        self.send_response(codigo)
        self.send_header("Content-Type", tipo)
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Security-Policy", "default-src 'self'; style-src 'self' 'unsafe-inline'; script-src 'self' 'unsafe-inline'")
        self.end_headers()
        self.wfile.write(cuerpo)

    def _json(self, datos, codigo=200):
        self._responder(codigo, json.dumps(datos, ensure_ascii=False).encode("utf-8"))

    def _autorizado(self) -> bool:
        return secrets.compare_digest(self.headers.get("X-Clave", ""), clave())

    def do_GET(self):
        ruta = urlparse(self.path).path
        if ruta == "/":
            self._responder(200, PAGINA.read_bytes(), "text/html; charset=utf-8")
        elif ruta == "/api/estado":
            if not self._autorizado():
                return self._json({"error": "clave"}, 401)
            con = memoria.abrir()
            try:
                self._json(estado(con))
            finally:
                con.close()
        else:
            self._json({"error": "no existe"}, 404)

    def do_POST(self):
        if not self._autorizado():
            return self._json({"error": "clave"}, 401)
        largo = min(int(self.headers.get("Content-Length", 0)), 20_000)
        try:
            datos = json.loads(self.rfile.read(largo) or b"{}")
        except ValueError:
            return self._json({"error": "json"}, 400)
        ruta = urlparse(self.path).path
        config.CHARLANDO.touch()
        con = memoria.abrir()
        try:
            sid, historial = _sesion(datos.get("sesion"))
            if ruta == "/api/hola":
                with _turno:
                    hola = bandeja.saludo(con)
                if hola:
                    memoria.guardar_episodio(con, sid, "angri", hola)
                    con.commit()
                    historial.append({"role": "assistant", "content": hola})
                self._json({"sesion": sid, "texto": hola})
            elif ruta == "/api/novedades":
                resto = bandeja.resto(con)
                if resto:
                    historial.append({"role": "assistant", "content": resto})
                self._json({"sesion": sid, "texto": resto or "Nada más por ahora."})
            elif ruta == "/api/mensaje":
                texto = str(datos.get("texto", "")).strip()[:2000]
                if not texto:
                    return self._json({"error": "vacío"}, 400)
                with _turno:
                    respuesta, _ = charla.responder(con, sid, historial, texto)
                config.CHARLANDO.touch()
                self._json({"sesion": sid, "texto": respuesta})
            else:
                self._json({"error": "no existe"}, 404)
        except OSError:
            self._json({"error": "El modelo no responde ahora. Probá en un rato."}, 503)
        finally:
            con.close()


def main():
    clave()
    servidor = ThreadingHTTPServer(("0.0.0.0", config.WEB_PUERTO), Manejador)
    print(f"Angri web en el puerto {config.WEB_PUERTO}")
    servidor.serve_forever()


if __name__ == "__main__":
    main()
