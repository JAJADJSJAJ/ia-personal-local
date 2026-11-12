import tempfile
import unittest
from pathlib import Path
from unittest import mock

from angri import memoria


class EscrituraSegura(unittest.TestCase):
    def test_escribe_y_reemplaza(self):
        d = Path(tempfile.mkdtemp())
        memoria.escribir_seguro(d / "a.md", "uno")
        memoria.escribir_seguro(d / "a.md", "dos")
        self.assertEqual((d / "a.md").read_text(encoding="utf-8"), "dos")
        self.assertEqual([p.name for p in d.iterdir()], ["a.md"])   # no quedan temporales

    def test_corte_a_mitad_deja_la_version_vieja(self):
        d = Path(tempfile.mkdtemp())
        memoria.escribir_seguro(d / "a.md", "versión vieja entera")
        # Simula el corte: el reemplazo nunca llega a pasar
        with mock.patch("os.replace", side_effect=OSError("se cortó la luz")):
            with self.assertRaises(OSError):
                memoria.escribir_seguro(d / "a.md", "versión nueva")
        self.assertEqual((d / "a.md").read_text(encoding="utf-8"), "versión vieja entera")


if __name__ == "__main__":
    unittest.main()
