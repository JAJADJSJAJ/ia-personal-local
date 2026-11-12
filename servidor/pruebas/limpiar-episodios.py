"""Borra TODOS los episodios de charla (y sus vectores, accesos e índice). Para limpiar pruebas.

Uso (en angri): sudo -u angri ANGRI_DATOS=/var/lib/angri python3 limpiar-episodios.py
No toca notas, lecturas, preguntas ni el diario.
"""
import sys

sys.path.insert(0, "/opt/angri/codigo")
from angri import memoria  # noqa: E402

con = memoria.abrir()
n = con.execute("SELECT COUNT(*) FROM episodios").fetchone()[0]
con.execute("DELETE FROM vectores WHERE tipo='episodio'")
con.execute("DELETE FROM accesos WHERE tipo='episodio'")
con.execute("DELETE FROM buscar WHERE tipo='episodio'")
con.execute("DELETE FROM episodios")
con.commit()
print(f"Borrados {n} episodios.")
