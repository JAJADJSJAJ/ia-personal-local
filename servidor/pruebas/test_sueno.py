import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest import mock

import numpy as np

from angri import config, memoria, sueno

config.DATOS = Path(tempfile.mkdtemp())
config.BASE = config.DATOS / "memoria.db"
config.LOGS = config.DATOS / "logs"
config.DIARIO = config.DATOS / "diario"
config.DURMIENDO = config.DATOS / "DURMIENDO"
config.PAUSA = config.DATOS / "PAUSA"


def vec(*xs):
    v = np.array(xs, dtype=np.float32)
    return (v / np.linalg.norm(v)).tobytes()


class Sueno(unittest.TestCase):
    def setUp(self):
        if config.BASE.exists():
            config.BASE.unlink()
        self.con = memoria.abrir()
        self.con.executescript(sueno.ESQUEMA)

    def tearDown(self):
        self.con.close()

    def nota(self, nid, lectura, resumen, vector):
        self.con.execute("INSERT OR IGNORE INTO lecturas (id, fecha, titulo, url) VALUES (?, ?, ?, ?)",
                         (lectura, memoria.ahora(), f"Art {lectura}", f"u{lectura}"))
        self.con.execute("INSERT INTO notas (id, fecha, lectura_id, resumen, cita) VALUES (?, ?, ?, ?, 'c')",
                         (nid, memoria.ahora(), lectura, resumen))
        self.con.execute("INSERT INTO vectores (tipo, ref_id, vector) VALUES ('nota', ?, ?)", (nid, vector))

    def estado(self, nid):
        return self.con.execute("SELECT estado FROM notas WHERE id=?", (nid,)).fetchone()[0]

    def test_junta_repetidas_de_fuentes_distintas(self):
        self.nota(1, 1, "Bucarest es la capital de Rumania.", vec(1, 0, 0))
        self.nota(2, 2, "La capital de Rumania es Bucarest.", vec(1, 0.05, 0))
        self.nota(3, 3, "Rumania tiene un sistema multipartidista.", vec(0.6, 0.8, 0))
        self.assertEqual(sueno.juntar_repetidas(self.con), 1)
        self.assertEqual((self.estado(1), self.estado(2), self.estado(3)), ("confirmada", "vencida", "provisoria"))

    def test_misma_lectura_no_confirma(self):
        self.nota(1, 1, "Dato A.", vec(1, 0, 0))
        self.nota(2, 1, "Dato A otra vez.", vec(1, 0.01, 0))
        self.assertEqual(sueno.juntar_repetidas(self.con), 0)

    def test_repasar_vence_notas_meta(self):
        self.nota(1, 1, "El texto no menciona al personaje Phantom Girl.", vec(1, 0, 0))
        self.nota(2, 2, "Phantom Girl fue creada por Jerry Siegel.", vec(0, 1, 0))
        self.assertEqual(sueno.repasar(self.con), 1)
        self.assertEqual(self.estado(1), "vencida")

    def test_olvida_preguntas_viejas(self):
        vieja = (datetime.now() - timedelta(days=20)).isoformat(timespec="seconds")
        self.con.execute("INSERT INTO preguntas (fecha, texto) VALUES (?, '¿Vieja?')", (vieja,))
        self.con.execute("INSERT INTO preguntas (fecha, texto) VALUES (?, '¿Nueva?')", (memoria.ahora(),))
        self.assertEqual(sueno.olvidar_preguntas(self.con), 1)
        abiertas = [t for (t,) in self.con.execute("SELECT texto FROM preguntas WHERE estado='abierta'")]
        self.assertEqual(abiertas, ["¿Nueva?"])

    def test_resumen_inventado_no_se_guarda(self):
        self.nota(1, 1, "Bucarest es la capital de Rumania.", vec(1, 0, 0))
        with mock.patch("angri.modelo.llamar", return_value="Hoy fui al cine y comí pizza con amigos."):
            self.assertIsNone(sueno.resumen_del_dia(self.con))
        self.assertIsNone(sueno.ultimo_resumen(self.con))

    def test_resumen_fiel_se_guarda(self):
        self.nota(1, 1, "Bucarest es la capital de Rumania.", vec(1, 0, 0))
        fiel = "Hoy leí «Art 1» y anoté que Bucarest es la capital de Rumania."
        with mock.patch("angri.modelo.llamar", return_value=fiel):
            self.assertEqual(sueno.resumen_del_dia(self.con), fiel)
        self.assertEqual(sueno.ultimo_resumen(self.con)[1], fiel)

    def test_dormir_completo_y_copia(self):
        self.nota(1, 1, "Bucarest es la capital de Rumania.", vec(1, 0, 0))
        self.con.commit()
        with mock.patch("angri.modelo.llamar", side_effect=OSError("caído")), \
             mock.patch("angri.recordar.indexar_pendientes", return_value=0):
            informe = sueno.dormir()
        self.assertIn("copia", informe)
        self.assertIn("sin resumen", informe)
        self.assertFalse(config.DURMIENDO.exists())
        self.assertEqual(len(list((config.DATOS / "copias").glob("*.db"))), 1)


if __name__ == "__main__":
    unittest.main()
