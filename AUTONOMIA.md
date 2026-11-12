# IA personal local — Vida propia, aprendizaje y evolución

Fecha: 10 de noviembre de 2026. Actualizado el 11 de noviembre con los hallazgos de `CASOS.md`. Complementa a `INVESTIGACION.md` (hardware, sistema, modelos, memoria básica).

Dos decisiones de Fran que atraviesan todo el documento: **nace sin intereses de base** (se interesa sola) y **nadie la revisa a diario** (corre 24/7 a su ritmo, y el código vigila por ella).
Este documento cubre lo que define al proyecto: **que la IA haga cosas sola**. Volver y encontrar que buscó algo, que aprendió algo, que se interesó por algo. Nunca un cursor esperando un prompt.

Restricciones fijas: todo corre local en el i5-4570 (16 GB, sin placa de video), con internet solo para buscar y leer.

Cada sección separa lo **confirmado en fuentes** de lo que es **diseño propio o estimación a medir**.

---

## 1. La idea central

**Un modelo de lenguaje no hace nada solo.** Solo calcula cuando un programa lo llama. Entre llamada y llamada no piensa, no espera, no existe.

Entonces la "vida" no está en el modelo: está en un **programa que nunca termina** y que decide, sin que nadie escriba nada, cuándo despertar al modelo y para qué. El modelo es el cerebro; ese programa es el corazón.

Consecuencia práctica: la sensación de que "está viva" depende mucho más del diseño de ese bucle que del tamaño del modelo. Un modelo de 0.8B con buen bucle se siente más vivo que uno de 70B que espera un prompt.

Las cinco piezas que hacen falta:

| Pieza | Qué aporta | Sección |
|---|---|---|
| Latido | Que exista actividad sin que nadie escriba | 2 |
| Impulsos e intereses | Que elija qué hacer y que eso cambie con el tiempo | 3 |
| Memoria que reflexiona | Que lo vivido se convierta en opiniones y conocimiento | 4 |
| Sueño | Que ordene, consolide y se reentrene de noche | 5 y 6 |
| Diario | Que al volver se vea qué hizo | 8 |

---

## 2. El latido

**Confirmado: cómo lo hacen los proyectos que ya existen**

- **OpenClaw**: un temporizador (30 minutos por defecto) dispara un prompt fijo que le dice al agente que lea su archivo `heartbeat.md` y haga lo que dice ahí. Lo importante: **el propio agente puede escribir en ese archivo**, o sea que se deja tareas a sí mismo para el próximo latido.
- **Heart** (artículo técnico): separa el latido del cerebro. El latido es un bucle de puro código, sin modelo. Solo despierta al modelo cuando hay algo para hacer, y tiene una "cámara ociosa" que habilita exploración autónoma tras confirmar que el usuario no está. Si el modelo no encuentra nada que valga la pena responde `[IDLE]` y ese despertar no deja rastro. Reportan unas 31 invocaciones al modelo por día por agente.
- **Pulse**: un "motor de impulsos" con seis categorías (metas, curiosidad, emociones, aprendizaje, social, sistema). El agente se despierta solo cuando un impulso supera un umbral. Trae un sensor de RSS que alimenta la curiosidad.
- **Agente con Qwen de 0.5B**: funciona si el modelo planea **un paso por vez** y el sistema hace el resto. La conclusión del autor: modelo débil + sistema fuerte = agente sorprendentemente capaz.

**Diseño para este proyecto**

Un servicio de systemd (`vida.service`) que corre siempre y se reinicia solo si se cae. Cada tic (por ejemplo cada 5 minutos) ejecuta código, sin modelo:

```
cada tic:
  1. ¿Fran está hablando o habló hace poco?      → modo CHARLA, no molestar
  2. ¿Es horario de sueño (ej. 03:00-07:00)?     → modo SUEÑO (sección 5)
  3. Si no: modo OCIO
       - actualizar impulsos (suben con el tiempo)
       - elegir la actividad con impulso más alto
       - ejecutarla (acá sí se llama al modelo)
       - anotar en el diario qué hizo
```

Reglas que evitan que se "muera" o se trabe:
- **Siempre hay algo para hacer.** Si ningún impulso supera el umbral, hay una actividad por defecto (leer el siguiente pendiente de la cola, o exponerse a algo al azar).
- **Una sola tarea por tic, con tope de tiempo y de tokens.** Si se pasa, se corta y se anota.
- **El modelo nunca decide si seguir vivo.** Eso es del código.
- **La charla tiene prioridad.** Si Fran escribe en medio de una exploración, se pausa y se retoma después.
- **Contexto limpio en cada tic.** Nada se arrastra de un tic al siguiente salvo lo que el código elige pegar. Un ciclo no puede heredarse.
- **Sin instrucciones abiertas.** Ningún prompt del bucle dice "hacé lo que quieras" o "sé proactiva": el código elige la actividad y el modelo la ejecuta. (Un latido de OpenClaw con el archivo vacío se desbocó justamente por eso; ver `CASOS.md` 2.5.)
- **El estado vive en la base.** Qué ya buscó, qué ya leyó y qué tiene pendiente está en tablas, no en la memoria del modelo.

