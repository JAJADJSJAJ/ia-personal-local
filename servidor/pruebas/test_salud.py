import tempfile
import unittest
from datetime import datetime, timedelta

from pathlib import Path

from angri import config, memoria, salud, verificar

config.DATOS = Path(tempfile.mkdtemp())
config.BASE = config.DATOS / "memoria.db"


class Salud(unittest.TestCase):
    def setUp(self):
        if config.BASE.exists():
            config.BASE.unlink()
        self.con = memoria.abrir()
        self.diario = []

    def tearDown(self):
        self.con.close()

    def fallar(self, oid=None, hace_min=0, mensaje="sin red"):
        try:
            raise ValueError(mensaje)
        except ValueError as e:
            salud.registrar_falla(self.con, e, oid, self.diario.append)
        if hace_min:
            fecha = (datetime.now() - timedelta(minutes=hace_min)).isoformat(timespec="seconds")
            self.con.execute("UPDATE ciclos SET fecha=? WHERE id=(SELECT MAX(id) FROM ciclos)", (fecha,))

    def test_espera_crece_con_tope(self):
        self.assertEqual(salud.espera_minutos(2), 0)
        self.assertEqual(salud.espera_minutos(3), 60)
        self.assertEqual(salud.espera_minutos(4), 120)
        self.assertEqual(salud.espera_minutos(20), 360)

    def test_descansa_tras_tres_fallas_y_avisa(self):
        self.fallar(); self.fallar()
        self.assertIsNone(salud.descansando(self.con))
        self.fallar()
        self.assertIsNotNone(salud.descansando(self.con))
        self.assertTrue(any("no responde" in l for l in self.diario))

    def test_el_descanso_se_termina(self):
        self.fallar(); self.fallar(); self.fallar(hace_min=61)
        self.assertIsNone(salud.descansando(self.con))

    def test_429_descansa_enseguida(self):
        self.fallar(mensaje="HTTP Error 429: Too Many Requests")
        self.assertIsNotNone(salud.descansando(self.con))

    def test_un_ciclo_bueno_corta_la_racha(self):
        self.fallar(); self.fallar(); self.fallar()
        self.con.execute("INSERT INTO ciclos (fecha, modo, resultado) VALUES (?, 'azar', 'ok')", (memoria.ahora(),))
        self.assertEqual(salud.fallas_seguidas(self.con), [])

    def test_abandona_objetivo_que_rompe(self):
        self.con.execute("INSERT INTO objetivos (id, pregunta, presupuesto, creado, ultima) VALUES (7, '¿Algo?', 5, ?, ?)",
                         (memoria.ahora(), memoria.ahora()))
        self.fallar(7)
        self.assertEqual(self.con.execute("SELECT estado FROM objetivos WHERE id=7").fetchone()[0], "abierto")
        self.fallar(7)
        self.assertEqual(self.con.execute("SELECT estado FROM objetivos WHERE id=7").fetchone()[0], "fallido")


class PreguntasMeta(unittest.TestCase):
    def test_descarta_meta(self):
        self.assertIsNone(verificar.pregunta_valida(
            "¿Qué otro detalle del contexto histórico se podría haber incluido en esa nota sin contradecirla?"))
        self.assertIsNone(verificar.pregunta_valida("¿Por qué el texto no explica la fecha?"))

    def test_deja_preguntas_del_mundo(self):
        p = "¿Cómo influyó en los faliscos la proximidad geográfica entre Etruria, Lacio y Roma?"
        self.assertEqual(verificar.pregunta_valida(p), p)


if __name__ == "__main__":
    unittest.main()
