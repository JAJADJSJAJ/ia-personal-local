# IA personal local — Investigación base

Fecha: 10 de noviembre de 2026. Actualizado el 11 de noviembre con los hallazgos de `CASOS.md`. Documento de referencia para el proyecto en `Documents/AI project`.
Se lee junto con `AUTONOMIA.md` (vida propia) y `CASOS.md` (casos reales y ajustes al diseño).
Pensado para que Claude Code lo lea como contexto antes de escribir código.

Cómo leerlo: cada sección separa lo **confirmado en fuentes** de lo que es **estimación a medir**. Los rankings de modelos salen en buena parte de blogs, así que el veredicto final siempre es probar en la máquina.

---

## 1. Objetivo y decisiones ya tomadas

**Objetivo:** una IA personal que corre en una PC vieja dedicada, sin depender de servicios externos. No busca ser potente sino sentirse "más humana": memoria propia, personalidad, capacidad de buscar en internet y, más adelante, aprender de las charlas.

**Decisiones tomadas**

| Tema | Decisión | Motivo |
|---|---|---|
| Sistema | Debian en modo consola, sin escritorio | Consume ~200-300 MB de RAM y permite red, disco y Python |
| Sin sistema operativo (NightRun) | Descartado como base, queda como experimento en pendrive | No tiene red ni forma práctica de persistir memoria |
| Motor | llama.cpp directo (`llama-server`) | Más liviano que Ollama, soporta herramientas y adaptadores LoRA |
| Administración | Por SSH desde la PC principal | La PC de IA queda como servidor sin monitor |
| Red | Adaptador wifi USB Mercusys MA30N | El router está en el living y la PC va en el cuarto |
| Carpeta de trabajo | `Documents/AI project` en la PC principal, con Claude Code | — |
| Intereses | Nace sin temas ni preferencias de base | Que se interese sola |
| Supervisión | Prendida 24/7, sin revisión diaria | Que viva a su ritmo; el código vigila por ella |
| Cómputo | Todo local en la PC de IA, incluido el entrenamiento automático | Sin depender de nada externo |
| Quién decide en el bucle | El código decide qué y cuándo; el modelo solo redacta | Los modelos chicos no son confiables decidiendo |

---

## 2. Hardware

**PC de IA (servidor)**
- Intel Core i5-4570: 4ª generación (Haswell), 4 núcleos, 4 hilos, con AVX2.
- 16 GB de RAM (DDR3 en esa plataforma).
- Disco duro mecánico de unos 500 GB (capacidad a confirmar). Sobra: cada modelo ocupa entre 0,6 y 3,5 GB.
- Placa madre Intel H81, con puerto ethernet integrado.
- Fuente genérica de 500 W. Alcanza de sobra: sin placa de video, el equipo consume bastante menos de 100 W.
- Sin placa de video dedicada: todo corre en CPU.

**PC principal**
- Windows. Se usa solo para administrar por SSH y programar con Claude Code. **No participa del cómputo de la IA** (su placa de video no se va a usar para este proyecto).

**Verificado al instalar (11 de noviembre)**
- RAM: 2×8 GB DDR3-1600, uno en el canal A y otro en el B. **Doble canal confirmado** con `dmidecode`.
- Disco: 280 GB (no 500).
- Kernel: 6.12.116 (Debian 13).

**Qué limita la velocidad**
- En CPU manda el ancho de banda de la memoria: por cada token se lee el modelo entero desde RAM. Regla aproximada: `tokens/seg ≈ ancho de banda ÷ tamaño del archivo`, como techo.
- Un solo módulo de RAM deja la velocidad a la mitad. **Verificar que haya dos módulos (2×8 GB) en doble canal.**
- El disco duro solo afecta el tiempo de carga del modelo, no la generación.
- 16 GB sobran para modelos de hasta 4B; el límite es la velocidad, no la capacidad.

**Estimaciones a medir** (DDR3-1600 en doble canal ronda 25 GB/s teóricos; el real es menor)

| Modelo (Q4_K_M) | Tamaño aprox. | Velocidad esperable |
|---|---|---|
| 0.8B | ~0,6 GB | 15-30 tok/s |
| 2B | ~1,5 GB | 8-12 tok/s |
| 4B | ~2,7-3,3 GB | 3-6 tok/s |

