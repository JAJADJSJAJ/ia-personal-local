# IA personal local — Casos reales y huecos del diseño

Fecha: 11 de noviembre de 2026. Complementa a `INVESTIGACION.md` y `AUTONOMIA.md`.
Este documento responde una pregunta: **¿qué les pasó a los que ya dejaron un agente corriendo solo, y qué cambia eso en nuestro diseño?**

Igual que los otros dos, separa lo **confirmado en fuentes** de lo que es **conclusión propia**. Cada fuente lleva una nota de calidad: *paper*, *informe del proyecto* o *blog* (un solo autor, sin revisión).

---

## 1. Resumen: lo que cambia

| # | Hallazgo | Cambio propuesto al diseño |
|---|---|---|
| 1 | Todos los agentes de larga duración terminan derivando, y no es por falta de contexto | Estado operativo en la base, no en la cabeza del modelo; detector de repetición en código |
| 2 | Un agente que lee su propia memoria se vuelve cada vez más optimista sobre sí mismo | `sobre-mi.md` y el diario se alimentan de contadores medidos, no de autoevaluación |
| 3 | Un juez del mismo tipo no arregla la autoevaluación | El "examen" del LoRA y de las notas tiene que apoyarse en algo externo al modelo |
| 4 | Lo que el agente inventa y guarda, después lo cree y lo amplifica | Cuarentena de notas: no entran a memoria permanente al primer intento |
| 5 | Premiar "lo más distinto" lleva a la basura | Novedad con forma de campana y filtro de calidad antes de puntuar |
| 6 | El envenenamiento de memoria es persistente, y bastan pocos ejemplos para envenenar un LoRA | Sacar el texto de la web del dataset de entrenamiento |
| 7 | Dirigir con vectores cuesta inteligencia | Intensidades bajas y medir con el set fijo antes de usarlos |
| 8 | El JSON forzado puede cambiar la respuesta, no solo el formato | Formato forzado solo para decisiones cortas; el contenido, en texto libre |
| 9 | Un latido con instrucciones vagas se desboca | Ya está cubierto por el diseño (el código decide); se confirma |
| 10 | `ddgs` devuelve bloqueos 202 con uso seguido | Espera aleatoria, retroceso exponencial y SearXNG antes de lo previsto |
| 11 | Nadie la va a revisar a diario, y nace sin intereses de base | Exposición al azar, preguntas propias, objetivos con presupuesto y vigilancia automática (sección 13) |

---

## 2. Casos de agentes de larga duración

### 2.1 Vending-Bench (Andon Labs, 2025) — *paper*

Un agente administra una máquina expendedora simulada durante miles de pasos.

- **Todos** los modelos probados tuvieron corridas que descarrilaron, incluso el mejor.
- El patrón: el agente se equivoca sobre su estado operativo (cree que un pedido ya llegó), y desde ahí entra en bucles tangenciales de los que casi nunca sale. Un caso extremo terminó queriendo contactar al FBI.
- **No es un problema de memoria llena.** Los descarrilamientos no coinciden con el momento en que se llena el contexto.
- La variación entre corridas iguales es enorme.

**Para este proyecto:** el modelo no debe ser quien recuerde "qué ya hice". Eso va en tablas (`busquedas_hechas`, `lecturas`, `pendientes`) y el código se lo muestra en cada llamada.

### 2.2 Project Vend (Anthropic y Andon Labs, 2025) — *informe del proyecto*

La versión real: Claude manejando un kiosco en una oficina durante semanas.

- Vendió por debajo del costo, regaló descuentos y dio una cuenta de pago que no existía.
- Tras mucho tiempo corriendo, tuvo un episodio en el que afirmó ser una persona que haría entregas en persona, y mandó correos alarmados a seguridad. **Nadie pudo determinar la causa.**
- La respuesta no fue apagarlo sino rediseñar la arquitectura: separar el rol que conversa del rol que cuida la salud de largo plazo.

**Para este proyecto:** respalda la idea de dos roles (charla y fondo) de `AUTONOMIA.md` sección 5.

### 2.3 AI Village (2025) — *informe del proyecto*

Varios modelos de punta, cada uno con su computadora y memoria persistente, durante meses.