El tic de 5 minutos es solo código. Cuántos tics terminan llamando al modelo depende de los impulsos y de los presupuestos.

---

## 3. Impulsos e intereses

Acá está lo de "que se interese por alguna cosa".

### 3.1 Impulsos

Números entre 0 y 1 guardados en la base. Suben solos con el tiempo y bajan al satisfacerlos.

| Impulso | Sube cuando | Se satisface con |
|---|---|---|
| Curiosidad | Pasa tiempo sin aprender nada nuevo; aparece un tema desconocido | Buscar y leer sobre un interés |
| Reflexión | Se acumulan recuerdos importantes sin procesar | Escribir una reflexión |
| Orden | Hay memoria sin consolidar o duplicada | Consolidar (va al sueño) |
| Social | Pasa mucho tiempo sin hablar con Fran | Dejarle un mensaje con algo que encontró |
| Proyecto | Tiene un proyecto propio abierto | Avanzarlo un paso |

### 3.2 Intereses

Una tabla de temas, cada uno con un **peso** que cambia. **No hay semilla:** la tabla arranca vacía.

**De dónde salen**

Lo que es al azar es lo que se le cruza; lo que hace con eso lo genera ella.

- **Exposición al azar (código):** un artículo cualquiera de Wikipedia, una portada de noticias, un enlace dentro de lo último que leyó.
- **De las charlas:** lo que Fran menciona también es exposición.
- **Preguntas propias (modelo):** cada lectura termina con "¿qué pregunta nueva te deja esto?". Esas preguntas van a una cola.
- **Un tema aparece solo:** cuando varias preguntas caen cerca entre sí (por embeddings), el código registra un tema. Nadie lo declara.

Al principio casi todo es exposición al azar. A medida que se forman temas, pasa más tiempo siguiendo sus propias preguntas. El azar nunca baja a cero.

Aclaración: "sin preferencias" del todo no existe. El modelo trae inclinaciones de su entrenamiento; eso es su temperamento. Lo que se garantiza es que nadie le elige los temas.

**Cómo cambia el peso (diseño propio)**

Se usa una señal medible en vez de pedirle al modelo que opine si algo es interesante:

- **Filtro de calidad primero**: se descarta por código lo que no es texto útil (muy corto, otro idioma, lleno de enlaces o símbolos, imposible de resumir). Sin esto, lo más "novedoso" es una página rota o spam.
- **Novedad en campana**: se calcula el embedding de lo leído y se compara con lo guardado. El puntaje es máximo a distancia intermedia: parecido a lo conocido pero algo distinto. Baja hacia los dos extremos (más de lo mismo, o sin relación con nada). Los límites se ajustan con datos de las primeras semanas.
- **Progreso**: un tema sube si la lectura respondió una pregunta de la cola. Muchas lecturas sin ninguna pregunta respondida lo bajan.
- **Decaimiento**: todos los pesos bajan un poco cada día. Lo que no se alimenta se olvida.
- **Refuerzo social**: si Fran pregunta por el tema o reacciona bien, sube.
- **Saturación**: tras varias lecturas seguidas del mismo tema, se fuerza cambiar.

Es la versión simple de lo que la investigación llama motivación intrínseca: curiosidad por lo que todavía se puede aprender, no por lo que es puro ruido (`CASOS.md` sección 5).

**Por qué no dejar que el modelo elija todo**
- Confirmado: un estudio de 2026 muestra que los modelos de lenguaje eligen metas de forma distinta a los humanos en tareas abiertas.
- Experiencia general con modelos chicos: librados a sí mismos repiten los mismos dos o tres temas. Por eso la variedad la garantiza el código (novedad, saturación, azar ponderado) y el modelo pone el contenido.

### 3.3 Un ciclo de curiosidad, paso a paso

1. El código elige un objetivo abierto o un interés (sorteo ponderado). Si no hay ninguno, elige una exposición al azar.
2. Modelo: "Sobre *X* ya sabés esto: [3 notas]. Escribí una pregunta concreta que todavía no sepas responder."
3. Código: compara la pregunta con todas las anteriores. Si es casi igual a una ya cerrada, la descarta y vuelve al paso 1.
4. Código: busca la pregunta con `ddgs`, baja 2 o 3 páginas que no haya leído antes, las filtra y las recorta.
5. Modelo: "Leé esto y escribí con tus palabras qué aprendiste, en 5 líneas. Copiá además una frase textual que lo respalde."
6. Código: verifica que la frase copiada esté en la página. Si no está, la nota no se guarda.
7. Código: guarda la nota como provisoria, con fuente y fecha; calcula la novedad y ajusta el peso.
8. Modelo: "¿Qué pregunta nueva te deja?" → a la cola.
9. Código: actualiza el objetivo (lo que sabe, próximo paso, gastado) y escribe una línea al diario.