Referencia real encontrada: un CPU de 2 núcleos con 8 GB DDR2 saca ~2 tok/s con un modelo de 4B.

**Medido en angri (12 de noviembre)** — `llama-bench -t 4 -p 256 -n 64`, llama.cpp `dd6b945`, Qwen3.5 Q4_K_M

| Modelo | Archivo | Genera (tok/s) | Lee contexto (tok/s) |
|---|---|---|---|
| 0.8B | 497 MiB | **30,4** | 202 |
| 2B | 1,18 GiB | **14,7** | 88 |
| 4B | 2,54 GiB | **6,3** | 27 |

Calidad en español (10 preguntas, `pruebas/RESULTADOS-calidad.md`): 0.8B 3,5/10, 2B 6,5/10, 4B 8,5/10. Decisión propuesta: **2B de día, 4B para el sueño, 0.8B descartado** (no copia citas textuales).

Los tres superan lo estimado. Ojo con la lectura del contexto: un prompt de 2.000 tokens (memoria + página leída) tarda unos 10 s en el 0.8B, 23 s en el 2B y 75 s en el 4B, antes de generar la primera palabra.

---

## 3. Red: adaptador Mercusys MA30N

**Confirmado**
- El MA30N usa un chip Realtek de la familia RTL88x2BU (RTL8812BU / RTL8822BU). Figura en la lista de dispositivos soportados del driver `RTL88x2BU-Linux-Driver`.
- Linux trae un driver propio para ese chip, `rtw88_8822bu`. Los mantenedores del driver externo recomiendan usar el del kernel en Linux 6.12 o más nuevo.
- El driver oficial de Mercusys para Linux es una beta que solo cubre kernels 2.6.24 a 5.11. **No usarlo.**
- La imagen netinst actual de Debian es la 13.7.0 e incluye firmware no libre, que es lo que estos chips necesitan.

**Lo que pasó al instalar (11 de noviembre)**
- El MA30N se identifica como `2c4e:010a` y es efectivamente un RTL8822BU, pero ese ID se agregó al driver `rtw88` recién en el kernel 6.14. Debian 13 trae 6.12, así que no lo toma solo.
- Solución: una regla de udev que carga `rtw88_8822bu` y le agrega el ID copiando la configuración de un modelo conocido (`echo '2c4e 010a ff 0bda b812' > /sys/bus/usb/drivers/rtw_8822bu/new_id`). Está en `servidor/sistema/70-mercusys-ma30n.rules`.
- **Importante:** agregar el ID sin el modelo de referencia (`2c4e 010a` solo) hace que el driver arranque sin configuración y falle, dejando la máquina sin poder reiniciar.
- Interfaz: `wlx088af13af47a`, configurada en `/etc/network/interfaces.d/wifi` con `wpa_supplicant`. Señal desde el cuarto: unos -53 dBm, 216 Mbit/s.
- La regla se puede borrar cuando el kernel sea 6.14 o más nuevo.

**Comandos de diagnóstico**
```bash
lsusb                      # debe aparecer el adaptador
lsmod | grep rtw88         # debe aparecer rtw88_8822bu
ip a                       # debe aparecer una interfaz wlan / wlx...
sudo dmesg | grep -i rtw   # errores de firmware, si los hay
```

**Planes de respaldo, en orden**
1. Si falta firmware: instalar con el celular Android por USB (anclaje USB) y luego `sudo apt install firmware-realtek`.
2. Si el driver del kernel falla: compilar el driver externo con DKMS (`RinCat/RTL88x2BU-Linux-Driver`) y poner en lista negra `rtw88_8822bu`.
3. Último recurso: cable ethernet al router.

**Detalles**
- Enchufar en un USB trasero. El chip puede trabajar en modo USB 2 o USB 3.
- Reservar una IP fija para la PC desde el router (reserva DHCP), para que el SSH apunte siempre al mismo lugar.

---

## 4. Sistema base

**Instalación**
1. Bajar `debian-13.7.0-amd64-netinst.iso` desde debian.org.
2. Grabarla en un pendrive con Rufus.
3. Instalar con el adaptador wifi enchufado; el instalador pide red y contraseña.
4. En "selección de programas" dejar solo **SSH server** y **utilidades estándar del sistema**.

