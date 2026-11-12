"""Pruebas de la campana de novedad y del olvido de temas. Correr desde servidor/: python -m unittest pruebas.test_temas"""
import unittest
from datetime import datetime, timedelta

from angri import config, temas


class Campana(unittest.TestCase):
    def test_maximo_en_el_ideal(self):
        self.assertAlmostEqual(temas.campana(config.NOVEDAD_IDEAL), 1.0)

    def test_lo_repetido_casi_no_suma(self):
        self.assertLess(temas.campana(0.0), 0.1)

    def test_lo_que_no_tiene_relacion_casi_no_suma(self):
        # El "televisor con ruido": lo más distinto no es lo más interesante
        self.assertLess(temas.campana(1.0), 0.1)

    def test_lo_intermedio_gana_a_los_extremos(self):
        self.assertGreater(temas.campana(0.5), temas.campana(0.1))
        self.assertGreater(temas.campana(0.5), temas.campana(0.95))


class Olvido(unittest.TestCase):
    def test_sin_tiempo_no_olvida(self):
        self.assertAlmostEqual(temas.peso_actual(2.0, datetime.now().isoformat()), 2.0, places=3)

    def test_baja_con_los_dias(self):
        hace_10 = (datetime.now() - timedelta(days=10)).isoformat()
        self.assertAlmostEqual(temas.peso_actual(2.0, hace_10), 2.0 * config.TEMA_OLVIDO_POR_DIA ** 10, places=3)


if __name__ == "__main__":
    unittest.main()
