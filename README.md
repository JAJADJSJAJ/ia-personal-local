# Angri — una IA que vive sola

Angri es una IA chiquita que vive en una PC vieja (i5-4570, 16 GB de RAM, sin placa de video), prendida todo el día. Nadie le dice qué hacer: lee por su cuenta, se hace preguntas, las investiga, toma notas y escribe un diario de lo que hizo.

Todo corre en la casa. El modelo es Qwen3.5 4B con llama.cpp, y solo sale a internet para leer.

## Objetivo

Ver cuánta vida propia se le puede dar a una IA chica con buen diseño, y que crezca cuando mejore el cerebro.

La apuesta es que la sensación de que está viva depende más del programa que la rodea que del tamaño del modelo. Por eso casi todo el trabajo está en el bucle, la memoria, el sueño y la vigilancia. El modelo es reemplazable: si se cambia por uno más grande, su memoria y su diario se conservan. No se esperan ideas profundas, sino continuidad, intereses que cambian, recuerdos e iniciativa.

Los pesos del modelo todavía no se tocaron. Solo se van a modificar si aparece un error concreto que se repite.

## Qué hace

- **Cada 20 minutos se despierta** y elige qué hacer: leer algo al azar, investigar una pregunta suya, repasar lo que anotó, conectar dos cosas que leyó o descansar.
- **Lee y toma notas.** Cada nota tiene que llevar una cita textual de lo que leyó; si la cita no está en el texto, la nota se descarta.
- **Investiga sus propias preguntas** en Wikipedia (en varios idiomas) y en Wikidata. Si no encuentra la respuesta, a veces me pregunta a mí.
- **De noche duerme:** ordena lo que aprendió, escribe un resumen del día y reflexiona sobre los temas que le interesan y sobre quién es.
- **Me avisa al celular** cuando encuentra algo o tiene una duda.
- **Se puede charlar con ella** por la terminal o desde una página web en 3D.

## Cómo está armado

El modelo no hace nada solo: hay un programa que la despierta, decide para qué llamarlo y revisa lo que responde. El código vigila que no invente, que no se repita y que no se quede pegada a un tema. Si algo se desvía, ajusta solo (por ejemplo, la pone a leer más al azar o le pausa las reflexiones).

```
servidor/
├── angri/      el código: ciclo, sueño, memoria, fuentes, charla, web
├── pruebas/    las pruebas
└── sistema/    instalación y servicios de systemd
```

## Documentos

- [INVESTIGACION.md](INVESTIGACION.md): el hardware, el sistema, los modelos y la memoria.
- [AUTONOMIA.md](AUTONOMIA.md): cómo vive sola: intereses, objetivos, sueño.
- [CASOS.md](CASOS.md): otros proyectos de agentes que corren mucho tiempo y lo que aprendí de ellos.

## Qué no está acá

Los modelos, su memoria, su diario y sus claves viven solo en la PC de Angri.