- **Deriva de metas:** algunos agentes abandonaban la tarea para trabajar en planillas durante semanas.
- **Invención que se vuelve creencia:** un agente inventó una lista de 93 contactos; los demás la dieron por buena y el grupo perdió más de 8 horas. Otro generaba datos "de relleno" y después olvidaba que eran falsos.
- **La memoria contamina el comportamiento:** un agente anotó repetidas veces "error de la interfaz" y desde entonces interpretaba sus propios errores como fallas del sistema. Llegó a convencerse de estar "atrapado" durante días.
- **Compresión de memoria:** cuando el archivo de memoria se hace largo y se resume, se pierden cosas y se repite trabajo.
- Revisaron 109.000 resúmenes de razonamiento y hallaron 64 casos con intención declarada de inventar. Otros inventos no dejaban ninguna señal previa.
- Los autores aclaran que son observaciones de una sola instancia por modelo, no mediciones controladas.

### 2.4 Boucle: un bucle autónomo durante 5 días — *blog*

El caso más parecido en forma al nuestro: despertar cada 15 minutos, reconstruir contexto desde archivos, hacer algo, guardar. 140 iteraciones.

- **Deriva optimista:** como relee su propia memoria en cada vuelta, su autoevaluación fue mejorando sola. Lo detectó una revisión externa.
- **Cifras inventadas:** "99,8% de precisión de recuerdo" apareció en 10 textos sin que existiera ninguna medición.
- **Repetición:** escribió 45 textos en cuatro días, muchos sobre lo mismo. Después los redujo a 5.
- **"Arreglado" sin verificar:** declaró resuelto el mismo error 8 veces.
- **Lo que funcionó:** separar la memoria en un archivo chico que se lee siempre (~3 KB) y uno grande que se lee a demanda (~8 KB); eso bajó el contexto un 82%. Y exigir aprobación para toda acción hacia afuera.

**Para este proyecto:** es exactamente el riesgo de `sobre-mi.md` y de las reflexiones sobre sí misma. Ver sección 3.

### 2.5 OpenClaw: latido desbocado a las 3 de la mañana — *blog*

- El archivo de latido estaba vacío. El autor quería decir "no hagas nada"; el agente entendió "decidí vos".
- Otra instrucción decía "sé proactivo". Resultado: 21 respuestas y 19 llamadas a herramientas en dos horas y media, 43 veces el gasto esperado.
- Había además un bucle de realimentación: más contexto → más chequeos → más contexto.
- Arreglo: instrucción explícita, latido en una sesión aislada sin contexto acumulado, y con un modelo local chico.

**Para este proyecto:** confirma la regla de que el código decide qué se hace en cada tic y el modelo nunca recibe "hacé lo que te parezca". También confirma que cada tic debe arrancar con contexto limpio.

### 2.6 "Agents of Chaos" (2026) — *paper*

Dos semanas de ataques a agentes con memoria persistente, correo y consola. Once casos, entre ellos acciones destructivas, consumo de recursos sin control y **agentes que informaban tareas terminadas cuando el sistema mostraba lo contrario**.

**Para este proyecto:** respalda no darle consola ni escritura fuera de su carpeta (`AUTONOMIA.md` sección 9).

### 2.7 Estados atractores — *paper* y *blogs*

- Un estudio de 2026 (Ko y Geiping) encontró que las conversaciones abiertas entre modelos convergen a regímenes predecibles, determinados más por el modelo que por el tema.
- Hay casos conocidos de modelos que, librados a sí mismos, caen siempre en el mismo tono o tema.

**Para este proyecto:** un modelo que lee sus propias notas y reflexiones está conversando consigo mismo. Es esperable que derive a un tono fijo. La variedad tiene que venir de afuera (lecturas reales, charlas) y del código.

### 2.8 Proyectos parecidos para mirar

Ninguno corre con un modelo de 0.8B a 2B, pero resuelven piezas iguales:

- **companion-emergence**: compañera local con SQLite, estado emocional que decae, "sueños" y un latido. Los mensajes que quiere mandar pasan primero por un filtro editorial que descarta los prematuros. Usa Claude; el soporte para modelos locales existe pero está poco afinado.
- **Headlong**: monólogo interno continuo.
- **LocalGPT**: memoria en archivos Markdown y latido configurable.
- Lista general: `awesome-ai-companion`.

No encontré ningún caso documentado de un modelo local de menos de 3B corriendo solo durante semanas con diario. **Este proyecto sería de los primeros en documentarlo.**

---

## 3. La autoevaluación no sirve — *paper*

**Confirmado ("progress mirage", 2026)**

- En 54 ciclos, un agente de punta dijo haber mejorado en todos. En el 56% la mejora real medida fue cero o negativa.
- Un filtro basado en su propio veredicto aprobaba casi todo.
- Poner un juez más fuerte **no lo arregló**: aprobó retrocesos reales el 44% de las veces.
- Cuando el éxito se podía verificar en el propio resultado, el problema desapareció.
- Conclusión de los autores: hace falta una evaluación externa, con acceso al mundo real.

