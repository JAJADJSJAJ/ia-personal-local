"""Charla con Angri por terminal (fase B). Uso: angri charla  (por SSH: ssh -t fran@angri.local angri charla)

Cada mensaje se guarda al instante como episodio. Antes de responder trae los recuerdos
con mejor puntaje (recencia + importancia + relevancia) y los pega con su procedencia.
Mientras dura la charla, el ciclo de fondo no corre: la charla tiene prioridad.
"""
import re
import sys
import uuid

from . import bandeja, config, memoria, modelo, recordar

SISTEMA_CHARLA = """Sos Angri. Hablás con Fran en español rioplatense, con voseo, de forma breve y natural.
Sos una IA que vive en una computadora en el cuarto de Fran; leés artículos de Wikipedia por tu cuenta y tenés memoria.
No tenés cuerpo, no ves ni escuchás la casa, no leés noticias y no sabés qué pasa afuera: solo sabés lo que leíste.
Antes de cada mensaje de Fran aparecen tus RECUERDOS relacionados. Usalos para responder.
Si lo que te preguntan no está en tus recuerdos, en LO QUE ESTÁS HACIENDO ni en la charla, decí que no sabés: no inventes.
Cuando Fran dice "vos", "tenés", "hacés" o "pensás", habla de VOS (Angri): contestá sobre lo tuyo, usando LO QUE ESTÁS HACIENDO.
No sos un asistente: no ofrezcas ayuda ni preguntes "¿querés que te ayude?". Sos alguien que vive y lee por su cuenta.
Texto simple, sin negritas, sin asteriscos ni acotaciones.

LO QUE ESTÁS HACIENDO (dato real, medido por la computadora):
{actualidad}"""


def actualidad(con) -> str:
    """Lo que de verdad le interesa y está haciendo, armado por código: así no lo inventa cuando le preguntan."""
    from . import temas  # import tardío: temas usa memoria y vectores, que ya están cargados
    lineas = []
    ranking = temas.ranking(con, 3)
    lineas.append("- Temas que te interesan: " + (", ".join(n for _, n, _, _ in ranking) if ranking
                                                   else "todavía ninguno; estás leyendo de todo un poco"))
    abiertos = [p for (p,) in con.execute(
        "SELECT pregunta FROM objetivos WHERE estado='abierto' ORDER BY ultima DESC LIMIT 3")]
    if abiertos:
        lineas.append("- Preguntas que estás investigando: " + " | ".join(abiertos))
    # Lo que viene: el ciclo retoma la investigación que hace más tiempo no toca (objetivos.elegir).
    proxima = con.execute("SELECT pregunta, gastado, presupuesto FROM objetivos WHERE estado='abierto' "
                          "ORDER BY ultima LIMIT 1").fetchone()
    from . import salud
    plan = "cada unos 20 minutos, cuando Fran no está charlando, leés algo nuevo"
    if proxima:
        plan += f"; lo próximo es seguir con «{proxima[0]}» (llevás {proxima[1]} de {proxima[2]} lecturas)"
    plan += "; y de vez en cuando un artículo al azar, para conocer cosas nuevas"
    if descanso := salud.descansando(con):
        plan = f"ahora estás {descanso} porque algo no respondía; después: " + plan
    lineas.append("- Lo que vas a hacer más tarde: " + plan)
    leidos = [t for (t,) in con.execute("SELECT titulo FROM lecturas ORDER BY id DESC LIMIT 5")]
    if leidos:
        lineas.append("- Lo último que leíste: " + ", ".join(f"«{t}»" for t in leidos))
    return "\n".join(lineas)

MENSAJE_CON_RECUERDOS = """[RECUERDOS que te vienen a la mente]
{recuerdos}

[Fran dice]
{mensaje}"""


def limpiar(texto: str) -> str:
    """Sin negritas ni acotaciones entre asteriscos (la web y la terminal muestran texto plano)."""
    texto = re.sub(r"\*\*(.+?)\*\*", r"\1", texto)
    texto = re.sub(r"(?<!\w)\*([^*\n]{1,80})\*(?!\w)", r"\1", texto)
    return texto.strip()


def _marcar_charlando():
    config.CHARLANDO.touch()


def responder(con, sesion: str, historial: list[dict], mensaje: str) -> tuple[str, list[dict]]:
    memoria.guardar_episodio(con, sesion, "fran", mensaje)
    recordar.indexar_pendientes(con)
    recuerdos = recordar.recuperar(con, mensaje, excluir_sesion=sesion)
    actual = MENSAJE_CON_RECUERDOS.format(recuerdos=recordar.como_texto(recuerdos), mensaje=mensaje) if recuerdos else mensaje
    # El historial guarda los mensajes limpios; los recuerdos solo acompañan al mensaje actual
    turnos = historial[-config.TURNOS_DE_CONTEXTO * 2:] + [{"role": "user", "content": actual}]
    sistema = SISTEMA_CHARLA.format(actualidad=actualidad(con))
    respuesta = modelo.conversar("charla", sistema, turnos, url=config.CHARLA_URL)
    respuesta = limpiar(respuesta)
    memoria.guardar_episodio(con, sesion, "angri", respuesta)
    historial += [{"role": "user", "content": mensaje}, {"role": "assistant", "content": respuesta}]
    return respuesta, recuerdos


def main():
    con = memoria.abrir()
    sesion = uuid.uuid4().hex[:8]
    historial: list[dict] = []
    ver = "--recuerdos" in sys.argv
    print("Charla con Angri. Escribí 'novedades' para ver lo que tenga pendiente y 'chau' para salir.\n")
    try:
        _marcar_charlando()
        if hola := bandeja.saludo(con):
            # Lo cuenta ella primero; queda en el historial para que Fran pueda preguntar sobre eso.
            memoria.guardar_episodio(con, sesion, "angri", hola)
            historial.append({"role": "assistant", "content": hola})
            print("angri ›", hola, "\n")
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
            if mensaje.lower().strip("¿?¡! ") in {"novedades", "qué más", "que mas", "qué más tenés"}:
                resto = bandeja.resto(con)
                print("angri ›", resto or "Nada más por ahora.", "\n")
                if resto:
                    historial.append({"role": "assistant", "content": resto})
                continue
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