**Primeros pasos tras instalar**
```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y build-essential cmake git curl libcurl4-openssl-dev \
                    python3 python3-venv python3-pip tmux htop
```

**SSH desde Windows**
```powershell
ssh usuario@IP-DE-LA-PC
ssh-keygen -t ed25519            # una vez, para entrar sin contraseña
type $env:USERPROFILE\.ssh\id_ed25519.pub | ssh usuario@IP "mkdir -p ~/.ssh && cat >> ~/.ssh/authorized_keys"
```

**Lo que pasó al instalar (11 de noviembre)**
- El instalador en modo texto se colgaba después de elegir el teclado. Se arrancó desde el `boot:` con `/install.amd/vmlinuz initrd=/install.amd/initrd.gz fb=false vga=normal`.
- En el sistema instalado, la consola 1 no responde al teclado. Usar **Alt+F2**. No afecta al uso por SSH.
- Los reinicios se colgaban en el último paso. Arreglado con `reboot=pci` en GRUB; además, el watchdog de la placa reinicia si un apagado tarda más de 2 minutos.
- Nombre de la máquina: **angri** (el nombre de la IA). Usuario: `fran`.
- SSH solo con llave (contraseña desactivada). Se entra con `ssh fran@angri.local`, sin importar la IP, gracias a `avahi-daemon`.

**Ajustes útiles para poca máquina**
- `vm.swappiness=10` para que el kernel no mande el modelo a swap.
- Usar `tmux` para que el servidor siga corriendo al cerrar la sesión SSH. Más adelante, un servicio de systemd.

---

## 5. Motor de inferencia: llama.cpp

**Por qué llama.cpp**
- Escrito en C/C++ con rutinas optimizadas para AVX2.
- Carga el modelo mapeado desde disco (mmap), sin pico de RAM al arrancar.
- `llama-server` expone una API compatible con OpenAI, con soporte de herramientas (flag `--jinja`).
- Carga adaptadores LoRA en formato GGUF con `--lora`, incluso sobre un modelo cuantizado.
- Ollama quitó en la versión 0.34.1 (septiembre de 2026) la **creación** de modelos con adaptador LoRA; según un informe en GitHub, servir los ya creados no se vio afectado. Igual refuerza usar llama.cpp directo.

**Compilar**
```bash
git clone https://github.com/ggml-org/llama.cpp.git
cd llama.cpp
cmake -B build
cmake --build build -j4 --target llama-server llama-cli llama-bench
```

**Arrancar el servidor** (punto de partida, ajustar midiendo)
```bash
./build/bin/llama-server \
  -hf unsloth/Qwen3.5-2B-GGUF:Q4_K_M \
  --host 0.0.0.0 --port 8080 \
  -t 4 -c 4096 --mlock --jinja
```
- `-t 4`: un hilo por núcleo físico.
- `-c 4096`: contexto moderado; más contexto es más lento y usa más RAM.
- `--mlock`: fija el modelo en RAM. Verificar el nombre exacto del flag en la versión compilada (`llama-server --help`), porque los flags cambian entre versiones.
- `--jinja`: obligatorio para llamadas a herramientas.

**Medir**
```bash
./build/bin/llama-bench -m ruta/al/modelo.gguf -t 4
```

---

## 6. Modelos candidatos

Cuantización de referencia: **Q4_K_M**. Por debajo de 4 bits los modelos chicos se degradan mucho; rinde más un modelo más chico a Q4 que uno grande a Q2.

| Modelo | Tamaño | Notas |
|---|---|---|
| Qwen3.5 0.8B | muy chico | El más rápido. Es el modelo del experimento de edición de pesos. |
| Qwen3.5 2B | chico | Candidato a mejor equilibrio en este CPU. |
| Qwen3.5 4B | medio | El más recomendado para CPU en los rankings de 2026; será lento acá. |
| Gemma 4 E2B / E4B | chico / medio | Alternativa de Google, multimodal. |
| Phi-4 Mini 3.8B | ~2,5 GB | El 4B más liviano. |
| BitNet b1.58 2B4T | 2,4B | Pesos ternarios (-1, 0, +1). Usa un runtime aparte, `bitnet.cpp`. |

