"""Muestra el coseno entre consultas y todo lo que hay en memoria, para elegir SIMILITUD_MINIMA.

Uso (en angri): cd /opt/angri/codigo && sudo -u angri ANGRI_DATOS=/var/lib/angri python3 ~/pruebas/calibrar-similitud.py
"""
import sys

sys.path.insert(0, "/opt/angri/codigo")
import numpy as np  # noqa: E402

from angri import memoria, vectores  # noqa: E402

CONSULTAS = [
    ("¿te acordás cómo se llama mi perro?", "perro"),
    ("¿Leíste algo sobre volcanes últimamente?", "volcán"),
    ("¿sabés cuál es mi color favorito?", None),
    ("¿qué música me gusta?", None),
    ("¿conocés alguna cantante de ópera?", "Souza"),
    ("¿qué sabés de poesía coreana?", "Choi"),
]

con = memoria.abrir()
filas = con.execute(
    "SELECT v.tipo, v.ref_id, v.vector FROM vectores v LEFT JOIN episodios e ON v.tipo='episodio' AND e.id=v.ref_id "
    "WHERE v.tipo='nota' OR (e.quien='fran' AND e.texto NOT LIKE '%?')"
).fetchall()
textos = []
for tipo, ref_id, _ in filas:
    if tipo == "nota":
        t = con.execute("SELECT l.titulo FROM notas n JOIN lecturas l ON l.id=n.lectura_id WHERE n.id=?", (ref_id,)).fetchone()[0]
    else:
        t = con.execute("SELECT texto FROM episodios WHERE id=?", (ref_id,)).fetchone()[0]
    textos.append(t[:45])
m = np.frombuffer(b"".join(f[2] for f in filas), dtype=np.float32).reshape(len(filas), -1)

for consulta, esperado in CONSULTAS:
    sim = m @ vectores.consulta(consulta)
    orden = np.argsort(-sim)[:3]
    print(f"\n{consulta}   (esperado: {esperado or 'NADA'})")
    for i in orden:
        print(f"   {sim[i]:.3f}  {textos[i]}")