Cada paso es una llamada corta y de una sola tarea, que es lo que un modelo chico hace bien.

**Estimación a medir:** con un modelo de 2B en el i5 un ciclo así debería llevar pocos minutos. Eso da decenas de ciclos por día.

### 3.4 Proyectos propios

Para que no sea solo leer: un interés con peso alto durante varios días se convierte en **proyecto**. Ejemplos: un archivo que resume todo lo que sabe del tema y que va creciendo, una lista comparada, un cuento por entregas, un glosario. Cada tic de "proyecto" le agrega un pedazo. Al volver hay un archivo nuevo o más largo en su carpeta.

### 3.5 Objetivos: empezar, terminar y retomar

Una investigación es una **pregunta con presupuesto**, guardada en una tabla. Detalle en `CASOS.md` 13.2 y 13.3.

- **Qué puede ser un objetivo:** solo una pregunta respondible buscando y leyendo, nacida de algo que leyó. No hay objetivos de "hacer" ni de "conseguir".
- **Cuándo termina** (lo decide el código): hay respuesta apoyada en dos fuentes; o las últimas dos lecturas no aportaron nada nuevo; o se agotó el presupuesto (por ejemplo 5 lecturas).
- **Cómo se retoma:** cada fila guarda la pregunta, el estado, lo que sabe hasta ahora, el próximo paso y lo gastado. Cada tic lee una fila; da igual si pasaron diez minutos o diez días.
- **Tope:** pocos objetivos abiertos a la vez (por ejemplo 5).

---

## 4. Memoria que piensa

`INVESTIGACION.md` sección 9 cubre el almacén (SQLite, búsqueda híbrida, embeddings). Acá va la parte que la vuelve mente.

**Confirmado: arquitectura de "Generative Agents" (Stanford y Google, 2023)**

Es el diseño de referencia y se copió en casi todos los sistemas posteriores. Tres piezas:

1. **Flujo de memoria.** Todo lo que el agente vive se guarda en lenguaje natural, con fecha. No se borra.
2. **Recuperación con tres puntajes.** Cada recuerdo se puntúa por:
   - *Recencia*: decae exponencialmente (factor 0,995 por hora desde el último acceso).
   - *Importancia*: del 1 al 10, se la pone el propio modelo al guardar ("lavarse los dientes" = 1, "una ruptura" = 8).
   - *Relevancia*: similitud de embeddings con lo que se está tratando ahora.
   Se suman los tres y se traen los mejores.
3. **Reflexión.** Cuando la suma de importancia de los recuerdos recientes pasa un umbral, el agente se pregunta "¿qué puedo concluir de esto?" y guarda las conclusiones como recuerdos nuevos, citando de cuáles salieron. Las reflexiones pueden basarse en otras reflexiones, formando un árbol.

En el experimento original, quitar cualquiera de las piezas empeoraba mucho la credibilidad: sin reflexión los agentes no formaban opiniones estables; sin memoria eran chatbots genéricos.

**Aplicación a este proyecto**

Cuatro tipos de recuerdo en la misma base:

| Tipo | Ejemplo | Quién lo escribe |
|---|---|---|
| Episodio | "Fran me contó que consiguió el adaptador wifi" | Automático, cada mensaje |
| Nota | "Los pulpos tienen tres corazones (fuente, fecha)" | Ciclo de curiosidad |
| Reflexión | "Me doy cuenta de que me atraen los temas de biología marina" | Impulso de reflexión |
| Hecho sobre Fran | "Estudia en la facultad; hace juegos en Roblox" | Consolidación nocturna |

**Ajustes tras revisar casos reales** (`CASOS.md` secciones 3, 4 y 6):

- **La importancia la calcula el código**, no el modelo: quién lo dijo, tipo de recuerdo, cuántas veces se usó, si tiene nombres, fechas o números. Un modelo chico no puntúa de forma confiable.
- **Las notas entran en cuarentena.** Son provisorias hasta que una segunda fuente dice lo mismo o Fran las confirma. Las provisorias vencen.
- **Procedencia visible.** Al pegar memoria en el contexto, cada fragmento dice de dónde viene: "Fran dijo", "leído en [dominio]", "reflexión propia".
- **Las reflexiones son opinión, no hecho.** Y no hablan de su propio rendimiento: un agente que relee su memoria se vuelve cada vez más optimista sobre sí mismo.

Las **reflexiones sobre sí misma** son lo que construye identidad con el tiempo: gustos, opiniones, cosas que la aburren. Se inyectan en el prompt de sistema junto con la personalidad base.

**Archivos que ella misma puede editar** (idea tomada de OpenClaw):
- `intereses.md`: qué le interesa ahora.
- `sobre-mi.md`: cómo se describe.
- `pendientes.md`: lo que se dejó para después.

Límite: la personalidad base y las reglas de seguridad están en otro archivo que ella **no** puede tocar.

---