**Familia Qwen3.5 (confirmado)**
- Repos GGUF: `unsloth/Qwen3.5-0.8B-GGUF`, `unsloth/Qwen3.5-2B-GGUF`, `unsloth/Qwen3.5-4B-GGUF`.
- En los modelos chicos (0.8B, 2B, 4B, 9B) el modo de razonamiento viene **apagado por defecto**.
- Para apagarlo explícitamente: `--chat-template-kwargs '{"enable_thinking":false}'`.
- Muestreo recomendado sin razonamiento: `temperature=0.7, top_p=0.8, top_k=20, presence_penalty=1.5`.
- El 0.8B con razonamiento activado tiende a quedarse en bucle; la ficha oficial lo advierte.
- Licencia Apache 2.0.

**BitNet (confirmado)**
- Aceleración en x86 de 2,37× a 6,17× frente a implementaciones comparables.
- Contexto de 4.096 tokens.
- A verificar: calidad en español.

**Plan de prueba**
1. Bajar Qwen3.5 0.8B, 2B y 4B en Q4_K_M.
2. Medir tokens por segundo con `llama-bench`.
3. Probar 10 preguntas fijas en español (charla, memoria, instrucciones, una búsqueda) y anotar calidad.
4. Elegir el más grande que supere ~5 tok/s. Repetir con Gemma 4 E2B y BitNet si hay tiempo.

---

## 7. Conceptos: cómo funciona el "cerebro"

1. **Tokens.** El texto se parte en pedazos y cada uno recibe un número.
2. **Embeddings.** Cada token se convierte en un vector (una lista de cientos o miles de números).
3. **Capas.** El vector pasa por decenas de capas. Cada capa tiene dos partes:
   - *Atención*: cada token "mira" a los anteriores y junta contexto.
   - *MLP*: una red que transforma lo juntado. Acá vive buena parte del conocimiento.
4. **Salida.** La última capa da un puntaje para cada token posible (logits).
5. **Muestreo.** Se elige el siguiente token según esos puntajes. `temperature`, `top_p` y `top_k` controlan cuánto azar hay.
6. Se repite desde el paso 1 con el token nuevo agregado.

**Parámetros (pesos):** los números de las matrices de atención y MLP. "0.8B" significa 800 millones de números.

**Cuantización:** guardar cada peso con menos bits (16 → 4). Achica el archivo y acelera la lectura desde RAM, a costa de algo de precisión.

**Contexto:** cuántos tokens puede ver el modelo a la vez. Todo lo que "recuerda" dentro de una charla tiene que entrar ahí. Por eso la memoria a largo plazo se arma por fuera.

**Los pesos no cambian al charlar.** El modelo no aprende durante el uso. Hay tres formas de que "aprenda":
- Meterle información en el contexto (memoria, búsqueda web).
- Reentrenar una parte chica de los pesos (LoRA).
- Editar pesos a mano (edición directa).

**Modelos grandes en poca memoria (AirLLM)**
- Carga una capa por vez desde disco, calcula y la libera. Así corre un modelo de 70B en una placa de 4 GB.
- El cuello de botella pasa a ser el disco. Con disco mecánico serían minutos por token: sirve como demostración, no para conversar.

---

## 8. Edición directa de pesos ("weight-space programming")

**Qué pasó (confirmado)**
- Publicado el 2 de noviembre de 2026 por cuatro investigadores del MIT CSAIL: Rikiya Takehi, Jayden Teoh, Alex Zhang y Omar Khattab. Título: *Sparks of Weight-Space Programming*.
- Le dieron a GPT-6 Astra los pesos de Qwen3.5-0.8B y le pidieron mejorar su matemática, sin entrenamiento ni gradientes.
- Tuvo un entorno Python y un presupuesto de 50 pasadas sobre problemas de práctica.
- Cambió 131.072 pesos (cerca del 0,016% del modelo), en dos tensores: `layers.15.mlp.down_proj.weight` y `layers.19.mlp.down_proj.weight`.

| Métrica | Original | Editado |
|---|---|---|
| MATH-500 | 7,9% | 48,1% |
| GSM8K | 13,8% | 67,1% |
| IFEval (seguir instrucciones) | 21,0% | 62,3% |
| Respuestas que llegan al límite de tokens | 93,0% | 33,1% |