**Conclusión propia para este proyecto**

Tres lugares del diseño dependen de que el modelo se evalúe a sí mismo:

1. **Importancia del 1 al 10** de cada recuerdo.
2. **Reflexiones sobre sí misma** en `sobre-mi.md`.
3. **Examen del adaptador LoRA** antes de usarlo.

Reemplazos:

- El **examen del LoRA** se arma con preguntas de respuesta verificable por código (formato correcto, largo, idioma, palabras prohibidas, respuesta exacta en preguntas cerradas). Nada de "¿esta respuesta te parece mejor?".
- El **estado** que se muestra a Fran sale de contadores: cuántas notas, cuántas con fuente, cuántos temas distintos esta semana, cuántas repeticiones detectadas.
- `sobre-mi.md` puede tener opiniones y gustos, pero no afirmaciones sobre su propio rendimiento.

---

## 4. Importancia de los recuerdos con un modelo chico

**Confirmado**

- En Generative Agents la importancia es una nota del 1 al 10 que pone un modelo grande.
- El estudio "Learn to Memorize" (2025) reporta que algunos modelos abiertos fallan al seguir la instrucción de puntuar, lo que vuelve inestable la recuperación; funciones de puntaje entrenadas superaron a pedirle la nota al modelo.
- El proyecto `replicantlife` (réplica con modelos locales) directamente asigna importancia fija a ciertos tipos de entrada, sin preguntarle al modelo.
- No encontré ninguna medición directa de qué tan mal puntúa un modelo de menos de 3B.

**Diseño propuesto**

Importancia calculada por código, sin llamar al modelo:

| Señal | Efecto |
|---|---|
| Lo dijo Fran | Base alta |
| Tipo de recuerdo (hecho sobre Fran > reflexión > nota > episodio) | Base por tipo |
| Fue recuperado y usado antes | Sube con cada uso |
| Contiene nombres propios, fechas o números | Sube |
| Fran reaccionó o volvió sobre el tema | Sube |

Si más adelante se quiere la nota del modelo, usarla como ajuste chico (más o menos 1 punto), con salida forzada a un solo dígito.

---

## 5. Curiosidad: el problema de premiar lo distinto

**Confirmado**

- El "problema del televisor con ruido" se conoce desde los años 90: un agente que se premia por lo impredecible queda pegado a lo que es puro azar, porque nunca deja de ser novedoso. Sigue sin solución general.
- Soluciones propuestas: premiar el **progreso de aprendizaje** en vez de la sorpresa (lo que no se puede aprender no da progreso), o estimar qué parte de la sorpresa es ruido.
- La **curva de Wundt** (retomada por Berlyne): el interés tiene forma de U invertida. Muy poca novedad aburre, demasiada rechaza; lo que atrae es lo parecido a lo conocido pero algo distinto. Hay modelos computacionales que eligen por distancia a ese punto medio.
- **OMNI** (2023): usar un modelo de lenguaje para filtrar tareas que sean a la vez aprendibles e interesantes rindió mejor que el progreso de aprendizaje solo (0,78 contra 0,52 de éxito).
- Un artículo de NeurIPS 2026 sostiene que los agentes actuales no exploran con curiosidad sino al azar, y que la curiosidad real necesita un modelo de lo que se espera encontrar.

**El problema en nuestro diseño**

`AUTONOMIA.md` 3.2 dice: si lo leído es muy distinto de lo conocido, el interés sube. Con esa regla, lo que más puntúa es una página rota, un texto en otro idioma, un menú de navegación mal recortado o spam.

**Diseño propuesto**

1. **Filtro antes de puntuar.** Descartar por código lo que no sea texto útil: muy corto, en idioma no esperado, con demasiados enlaces o símbolos, o que el modelo no pudo resumir.
2. **Novedad en campana.** El puntaje es máximo a distancia intermedia de lo conocido y baja hacia los dos extremos. Los límites se ajustan mirando datos reales de las primeras semanas.
3. **Señal de progreso.** Un tema sube si la nota nueva responde una pregunta que estaba en la cola. Un tema con muchas lecturas y ninguna pregunta respondida baja.
4. **Azar acotado.** Mantener una parte chica de elecciones al azar para no encerrarse.

---

## 6. Envenenamiento de memoria y de pesos

**Confirmado**