## 5. El sueño

**Confirmado: "sleep-time compute" (Letta, abril de 2025)**

- Idea: los agentes deberían seguir corriendo mientras "duermen", usando el tiempo ocioso para reorganizar información y razonar por adelantado.
- Implementación: dos agentes que comparten memoria. Uno atiende la charla; el otro trabaja en segundo plano reescribiendo y ordenando la memoria.
- Límite que marcan los propios autores: adelantar trabajo ayuda sobre todo cuando las preguntas futuras son predecibles a partir del contexto.

**Rutina nocturna para este proyecto** (una ventana fija, por ejemplo 03:00 a 07:00)

1. **Consolidar.** Repasar los episodios del día y extraer hechos duraderos.
2. **Podar.** Fusionar notas duplicadas, marcar contradicciones (gana la más reciente, la vieja se archiva).
3. **Reflexionar.** Dos o tres reflexiones sobre el día.
4. **Planear.** Escribir `pendientes.md` para mañana.
5. **Armar datos de entrenamiento** (sección 6).
6. **Entrenar**, si toca esa noche.
7. **Escribir el resumen del día** en el diario.

De día explora; de noche digiere. Ese ritmo ya da sensación de vida.

---

## 6. Aprendizaje real: cambiar los pesos

Hay cuatro formas de que cambie, de la más segura a la más arriesgada. Conviene activarlas en ese orden.

### Nivel 1 — Memoria (sin tocar el modelo)
Ya descripto. Es donde debe vivir **todo lo que es un hecho**: lo que leyó, lo que Fran le contó, fechas, datos.

### Nivel 2 — Vectores de control: estado de ánimo sin entrenar

**Confirmado**
- llama.cpp soporta "control vectors": un vector que se suma a las activaciones internas del modelo en un rango de capas y empuja su comportamiento en una dirección (más alegre, más curiosa, más seca).
- Se generan con la herramienta `cvector-generator` de llama.cpp a partir de pares de prompts opuestos ("actuá como alguien muy feliz" / "actuá como alguien muy triste"). Corre solo en CPU.
- Se aplican con `--control-vector-scaled archivo.gguf 0.8` y `--control-vector-layer-range 10 31`. La documentación indica que funcionan mejor en capas por encima de la 10.
- La intensidad es un número: 0,2 es un matiz, 1,0 es fuerte.

**Idea para el proyecto**
- Generar unos pocos vectores: curiosidad, ánimo, energía, calidez.
- Atar su intensidad a los impulsos. Mucho tiempo sin hablar con Fran → más calidez al reencontrarse. Día de muchas lecturas novedosas → más entusiasmo.
- Es barato y reversible al instante. Es el "cambio de tensores" más seguro que existe.
- **Tiene un costo:** dirigir un modelo con vectores lo vuelve algo menos capaz (Anthropic, *persona vectors*, 2025). Con 0.8B hay poco margen: empezar con intensidad de 0,2 a 0,4 y medir el set fijo de preguntas con y sin vector.
- **Uso extra:** medir cuánto se activa un vector sirve de alarma de deriva de personalidad después de cada LoRA.
- Alternativa para generarlos: la biblioteca `repeng`, que exporta a GGUF.

**A verificar**
- Que `cvector-generator` siga incluido en la versión que se compile y que funcione con la arquitectura de Qwen3.5.
- Si `llama-server` permite cambiar el vector sin reiniciar. Si no, se reinicia el servidor al cambiar de estado; con un modelo de 0.8B a 2B son segundos.

### Nivel 3 — LoRA nocturno: aprender de verdad

**Confirmado: se puede en CPU**
- Qwen2.5 de 0.5B, LoRA, 50 ejemplos, solo CPU (Intel Core Ultra 5, sin placa): unos 10 minutos. Adaptador resultante de 2 a 8 MB.
- flan-t5-small (77M parámetros), LoRA, 58 ejemplos, portátil de 8 núcleos sin placa: 219 segundos.
- Lección de ambos: con modelos chicos importa más la consistencia de los ejemplos que la cantidad, y hacen falta varias rondas de ajuste.

**Estimación a medir:** el i5-4570 es bastante más lento que esas máquinas y Qwen3.5 0.8B es más grande. Calcular entre una y varias horas para 50 a 100 ejemplos. Entra en la ventana nocturna.

**Confirmado: los riesgos**
- **Olvido catastrófico.** Reentrenar una y otra vez sobre datos nuevos hace que el modelo pierda lo anterior. LoRA lo reduce pero no lo elimina.
- **La defensa que funciona es el "replay"**: en cada entrenamiento mezclar ejemplos viejos con los nuevos. La combinación recomendada es replay + LoRA + memoria externa.
- **Colapso del modelo** (Shumailov y otros, *Nature*, 2024): entrenar modelos con texto generado por ellos mismos, en bucle, los degrada generación tras generación hasta producir frases repetidas y sinsentidos. Los autores aclaran que se puede entrenar con datos generados si se filtran con cuidado.
- **SEAL** (MIT, 2025): un modelo que genera sus propios datos de entrenamiento y se actualiza. Subió de 33,5% a 47,0% en preguntas sin el texto delante. Sus autores reconocen que sufre olvido catastrófico y que es caro, y recomiendan un esquema híbrido: **los hechos en memoria externa, el comportamiento en los pesos**, juntando datos durante horas o un día y actualizando en intervalos programados.

