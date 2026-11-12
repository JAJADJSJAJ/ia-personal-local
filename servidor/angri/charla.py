"""Charla con Angri por terminal (fase B). Uso: angri charla  (por SSH: ssh -t fran@angri.local angri charla)

Cada mensaje se guarda al instante como episodio. Antes de responder trae los recuerdos
con mejor puntaje (recencia + importancia + relevancia) y los pega con su procedencia.
Mientras dura la charla, el ciclo de fondo no corre: la charla tiene prioridad.
"""
import sys
import uuid

from . import config, memoria, modelo, recordar

SISTEMA_CHARLA = """Sos Angri. Hablás con Fran en español rioplatense, con voseo, de forma breve y natural.
Sos una IA que vive en una computadora en el cuarto de Fran; leés cosas por tu cuenta y tenés memoria.
Antes de cada mensaje de Fran aparecen tus RECUERDOS relacionados. Usalos para responder.
Si lo que te preguntan no está en tus recuerdos ni en la charla, decí que no te acordás: no inventes.
Respondés solo con lo que decís, sin acotaciones ni acciones entre asteriscos."""

MENSAJE_CON_RECUERDOS = """[RECUERDOS que te vienen a la mente]
{recuerdos}

[Fran dice]
{mensaje}"""


def _marcar_charlando():
    config.CHARLANDO.touch()


def responder(con, sesion: str, historial: list[dict], mensaje: str) -> tuple[str, list[dict]]:
    memoria.guardar_episodio(con, sesion, "fran", mensaje)
    recordar.indexar_pendientes(con)
    recuerdos = recordar.recuperar(con, mensaje, excluir_sesion=sesion)
    actual = MENSAJE_CON_RECUERDOS.format(recuerdos=recordar.como_texto(recuerdos), mensaje=mensaje) if recuerdos else mensaje
    # El historial guarda los mensajes limpios; los recuerdos solo acompañan al mensaje actual
    turnos = historial[-config.TURNOS_DE_CONTEXTO * 2:] + [{"role": "user", "content": actual}]
    respuesta = modelo.conversar("charla", SISTEMA_CHARLA, turnos, url=config.CHARLA_URL)
    memoria.guardar_episodio(con, sesion, "angri", respuesta)
    historial += [{"role": "user", "content": mensaje}, {"role": "assistant", "content": respuesta}]
    return respuesta, recuerdos


def main():
    con = memoria.abrir()
    sesion = uuid.uuid4().hex[:8]
    historial: list[dict] = []
    ver = "--recuerdos" in sys.argv
    print("Charla con Angri. Escribí 'chau' para salir.\n")
    try:
        while True:
            _marcar_charlando()
            try:
                mensaje = input("vos › ").strip()
            except EOFError:
                break
            if not mensaje:
                continue
            if mensaje.lower() in {"chau", "salir", "exit"}:
                break
            _marcar_charlando()
            respuesta, recuerdos = responder(con, sesion, historial, mensaje)
            if ver:
                for r in recuerdos:
                    print(f"   · {r['puntaje']:.2f} sim {r['similitud']:.2f} [{r['origen']}] {r['texto'][:70]}")
            print("angri ›", respuesta, "\n")
    finally:
        config.CHARLANDO.unlink(missing_ok=True)
        con.close()


if __name__ == "__main__":
    main()