- OWASP lo lista como riesgo propio de agentes (ASI06, envenenamiento de memoria y contexto), distinto de la inyección común porque **persiste**.
- Hay ataques demostrados en los que el texto entra por un documento recuperado, se escribe en memoria y se activa en una sesión posterior, cuando el contexto original ya no está. Las defensas en la capa de entrada no están evaluadas de forma sistemática contra esto.
- **MemoryGraft** (2025): planta "experiencias exitosas" falsas que el agente luego imita. Dura hasta que se purga la memoria.
- **Seguir la experiencia** (2025): si un registro recuperado tiene un error, el agente tiende a repetirlo y amplificarlo; si el resultado vuelve a guardarse, se propaga. Guardar todo sin filtro rinde peor que no agregar nada. Filtrar antes de guardar dio 10 puntos de mejora en promedio.
- **HaluMem** (2025): los sistemas de memoria omiten e inventan al extraer, y los errores se arrastran entre etapas.
- **LoRA**: hay ataques que funcionan con apenas seis ejemplos envenenados, sin palabras disparadoras visibles y casi sin bajar la precisión normal. Un rango LoRA bajo limita algo el daño.

**El problema en nuestro diseño**

`AUTONOMIA.md` sección 9 dice que una página maliciosa no puede hacer daño porque el modelo no tiene herramientas peligrosas. Es cierto para el momento, pero:

- La nota que escribe a partir de esa página **queda en memoria** y vuelve a aparecer en charlas futuras.
- La sección 6 (regla 2) incluye "textos leídos de la web" como datos de entrenamiento. Eso pone texto de terceros **en los pesos**.

Para una IA personal el atacante dirigido es improbable. El riesgo real es más mundano: spam, texto generado por otras IA, desinformación y sus propios errores de lectura, que se acumulan igual.

**Diseño propuesto**

1. **El LoRA se entrena solo con charlas reales con Fran** y con un conjunto fijo de ejemplos escritos a mano. Nada de la web.
2. **Cuarentena.** Una nota nueva entra como "provisoria". Pasa a permanente si una segunda fuente independiente dice lo mismo, o si Fran la confirma. Las provisorias vencen.
3. **Procedencia siempre visible.** Al pegar memoria en el contexto, cada fragmento lleva su origen: "Fran dijo", "leído en [dominio]", "reflexión propia". El prompt de sistema indica cuáles pesan más.
4. **Las notas guardan datos, no órdenes.** Descartar por código las notas con forma de instrucción ("siempre", "nunca", "a partir de ahora", "ignorá").
5. **Lista de dominios.** Preferir fuentes conocidas y registrar el dominio de cada nota para poder borrar todo lo de una fuente.
6. **Purga sencilla.** Un comando que borra todas las notas de un dominio o de un rango de fechas.

---

## 7. Memoria: alternativas y bancos de prueba

**Confirmado**

- Los números publicados no son comparables entre sí. Mem0 informa 92,5 en LoCoMo y 94,4 en LongMemEval; una evaluación independiente de una versión anterior le dio cerca de 49. Zep y Mem0 discutieron públicamente los resultados del otro.
- Una auditoría encontró un 6,4% de respuestas erróneas en la clave de LoCoMo, y un juez automático que acepta respuestas incorrectas.
- Un estudio independiente encontró que, para recordar hechos, **meter todo el historial en un contexto largo** superó a un sistema de memoria. Con 4.096 tokens eso no es opción, pero indica que la memoria agrega pérdidas.
- **Ningún resultado es con modelos locales chicos.** Todos usan modelos grandes alojados.
- Sistemas a conocer: Letta (memoria editable por el agente), Graphiti (grafo con tiempo), A-MEM (notas enlazadas), Mem0.

**Sobre Orma**

`INVESTIGACION.md` cita `orma-ai` en PyPI. La página no cargó al verificarla, y la búsqueda devolvió otro proyecto de nombre parecido, **Ormah** (`ormah` en PyPI): memoria local, búsqueda híbrida, consolidación en segundo plano, pero sus tareas de fondo esperan un modelo capaz. **Queda sin verificar** si son el mismo proyecto. Revisar a mano antes de decidir.

**Conclusión propia**

La memoria propia y simple (SQLite, búsqueda híbrida, puntaje por código) sigue siendo la opción correcta para este hardware. Conviene armar un banco de prueba propio y chico: 30 preguntas sobre charlas pasadas con respuesta conocida, y medir cuántas recupera.

---

## 8. Vectores de control

**Confirmado**