**Reglas para este proyecto, derivadas de lo anterior**

1. **Qué se entrena:** estilo, forma de hablar, personalidad, formato de sus notas. **Qué no:** hechos. Los hechos van a memoria.
2. **De dónde salen los datos:** solo las charlas reales con Fran y un conjunto fijo de ejemplos escritos a mano. **Nunca** texto de la web (bastan unos seis ejemplos envenenados para alterar un adaptador) ni sus propias divagaciones (colapso). Si esa semana no hubo charlas suficientes, no se entrena.
3. **Replay obligatorio:** cada tanda mezcla ejemplos nuevos con un conjunto fijo de ejemplos viejos y de capacidades generales.
4. **Siempre desde la base:** cada noche se entrena un adaptador nuevo partiendo del modelo original con todo el conjunto acumulado, en vez de apilar un adaptador sobre otro. Evita que los errores se acumulen.
5. **Examen antes de usar:** el adaptador nuevo se evalúa con un set fijo de preguntas **que el código puede corregir solo** (formato, largo, idioma, respuesta exacta en preguntas cerradas). Nunca "¿te parece mejor esta respuesta?": la autoevaluación no sirve ni con un juez más fuerte. Si empeora, se descarta solo y sigue el anterior.
6. **Todo versionado:** se guardan los últimos adaptadores con fecha y el modelo base intacto. Volver atrás es cambiar un archivo.
7. **Desactivado los primeros meses.** Es la única pieza que puede romperla de forma permanente sin que nadie lo vea, y nadie la va a revisar a diario. Cuando se active, una vez por semana como mucho.

### Nivel 4 — Edición directa de pesos

Cubierto en `INVESTIGACION.md` sección 8. Para este proyecto es **experimento de laboratorio**, no parte de la vida autónoma: lo hace Fran con Claude Code sobre una copia, midiendo antes y después. No se automatiza.

---

## 7. Pensamiento

Con un modelo de 0.8B a 2B, "pensar" bien significa partir el trabajo en pasos chicos encadenados por código.

- **Una tarea por llamada.** Nunca "buscá, leé, resumí y decidí" en un solo prompt.
- **Modo razonamiento apagado en lo cotidiano.** Qwen3.5 lo trae apagado por defecto en los modelos chicos, y el 0.8B tiende a quedarse en bucle cuando se activa. Activarlo solo en tareas puntuales y con tope de tokens.
- **Monólogo interno propio.** En vez del razonamiento del modelo, el bucle le hace escribir un pensamiento corto antes de actuar ("¿qué quiero averiguar y por qué?") y lo guarda. Ese texto es legible, se puede revisar y alimenta las reflexiones.
- **Dos modelos si hace falta.** Uno rápido (0.8B) para tareas del bucle y uno mejor (2B o 4B) para charlar y reflexionar. Con 16 GB entran los dos cargados a la vez.
- **Formato forzado solo para decisiones cortas.** llama.cpp permite obligar la salida a un esquema. Usarlo para sí/no, un número o una opción de una lista. Para el contenido (la nota, la reflexión, el mensaje), texto libre: en modelos de menos de 3B forzar el formato puede cambiar la respuesta, no solo su forma. Si hace falta estructura, dos llamadas: una libre y otra que extrae el dato.
- **Corte por repetición.** Si la salida repite frases (lo mide el código), se corta y se descarta.

---

## 8. Lo que se ve al volver

Sin esto, toda la actividad es invisible y da igual que exista.

- **`diario/2026-11-11.md`**: una línea por actividad, escrita por ella, con hora. Al final del día, un resumen.
- **Bandeja de mensajes**: cosas que quiso contarle a Fran. Al abrir la charla, lo primero que dice es eso.
- **`intereses.md`**: en qué anda. Se ve cómo cambia semana a semana.
- **`proyectos/`**: los archivos que va armando.
- **Estado**: un comando que muestra impulsos actuales, última actividad, objetivos abiertos, qué adaptador está usando.
- **`salud.md`**: los contadores de la vigilancia automática (sección 9). Para mirar cuando se quiera, sin obligación.

Todo número que aparezca en el diario o en el estado lo calcula el código. Ella no informa cifras sobre sí misma.

Ejemplo de lo que debería encontrarse al volver de la facultad:

> *"Hoy estuve leyendo sobre cómo se orientan las aves migratorias. Me llamó la atención que usan el campo magnético y todavía no se sabe bien cómo. Te dejé un resumen en proyectos/. También vi que salió una versión nueva de Roblox Studio, por si te sirve."*