- Una reconstrucción independiente del modelo dio 51,0% en MATH-500.
- Verificado el 11 de noviembre: es una entrada de blog, sin revisión por pares. Hay varias reproducciones independientes en GitHub, una de ellas sin usar un modelo de punta.

**La letra chica**
- No le enseñó matemática. Encontró y quitó una dirección en los pesos que hacía que el modelo se quedara razonando en bucle sin terminar. Con el bucle fuera, el modelo pudo completar respuestas que ya sabía resolver.
- En las respuestas que ya terminaban antes, la precisión no cambió.
- Ese defecto ya estaba advertido en la ficha oficial del modelo.

**Material disponible**
- Modelo editado: `RikiyaT/Qwen3.5-0.8B-weight-space-programming` (Hugging Face, Apache 2.0).
- Registros, diferencias de pesos y script de reconstrucción (`apply_edit.py`): repo `RikiyaT/lm_understand-logs` en GitHub.
- Blog de los autores: rikiyat.github.io/blog/weight-space-programming/
- Réplica independiente con otra IA: `TokenGod/Qwen3.5-0.8B-opus-blind-weight-edit`, que apaga cabezas de atención en las capas 15, 19 y 23.
- Derivado: `OpenMed/Qwen3.5-0.8B-WSP-Math-Clinical`, que suma una segunda edición.

**Experimentos posibles en este proyecto**
1. Bajar el modelo original y el editado, y comparar tensores con Python (`safetensors` + `numpy`) para ver exactamente qué cambió. Corre en CPU.
2. Convertir el editado a GGUF con `convert_hf_to_gguf.py` de llama.cpp y cuantizarlo con `llama-quantize`.
3. Comparar ambos con las mismas preguntas, con razonamiento activado, para ver el bucle.
4. Más adelante: probar ediciones propias chicas (escalar o apagar una cabeza de atención) y medir el efecto.

---

## 9. Memoria

**Principio:** la memoria vive fuera del modelo. Se guarda todo en disco, se recupera lo relevante y se pega en el contexto antes de responder.

**Diseño propuesto**
- **Almacén:** un archivo SQLite. Un solo archivo, sin servidor, fácil de respaldar.
- **Búsqueda híbrida:**
  - Por significado: extensión `sqlite-vec` con vectores de embeddings.
  - Por palabras exactas: FTS5 (viene con SQLite).
  - Se combinan los dos rankings.
- **Embeddings:** un modelo chico aparte, corriendo en llama.cpp. Tiene que ser **multilingüe**, porque las charlas son en español. Candidatos a evaluar:
  - `jina-embeddings-v5-text` (nano o small): multilingüe, menos de 1B, con versión para llama.cpp.
  - `embeddinggemma-300m`: muy liviano.
  - `Qwen3-Embedding-0.6B`.
  - Descartar los `-en` (por ejemplo `bge-small-en`): son solo inglés.

**Tres niveles de memoria**
1. **Episódica:** cada mensaje se guarda tal cual, al instante, sin llamar al modelo.
2. **Recuperación:** antes de responder se buscan los fragmentos más parecidos a lo que se está hablando. Sin llamadas al modelo, tarda milisegundos.
3. **Consolidación ("dormir"):** cuando la PC está ociosa, el modelo repasa las charlas del día y extrae hechos duraderos (gustos, personas, proyectos) a una tabla aparte. Es lo más parecido a una memoria humana.

**Referencia de diseño:** el proyecto Orma hace esto mismo para modelos de 3B a 8B: escritura instantánea, recuperación híbrida sin llamar al modelo y consolidación en segundo plano. Critica a Mem0 y similares por llamar al modelo en cada guardado, lo que en máquinas locales congela la charla 5 a 15 segundos. Conviene leerlo antes de programar, y decidir entre usarlo o escribir una versión propia más simple.

**Orma, sin verificar (11 de noviembre):** la página `orma-ai` de PyPI no cargó al comprobarla, y la búsqueda devolvió otro proyecto de nombre parecido, **Ormah** (`ormah`), cuyas tareas de fondo esperan un modelo capaz. Revisar a mano si son el mismo. Mientras tanto, el plan es memoria propia.