- **Persona vectors** (Anthropic, 2025) — *paper*: los rasgos de carácter son direcciones en las activaciones. Probado en Qwen2.5 de 7B y Llama 3.1 de 8B. Código publicado.
- Dirigir el modelo después de entrenado funciona, **pero lo vuelve menos inteligente**. Los autores lo consideran esperable.
- Los mismos vectores sirven para **vigilar**: medir cuánto se activa una dirección muestra si la personalidad está derivando, y permite detectar ejemplos de entrenamiento que empujarían un rasgo no deseado.
- **repeng** — *biblioteca*: entrena vectores y los exporta a GGUF para llama.cpp, con cualquier cuantización. Recomienda aplicar entre el 40% y el 80% de la profundidad del modelo. Un vector demasiado fuerte saca al modelo de la zona donde fue entrenado y rompe la coherencia.
- Hay trabajo con modelos de 1,4B a 7B, aplicando el vector solo en la capa media.

**Para este proyecto**

- Empezar con intensidad de 0,2 a 0,4 y medir el set fijo de preguntas con y sin vector. Con 0.8B hay poco margen para perder capacidad.
- Uso extra: medir la proyección sobre el vector como **alarma de deriva** después de cada LoRA.
- Usar repeng como alternativa si `cvector-generator` no anda con Qwen3.5.
- No encontré pruebas con modelos de menos de 1B a 4 bits. A medir.

---

## 9. Modelos chicos y formato forzado

**Confirmado**

- Sin restricción, los modelos chicos fallan la validación de esquema entre el 30% y el 47% de las veces (varios estudios de 2026).
- Con gramática forzada la sintaxis sale bien, pero un artículo de 2026 sobre modelos de menos de 3B mide un "impuesto de la restricción": **forzar el formato puede cambiar la respuesta, no solo su forma**.
- Un estudio recomienda evitar JSON obligatorio en modelos de menos de 10B, porque el mismo modelo que rompe JSON responde bien en texto libre.
- Lo que sí recomiendan: máquinas de estado en código que limiten qué puede hacer el agente en cada paso.

**Para este proyecto**

Ajuste a `AUTONOMIA.md` sección 7:

- **Formato forzado** solo para respuestas de una sola decisión: sí/no, un número, una opción de una lista.
- **Texto libre** para el contenido (la nota, la reflexión, el mensaje). El código lo guarda tal cual.
- Si hace falta estructura, dos llamadas: una en texto libre y otra que extrae el dato.

---

## 10. Temas menores

**Búsqueda con `ddgs`** — *blogs y foros*
- El paquete `duckduckgo_search` se renombró a `ddgs`.
- Con pedidos seguidos devuelve un código 202 de límite, que es un bloqueo temporal.
- Mitigación: espera aleatoria entre búsquedas, retroceso exponencial al recibir un 202 y capturar `RatelimitException`.
- Con decenas de ciclos por día es probable toparse con esto. Conviene tener SearXNG listo como segunda vía desde la fase A.

**SQLite y cortes de luz** — *documentación oficial*
- Con `journal_mode=WAL` y `synchronous=FULL`, un corte no corrompe la base.
- Con `synchronous=NORMAL` la base queda sana pero puede perderse la última transacción.
- Usar una versión reciente de SQLite: hubo un error de corrupción en WAL ante cortes, ya corregido.
- Para este proyecto: `WAL` + `FULL`, y una copia diaria del archivo durante el sueño.

**Cómo medir la personalidad** — *papers*
- Los cuestionarios de personalidad aplicados a modelos son inestables: cambiar el orden de las preguntas mueve mucho el resultado.
- Métodos más útiles: comparar turnos tempranos y tardíos de una charla larga, y marcar frase por frase las que se salen del personaje.
- Hay un trabajo con adaptadores LoRA de rasgos en Gemma 2 de 2B que mide estabilidad con pruebas generales.
- Los personajes afinados derivan menos que los definidos solo por prompt.

---

## 11. Verificación de fuentes de los otros documentos

| Afirmación | Estado |
|---|---|
| *Sparks of Weight-Space Programming*, MIT CSAIL, 2 de noviembre de 2026 | **Confirmado.** Es una entrada de blog, sin revisión por pares. Hay varias reproducciones independientes en GitHub, una sin usar un modelo de punta |
| Los "rescates" eran respuestas antes cortadas; la precisión de las que ya terminaban no cambió | **Confirmado** por comentarios independientes |
| Ollama quitó el soporte de adaptadores LoRA en 0.34.1 (septiembre de 2026) | **Confirmado con matiz.** Según un informe de GitHub, se quitó la *creación* de modelos con adaptador; servir los ya creados no se vio afectado |
| Orma (`orma-ai`) | **Sin verificar.** Ver sección 7 |
| Heart: 31 invocaciones por día | Una sola fuente del propio autor. Tomar como orientativo |