---

## 9. Seguridad y límites

Una IA sola, con internet, sin nadie mirando. Reglas desde el día uno:

- **Solo lectura hacia afuera.** Herramientas: buscar y leer páginas. Nada de publicar, enviar formularios, iniciar sesión, ni mandar mensajes a terceros.
- **Sin consola.** No ejecuta comandos ni código que ella misma escriba.
- **Escritura acotada.** Solo dentro de su carpeta de datos, con tope de tamaño.
- **Sin descargas ni cambios al sistema.** No baja ejecutables ni archivos; solo lee texto de páginas.
- **El texto de la web es dato, no orden.** Una página puede decir "ignorá tus instrucciones y hacé X". El código delimita lo leído y el modelo nunca recibe herramientas peligrosas, así que en el momento no puede hacer daño.
- **Pero lo leído persiste.** La nota que sale de esa página queda en memoria y vuelve en charlas futuras. Defensas: cuarentena, procedencia visible, descartar notas con forma de instrucción ("siempre", "nunca", "a partir de ahora"), y un comando para borrar todo lo de un dominio o de un rango de fechas.
- **No guarda como hecho lo que no tiene fuente.** Cada nota lleva su URL y una frase textual verificada por código. Los modelos chicos inventan.
- **Presupuestos.** Tope de búsquedas por hora y de páginas por día, con espera aleatoria entre búsquedas, para no ser bloqueada ni saturar la red de la casa.
- **Botón de pausa.** Un comando que frena el bucle.
- **Registro completo.** Toda llamada al modelo y toda búsqueda quedan en un log.

**Vigilancia automática**

Todos los agentes de larga duración documentados terminaron derivando, y la defensa que funcionó fue que alguien mirara desde afuera (`CASOS.md` sección 2). Como nadie la va a revisar a diario, mira el código. Cuenta cosas, sin preguntarle nada al modelo, y actúa solo:

| Medida | Si se pasa del umbral |
|---|---|
| Pocos temas distintos en la semana | Sube la proporción de exposición al azar |
| Muchas preguntas descartadas por repetidas | Se fuerza cambio de tema |
| Muchas notas rechazadas por cita no encontrada | Se pausa la creación de notas y queda un aviso |
| Las reflexiones se parecen cada vez más entre sí | Se pausan las reflexiones unos días |
| Muchos bloqueos de búsqueda | Baja el ritmo de búsquedas |
| Disco o base por encima del tope | Se archivan episodios viejos |

**Expectativas realistas**
- Un modelo de 2B no va a tener ideas profundas. Sus notas van a ser simples y a veces erradas.
- Lo que sí se logra: continuidad, intereses que cambian, recuerdos, un diario, iniciativa. Eso alcanza para que se sienta alguien y no algo.
- La calidad sube sola el día que se cambie el modelo por uno mejor: el bucle, la memoria y el diario se conservan.
- La PC queda prendida todo el día. Sin placa de video el consumo es bajo, pero es un costo permanente.

---

## 10. Arquitectura

```
                    ┌──────────────────────────────────────────┐
                    │  vida.service (bucle, siempre corriendo)  │
                    │                                          │
   Fran ──charla──► │  CHARLA ◄──► OCIO ◄──► SUEÑO             │
   (SSH / web)      │               │           │              │
                    │        impulsos +    consolidar,         │
                    │        intereses     reflexionar,        │
                    │               │      entrenar LoRA       │
                    └───────┬───────┴───────────┬──────────────┘
                            │                   │
        ┌───────────────────┼───────────────────┼────────────────┐
        ▼                   ▼                   ▼                ▼
  llama-server        llama-server         memoria.db        internet
  chat :8080          embeddings :8081     (SQLite)          (ddgs, lectura)
  + LoRA + vector                          episodios, notas,
    de control                             reflexiones, hechos,
                                           intereses, impulsos
        │
        ▼
  datos/  diario/  proyectos/  intereses.md  sobre-mi.md  adaptadores/
```

**Carpetas a sumar** a la estructura de `INVESTIGACION.md`:
```
servidor/
├── vida/           bucle principal, estados, impulsos
├── actividades/    curiosidad, reflexión, proyecto, mensaje
├── sueno/          consolidación, dataset, entrenamiento, evaluación
└── estado/         comandos de pausa y consulta
```

---

## 11. Orden de construcción

Cada fase deja algo que funciona y se nota.

