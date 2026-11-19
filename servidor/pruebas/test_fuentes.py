"""Fuentes fuera de Wikipedia y cambios de quién soy (18/11/2026)."""
import unittest

from angri import fuentes, reflexion, verificar

class TestWeb(unittest.TestCase):
    def test_texto_sin_menus_ni_scripts(self):
        html = ("<html><nav>Inicio Contacto Menú de navegación con muchas palabras que no sirven para nada aquí</nav>"
                "<script>var x = 'código que no hay que leer jamás porque es javascript puro y duro';</script>"
                "<p>Manuel de Salas fundó en 1797 la Academia de San Luis, dedicada a la enseñanza de las ciencias.</p>"
                "<footer>Todos los derechos reservados por la empresa que hizo este sitio web hace años</footer></html>")
        t = fuentes.texto_de_html(html)
        self.assertIn("Academia de San Luis", t)
        self.assertNotIn("javascript", t)
        self.assertNotIn("Menú", t)
        self.assertNotIn("derechos", t)


class TestAnclajeNombres(unittest.TestCase):
    FUENTE = "Imelda Lambertini was born in Bologna in 1322 and died in 1333 at the Dominican monastery."

    def test_traduccion_fiel(self):
        r = "Imelda Lambertini nació en Bologna en 1322 y murió en 1333 en un monasterio."
        self.assertGreaterEqual(verificar.anclaje_nombres(r, self.FUENTE), 0.5)

    def test_inventa_nombres_y_fechas(self):
        r = "Imelda vivió en Roma con Francisco hasta 1450, según Benedicto."
        self.assertLess(verificar.anclaje_nombres(r, self.FUENTE), 0.5)


class TestFirmaQuienSoy(unittest.TestCase):
    def test_solo_cambian_los_numeros(self):
        a = ["Llevo 5 días leyendo.", "Leí 100 artículos y guardé 90 notas."]
        b = ["Llevo 6 días leyendo.", "Leí 120 artículos y guardé 104 notas."]
        self.assertEqual(reflexion.firma(a), reflexion.firma(b))

    def test_algo_nuevo_cambia_la_firma(self):
        a = ["Leí 100 artículos."]
        b = ["Leí 100 artículos.", "Preguntas que me hice hoy: ¿Quién fundó Bologna?"]
        self.assertNotEqual(reflexion.firma(a), reflexion.firma(b))


class TestPausaFuentes(unittest.TestCase):
    def test_respeta_retry_after(self):
        import tempfile
        from pathlib import Path
        from unittest import mock
        from angri import config
        with tempfile.TemporaryDirectory() as d, mock.patch.object(config, "DATOS", Path(d)):
            self.assertFalse(fuentes.en_pausa("wikidata"))
            fuentes.pausar("wikidata", "120")
            self.assertTrue(fuentes.en_pausa("wikidata"))
            self.assertFalse(fuentes.en_pausa("en"))


class TestJuez(unittest.TestCase):
    def test_gana_la_mayoria(self):
        from unittest import mock
        from angri import objetivos
        with mock.patch("angri.objetivos.modelo.llamar", side_effect=["NO", "SI", "**SI**"]):
            self.assertEqual(objetivos.juzgar("p", "n"), "SI")
        with mock.patch("angri.objetivos.modelo.llamar", side_effect=["NO", "PARCIAL", "NO"]):
            self.assertEqual(objetivos.juzgar("p", "n"), "NO")


if __name__ == "__main__":
    unittest.main()


class TestNotaContado(unittest.TestCase):
    def test_marca_lo_que_conto_fran(self):
        from angri import charla
        contadas = [("¿Qué le pasó a Imelda Lambertini?", "Murió en 1333.")]
        self.assertIn("te lo contó Fran", charla.nota_contado(contadas, "¿Leíste sobre imelda?"))
        self.assertEqual(charla.nota_contado(contadas, "¿Qué pasó hoy?"), "")
