import json
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

import numpy as np

from angri import actividades, config, fuentes, memoria, vigilancia

config.DATOS = Path(tempfile.mkdtemp())
config.BASE = config.DATOS / "memoria.db"
config.DIARIO = config.DATOS / "diario"


def vec(*x):
    v = np.array(x, dtype=np.float32)
    return (v / np.linalg.norm(v)).tobytes()


class Actividades(unittest.TestCase):
    def setUp(self):
        if config.BASE.exists():
            config.BASE.unlink()
        (config.DATOS / "wikipedia.json").unlink(missing_ok=True)
        self.con = memoria.abrir()
        self.con.executescript(actividades.ESQUEMA)

    def tearDown(self):
        self.con.close()

    def notas(self, n):
        for i in range(1, n + 1):
            self.con.execute("INSERT INTO lecturas (id, fecha, titulo, url) VALUES (?, ?, ?, ?)",
                             (i, memoria.ahora(), f"Art {i}", f"u{i}"))
            self.con.execute("INSERT INTO notas (id, fecha, lectura_id, resumen, cita) VALUES (?, ?, ?, ?, 'c')",
                             (i, memoria.ahora(), i, f"Dato número {i} sobre Rumania y su política."))
            # notas separadas ~51° entre vecinas: coseno 0,62, dentro del rango "ni iguales ni sin relación"
            self.con.execute("INSERT INTO vectores (tipo, ref_id, vector) VALUES ('nota', ?, ?)",
                             (i, vec(np.cos(i * 0.9), np.sin(i * 0.9), 0)))

    def ciclo(self, modo):
        self.con.execute("INSERT INTO ciclos (fecha, modo, resultado) VALUES (?, ?, 'ok')", (memoria.ahora(), modo))

    def test_recien_nacida_solo_lee(self):
        self.notas(2)
        self.assertEqual(actividades.posibles(self.con), ["azar"])

    def test_con_notas_tiene_opciones(self):
        self.notas(6)
        p = actividades.posibles(self.con)
        for a in ("azar", "descansar", "repasar", "conectar"):
            self.assertIn(a, p)

    def test_no_se_encierra_en_una(self):
        self.notas(6)
        for _ in range(3):
            self.ciclo("repasar")
        self.assertNotIn("repasar", actividades.posibles(self.con))

    def test_no_descansa_dos_veces_seguidas(self):
        self.notas(6)
        self.ciclo("descansar")
        self.assertNotIn("descansar", actividades.posibles(self.con))

    def test_sin_cupo_de_wikipedia_no_usa_internet(self):
        self.notas(6)
        (config.DATOS / "wikipedia.json").write_text(json.dumps(
            {"hora": time.strftime("%Y-%m-%dT%H"), "n": config.WIKI_PEDIDOS_POR_HORA, "ultimo": 0}))
        p = actividades.posibles(self.con)
        self.assertNotIn("azar", p)
        self.assertIn("repasar", p)

    def test_vigilancia_solo_azar(self):
        self.notas(6)
        vigilancia.poner(self.con, "solo_azar", 1, 24, "prueba")
        self.assertEqual(actividades.posibles(self.con), ["azar"])

    def test_elige_lo_que_dice_el_modelo(self):
        self.notas(6)
        def llamar(tarea, pedido, sistema=None):
            for linea in pedido.splitlines():
                if "Releer" in linea:
                    return linea.split(".")[0]
        with mock.patch("angri.modelo.llamar", side_effect=llamar):
            self.assertEqual(actividades.elegir(self.con), "repasar")

    def test_respuesta_confusa_sortea(self):
        self.notas(6)
        with mock.patch("angri.modelo.llamar", return_value="mmm, no sé"):
            self.assertIn(actividades.elegir(self.con), actividades.DESCRIPCION)

    def test_conectar_inventado_no_se_guarda(self):
        self.notas(3)
        with mock.patch("angri.modelo.llamar", return_value="Las dos hablan de dinosaurios voladores de Marte."):
            r, _ = actividades.conectar(self.con)
        self.assertIn("no tenían nada que ver", r)
        self.assertEqual(self.con.execute("SELECT valida FROM conexiones").fetchone()[0], 0)

    def test_conectar_respaldado_se_cuenta(self):
        self.notas(3)
        texto = "Las dos notas cuentan datos sobre Rumania y su política."
        with mock.patch("angri.modelo.llamar", return_value="Los dos datos tratan sobre Rumania y su política."):
            r, _ = actividades.conectar(self.con)
        self.assertIn("conecté", r)


class Contador(unittest.TestCase):
    def test_limite_por_hora(self):
        (config.DATOS / "wikipedia.json").write_text(json.dumps(
            {"hora": time.strftime("%Y-%m-%dT%H"), "n": config.WIKI_PEDIDOS_POR_HORA, "ultimo": 0}))
        with self.assertRaises(fuentes.Limite):
            fuentes._respetar_ritmo()

    def test_cuenta_y_espera(self):
        (config.DATOS / "wikipedia.json").unlink(missing_ok=True)
        with mock.patch("time.sleep") as dormir:
            fuentes._respetar_ritmo()
            fuentes._respetar_ritmo()
        self.assertTrue(dormir.called)   # el segundo pedido esperó el intervalo
        self.assertEqual(json.loads((config.DATOS / "wikipedia.json").read_text())["n"], 2)


if __name__ == "__main__":
    unittest.main()
