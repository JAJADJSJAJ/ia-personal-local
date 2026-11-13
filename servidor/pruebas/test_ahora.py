import json
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

from angri import ahora, config

config.DATOS = Path(tempfile.mkdtemp())
config.EN_CICLO = config.DATOS / "EN_CICLO"
config.CHARLA_WEB = config.DATOS / "CHARLA_WEB"
config.DURMIENDO = config.DATOS / "DURMIENDO"


class Charla(unittest.TestCase):
    def setUp(self):
        for f in (config.EN_CICLO, config.CHARLA_WEB, config.DURMIENDO):
            f.unlink(missing_ok=True)

    def test_iniciar_y_terminar(self):
        ahora.iniciar_charla("abc")
        self.assertEqual(ahora.charla_activa()["sesion"], "abc")
        ahora.terminar_charla()
        self.assertIsNone(ahora.charla_activa())

    def test_se_cierra_sola_sin_mensajes(self):
        ahora.iniciar_charla("abc")
        c = json.loads(config.CHARLA_WEB.read_text())
        c["mensaje"] -= config.CHARLA_WEB_INACTIVIDAD_MIN * 60 + 1
        config.CHARLA_WEB.write_text(json.dumps(c))
        self.assertIsNone(ahora.charla_activa())
        self.assertFalse(config.CHARLA_WEB.exists())

    def test_se_cierra_sola_si_la_pagina_desaparece(self):
        ahora.iniciar_charla("abc")
        c = json.loads(config.CHARLA_WEB.read_text())
        c["latido"] -= config.CHARLA_WEB_LATIDO_SEG + 1
        config.CHARLA_WEB.write_text(json.dumps(c))
        self.assertIsNone(ahora.charla_activa())

    def test_latido_de_otra_sesion_no_vale(self):
        ahora.iniciar_charla("abc")
        self.assertIsNone(ahora.latido("otra"))
        self.assertIsNotNone(ahora.latido("abc", mensaje=True))

    def test_el_mensaje_reinicia_el_contador(self):
        ahora.iniciar_charla("abc")
        c = json.loads(config.CHARLA_WEB.read_text())
        c["mensaje"] -= 300
        config.CHARLA_WEB.write_text(json.dumps(c))
        self.assertLess(ahora.segundos_restantes(ahora.charla_activa()), 400)
        ahora.latido("abc", mensaje=True)
        self.assertGreater(ahora.segundos_restantes(ahora.charla_activa()), 590)

    def test_solo_corta_procesos_de_angri(self):
        config.EN_CICLO.write_text(json.dumps({"pid": 12345, "actividad": "azar", "desde": time.time()}))
        with mock.patch("angri.ahora.proceso_vivo", return_value=False), mock.patch("os.kill") as matar:
            self.assertIsNone(ahora.iniciar_charla("abc"))
        matar.assert_not_called()   # el pid no es de un ciclo de Angri: no se toca

    def test_corta_el_ciclo_en_curso(self):
        config.EN_CICLO.write_text(json.dumps({"pid": 12345, "actividad": "azar", "desde": time.time()}))
        vivo = iter([True, False])
        with mock.patch("angri.ahora.proceso_vivo", side_effect=lambda pid, mod: next(vivo, False)), \
             mock.patch("os.kill") as matar:
            self.assertEqual(ahora.iniciar_charla("abc"), "azar")
        matar.assert_called_once()
        self.assertFalse(config.EN_CICLO.exists())


if __name__ == "__main__":
    unittest.main()
