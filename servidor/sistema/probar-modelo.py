"""Prueba rápida de que el modelo de día responde. Uso: python3 probar-modelo.py [puerto]"""
import json
import sys
import time
import urllib.request

puerto = sys.argv[1] if len(sys.argv) > 1 else "8080"
cuerpo = {"messages": [{"role": "user", "content": "Decí hola en una palabra."}], "max_tokens": 10}
pedido = urllib.request.Request(
    f"http://127.0.0.1:{puerto}/v1/chat/completions",
    data=json.dumps(cuerpo).encode(),
    headers={"Content-Type": "application/json"},
)
t0 = time.time()
with urllib.request.urlopen(pedido, timeout=120) as r:
    print(json.load(r)["choices"][0]["message"]["content"].strip(), f"({time.time() - t0:.1f}s)")
