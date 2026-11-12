"""Herramienta de revisión: muestra las últimas notas pedidas al modelo con su anclaje.

Uso: python3 -m angri.revisar [N]
"""
import json
import re
import sys

from . import config, verificar


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 3
    lineas = (config.LOGS / "llamadas.jsonl").read_text(encoding="utf-8").splitlines()
    notas = [json.loads(l) for l in lineas if '"tarea": "nota"' in l][-n:]
    for r in notas:
        m = re.search(r"<texto>\n(.*)\n</texto>", r["pedido"], re.S)
        fuente = m.group(1) if m else ""
        resumen, cita = verificar.separar_resumen_y_cita(r["respuesta"])
        titulo = re.search(r"TÍTULO: (.*)", r["pedido"])
        print("=" * 70)
        print("TÍTULO:", titulo.group(1) if titulo else "?")
        print("FUENTE (inicio):", " ".join(fuente.split())[:400])
        print("RESPUESTA:", r["respuesta"])
        print(f"ANCLAJE: {verificar.anclaje(resumen, fuente):.0%}  CITA OK: {bool(cita) and verificar.cita_valida(cita, fuente)}")


if __name__ == "__main__":
    main()
