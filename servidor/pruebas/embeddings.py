"""Compara modelos de embeddings en español: para cada consulta, ¿el texto correcto queda primero?

Uso: python3 embeddings.py PUERTO [prefijo_consulta] [prefijo_documento]
"""
import json
import math
import sys
import time
import urllib.request

puerto = sys.argv[1]
pre_q = sys.argv[2] if len(sys.argv) > 2 else ""
pre_d = sys.argv[3] if len(sys.argv) > 3 else ""

DOCUMENTOS = [
    "Fran me contó que consiguió el adaptador wifi para la PC del cuarto.",
    "Los pulpos tienen tres corazones y nadar los agota.",
    "El volcán Tupungato es el más alto del sur de los Andes, entre Argentina y Chile.",
    "Fran hace juegos en Roblox; el último es de mascotas que se incuban.",
    "Noemí Souza fue una mezzosoprano argentina que cantó en el Teatro Colón.",
    "Fran estudia en la facultad y vuelve cansado los martes.",
    "Las abejas comunican dónde hay flores con una danza.",
    "Un autómata finito determinista tiene una sola transición posible por símbolo.",
]
# (consulta, índice del documento que debería quedar primero)
CONSULTAS = [
    ("¿Qué te conté del wifi?", 0),
    ("animales marinos con varios corazones", 1),
    ("montañas altas en Sudamérica", 2),
    ("¿En qué juego estoy trabajando?", 3),
    ("cantantes de ópera de Argentina", 4),
    ("¿Cómo me va con los estudios?", 5),
    ("insectos que bailan", 6),
    ("teoría de la computación", 7),
    ("¿Me acordás qué compré para la compu?", 0),
    ("biología de los cefalópodos", 1),
]


def embeber(textos):
    pedido = urllib.request.Request(
        f"http://127.0.0.1:{puerto}/v1/embeddings",
        data=json.dumps({"input": textos}).encode(), headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(pedido, timeout=120) as r:
        return [d["embedding"] for d in json.load(r)["data"]]


def coseno(a, b):
    return sum(x * y for x, y in zip(a, b)) / (math.sqrt(sum(x * x for x in a)) * math.sqrt(sum(y * y for y in b)))


t0 = time.time()
docs = embeber([pre_d + d for d in DOCUMENTOS])
qs = embeber([pre_q + q for q, _ in CONSULTAS])
segundos = time.time() - t0

aciertos, margen = 0, 0.0
for (q, correcto), vq in zip(CONSULTAS, qs):
    puntajes = sorted(((coseno(vq, vd), i) for i, vd in enumerate(docs)), reverse=True)
    acierto = puntajes[0][1] == correcto
    aciertos += acierto
    margen += puntajes[0][0] - puntajes[1][0] if acierto else 0
    print(f"{'✓' if acierto else '✗'} {q}  →  {DOCUMENTOS[puntajes[0][1]][:50]}")
print(f"\nAciertos: {aciertos}/{len(CONSULTAS)}   margen medio: {margen / len(CONSULTAS):.3f}   "
      f"tiempo: {segundos:.1f}s para {len(DOCUMENTOS) + len(CONSULTAS)} textos   dimensión: {len(docs[0])}")