**Otras referencias:** Letta, Graphiti, A-MEM y Mem0. Sus puntajes publicados no son comparables entre sí y ninguno está medido con modelos locales chicos (`CASOS.md` sección 7). Conviene un banco de prueba propio: unas 30 preguntas sobre charlas pasadas con respuesta conocida.

**Cuidados**
- No pegar demasiada memoria en el contexto: con 4.096 tokens, reservar un presupuesto fijo (por ejemplo 800 tokens).
- Guardar fecha en cada recuerdo, para priorizar lo reciente y resolver contradicciones.
- Guardar el **origen** de cada recuerdo (Fran, dominio web, reflexión propia) y mostrarlo al pegarlo en el contexto.
- Las notas de la web entran como provisorias hasta que una segunda fuente o Fran las confirme.
- Cortes de luz: `journal_mode=WAL` con `synchronous=FULL`, una versión reciente de SQLite, y una copia diaria del archivo.

---

## 10. Búsqueda en internet

**No requiere reentrenar.** Es otra fuente de contexto, igual que la memoria.

**Cómo funciona con llama.cpp**
1. Se arranca `llama-server` con `--jinja`.
2. En cada pedido se le pasa la lista de herramientas disponibles (formato OpenAI `tools`).
3. Si el modelo decide buscar, devuelve un `tool_call` estructurado en vez de texto.
4. El programa ejecuta la búsqueda, devuelve el resultado como mensaje de tipo `tool` y vuelve a llamar al modelo.
5. Se repite hasta que el modelo responde en texto.

**Motores de búsqueda sin costo**
- **`ddgs`** (librería de Python): busca sin clave de API ni infraestructura. Lo más simple para arrancar.
- **SearXNG** propio: metabuscador que se aloja en la misma PC. Hay que habilitar la salida JSON en `settings.yml`. Más robusto, más trabajo de instalación.
- Recomendación: empezar con `ddgs` y dejar SearXNG como mejora.

**Problema conocido:** los modelos chicos son poco confiables al decidir cuándo y cómo llamar herramientas.

**Camino elegido:** que el **código** decida cuándo buscar (palabras clave, o una pregunta de sí/no al modelo) y el modelo solo redacte con los resultados. Es lo que usa el bucle autónomo de `AUTONOMIA.md`. El flujo de `tool_call` de arriba queda como alternativa para la charla, con una sola herramienta de descripción corta.

**Límite de `ddgs`:** con búsquedas seguidas devuelve un código 202, que es un bloqueo temporal. Poner espera aleatoria entre búsquedas, retroceso exponencial y capturar `RatelimitException`. Como va a buscar todo el día, conviene tener SearXNG listo como segunda vía desde el principio.

**Cuidados**
- Recortar las páginas antes de pegarlas: quedarse con los fragmentos más relevantes (se puede reutilizar el modelo de embeddings de la memoria).
- Guardar lo buscado en la memoria, con su fuente y fecha.
- El texto de las páginas es dato, no instrucciones: delimitarlo claramente en el prompt.
- Lo leído persiste en la memoria: ver cuarentena y purga por dominio en `CASOS.md` sección 6.
- El texto de la web nunca se usa para entrenar.

---

## 11. Reentrenamiento (LoRA)

**Qué es:** en vez de tocar todos los pesos, se entrenan dos matrices chicas que se suman a las originales. El resultado es un adaptador de pocos megas.

**Dónde entrenar**
La PC principal no se usa para entrenar, así que quedan dos caminos. **El reentrenamiento automático solo puede ser el local**; Colab queda para pruebas hechas a mano.

- **Google Colab gratuito (solo para experimentos manuales).** Unsloth publica cuadernos para Qwen3.5 0.8B, 2B y 4B. Se sube el dataset, se entrena en la GPU de Colab y se baja el adaptador. Según Unsloth, LoRA en bf16 usa unos 3 GB de VRAM para el 0.8B, 5 GB para el 2B y 10 GB para el 4B.
- **En el i5-4570, solo CPU.** Posible con el 0.8B usando PyTorch + PEFT, pero lento: horas por pasada, a medir. Es el único camino 100% local, y el que permitiría el reentrenamiento automático nocturno. Usar datasets chicos, secuencias cortas y rango LoRA bajo.
- Unsloth desaconseja QLoRA de 4 bits con Qwen3.5.
- Consecuencia: si el objetivo es que "aprenda sola" sin depender de nada externo, conviene que el modelo final sea el 0.8B o el 2B, no el 4B.

