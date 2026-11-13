import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest import mock

from angri import bandeja, config, memoria, vigilancia

config.DATOS = Path(tempfile.mkdtemp())
config.BASE = config.DATOS / "memoria.db"


class Vigilancia(unittest.TestCase):
    def setUp(self):
        if config.BASE.exists():
            config.BASE.unlink()
        self.con = memoria.abrir()

    def tearDown(self):
        self.con.close()

    def eventos(self, tipo, n):
        for _ in range(n):
            memoria.evento(self.con, tipo, "x")

    def test_muchas_notas_rechazadas_pausan_la_lectura_y_avisan(self):
        self.eventos("nota_ok", 2)
        self.eventos("nota_rechazada", 8)
        self.assertEqual(vigilancia.vigilar_rapido(self.con), ["pausa de lectura"])
        self.assertTrue(vigilancia.ajuste(self.con, "pausa_lectura"))
        self.assertEqual(bandeja.pendientes(self.con)[0][1], "vigilancia")
        # no avisa dos veces mientras sigue la pausa
        self.assertEqual(vigilancia.vigilar_rapido(self.con), [])

    def test_rechazo_normal_no_hace_nada(self):
        self.eventos("nota_ok", 7)
        self.eventos("nota_rechazada", 4)
        self.assertEqual(vigilancia.vigilar_rapido(self.con), [])
        self.assertIsNone(vigilancia.ajuste(self.con, "pausa_lectura"))

    def test_pocas_notas_no_alcanzan_para_juzgar(self):
        self.eventos("nota_rechazada", 5)
        self.assertEqual(vigilancia.vigilar_rapido(self.con), [])

    def test_los_ajustes_vencen(self):
        vigilancia.poner(self.con, "solo_azar", 1, 1, "prueba")
        self.assertTrue(vigilancia.ajuste(self.con, "solo_azar"))
        pasado = (datetime.now() - timedelta(minutes=1)).isoformat(timespec="seconds")
        self.con.execute("UPDATE ajustes SET hasta=?", (pasado,))
        self.assertIsNone(vigilancia.ajuste(self.con, "solo_azar"))

    def test_un_tema_que_acapara_baja_los_objetivos(self):
        for i in range(20):
            self.con.execute("INSERT INTO ciclos (fecha, modo, tema_id, resultado) VALUES (?, 'objetivo', ?, 'ok')",
                             (memoria.ahora(), 1 if i < 17 else 2))
        with mock.patch("angri.vigilancia.medir_reflexion", return_value={"versiones": 0, "parecido_minimo": None}):
            acciones = vigilancia.vigilar(self.con)
        self.assertIn("más lectura al azar por 3 días", acciones)
        self.assertEqual(vigilancia.ajuste(self.con, "prob_objetivo"), config.VIG_PROB_OBJETIVO_BAJA)
        salud = (config.DATOS / "salud.md").read_text(encoding="utf-8")
        self.assertIn("85%", salud)
        self.assertIn("prob_objetivo", salud)

    def test_reflexiones_iguales_se_pausan(self):
        with mock.patch("angri.vigilancia.medir_reflexion", return_value={"versiones": 3, "parecido_minimo": 0.99}):
            self.assertIn("pausa de reflexiones por 3 días", vigilancia.vigilar(self.con))

    def test_salud_sin_problemas(self):
        with mock.patch("angri.vigilancia.medir_reflexion", return_value={"versiones": 1, "parecido_minimo": None}):
            self.assertEqual(vigilancia.vigilar(self.con), [])
        self.assertIn("Ninguno: todo normal", (config.DATOS / "salud.md").read_text(encoding="utf-8"))

    def test_el_ciclo_respeta_solo_azar(self):
        from angri import actividades
        self.con.executescript(actividades.ESQUEMA)
        vigilancia.poner(self.con, "solo_azar", 1, 24, "prueba")
        self.assertEqual(actividades.posibles(self.con), ["azar"])

if __name__ == "__main__":
    unittest.main()
