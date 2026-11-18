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


if __name__ == "__main__":
    unittest.main()