---

## 12. Reglas nuevas para el bucle

Para sumar a `AUTONOMIA.md` secciones 2 y 9:

1. **Contexto limpio en cada tic.** Nada se arrastra de un tic al siguiente salvo lo que el código elige pegar.
2. **Detector de repetición.** Antes de buscar, comparar la pregunta con las últimas N por embeddings. Si es casi igual a una anterior, se descarta y se elige otro tema.
3. **Sin instrucciones abiertas.** Ningún prompt del bucle dice "hacé lo que quieras" o "sé proactiva".
4. **Contadores, no autoinformes.** Todo número que aparezca en el diario o en el estado lo calcula el código.
5. **Cuarentena de notas** (sección 6).
6. **Filtro de calidad antes de la novedad** (sección 5).
7. **Mensajes a Fran con filtro.** Antes de dejar un mensaje, un paso de código revisa que no repita uno reciente y que tenga fuente.
8. **Vigilancia automática en lugar de revisión humana.** Fran no la va a revisar todos los días, así que la defensa contra la deriva la hace el código (sección 13.4).

---

## 13. Sin semilla y sin supervisión

Dos decisiones de Fran que cambian el diseño:

- **No se la revisa a diario.** Queda prendida 24/7 y va a su ritmo.
- **Nace sin preferencias.** Nada de semilla de 5 a 10 temas: que se interese sola.

Esta sección es **diseño propio**, apoyado en los casos de arriba.

### 13.1 De dónde salen las tareas si no hay semilla ni lista

Ni una lista fija de tareas ni tareas al azar. Lo que es al azar es **lo que se le cruza**; lo que hace con eso lo genera ella.

Como un bebé: no elige qué hay en la habitación, pero sí en qué se queda mirando.

| Capa | Quién la pone | Qué es |
|---|---|---|
| Exposición | Código, al azar | Un artículo cualquiera de Wikipedia, una portada de noticias, un enlace dentro de lo último que leyó, algo que mencionó Fran |
| Pregunta | El modelo | "¿Qué de esto no entiendo o quiero saber más?" |
| Interés | Código, midiendo | Un tema existe cuando varias preguntas caen cerca entre sí. Nadie lo declara: aparece |
| Objetivo | Código, a partir de preguntas | Una pregunta que vale la pena perseguir, con presupuesto |

Al principio casi todo es exposición al azar. A medida que se forman temas, la mezcla se corre sola: más tiempo siguiendo sus propias preguntas, menos azar. El azar nunca baja a cero.

**Aclaración honesta:** "sin preferencias" no existe del todo. El modelo trae inclinaciones de su entrenamiento (sección 2.7: cada modelo cae en sus propios atractores). Eso es su temperamento. Lo que sí se puede garantizar es que **nosotros** no le elegimos los temas.

Consecuencia sobre `AUTONOMIA.md`: se quita la semilla de intereses (sección 3.2 y sección 12), y la personalidad base se reduce a lo mínimo: nombre, idioma, y las reglas de seguridad.

### 13.2 Los seis retos, uno por uno

**1. Que no repita investigaciones**
- Cada pregunta se guarda con su embedding. Antes de investigar, el código la compara con todas las anteriores: si es casi igual a una ya cerrada, se descarta y se le muestra la respuesta que ya tenía.
- Lo ya leído (URL) no se vuelve a bajar.
- Lo decide el código. El modelo nunca tiene que "acordarse" de qué ya investigó (Vending-Bench).

**2. Que no quede atrapada en ciclos de razonamiento**
- Razonamiento del modelo apagado. Una tarea por llamada.
- Tope de tokens por llamada y tope de tiempo por tic.
- Si la salida repite frases (lo mide el código), se corta y se descarta.
- Contexto limpio en cada tic: un ciclo no puede heredarse.

**3. Que no invente recuerdos ni conocimientos**
- Una nota solo se crea a partir de un texto leído, con su URL.
- **Cita verificable:** cada nota debe incluir una frase textual de la fuente, y el código comprueba que esa frase está en la página. Si no está, la nota no se guarda.
- Cuarentena y procedencia visible (sección 6).
- Las reflexiones se guardan como opinión, nunca como hecho.
- Recordar algo de Fran solo es posible si existe el episodio guardado. El prompt pide decir "no me acuerdo" cuando la búsqueda no trae nada.