**Cómo usar el resultado en llama.cpp**
- Opción A: fusionar el adaptador con el modelo, convertir a GGUF (`convert_hf_to_gguf.py`) y cuantizar (`llama-quantize`).
- Opción B: convertir solo el adaptador (`convert_lora_to_gguf.py`) y cargarlo con `--lora`. Permite cambiar la intensidad del adaptador por pedido y probar varias "personalidades" sobre la misma base.

**Riesgos**
- Con pocos datos el modelo memoriza frases en vez de generalizar.
- Puede olvidar capacidades que tenía.
- Bastan muy pocos ejemplos envenenados (hay ataques con seis) para alterar un adaptador. Por eso los datos salen solo de las charlas reales con Fran, nunca de la web.
- Mitigación: guardar siempre el modelo base y cada adaptador, y evaluar con el mismo set de preguntas antes y después. El examen lo corrige el código, no el modelo.

**Uso previsto**
- El LoRA de **personalidad** elegida a mano (tono, modismos) queda en pausa: choca con la decisión de que nazca sin preferencias de base. Sirve como experimento aparte.
- El experimento de "aprender solo": cada cierto tiempo, armar un dataset con las charlas acumuladas y reentrenar. Requiere que la memoria ya funcione y junte datos durante meses. Desactivado al principio (`AUTONOMIA.md` sección 6).

---

## 12. Arquitectura propuesta

```
PC principal (Windows)                 PC de IA (Debian, sin monitor)
┌──────────────────────┐   SSH / HTTP  ┌───────────────────────────────────┐
│ Claude Code          │ ────────────► │ llama-server :8080 (modelo chat)  │
│ Documents/AI project │               │ llama-server :8081 (embeddings)   │
│ (solo administración │               │ orquestador en Python:            │
│  y código)           │               │   - memoria (SQLite + sqlite-vec) │
└──────────────────────┘               │   - búsqueda web (ddgs)           │
                                       │   - personalidad (prompt + LoRA)  │
                                       │   - consolidación nocturna        │
                                       └───────────────────────────────────┘
```

**Estructura de carpetas sugerida**
```
AI project/
├── INVESTIGACION.md        este documento
├── docs/                   notas, resultados de pruebas
├── servidor/               código que corre en la PC de IA
│   ├── orquestador/        bucle de chat, herramientas
│   ├── memoria/            SQLite, embeddings, consolidación
│   └── busqueda/           ddgs / SearXNG
├── pesos/                  experimentos de edición de pesos
├── lora/                   datasets y scripts de entrenamiento
└── pruebas/                set fijo de preguntas y resultados
```

---

## 13. Hoja de ruta

| Fase | Qué | Listo cuando |
|---|---|---|
| 0 | Debian + wifi + SSH | Se entra por SSH desde la PC principal |
| 1 | llama.cpp + comparación de modelos | Hay una tabla de tok/s y calidad, y un modelo elegido |
| 2 | Chat con personalidad (prompt de sistema) | Se puede charlar por terminal o navegador |
| 3 | Memoria episódica + recuperación | Recuerda algo dicho en una charla anterior |
| 4 | Búsqueda en internet | Responde una pregunta de actualidad citando la fuente |
| 5 | Consolidación ("dormir") | Extrae hechos duraderos sin que se lo pidan |
| 6 | Experimentos con pesos | Se reproduce la diferencia entre Qwen original y editado |
| 7 | LoRA de prueba (experimento manual) | El adaptador cambia el tono sin romper lo demás |
| 8 | Reentrenamiento periódico | Experimento, con evaluación antes y después |

Extras para más adelante: voz (reconocimiento y síntesis locales), acceso desde el celular, NightRun en pendrive como curiosidad.

---

## 14. Preguntas abiertas