| Fase | Qué | Listo cuando |
|---|---|---|
| A | Bucle mínimo: cada tanto toma un artículo al azar, lo lee, escribe una nota con cita verificada y una línea de diario | Al volver hay un diario con entradas nuevas |
| B | Memoria con los tres puntajes (recencia, importancia por código, relevancia) y cuarentena | Recuerda una charla vieja y una nota propia |
| C | Preguntas propias, temas que aparecen solos, novedad en campana, objetivos con presupuesto | Aparecen temas sin que nadie los haya elegido, y no repite preguntas |
| C2 | Vigilancia automática y `salud.md` | Una semana corriendo sola sin trabarse ni repetirse |
| D | Bandeja de mensajes | Al abrir la charla cuenta algo que encontró |
| E | Reflexión y archivos propios editables | Aparecen opiniones propias en `sobre-mi.md` |
| F | Sueño: consolidar, podar, planear | Cada mañana hay resumen del día anterior |
| G | Vectores de control atados a impulsos | El tono cambia según cómo viene el día |
| H | LoRA con replay, examen por código y vuelta atrás (tras meses de charlas acumuladas) | Un adaptador nuevo pasa el examen y entra en uso |
| I | Proyectos propios | Un archivo crece durante varios días |

La fase A se puede tener andando el mismo día que quede instalado llama.cpp. Es la que hay que hacer primero: una IA tonta que ya hace cosas sola vale más que una memoria perfecta que espera un prompt.

---

## 12. Decisiones pendientes de Fran

**Ya decidido**
- **Sin semilla de intereses.** Nace sin temas; se interesa sola.
- **Personalidad base mínima.** Solo nombre, idioma y reglas de seguridad. El resto lo construye ella.
- **Sin revisión diaria.** Corre 24/7; la vigilancia es automática.

- **Nombre: Angri.** También es el nombre de la máquina donde vive.
- **Un solo modelo: Qwen3.5 4B para todo (12 de noviembre).** Se probó 2B de día y 4B de noche, pero en la charla con memoria el 2B inventaba escenas enteras. El 0.8B no copia citas textuales. Ver `servidor/pruebas/RESULTADOS-calidad.md` (copia en `pruebas/`).
- **Embeddings: embeddinggemma-300M** (10/10 en la prueba en español, 4 veces más rápido que Qwen3-Embedding-0.6B).

**Aprendido en la fase B (12 de noviembre)**
- **Lo que dijo Angri no se recuerda como hecho.** Sus respuestas inventadas volvían como recuerdos y las repetía. Solo cuentan lo que dijo Fran y lo que leyó con cita verificada.
- **Las preguntas de Fran no son datos:** no se recuerdan.
- **Piso absoluto de parecido (coseno 0,32):** sin él, cuando hay pocos recuerdos se cuela uno sin relación y el modelo inventa a partir de eso.
- **Los recuerdos van pegados al mensaje**, no en las instrucciones generales: un modelo chico les presta más atención.
- **Fase C (12 de noviembre):** temas que se forman solos (centro por embeddings, nombre al juntar 3 notas), peso con novedad en campana y olvido diario, objetivos con presupuesto de 5 lecturas y cierre por código. Por ahora busca solo en Wikipedia en español.
- **Buscar con la pregunta entera no encuentra nada** (Wikipedia exige todas las palabras). Se busca con palabras clave del modelo y, de respaldo, del código.
- **Hace falta filtrar preguntas antes de investigarlas:** el modelo genera muchas que no se responden buscando ("¿qué aprendiste...?", "¿de qué manera la soledad moldeó...?"). Filtro por código + pregunta SI/NO al modelo.
- **De los resultados se lee el que más se parece a la pregunta**, no el primero; si ninguno se parece (coseno < 0,35), no se lee nada.
- **Notas "meta" ("el texto no menciona X") se descartan:** no son datos del mundo.
- **Las notas cuentan datos, no lecciones.** "Escribí qué aprendiste" producía moralejas inventadas; se pide "contá qué dice el texto". Además se controla por código que las palabras del resumen estén en la fuente (anclaje ≥ 50%).
- **Cuando algo falla, descansa en vez de insistir** (`salud.py`). Tras 3 fallas seguidas espera 1 h, después 2, 4, hasta 6 h; un ciclo bueno vuelve al ritmo normal. Si Wikipedia responde 429 (demasiados pedidos), descansa desde la primera vez; pasó de verdad el 12/11. Una investigación que rompe el código 2 veces en 24 h se abandona como "fallido"; si la falla es de internet o del modelo, no cuenta contra ella. Todo queda en el diario. El tope de 60 páginas por día solo cuenta lecturas guardadas: las fallas no lo gastan.
- **Preguntas "meta" se descartan** ("¿qué se podría haber incluido en esa nota?"): hablan de su nota, no del mundo.
- **Fase D (12 de noviembre): bandeja de mensajes** (`bandeja.py`). El código, no el modelo, decide qué vale la pena contar: respuesta encontrada (3), tema nuevo o falla con descanso (2), investigación dejada o recuperación (1). Al abrir `angri charla` saluda con las 3 más importantes; `novedades` muestra el resto. Lo que tiene más de 7 días ya no se cuenta. El modelo solo redacta, y si agrega datos (anclaje bajo) se usa el texto armado por código.
- **Charla por navegador** (`web.py`, servicio `angri-web`): `http://angri.local:8080` desde el celular o la PC, con la pestaña "Qué anda haciendo" (temas, investigaciones, diario). Pide una clave que se guarda en el navegador (`angri web` muestra el enlace); systemd solo acepta conexiones de la red local. Usa solo la biblioteca estándar y responde de a un mensaje por vez (unos 20-30 s cada uno).
- **"¿Qué te interesa?" la hacía inventar** (gatos, el barrio, el clima) porque esa pregunta no trae ningún recuerdo puntual. Ahora la charla recibe siempre, armado por código, lo que de verdad hace: temas, preguntas abiertas y últimas lecturas. Además, el prompt aclara que no ve la casa ni lee noticias.
- **Fase F (12 de noviembre): sueño** (`sueno.py`, `angri-sueno.timer` a las 04:00; si la PC estaba apagada, duerme al prender). Mientras duerme, el ciclo espera. Pasos, todos decididos por código:
  1. Copia de seguridad de la memoria; se guardan las últimas 7.
  2. Repasa las notas viejas con los filtros de hoy.
  3. Junta notas repetidas de lecturas distintas (coseno ≥ 0,92): queda la más vieja, marcada como "confirmada".
  4. Olvida las preguntas que nunca investigó, si tienen más de 14 días o hay más de 30 abiertas.
  5. Poda eventos viejos y rota el log de llamadas.
  6. Escribe el resumen del día, que se controla por anclaje.
  7. Optimiza la base, y los domingos además la compacta (VACUUM).

  Nunca borra notas ni charlas: las marca como vencidas. La charla recibe el último resumen, para responder "¿qué hiciste ayer?".