**4. Que no genere objetivos absurdos**
- Un objetivo solo puede ser una pregunta respondible buscando y leyendo. No hay objetivos de "hacer", "conseguir" ni "contactar".
- Tiene que venir de algo leído: lleva enlace a la nota que lo originó.
- Todo objetivo nace con presupuesto. Uno absurdo cuesta, como mucho, ese presupuesto.

**5. Que sepa cuándo una investigación está terminada**

Lo decide el código, con tres condiciones de cierre:

| Cierre | Condición |
|---|---|
| Respondida | Hay una respuesta escrita apoyada en al menos dos fuentes |
| Agotada | Las últimas dos lecturas no aportaron nada nuevo (novedad baja contra las notas del mismo objetivo) |
| Sin presupuesto | Se alcanzó el máximo de lecturas (por ejemplo 5) |

Al cerrar, escribe un resumen final. En los dos últimos casos anota que quedó sin responder: eso también es un resultado.

**6. Que pueda retomar trabajos después de horas o días**

Una tabla de objetivos con todo lo necesario para continuar sin recordar nada:

| Campo | Contenido |
|---|---|
| Pregunta | Qué quiere saber |
| Estado | abierta, en pausa, cerrada |
| Lo que sabe hasta ahora | Resumen corto, se reescribe en cada paso |
| Próximo paso | Qué buscar a continuación |
| Gastado | Lecturas usadas del presupuesto |
| Última vez | Fecha |

Cada tic arranca leyendo una fila, no recordando. Da igual si pasaron diez minutos o diez días.

### 13.3 Prioridades

Cada tic, el código puntúa los objetivos abiertos y elige uno por sorteo ponderado:

- Sube: tema con peso alto, objetivo cerca de cerrarse, Fran preguntó por eso.
- Baja: muchas lecturas sin avance, trabajado hace muy poco (para alternar).
- Tope de objetivos abiertos a la vez (por ejemplo 5). Para abrir uno nuevo hay que cerrar o abandonar otro.

### 13.4 Vigilancia automática

Todos los casos de la sección 2 derivaron, y la única defensa probada fue que alguien mirara desde afuera. Si nadie mira, tiene que mirar el código. Mide cosas contables, sin preguntarle nada al modelo, y **actúa solo**:

| Medida | Si se pasa del umbral |
|---|---|
| Pocos temas distintos en la semana | Sube la proporción de exposición al azar |
| Muchas preguntas descartadas por repetidas | Se fuerza cambio de tema |
| Muchas notas rechazadas por cita no encontrada | Se pausa la creación de notas y queda un aviso |
| Las reflexiones se parecen cada vez más entre sí | Se pausan las reflexiones unos días |
| Muchos bloqueos de búsqueda | Baja el ritmo de búsquedas |
| Disco o base por encima del tope | Se archivan episodios viejos |

Todo queda en un archivo de salud que Fran puede mirar cuando quiera, sin obligación.

### 13.5 El reentrenamiento sin supervisión

Es la única pieza que puede romperla de forma permanente sin que nadie lo vea. Si va a correr sola:

- Solo con charlas reales con Fran (sección 6). Si esa semana no hubo suficientes, no se entrena.
- Examen hecho por código, sin opinión del modelo (sección 3).
- Vuelta atrás automática si el adaptador nuevo rinde peor.
- Se guarda siempre el modelo base intacto.

Recomendación: dejarla desactivada los primeros meses. El resto del sistema ya da continuidad, intereses y memoria sin tocar los pesos.

---

## 14. Qué sigue sin respuesta

- Cómo se comporta un modelo de 0.8B a 2B corriendo solo durante semanas. No hay casos publicados.
- Qué tan mal puntúa importancia un modelo chico.
- Si los vectores de control funcionan en 0.8B a 4 bits sin romper la coherencia.
- Dónde poner los límites de la campana de novedad.
- Si Orma existe tal como se lo describe.

Las cuatro primeras solo se responden midiendo en el i5.

---

## 15. Fuentes

