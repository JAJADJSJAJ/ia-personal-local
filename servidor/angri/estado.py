"""Estado de Angri: contadores medidos por código y las últimas líneas del diario."""
from datetime import date, timedelta

from . import bandeja, config, memoria, salud, temas


def main():
    con = memoria.abrir()
    hoy = date.today().isoformat()
    semana = (date.today() - timedelta(days=7)).isoformat()

    def contar(sql, *args):
        return con.execute(sql, args).fetchone()[0]

    print("Angri —", "EN PAUSA" if config.PAUSA.exists() else (salud.descansando(con) or "despierta"))
    print()
    print(f"Lecturas      hoy {contar('SELECT COUNT(*) FROM lecturas WHERE fecha >= ?', hoy):>4}"
          f"   semana {contar('SELECT COUNT(*) FROM lecturas WHERE fecha >= ?', semana):>4}"
          f"   total {contar('SELECT COUNT(*) FROM lecturas'):>5}")
    print(f"Notas         hoy {contar('SELECT COUNT(*) FROM notas WHERE fecha >= ?', hoy):>4}"
          f"   total {contar('SELECT COUNT(*) FROM notas'):>5}")
    abiertas = contar("SELECT COUNT(*) FROM preguntas WHERE estado='abierta'")
    print(f"Preguntas     abiertas {abiertas:>4}")
    print(f"Mensajes para vos sin leer {len(bandeja.pendientes(con)):>3}   (se los cuenta al abrir 'angri charla')")
    ranking = temas.ranking(con, 5)
    if ranking:
        print("\nLo que le interesa ahora (temas que se formaron solos):")
        for _, nombre, peso, n in ranking:
            print(f"  {nombre:<32} peso {peso:4.1f}   {n} notas")
    abiertos = con.execute(
        "SELECT pregunta, gastado, presupuesto FROM objetivos WHERE estado='abierto' ORDER BY ultima DESC"
    ).fetchall()
    if abiertos:
        print("\nInvestigando:")
        for p, g, pres in abiertos:
            print(f"  [{g}/{pres}] {p}")
    cerrados = con.execute(
        "SELECT pregunta, estado, respuesta FROM objetivos WHERE estado != 'abierto' ORDER BY ultima DESC LIMIT 3"
    ).fetchall()
    if cerrados:
        print("\nÚltimas investigaciones cerradas:")
        for p, e, r in cerrados:
            print(f"  ({e}) {p}")
            if r:
                print(f"     → {' '.join(r.split())[:200]}")
    modos = dict(con.execute("SELECT modo, COUNT(*) FROM ciclos WHERE fecha >= ? GROUP BY modo", (hoy,)).fetchall())
    if modos:
        print(f"\nCiclos hoy: {modos.get('azar', 0)} al azar, {modos.get('objetivo', 0)} siguiendo sus preguntas"
              f", {modos.get('falla', 0)} con fallas")
    print()
    print("Últimos 7 días:")
    for tipo, n in con.execute(
        "SELECT tipo, COUNT(*) FROM eventos WHERE fecha >= ? GROUP BY tipo ORDER BY 2 DESC", (semana,)
    ):
        print(f"  {tipo:<22}{n:>5}")

    archivo = config.DIARIO / f"{date.today():%Y-%m-%d}.md"
    if archivo.exists():
        print("\nDiario de hoy (últimas líneas):")
        for linea in archivo.read_text(encoding="utf-8").splitlines()[-5:]:
            if linea.startswith("- "):
                print(" ", linea[2:])
    con.close()


def notas(cantidad: int = 5):
    con = memoria.abrir()
    filas = con.execute(
        "SELECT n.fecha, l.titulo, l.url, n.resumen, n.cita, n.estado FROM notas n "
        "JOIN lecturas l ON l.id = n.lectura_id ORDER BY n.id DESC LIMIT ?", (cantidad,)
    ).fetchall()
    for fecha, titulo, url, resumen, cita, estado in reversed(filas):
        print(f"── {fecha[:16].replace('T', ' ')} · {titulo} ({estado})")
        print(f"   {url}")
        print("   " + resumen.replace("\n", "\n   "))
        print(f"   CITA: {cita}\n")
    con.close()


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "notas":
        notas(int(sys.argv[2]) if len(sys.argv) > 2 else 5)
    else:
        main()