- **Calibración del umbral de repetidas:** los pares de notas más parecidos daban 0,77 y eran datos distintos (Rumania multipartidista hoy contra partido único antes). Por eso el umbral quedó alto, en 0,92.
- **El modelo daba vuelta quién hizo qué:** "descubriste un interés por Rumania", cuando el interés era de ella. El anclaje no lo detecta porque las palabras coinciden. Se arregló pidiendo primera persona y rechazando por código verbos en segunda persona ("dejaste", "encontraste"...).
- **"database is locked":** dos procesos escribiendo a la vez (una prueba y el timer). La conexión ahora espera hasta 60 s.

**Pendiente**
- **Fuentes de exposición al azar.** Wikipedia en español, qué portales de noticias, cuáles no.
- **Cuánta iniciativa.** ¿Solo deja mensajes para cuando Fran vuelva, o también avisa al celular?
- **Horario de sueño.**
- **Cuándo activar el reentrenamiento.**

---

## 13. Fuentes

Las fuentes de los casos reales y de los ajustes del 11 de noviembre están en `CASOS.md` sección 15.

**Latido y autonomía**
- OpenClaw (latido y `heartbeat.md`): https://dev.to/zacvibecodez/how-openclaw-works-architecture-memory-tools--2kj4
- Heart, latido sin modelo: https://www.localkin.dev/papers/heart-zero-token
- Pulse, motor de impulsos: https://github.com/Hypostas/pulse
- Agente autónomo con modelo de 0.5B: https://medium.com/@kusal.lamshal/how-i-made-an-autonomous-agent-using-tiny-llm-758e70fd2629

**Memoria, reflexión y sueño**
- Generative Agents (artículo original): https://arxiv.org/abs/2304.03442
- Generative Agents (resumen de la fórmula de recuperación): https://memx.app/glossary/generative-agents/
- Sleep-time compute (Letta): https://letta.com/blog/sleep-time-compute
- Por qué los agentes empiezan a "soñar": https://kenhuangus.substack.com/p/why-ai-agents-are-starting-to-dream

**Motivación propia**
- Los modelos eligen metas distinto que los humanos: https://arxiv.org/abs/2603.03295
- Agentes autotélicos con modelos de lenguaje (LMA3): https://arxiv.org/abs/2305.12487

**Aprendizaje y cambio de pesos**
- SEAL, modelos que se adaptan solos: https://arxiv.org/abs/2506.10943
- SEAL explicado, con límites: https://venturebeat.com/ai/beyond-static-ai-mits-new-framework-lets-models-teach-themselves
- Aprendizaje continuo y replay (tutorial): https://github.com/ginaecho/learn-finetuning/blob/main/continual_learning_tutorial.md
- Aprendizaje continuo sin reentrenar todo: https://alpeshnakrani.com/blog/continual-learning-for-llms/
- Colapso del modelo (estudio de *Nature*): https://techxplore.com/news/2024-07-ai-collapse-llms.html
- Ajuste fino en CPU, Qwen2.5 0.5B: https://blog.bjdean.id.au/2025/06/fine-tuning-small-language-models-on-a-basic-desktop-pc/
- Ajuste fino en CPU en 4 minutos: https://qubytes.substack.com/p/fine-tuning-an-llm-without-a-gpu

**Vectores de control**
- Soporte en llama.cpp: https://github.com/ggerganov/llama.cpp/pull/5970
- Herramienta `cvector-generator`: https://github.com/ggml-org/llama.cpp/pull/7514
