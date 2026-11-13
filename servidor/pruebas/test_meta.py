import unittest

from angri import verificar as v


class PreguntasYRespuestasMeta(unittest.TestCase):
    def test_preguntas_sobre_lo_leido_se_descartan(self):
        for p in ["¿Por qué es imposible determinar si Ogallala fue habitado con base únicamente en esta información?",
                  "¿Qué otro detalle se podría haber incluido en esa nota?",
                  "¿Qué dice el artículo sobre la guerra?",
                  "¿Basándose solo en mis notas, quién ganó?"]:
            self.assertIsNone(v.pregunta_valida(p), p)

    def test_preguntas_del_mundo_pasan(self):
        for p in ["¿Qué relación familiar existe entre Benedikt Ásgeirsson y los países donde fue embajador?",
                  "¿Qué información genética comparten los faliscos y los etruscos?",
                  "¿Por qué Rumania eligió un único partido en lugar de elegir a varios?"]:
            self.assertEqual(v.pregunta_valida(p), p)

    def test_respuesta_meta(self):
        self.assertTrue(v.habla_de_la_fuente("Las notas proporcionadas no mencionan nada sobre Phantom Girl."))
        self.assertTrue(v.habla_de_la_fuente("El texto indica que Rumania es multipartidista."))
        self.assertFalse(v.habla_de_la_fuente("En 1947 los comunistas forzaron la unidad de los partidos."))

    def test_saca_solo_la_oracion_meta(self):
        r = ("Rumania eligió un único partido porque en 1947 los comunistas forzaron la unidad. "
             "Las notas indican claramente que de 1948 a 1989 fue unipartidista.")
        self.assertEqual(v.sin_oraciones_de_la_fuente(r),
                         "Rumania eligió un único partido porque en 1947 los comunistas forzaron la unidad.")
        self.assertEqual(v.sin_oraciones_de_la_fuente("Las notas proporcionadas no mencionan nada."), "")


if __name__ == "__main__":
    unittest.main()
