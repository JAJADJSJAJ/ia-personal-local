"""Prueba de calidad: corre preguntas.json contra un llama-server y guarda las respuestas.

Uso: python3 calidad.py MODELO PUERTO SALIDA.json
"""
import json
import sys
import time
import urllib.request
from pathlib import Path

modelo, puerto, salida = sys.argv[1], sys.argv[2], sys.argv[3]
preguntas = json.loads((Path(__file__).parent / "preguntas.json").read_text(encoding="utf-8"))
url = f"http://127.0.0.1:{puerto}/v1/chat/completions"

resultados = []
for p in preguntas:
    cuerpo = {
        "messages": [
            {"role": "system", "content": p["system"]},
            {"role": "user", "content": p["user"]},
        ],
        # Muestreo recomendado para Qwen3.5 sin razonamiento
        "temperature": 0.7,
        "top_p": 0.8,
        "top_k": 20,
        "presence_penalty": 1.5,
        "max_tokens": 300,
        "chat_template_kwargs": {"enable_thinking": False},
    }
    pedido = urllib.request.Request(
        url, data=json.dumps(cuerpo).encode(), headers={"Content-Type": "application/json"}
    )
    t0 = time.time()
    with urllib.request.urlopen(pedido, timeout=900) as r:
        datos = json.load(r)
    segundos = time.time() - t0
    texto = datos["choices"][0]["message"]["content"].strip()
    resultados.append({"id": p["id"], "segundos": round(segundos, 1), "respuesta": texto})
    print(f"[{modelo}] {p['id']}: {segundos:.1f}s", flush=True)

Path(salida).write_text(json.dumps({"modelo": modelo, "resultados": resultados}, ensure_ascii=False, indent=2), encoding="utf-8")
