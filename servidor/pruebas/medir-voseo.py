"""Mide cuánto vosea Angri: manda preguntas con el prompt real de la charla y cuenta marcas de voseo y de tuteo.

Uso (en angri):  sudo -u angri ANGRI_DATOS=/var/lib/angri python3 medir-voseo.py [url del modelo] [repeticiones]
Se corre antes y después del vector de control, con el mismo servidor y las mismas preguntas.
"""
import json
import re
import sys
import urllib.request

sys.path.insert(0, "/opt/angri/codigo")
from angri import charla, config, memoria  # noqa: E402

PREGUNTAS = [
    "Hola, ¿cómo andás?", "¿Qué hiciste hoy?", "Contame algo que hayas leído.", "¿Te puedo hacer una pregunta?",
    "¿Qué opinás de lo que estás leyendo?", "¿Me recomendás algo para leer?", "Estoy cansado, me voy a dormir.",
    "¿Qué te gustaría aprender?", "¿Sabés algo de música?", "Explicame qué es un partido político.",
    "¿Querés que te cuente algo?", "¿Qué necesitás para seguir aprendiendo?",
]

VOSEO = re.compile(r"\b(vos|tenés|sabés|querés|podés|andás|contame|decime|mirá|fijate|sos|hacés|pensás|leés|"
                   r"necesitás|preguntá|avisame|contás|decís|venís|escribís|elegí|sentís)\b", re.I)
TUTEO = re.compile(r"\b(tú|tienes|sabes|quieres|puedes|andas|cuéntame|dime|mira|fíjate|eres|haces|piensas|lees|"
                   r"necesitas|pregunta|avísame|cuentas|dices|vienes|escribes|sientes|contigo)\b", re.I)


def main():
    url = sys.argv[1] if len(sys.argv) > 1 else config.CHARLA_URL
    reps = int(sys.argv[2]) if len(sys.argv) > 2 else 2
    con = memoria.abrir()
    sistema = charla.SISTEMA_CHARLA.format(actualidad=charla.actualidad(con)) + charla.reflexiones_para(con, "hola")
    v = t = 0
    con_tuteo = []
    for _ in range(reps):
        for p in PREGUNTAS:
            cuerpo = {"messages": [{"role": "system", "content": sistema}, {"role": "user", "content": p}],
                      "max_tokens": 200, "chat_template_kwargs": {"enable_thinking": False}, **config.MUESTREO}
            req = urllib.request.Request(url, json.dumps(cuerpo).encode(), {"Content-Type": "application/json"})
            r = json.load(urllib.request.urlopen(req, timeout=600))["choices"][0]["message"]["content"]
            nv, nt = len(VOSEO.findall(r)), len(TUTEO.findall(r))
            v, t = v + nv, t + nt
            if nt:
                con_tuteo.append(f"[{p}] {' '.join(r.split())[:160]}")
    total = v + t or 1
    print(f"voseo {v}  tuteo {t}  -> {100 * v / total:.0f}% voseo, {len(con_tuteo)} respuestas con tuteo de {reps * len(PREGUNTAS)}")
    for linea in con_tuteo[:5]:
        print("  ", linea)


if __name__ == "__main__":
    main()
