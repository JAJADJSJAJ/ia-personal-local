import tempfile
import unittest
from pathlib import Path
from unittest import mock

from angri import bandeja, config, memoria

config.DATOS = Path(tempfile.mkdtemp())
config.BASE = config.DATOS / "memoria.db"


class Bandeja(unittest.TestCase):
    def setUp(self):
        if config.BASE.exists():
            config.BASE.unlink()
        self.con = memoria.abrir()

    def tearDown(self):
        self.con.close()

    def test_sin_novedades_no_saluda(self):
        self.assertIsNone(bandeja.saludo(self.con))

    def test_no_duplica_y_ordena_por_importancia(self):
        bandeja.dejar(self.con, "dejado", "Dejé una pregunta.", 1)
        bandeja.dejar(self.con, "dejado", "Dejé una pregunta.", 1)
        bandeja.dejar(self.con, "respuesta", "Encontré respuesta a algo.", 3)
        p = bandeja.pendientes(self.con)
        self.assertEqual(len(p), 2)
        self.assertEqual(p[0][1], "respuesta")

    def test_saludo_inventado_se_reemplaza_por_codigo(self):
        bandeja.dejar(self.con, "tema", "Me di cuenta de que me interesa un tema: Historia política de Rumania.", 2)
        with mock.patch("angri.modelo.llamar", return_value="¡Hola! Hoy aprendí cocina tailandesa y astronomía."):
            texto = bandeja.saludo(self.con)
        self.assertIn("Rumania", texto)
        self.assertNotIn("tailandesa", texto)
        self.assertEqual(bandeja.pendientes(self.con), [])  # quedó entregado

    def test_persona_cambiada_se_reemplaza(self):
        bandeja.dejar(self.con, "tema", "Me di cuenta de que me interesa un tema: Historia política de Rumania.", 2)
        mal = "Fran, descubriste un interés por la historia política de Rumania."
        with mock.patch("angri.modelo.llamar", return_value=mal):
            self.assertNotIn("descubriste", bandeja.saludo(self.con))

    def test_saludo_fiel_se_usa(self):
        bandeja.dejar(self.con, "tema", "Me di cuenta de que me interesa un tema: Historia política de Rumania.", 2)
        fiel = "Hola, Fran. Me di cuenta de que me interesa la historia política de Rumania."
        with mock.patch("angri.modelo.llamar", return_value=fiel):
            self.assertEqual(bandeja.saludo(self.con), fiel)

    def test_cuenta_tres_y_guarda_el_resto(self):
        for i in range(5):
            bandeja.dejar(self.con, "dejado", f"Dejé la pregunta número {i}.", 1)
        with mock.patch("angri.modelo.llamar", side_effect=OSError("modelo caído")):
            texto = bandeja.saludo(self.con)
        self.assertIn("2 cosas más", texto)
        self.assertEqual(len(bandeja.pendientes(self.con)), 2)
        self.assertIn("número 0", bandeja.resto(self.con))


if __name__ == "__main__":
    unittest.main()
