import tempfile
import unittest
from pathlib import Path
from unittest import mock

import numpy as np

from angri import config, memoria, reflexion

config.DATOS = Path(tempfile.mkdtemp())
config.BASE = config.DATOS / "memoria.db"

NOTAS = [
    "En 1947 los partidos de la coalición se unieron dentro del Partido Comunista Rumano.",
    "El 3 de febrero de 1957 el Frente Democrático Popular fue el único partido en las elecciones de Rumania.",
    "Rumania tiene actualmente un sistema multipartidista con dos partidos dominantes.",
]


class Reflexion(unittest.TestCase):
    def setUp(self):
        if config.BASE.exists():
            config.BASE.unlink()
        self.con = memoria.abrir()
        self.con.executescript(reflexion.ESQUEMA)
        centro = np.array([1, 0, 0], dtype=np.float32)
        self.con.execute("INSERT INTO temas (id, nombre, centro, peso, n, creado, actualizado) VALUES "
                         "(1, 'Historia política de Rumania', ?, 1.3, 3, ?, ?)", (centro.tobytes(), memoria.ahora(), memoria.ahora()))
        for i, r in enumerate(NOTAS, 1):
            self.con.execute("INSERT INTO lecturas (id, fecha, titulo, url) VALUES (?, ?, ?, ?)", (i, memoria.ahora(), f"Art {i}", f"u{i}"))
            self.con.execute("INSERT INTO notas (id, fecha, lectura_id, resumen, cita) VALUES (?, ?, ?, ?, 'c')", (i, memoria.ahora(), i, r))
            self.con.execute("INSERT INTO nota_tema (nota_id, tema_id) VALUES (?, 1)", (i,))
        self.con.execute("INSERT INTO preguntas (id, fecha, texto) VALUES (1, ?, '¿Por qué Rumania eligió un único partido?')",
                         (memoria.ahora(),))
        self.con.execute("INSERT INTO vectores (tipo, ref_id, vector) VALUES ('pregunta', 1, ?)", (centro.tobytes(),))
        self.con.commit()

    def tearDown(self):
        self.con.close()

    def test_tema_tira_lo_inventado_y_pone_preguntas(self):
        texto = ("En 1947 los partidos de la coalición se unieron dentro del Partido Comunista Rumano. "
                 "Después, en 1957, el Frente Democrático Popular fue el único partido en las elecciones. "
                 "Los rumanos siempre fueron un pueblo muy valiente y amante de la música folclórica.")
        with mock.patch("angri.modelo.llamar", return_value=texto):
            informe = reflexion.reflexionar_tema(self.con)
        self.assertIn("2 oraciones respaldadas, 1 descartadas", informe)
        archivo = reflexion.leer("temas/historia-politica-de-rumania.md")
        self.assertNotIn("folclórica", archivo)
        self.assertIn("¿Por qué Rumania eligió un único partido?", archivo)

    def test_numeros_y_meta(self):
        fuente = "Gobernó desde 1948 hasta 1989 el Partido Comunista Rumano."
        ok, malas = reflexion.filtrar([
            "El Partido Comunista Rumano gobernó desde 1948 hasta 1989.",
            "El Partido Comunista Rumano gobernó durante veinte años desde 1948.",
            "El Partido Comunista Rumano gobernó desde 1950 hasta 1989.",
            "El texto menciona que el Partido Comunista Rumano gobernó desde 1948.",
        ], fuente)
        self.assertEqual(ok, ["El Partido Comunista Rumano gobernó desde 1948 hasta 1989."])
        self.assertEqual(malas, 3)

    def test_no_repite_tema_sin_notas_nuevas(self):
        with mock.patch("angri.modelo.llamar", return_value=NOTAS[0]):
            reflexion.reflexionar_tema(self.con)
            self.assertIsNone(reflexion.reflexionar_tema(self.con))

    def test_guarda_historial(self):
        with mock.patch("angri.modelo.llamar", return_value=NOTAS[0]):
            reflexion.reflexionar_tema(self.con)
        self.con.execute("UPDATE temas SET n=4 WHERE id=1")
        with mock.patch("angri.modelo.llamar", return_value=NOTAS[1]):
            reflexion.reflexionar_tema(self.con)
        self.assertTrue(list((config.DATOS / "yo" / "historial").glob("historia-politica-de-rumania-*.md")))

    def test_genero_lo_elige_una_vez(self):
        with mock.patch("angri.modelo.llamar", return_value="neutro\nPorque no tengo cuerpo."):
            self.assertEqual(reflexion.decidir_genero(self.con), "neutro")
        with mock.patch("angri.modelo.llamar", return_value="femenino\nOtra cosa."):
            self.assertIsNone(reflexion.decidir_genero(self.con))
        self.assertEqual(reflexion.genero(self.con)[0], "neutro")
        self.assertIn("sin marcar género", reflexion.como_hablar(self.con))

    def test_genero_ambiguo_no_se_guarda(self):
        with mock.patch("angri.modelo.llamar", return_value="Femenino o masculino, no sé."):
            self.assertIsNone(reflexion.decidir_genero(self.con))
        self.assertIsNone(reflexion.genero(self.con))

    def test_quien_soy_con_datos(self):
        with mock.patch("angri.modelo.llamar", return_value="Soy un dragón que vive en la luna. Me gusta el queso."):
            reflexion.reflexionar_quien_soy(self.con)
        texto = reflexion.leer("quien-soy.md")
        self.assertNotIn("dragón", texto)
        self.assertIn("Historia política de Rumania", texto)


if __name__ == "__main__":
    unittest.main()
