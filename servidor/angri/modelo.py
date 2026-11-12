"""Llamadas al modelo. Una tarea por llamada, sin razonamiento, todo registrado."""
import json
import time
import urllib.request
from datetime import datetime

from . import config

# Personalidad base mínima: nombre e idioma. El resto lo construye ella.
SISTEMA = "Sos Angri. Escribís en español, en primera persona, de forma breve y clara."


def llamar(tarea: str, usuario: str, sistema: str = SISTEMA) -> str:
    cuerpo = {
        "messages": [{"role": "system", "content": sistema}, {"role": "user", "content": usuario}],
        "max_tokens": config.MAX_TOKENS,
        "chat_template_kwargs": {"enable_thinking": False},
        **config.MUESTREO,
    }
    pedido = urllib.request.Request(
        config.MODELO_URL, data=json.dumps(cuerpo).encode(), headers={"Content-Type": "application/json"}
    )
    t0 = time.time()
    with urllib.request.urlopen(pedido, timeout=config.TIMEOUT_MODELO) as r:
        datos = json.load(r)
    respuesta = datos["choices"][0]["message"]["content"].strip()
    _registrar(tarea, usuario, respuesta, time.time() - t0, datos.get("usage", {}))
    return respuesta


def _registrar(tarea, usuario, respuesta, segundos, uso):
    config.LOGS.mkdir(parents=True, exist_ok=True)
    linea = {
        "fecha": datetime.now().isoformat(timespec="seconds"), "tarea": tarea,
        "segundos": round(segundos, 1), "uso": uso, "pedido": usuario, "respuesta": respuesta,
    }
    with open(config.LOGS / "llamadas.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps(linea, ensure_ascii=False) + "\n")