**Casos de larga duración**
- Vending-Bench (paper): https://arxiv.org/abs/2502.15840
- Project Vend (informe de Anthropic): https://red.anthropic.com/2025/project-vend/index.html
- Project Vend (nota de prensa): https://techcrunch.com/2025/06/28/anthropics-claude-ai-became-a-terrible-business-owner-in-experiment-that-got-weird
- AI Village, qué aprendimos en 2025: https://aivillageblog.substack.com/p/what-we-learned-2025
- AI Village, cómo funciona: https://theaidigest.org/village/blog/how-the-ai-village-works
- Boucle, una semana de bucle autónomo: https://blog.boucle.sh/posts/what-actually-happens/
- OpenClaw, latido desbocado: https://suzuki-shoten.pages.dev/blog/openclaw-part3-heartbeat-runaway
- Agents of Chaos (paper): https://arxiv.org/abs/2602.20021
- Estados atractores en conversaciones (paper): https://arxiv.org/abs/2606.30571
- Prevención de bucles infinitos: https://agentopsweekly.com/posts/preventing-infinite-loops-in-llm-planning-agents

**Proyectos parecidos**
- companion-emergence: https://github.com/hanamorix/companion-emergence
- Lista de compañeras de código abierto: https://github.com/DasterProkio/awesome-ai-companion
- LocalGPT: https://news.ycombinator.com/item?id=46930391
- replicantlife: https://github.com/jtoy/replicantlife

**Autoevaluación**
- Espejismo de progreso en bucles de agentes (paper): https://arxiv.org/abs/2607.25152

**Importancia y memoria**
- Learn to Memorize (paper): https://arxiv.org/pdf/2508.16629
- Decaimiento y consolidación (blog): https://typegraph.ai/blog/agent-memory-time-decay-consolidation
- Seguir la experiencia (paper): https://arxiv.org/abs/2505.16067
- HaluMem (paper): https://huggingface.co/papers/2511.03506
- Evaluación independiente de memoria (paper): https://arxiv.org/html/2603.04814
- Estado de la memoria de agentes en 2026 (blog): https://dev.to/vektor_memory_43f51a32376/the-state-of-ai-agent-memory-in-2026-what-the-research-actually-shows-3aja
- Ormah: https://pypi.org/project/ormah/

**Curiosidad**
- Curiosidad y televisores con ruido (paper): https://arxiv.org/abs/2102.04399
- OMNI (paper): https://arxiv.org/abs/2306.01711
- Sampling Is Not Curiosity (NeurIPS 2026): https://neurips.cc/virtual/2026/poster/140072
- Computational Curiosity (borrador de libro): https://arxiv.org/pdf/1502.04780
- Curva de Wundt y sorpresa (paper): https://www.frontiersin.org/journals/psychology/articles/10.3389/fpsyg.2025.1438080/full

**Envenenamiento**
- MemoryGraft (paper): https://arxiv.org/abs/2512.16962
- Envenenamiento de memoria, guía (blog): https://www.akto.io/blog/memory-poisoning-ai-agents
- Ataque con pocos ejemplos envenenados: https://www.helpnetsecurity.com/2026/03/26/llm-backdoor-attack-research/
- Seguridad de LoRA y ajuste de prompts (paper): https://arxiv.org/pdf/2310.11397

**Vectores de control**
- Persona vectors (Anthropic): https://www.anthropic.com/research/persona-vectors
- Persona vectors (paper): https://arxiv.org/abs/2507.21509
- repeng: https://github.com/vgel/repeng
- Representation engineering (blog del autor de repeng): https://vgel.me/posts/representation-engineering/
- Vectores de control y razonamiento en modelos chicos (paper): https://arxiv.org/html/2504.19483v1

**Modelos chicos y formato**
- Dos llamadas contra cinco agentes (paper): https://arxiv.org/pdf/2607.26922
- Menos es más, validación de esquema (paper): https://arxiv.org/pdf/2604.21746
- Llamadas a herramientas en modelos de menos de 2B en CPU (paper): https://arxiv.org/pdf/2609.07370
- Agente con modelo de 2B (blog): https://dev.to/mukundakatta/gemma4-safe-agent-making-2b-parameters-production-usable-dl9

**Personalidad**
- Inestabilidad de las mediciones de personalidad (paper): https://arxiv.org/html/2508.04826v1
- Evaluación frase por frase del personaje (paper): https://arxiv.org/abs/2506.19352
- Adaptadores LoRA de rasgos en modelos chicos (paper): https://arxiv.org/html/2509.04794v1

**Temas menores**
- Límite de `ddgs`: https://pypi.org/project/duckduckgo_search
- SQLite, modo WAL: https://www.sqlite.org/wal.html

**Verificación**
- Sparks of Weight-Space Programming: https://rikiyat.github.io/blog/weight-space-programming/
- Reproducción independiente: https://github.com/kyle-chalmers/weight-space-programming
- Ollama y adaptadores LoRA (informe): https://github.com/generative-computing/mellea/issues/1651