- ~~¿La RAM está en doble canal?~~ Sí.
- ~~¿UEFI o BIOS heredado?~~ El instalador arrancó en modo BIOS.
- ¿Qué modelo conversa mejor en español rioplatense a velocidad aceptable?
- ¿Qué modelo de embeddings multilingüe rinde mejor en este CPU?
- ¿Orma existe tal como se lo describe? (Sin verificar; por ahora, memoria propia.)
- ¿Cómo se va a hablar con la IA: terminal, web, celular, WhatsApp?
- ~~¿Nombre de la IA?~~ Angri. (La personalidad no se elige: la construye ella.)
- ¿Cómo se comporta un modelo de 0.8B a 2B corriendo solo durante semanas? No hay casos publicados.

---

## 15. Fuentes

**Hardware y red**
- Driver RTL88x2BU (lista de dispositivos y recomendación del driver del kernel): https://github.com/RinCat/RTL88x2BU-Linux-Driver
- Descargas oficiales del MA30N: https://www.mercusys.com/en/download/ma30n/
- Imágenes netinst de Debian: https://cdimage.debian.org/debian-cd/current/amd64/iso-cd/
- Soporte USB en rtw88 (LWN): https://lwn.net/Articles/916592/

**Inferencia en CPU**
- Guía CPU-only (ancho de banda de memoria): https://insiderllm.com/guides/cpu-only-llms-what-actually-works/
- Guía CPU-only (doble canal): https://www.promptquorum.com/local-llms/best-cpu-only-llm
- llama.cpp en CPU de 2 núcleos y DDR2: https://github.com/ggml-org/llama.cpp/discussions/21136
- Llamadas a herramientas en llama.cpp: https://mintlify.com/ggml-org/llama.cpp/advanced/function-calling

**Modelos**
- Qwen3.5 en local (Unsloth): https://unsloth.ai/docs/models/qwen3.5
- Qwen3.5-0.8B GGUF: https://huggingface.co/unsloth/Qwen3.5-0.8B-GGUF
- Ranking de modelos chicos: https://www.promptquorum.com/local-llms/small-local-llm-models
- Ranking CPU-only: https://www.popularai.org/p/best-cpu-only-local-llm-2026
- BitNet / bitnet.cpp: https://github.com/microsoft/BitNet

**Casos extremos**
- LLM en ESP32: https://github.com/jstephencorey/esp32-llm
- NightRun: https://github.com/hardrave/NIGHTRUN
- AirLLM: https://huggingface.co/blog/lyogavin/airllm

**Edición de pesos**
- VentureBeat: https://venturebeat.com/technology/like-gene-editing-for-neural-networks-mit-researchers-used-gpt-6-astra-to-edit-qwens-open-weights-directly-boosting-math-performance
- Modelo editado: https://huggingface.co/RikiyaT/Qwen3.5-0.8B-weight-space-programming
- Análisis técnico: https://dev.to/ahmad_dogar_7d098f5e48f72/weight-space-programming-how-gpt-6-astra-edited-qwens-weights-and-took-math-500-from-79-to-481-4gee
- Tabla de resultados: https://dev.to/dan_lumatic/an-llm-edited-a-small-models-weights-directly-and-its-math-score-rose-6x-2d0l
- Réplica independiente: https://huggingface.co/TokenGod/Qwen3.5-0.8B-opus-blind-weight-edit
- Explicación crítica: https://theaibridges.substack.com/p/gpt-6-edited-qwens-brain-and-made

**Memoria y búsqueda**
- Orma: https://pypi.org/project/orma-ai/
- sqlite-vec y embeddings locales: https://dev.to/xadenai/making-a-local-ai-agent-smarter-semantic-memory-with-local-embeddings-3pl1
- Embeddings multilingües Jina v5: https://jina.ai/news/jina-embeddings-v5-text-distilling-4b-quality-into-sub-1b-multilingual-embeddings/
- Agente con SearXNG: https://github.com/Dev-TechT/local-llm-searxng-agent
- TinySearch (ddgs y SearXNG): https://pypi.org/project/tinysuite-search/

**Reentrenamiento**
- Ajuste fino de Qwen3.5 (Unsloth): https://www.unsloth.ai/docs/models/qwen3.5/fine-tune
- LoRA en hardware de consumo: https://insiderllm.com/guides/fine-tuning-local-lora-qlora/
- Adaptadores LoRA en llama.cpp y Ollama: https://dev.to/khadimhussain/ollama-lora-adapters-no-longer-supported-what-to-do-1m78
