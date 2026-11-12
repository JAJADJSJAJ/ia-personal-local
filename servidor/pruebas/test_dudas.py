import tempfile
import unittest
from pathlib import Path
from unittest import mock

import numpy as np

from angri import bandeja, config, dudas, memoria

config.DATOS = Path(tempfile.mkdtemp())
config.BASE = config.DATOS / "memoria.db"
config.DIARIO = config.DATOS / "diario"

DUDA = "Estuve buscando «¿Por qué Gabriel Roca se mudó a Barcelona?» y no lo encontré en Wikipedia. ¿Vos sabés algo?"


def vec(x):
    v = np.array(x, dtype=np.float32)
    return v / np.linalg.norm(v)


class Dudas(unittest.TestCase):
    def setUp(self):
        if config.BASE.exists():
            config.BASE.unlink()
        self.con = memoria.abrir()
        bandeja.dejar(self.con, "duda", DUDA, 2)
        self.con.commit()

    def tearDown(self):
        self.con.close()

    def con_similitud(self, sim):
        q = vec([1, 0])
        m = vec([sim, (1 - sim ** 2) ** 0.5])
        return mock.patch.multiple("angri.vectores", consulta=mock.Mock(return_value=m),
                                   documentos=mock.Mock(return_value=np.stack([q])))

    def test_respuesta_en_contexto_se_vincula(self):
        with self.con_similitud(0.26):
            p = dudas.vincular(self.con, "creo que fue por trabajo, lo contrataron allá", ultimo_de_angri=DUDA)
        self.assertEqual(p, "¿Por qué Gabriel Roca se mudó a Barcelona?")
        self.assertEqual(dudas.pendientes(self.con), [])
        self.assertEqual(dudas.respondidas(self.con)[0][1], "creo que fue por trabajo, lo contrataron allá")

    def test_mismo_parecido_fuera_de_contexto_no_alcanza(self):
        with self.con_similitud(0.26):
            self.assertIsNone(dudas.vincular(self.con, "creo que fue por trabajo", ultimo_de_angri="Hola"))

    def test_mensaje_sin_relacion_no_se_vincula(self):
        with self.con_similitud(0.10):
            self.assertIsNone(dudas.vincular(self.con, "hoy comí milanesas", ultimo_de_angri=DUDA))
        self.assertEqual(len(dudas.pendientes(self.con)), 1)

    def test_parecido_alto_sin_contexto_se_vincula(self):
        with self.con_similitud(0.45):
            self.assertIsNotNone(dudas.vincular(self.con, "se mudó a Barcelona por trabajo en el puerto"))


if __name__ == "__main__":
    unittest.main()
