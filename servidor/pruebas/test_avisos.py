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

    def elige(self, respuesta):
        """El modelo 'elige' la opción cuyo texto contiene `respuesta` (o 'ninguna')."""
        def llamar(tarea, pedido, sistema=None):
            for linea in pedido.splitlines():
                if respuesta.lower() in linea.lower() and linea[:1].isdigit():
                    return linea.split(".")[0] + "\n" + "¿Vos sabés algo de Gabriel Roca y por qué se mudó a Barcelona?"
            return "?"
        return mock.patch("angri.modelo.llamar", side_effect=llamar)

    def test_solo_ofrece_lo_importante_y_no_las_fallas(self):
        bandeja.dejar(self.con, "falla", "No respondía internet.", 2)
        bandeja.dejar(self.con, "dejado", "Dejé una pregunta.", 1)
        self.assertEqual(avisos.candidatas(self.con), [])
        with mock.patch("angri.avisos.puede_avisar", return_value=True):
            self.assertIsNone(avisos.avisar(self.con))
        self.assertEqual(self.enviados, [])

    def test_elige_una_y_la_redacta(self):
        bandeja.dejar(self.con, "duda", "Estuve buscando por qué Gabriel Roca se mudó a Barcelona. ¿Vos sabés algo?", 2)
        bandeja.dejar(self.con, "tema", "Me interesa un tema: Teatro japonés.", 2)
        with mock.patch("angri.avisos.puede_avisar", return_value=True), self.elige("Gabriel Roca"):
            self.assertIn("Gabriel Roca", avisos.avisar(self.con))
        self.assertEqual(self.enviados[0][0], "Una duda")

    def test_puede_elegir_ninguna(self):
        bandeja.dejar(self.con, "tema", "Me interesa un tema: Teatro japonés.", 2)
        with mock.patch("angri.avisos.puede_avisar", return_value=True), self.elige("Ninguna"):
            self.assertIsNone(avisos.avisar(self.con))
        self.assertEqual(self.enviados, [])
        # y después de elegir ninguna, espera unas horas antes de volver a pensarlo
        self.assertFalse(avisos.puede_avisar(self.con, datetime.now() + timedelta(minutes=30)))

    def test_mensaje_inventado_se_reemplaza(self):
        bandeja.dejar(self.con, "tema", "Me interesa un tema: Teatro japonés.", 2)
        def llamar(tarea, pedido, sistema=None):
            return "1\nFran, hoy fui a ver una obra de teatro con mis amigos y comimos sushi."
        with mock.patch("angri.avisos.puede_avisar", return_value=True), \
             mock.patch("angri.modelo.llamar", side_effect=llamar):
            self.assertEqual(avisos.avisar(self.con), "Me interesa un tema: Teatro japonés.")

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
        self.assertEqual(avisos.candidatas(self.con), [])

    def test_canal_secreto_y_estable(self):
        c = avisos.canal()
        self.assertTrue(c.startswith("angri-") and len(c) > 25)
        self.assertEqual(c, avisos.canal())


if __name__ == "__main__":
    unittest.main()
