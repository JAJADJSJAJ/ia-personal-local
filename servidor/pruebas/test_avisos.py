import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest import mock

from angri import avisos, bandeja, config, memoria

config.DATOS = Path(tempfile.mkdtemp())
config.BASE = config.DATOS / "memoria.db"

MEDIODIA = datetime.now().replace(hour=12, minute=0)


class Avisos(unittest.TestCase):
    def setUp(self):
        if config.BASE.exists():
            config.BASE.unlink()
        self.con = memoria.abrir()
        self.enviados = []
        self.p = mock.patch("angri.avisos.enviar", side_effect=lambda t, x: self.enviados.append((t, x)))
        self.p.start()

    def tearDown(self):
        self.p.stop()
        self.con.close()

    def test_no_avisa_de_noche(self):
        self.assertFalse(avisos.puede_avisar(self.con, MEDIODIA.replace(hour=2)))
        self.assertTrue(avisos.puede_avisar(self.con, MEDIODIA))

    def test_avisa_lo_importante_y_no_las_fallas(self):
        bandeja.dejar(self.con, "falla", "No respondía internet.", 2)
        bandeja.dejar(self.con, "dejado", "Dejé una pregunta.", 1)
        with mock.patch("angri.avisos.puede_avisar", return_value=True):
            self.assertIsNone(avisos.avisar(self.con))
            bandeja.dejar(self.con, "duda", "¿Vos sabés algo de Gabriel Roca?", 2)
            self.assertIn("Gabriel Roca", avisos.avisar(self.con))
        self.assertEqual(self.enviados[0][0], "Una duda")

    def test_tope_por_dia_y_separacion(self):
        for i in range(4):
            bandeja.dejar(self.con, "tema", f"Me interesa el tema {i}.", 2)
        avisos._columna(self.con)
        self.con.execute("UPDATE bandeja SET avisado=? WHERE id=1", (MEDIODIA.isoformat(timespec="seconds"),))
        self.assertFalse(avisos.puede_avisar(self.con, MEDIODIA + timedelta(hours=1)))   # muy seguido
        self.assertTrue(avisos.puede_avisar(self.con, MEDIODIA + timedelta(hours=4)))
        self.con.execute("UPDATE bandeja SET avisado=? WHERE id=2",
                         ((MEDIODIA + timedelta(hours=4)).isoformat(timespec="seconds"),))
        self.assertFalse(avisos.puede_avisar(self.con, MEDIODIA + timedelta(hours=8)))   # ya van 2 hoy

    def test_lo_ya_contado_en_la_charla_no_se_avisa(self):
        bandeja.dejar(self.con, "tema", "Me interesa Rumania.", 2)
        self.con.execute("UPDATE bandeja SET entregado=?", (memoria.ahora(),))
        self.assertIsNone(avisos.elegir(self.con))

    def test_canal_secreto_y_estable(self):
        c = avisos.canal()
        self.assertTrue(c.startswith("angri-") and len(c) > 25)
        self.assertEqual(c, avisos.canal())


if __name__ == "__main__":
    unittest.main()
